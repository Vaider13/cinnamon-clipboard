import hashlib
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk

from ..i18n import _
from .database import HistoryDatabase
from .settings import SettingsManager
from .x11_file_clipboard import X11FileClipboard


class ClipboardManager:
    """Manages clipboard communication in GTK3 with deduplication, permanent storage, and SQLite integration."""

    def __init__(self):
        self.settings = SettingsManager()
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.x11_file_clipboard = X11FileClipboard()
        self.change_count = 0
        self.max_history = self.settings.get("max_history")

        self._debounce_timer_id = None
        self._last_content_signature = None
        self.is_self_copying = False  # Flag to avoid reinserting items copied from the history

        # Subscribers to notify interface changes in real time
        self._on_history_changed_callbacks = []

        # Permanent data directory for images (alongside the database)
        self.data_media_dir = Path.home() / ".local" / "share" / "cinnamon-clipboard" / "media"
        self.data_media_dir.mkdir(parents=True, exist_ok=True)

        # SQLite database
        self.db = HistoryDatabase()
        self.history = self._load_history_from_db()

    def add_history_listener(self, callback):
        """Register a function to be notified when the history changes."""
        if callback not in self._on_history_changed_callbacks:
            self._on_history_changed_callbacks.append(callback)

    def remove_history_listener(self, callback):
        """Remove a subscribed function from change notifications."""
        if callback in self._on_history_changed_callbacks:
            self._on_history_changed_callbacks.remove(callback)

    def _notify_history_changed(self):
        """Notify all subscribers on the GTK main thread."""
        for cb in list(self._on_history_changed_callbacks):
            GLib.idle_add(cb)

    def _load_history_from_db(self):
        """Load the history saved in SQLite and rebuild the objects so the interface can render them correctly."""
        raw_items = self.db.load_history(limit=self.max_history)
        processed_items = []

        for item in raw_items:
            item_type = item.get("type")

            # 1. IMAGES
            if item_type == "image":
                data_path = item.get("data_path")
                if data_path and os.path.exists(data_path):
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file(data_path)
                        item["pixbuf"] = self._scale_pixbuf(pixbuf, target_size=140)
                    except Exception as e:
                        item["pixbuf"] = None

            # 2. FILES
            elif item_type == "files":
                if not item.get("preview") and isinstance(item.get("data"), list):
                    item["preview"] = self._format_files_preview(item["data"])

            # 3. TEXT
            elif item_type == "text":
                if not item.get("preview") and item.get("data"):
                    text = item["data"]
                    item["preview"] = text[:60].replace("\n", " ") + ("..." if len(text) > 60 else "")

            processed_items.append(item)

        return processed_items

    def connect_to_changes(self):
        """Connect the clipboard owner-change signal."""
        self.clipboard.connect("owner-change", self._on_clipboard_changed)

    def _is_clipboard_secret(self):
        """Check whether the owning application explicitly marks the content as secret."""
        try:
            target = Gdk.Atom.intern("x-kde-passwordManagerHint", False)
            selection_data = self.clipboard.wait_for_contents(target)

            if not selection_data:
                return False

            data = selection_data.get_data()
            if not data:
                return False

            value = data.decode("utf-8", errors="ignore").strip().lower()
            return value == "secret"

        except Exception as e:
            return False

    def _on_clipboard_changed(self, clipboard, event):
        """Apply a dynamic debounce before processing the content."""
        if self._debounce_timer_id is not None:
            GLib.source_remove(self._debounce_timer_id)

        # If the clipboard contains an image, we give it 250 ms so Cinnamon can acknowledge the capture event
        debounce_ms = 250 if clipboard.wait_is_image_available() else 150
        self._debounce_timer_id = GLib.timeout_add(debounce_ms, self._process_clipboard_content)

    def _process_clipboard_content(self):
        self._debounce_timer_id = None

        # If the change was triggered by ourselves from the history, do not reinsert it
        if self.is_self_copying:
            self.is_self_copying = False
            return False

        # CHECK: PRIVATE MODE / HISTORY SAVING DISABLED
        if not self.settings.get("enable_history"):
            return False

        if self._is_clipboard_secret():
            return False

        # -----------------------------------------------------------------
        # DETECT WHETHER THE CLIPBOARD CONTAINS FILES OR FOLDERS
        # -----------------------------------------------------------------
        res = self.clipboard.wait_for_targets()
        if res:
            targets = res[1] if isinstance(res, tuple) and len(res) == 2 else res
            target_names = []

            if isinstance(targets, (list, tuple)):
                for target in targets:
                    if hasattr(target, "name"):
                        target_names.append(target.name())
                    elif isinstance(target, Gdk.Atom):
                        target_names.append(Gdk.Atom.name(target))

            is_file_clipboard = (
                "text/uri-list" in target_names
                or "x-special/gnome-copied-files" in target_names
                or "x-special/mate-copied-files" in target_names
            )

            # -----------------------------------------------------------------
            # FILES AND FOLDERS
            # -----------------------------------------------------------------
            if is_file_clipboard:
                # If file capture is disabled, ignore this content completely to avoid saving it as text.
                if not self.settings.get("save_files"):
                    return False

                uri_data = self._read_uri_list()
                if uri_data:
                    file_paths = uri_data["paths"]
                    signature = ("files", tuple(sorted(file_paths)))

                    if signature != self._last_content_signature:
                        self._last_content_signature = signature
                        self.change_count += 1

                        preview_text = self._format_files_preview(file_paths)
                        item = {
                            "type": "files",
                            "data": file_paths,
                            "preview": preview_text,
                            "pinned": False
                        }
                        self._add_to_history(item)
                        return False

        # -----------------------------------------------------------------
        # PRIORITY 2: IMAGES
        # -----------------------------------------------------------------
        if self.settings.get("save_images"):
            pixbuf = self.clipboard.wait_for_image()
            if pixbuf:
                image_bytes = pixbuf.get_pixels()
                img_hash = hashlib.sha256(image_bytes).hexdigest()
                w, h = pixbuf.get_width(), pixbuf.get_height()

                signature = ("image", w, h, img_hash)

                if signature != self._last_content_signature:
                    self._last_content_signature = signature
                    self.change_count += 1

                    scaled_pixbuf = self._scale_pixbuf(pixbuf, target_size=140)

                    saved_file_path = self.data_media_dir / f"{w}x{h}_{img_hash}.png"
                    if not saved_file_path.exists():
                        pixbuf.savev(str(saved_file_path), "png", [], [])

                    item = {
                        "type": "image",
                        "data": str(saved_file_path),
                        "data_path": str(saved_file_path),
                        "pixbuf": scaled_pixbuf,
                        "preview": _("Image (%(width)d×%(height)d px)") % {"width": w, "height": h},
                        "pinned": False
                    }
                    self._add_to_history(item)
                    return False

        # -----------------------------------------------------------------
        # PRIORITY 3: PLAIN TEXT
        # -----------------------------------------------------------------
        text = self.clipboard.wait_for_text()
        if text and text.strip():
            signature = ("text", text.strip())
            if signature != self._last_content_signature:
                self._last_content_signature = signature
                self.change_count += 1

                item = {
                    "type": "text",
                    "data": text,
                    "preview": text[:60].replace("\n", " ") + ("..." if len(text) > 60 else ""),
                    "pinned": False
                }
                self._add_to_history(item)
                return False

        return False

    def _show_notification(self, title, message):
        """Show a desktop notification using the standard D-Bus notification service."""
        notification = Gio.Notification.new(title)
        notification.set_body(message)
        notification.set_icon(Gio.ThemedIcon.new("cinnamon-clipboard"))

        app = Gio.Application.get_default()
        if app is not None:
            app.send_notification(None, notification)
    
    def set_files(self, file_paths):
        """Publish available files to the clipboard and notify about missing files."""
        missing_paths = [
            path for path in file_paths
            if not os.path.exists(path)
        ]

        available_paths = [
            path for path in file_paths
            if os.path.exists(path)
        ]

        if missing_paths:
            missing_count = len(missing_paths)

            if available_paths:
                message = _(
                    "Only some files were added to the clipboard because some are no longer available."
                )
            elif missing_count == 1:
                message = _("The file is no longer available for copying.")
            else:
                message = _(
                    "%(count)d files are no longer available for copying."
                ) % {"count": missing_count}

            self._show_notification(
                _("Cinnamon Clipboard"),
                message,
            )

        if not available_paths:
            self.is_self_copying = False
            return

        try:
            success = self.x11_file_clipboard.set_files(available_paths)

            if success:
                self.is_self_copying = True
            else:
                print("X11 file clipboard failed to acquire ownership.")
                self.is_self_copying = False

        except Exception as e:
            print(f"X11 file clipboard error: {e}")
            self.is_self_copying = False

    def _read_uri_list(self):
        """Extract local paths from the file selection in text/uri-list or gnome-copied-files format."""
        selection_data = self.clipboard.wait_for_contents(
            Gdk.Atom.intern("x-special/mate-copied-files", False)
        )
        if not selection_data or not selection_data.get_data():
            selection_data = self.clipboard.wait_for_contents(
                Gdk.Atom.intern("x-special/gnome-copied-files", False)
            )
        if not selection_data or not selection_data.get_data():
            selection_data = self.clipboard.wait_for_contents(
                Gdk.Atom.intern("text/uri-list", False)
            )
        if not selection_data:
            return None

        data_bytes = selection_data.get_data()
        if not data_bytes:
            return None

        lines = data_bytes.decode("utf-8", errors="ignore").splitlines()
        paths = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and line != "copy" and line != "cut":
                if line.startswith("file://"):
                    parsed_path = unquote(urlparse(line).path)
                    if os.path.exists(parsed_path):
                        paths.append(parsed_path)

        return {"paths": paths} if paths else None

    def _format_files_preview(self, file_paths):
        """Generate the formatted, decoded preview text for copied files."""
        count = len(file_paths)
        if count == 1:
            name = unquote(os.path.basename(file_paths[0]))
            return _("File: %(name)s") % {"name": name}
        else:
            first_name = unquote(os.path.basename(file_paths[0]))
            return _("%(name)s and %(count)d more file(s)") % {
                "name": first_name,
                "count": count - 1,
            }

    def _scale_pixbuf(self, pixbuf, target_size=140):
        """Scale the image proportionally for the menu thumbnail."""
        w = pixbuf.get_width()
        h = pixbuf.get_height()

        if w > h:
            new_w = target_size
            new_h = max(1, int(h * (target_size / w)))
        else:
            new_h = target_size
            new_w = max(1, int(w * (target_size / h)))

        return pixbuf.scale_simple(new_w, new_h, GdkPixbuf.InterpType.BILINEAR)

    def _add_to_history(self, item):
        """Save to the database, add to in-memory history, and notify open windows."""
        db_id = self.db.add_item(
            item_type=item["type"],
            data=item["data"],
            preview=item["preview"],
            data_path=item.get("data_path")
        )
        item["id"] = db_id

        # Insert after the last pinned item.
        insert_idx = 0
        for idx, h_item in enumerate(self.history):
            if h_item.get("pinned", False):
                insert_idx = idx + 1
            else:
                break

        self.history.insert(insert_idx, item)

        self.max_history = self.settings.get("max_history")

        # The limit applies only to unpinned items.
        normal_items = [
            history_item for history_item in self.history
            if not history_item.get("pinned", False)
        ]

        if len(normal_items) > self.max_history:
            # Remove the oldest unpinned item.
            for i in range(len(self.history) - 1, -1, -1):
                if not self.history[i].get("pinned", False):
                    removed_item = self.history.pop(i)
                    self.db.delete_item(removed_item["id"])

                    if removed_item.get("type") == "image" and "data_path" in removed_item:
                        path = removed_item["data_path"]

                        if not any(
                            history_item.get("data_path") == path
                            for history_item in self.history
                        ):
                            if os.path.exists(path):
                                os.remove(path)

                    break

        self._notify_history_changed()

    def apply_max_history(self, max_history):
        """Immediately apply the new limit by removing extra normal items."""
        self.max_history = max_history

        normal_items = [
            item for item in self.history
            if not item.get("pinned", False)
        ]

        while len(normal_items) > self.max_history:
            removed_item = normal_items.pop()

            self.history.remove(removed_item)
            self.db.delete_item(removed_item["id"])

            if removed_item.get("type") == "image" and "data_path" in removed_item:
                path = removed_item["data_path"]

                if not any(
                    history_item.get("data_path") == path
                    for history_item in self.history
                ):
                    if os.path.exists(path):
                        os.remove(path)

        self._notify_history_changed()

    def promote_item(self, item_id):
        """Move an item to the beginning of its respective group and save the new order."""
        target_item = None

        for item in self.history:
            if item["id"] == item_id:
                target_item = item
                break

        if not target_item:
            return

        # Remove the item from its current position.
        self.history.remove(target_item)

        if target_item.get("pinned", False):
            # If it is pinned: move it to the top.
            self.history.insert(0, target_item)
        else:
            # If it is unpinned: move it just below all pinned items.
            insert_idx = 0

            for idx, h_item in enumerate(self.history):
                if h_item.get("pinned", False):
                    insert_idx = idx + 1
                else:
                    break

            self.history.insert(insert_idx, target_item)

        # Persist the complete history order.
        self.db.save_order(self.history)

        self._notify_history_changed()

    def toggle_pin_item(self, item_id):
        """Toggle the pinned state of an item and persist the new order."""
        for item in self.history:
            if item["id"] == item_id:
                new_state = not item.get("pinned", False)
                item["pinned"] = new_state
                self.db.toggle_pin(item_id, new_state)
                break
        else:
            return

        # Reorder the item according to its new pinned state.
        self.promote_item(item_id)

    def copy_item_to_system(self, item):
        """Unified method to publish any item type to the system clipboard."""
        if not item:
            return

        item_type = item.get("type")

        if item_type == "text":
            self.is_self_copying = True
            self.clipboard.set_text(item["data"], -1)

        elif item_type == "image":
            if "data_path" in item and os.path.exists(item["data_path"]):
                self.is_self_copying = True
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(item["data_path"])
                self.clipboard.set_image(pixbuf)
            else:
                self.is_self_copying = False
                self._show_notification(
                    _("Cinnamon Clipboard"),
                    _("The image is no longer available for copying."),
                )

        elif item_type == "files":
            self.set_files(item["data"])

        # Promote the item to the top of its group
        if "id" in item:
            self.promote_item(item["id"])

    def remove_item(self, item_id):
        """Remove an item from the in-memory history and from SQLite."""
        removed_items = [i for i in self.history if i["id"] == item_id]
        self.history = [i for i in self.history if i["id"] != item_id]

        self.db.delete_item(item_id)

        for item in removed_items:
            if item.get("type") == "image" and "data_path" in item:
                path = item["data_path"]
                if not any(i.get("data_path") == path for i in self.history):
                    if os.path.exists(path):
                        os.remove(path)

        self._notify_history_changed()

    def clear_history(self):
        """Clear the unpinned history in memory, its images, and the database."""
        items_to_keep = []
        for item in self.history:
            if item.get("pinned", False):
                items_to_keep.append(item)
            else:
                if item.get("type") == "image" and "data_path" in item:
                    if os.path.exists(item["data_path"]):
                        os.remove(item["data_path"])

        self.history = items_to_keep
        self.db.clear_all(keep_pinned=True)
        self._last_content_signature = None
        self._notify_history_changed()