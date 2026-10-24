import hashlib
import logging
import gi
import shutil
import os

from pathlib import Path
from urllib.parse import unquote, urlparse

from Xlib import X, XK, display as xlib_display
from Xlib.ext import xtest

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk

from ..i18n import _
from .database import HistoryDatabase
from .settings import SettingsManager
from .x11_file_clipboard import X11FileClipboard

logger = logging.getLogger(__name__)

TERMINAL_WM_CLASSES = {
    "gnome-terminal",
    "gnome-terminal-server",
    "xfce4-terminal",
    "mate-terminal",
    "konsole",
    "kitty",
    "alacritty",
    "terminator",
    "tilix",
    "xterm",
    "uxterm",
    "lxterminal",
    "qterminal",
    "sakura",
    "guake",
    "yakuake",
    "wezterm",
    "foot",
    "ghostty",
}


class ClipboardManager:
    """Manages clipboard communication in GTK3 with deduplication, permanent storage, and SQLite integration."""

    @staticmethod
    def _clean_persistent_storage():
        """Remove persistent history files before starting in temporary mode."""
        data_dir = (
            Path.home()
            / ".local"
            / "share"
            / "cinnamon-clipboard"
        )
        db_path = data_dir / "history.db"
        media_dir = data_dir / "media"

        # Validate the application data directory.
        if data_dir.is_symlink():
            raise OSError(
                f"Refusing to use unexpected symbolic link: {data_dir}"
            )

        if data_dir.exists() and not data_dir.is_dir():
            raise OSError(
                f"Expected a data directory, found another file: {data_dir}"
            )

        db_files = (
            db_path,
            Path(str(db_path) + "-wal"),
            Path(str(db_path) + "-shm"),
            Path(str(db_path) + "-journal"),
        )

        # Validate database files before deleting anything.
        for path in db_files:
            if path.is_symlink():
                raise OSError(
                    f"Refusing to delete unexpected symbolic link: {path}"
                )

        # Validate the image directory before deleting anything.
        if media_dir.is_symlink():
            raise OSError(
                f"Refusing to delete unexpected symbolic link: {media_dir}"
            )

        if media_dir.exists() and not media_dir.is_dir():
            raise OSError(
                f"Expected an image directory, found another file: {media_dir}"
            )

        # Delete SQLite database files and possible journal sidecars.
        for path in db_files:
            if path.exists():
                path.unlink()

        # Remove the application's image-storage directory.
        if media_dir.exists():
            shutil.rmtree(media_dir)

    def __init__(self):
        self.settings = SettingsManager()
        self.history_mode = self.settings.get("history_mode") or "persistent"

        # Initialize the system clipboard.
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.x11_file_clipboard = X11FileClipboard()
        self.change_count = 0
        self.max_history = self.settings.get("max_history")

        self._debounce_timer_id = None
        self._last_content_signature = None
        self.is_self_copying = False

        # Subscribers to notify interface changes in real time.
        self._on_history_changed_callbacks = []

        # Temporary item IDs are negative to avoid collisions with SQLite IDs.
        self._next_temp_id = -1

        # Persistent storage is initialized only in persistent mode.
        self.data_media_dir = None
        self.db = None

        if self.history_mode == "persistent":
            self.data_media_dir = (
                Path.home()
                / ".local"
                / "share"
                / "cinnamon-clipboard"
                / "media"
            )
            self.data_media_dir.mkdir(parents=True, exist_ok=True)
            self.db = HistoryDatabase()
            self.history = self._load_history_from_db()
        else:
            try:
                self._clean_persistent_storage()
            except OSError as error:
                logger.exception(
                    "Failed to clean persistent history in temporary mode"
                )
                raise RuntimeError(
                    "Cannot start temporary mode because persistent "
                    "history files could not be removed."
                ) from error

            self.history = []

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

        # If the change was triggered by ourselves from the history, do not reinsert it.
        if self.is_self_copying:
            self.is_self_copying = False
            return False

        # History saving disabled.
        if not self.settings.get("enable_history"):
            return False

        if self._is_clipboard_secret():
            return False

        # Detect files and folders.
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

            # Files and folders.
            if is_file_clipboard:
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
                            "pinned": False,
                        }
                        self._add_to_history(item)

                    return False

        # Images.
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

                    item = {
                        "type": "image",
                        "preview": _("Image (%(width)d×%(height)d px)") % {
                            "width": w,
                            "height": h,
                        },
                        "pixbuf": scaled_pixbuf,
                        "pinned": False,
                    }

                    if self.history_mode == "persistent":
                        saved_file_path = (
                            self.data_media_dir / f"{w}x{h}_{img_hash}.png"
                        )
                        if not saved_file_path.exists():
                            pixbuf.savev(str(saved_file_path), "png", [], [])

                        item["data"] = str(saved_file_path)
                        item["data_path"] = str(saved_file_path)
                    else:
                        # Keep the original image in RAM; do not write it to disk.
                        item["data"] = f"memory:{w}x{h}:{img_hash}"
                        item["pixbuf_original"] = pixbuf

                    self._add_to_history(item)
                    return False

        # Plain text.
        text = self.clipboard.wait_for_text()
        if text and text.strip():
            text_lines = tuple(
                line.strip()
                for line in text.splitlines()
                if line.strip()
            )

            # Ignore the text representation generated when copying files.
            if getattr(self, "_last_file_paths", ()) and text_lines == self._last_file_paths:
                return False

            signature = ("text", text.strip())

            if signature != self._last_content_signature:
                self._last_content_signature = signature
                self.change_count += 1

                item = {
                    "type": "text",
                    "data": text,
                    "preview": text[:60].replace("\n", " ") + ("..." if len(text) > 60 else ""),
                    "pinned": False,
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
            return False

        try:
            success = self.x11_file_clipboard.set_files(available_paths)

            if success:
                self.is_self_copying = True
                return True
            else:
                print("X11 file clipboard failed to acquire ownership.")
                self.is_self_copying = False
                return False

        except Exception as e:
            print(f"X11 file clipboard error: {e}")
            self.is_self_copying = False
            return False

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
        """Add an item to history and persist it only in persistent mode."""
        if self.db is not None:
            db_id = self.db.add_item(
                item_type=item["type"],
                data=item["data"],
                preview=item["preview"],
                data_path=item.get("data_path"),
            )
            item["id"] = db_id
        else:
            item["id"] = self._next_temp_id
            self._next_temp_id -= 1

        # Insert after the last pinned item.
        insert_idx = 0
        for idx, h_item in enumerate(self.history):
            if h_item.get("pinned", False):
                insert_idx = idx + 1
            else:
                break
        self.history.insert(insert_idx, item)

        self.max_history = self.settings.get("max_history")
        normal_items = [
            history_item
            for history_item in self.history
            if not history_item.get("pinned", False)
        ]

        if len(normal_items) > self.max_history:
            for i in range(len(self.history) - 1, -1, -1):
                if not self.history[i].get("pinned", False):
                    removed_item = self.history.pop(i)

                    if self.db is not None:
                        self.db.delete_item(removed_item["id"])

                    if (
                        self.db is not None
                        and removed_item.get("type") == "image"
                        and removed_item.get("data_path")
                    ):
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
        """Apply the history limit and persist removals when applicable."""
        self.max_history = max_history
        normal_items = [
            item for item in self.history
            if not item.get("pinned", False)
        ]

        while len(normal_items) > self.max_history:
            removed_item = normal_items.pop()
            self.history.remove(removed_item)

            if self.db is not None:
                self.db.delete_item(removed_item["id"])

            if (
                self.db is not None
                and removed_item.get("type") == "image"
                and removed_item.get("data_path")
            ):
                path = removed_item["data_path"]
                if not any(
                    item.get("data_path") == path
                    for item in self.history
                ):
                    if os.path.exists(path):
                        os.remove(path)

        self._notify_history_changed()

    
    def promote_item(self, item_id):
        """Move an item to the beginning of its respective group."""
        target_item = None
        for item in self.history:
            if item["id"] == item_id:
                target_item = item
                break

        if not target_item:
            return

        self.history.remove(target_item)

        if target_item.get("pinned", False):
            self.history.insert(0, target_item)
        else:
            insert_idx = 0
            for idx, h_item in enumerate(self.history):
                if h_item.get("pinned", False):
                    insert_idx = idx + 1
                else:
                    break
            self.history.insert(insert_idx, target_item)

        if self.db is not None:
            self.db.save_order(self.history)

        self._notify_history_changed()


    def toggle_pin_item(self, item_id):
        """Toggle the pinned state of an item and persist it when applicable."""
        for item in self.history:
            if item["id"] == item_id:
                new_state = not item.get("pinned", False)
                item["pinned"] = new_state

                if self.db is not None:
                    self.db.toggle_pin(item_id, new_state)
                break
        else:
            return

        self.promote_item(item_id)

   
    def copy_item_to_system(self, item):
        """Publish any history item to the system clipboard."""
        if not item:
            return False

        item_type = item.get("type")
        copied = False

        if item_type == "text":
            self.is_self_copying = True
            self.clipboard.set_text(item["data"], -1)
            copied = True

        elif item_type == "image":
            try:
                if item.get("pixbuf_original") is not None:
                    # Temporary mode: copy the original image from RAM.
                    pixbuf = item["pixbuf_original"]
                elif item.get("data_path") and os.path.exists(item["data_path"]):
                    # Persistent mode: load the image from disk.
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(item["data_path"])
                else:
                    pixbuf = None

                if pixbuf is not None:
                    self.is_self_copying = True
                    self.clipboard.set_image(pixbuf)
                    copied = True
                else:
                    self.is_self_copying = False
                    self._show_notification(
                        _("Cinnamon Clipboard"),
                        _("The image is no longer available for copying."),
                    )
            except Exception:
                self.is_self_copying = False
                logging.exception("Could not copy an image from clipboard history")
                self._show_notification(
                    _("Cinnamon Clipboard"),
                    _("The image could not be copied."),
                )

        elif item_type == "files":
            copied = bool(self.set_files(item["data"]))

        if copied and "id" in item:
            self.promote_item(item["id"])

        return copied


    def _is_focused_window_terminal(self, disp):
        """Return True if the currently focused X11 window belongs to a terminal emulator."""
        try:
            focus_reply = disp.get_input_focus()
            win = focus_reply.focus
            if not win or isinstance(win, int):
                return False

            visited = set()
            while win and not isinstance(win, int) and win.id not in visited:
                visited.add(win.id)
                try:
                    wm_class = win.get_wm_class()
                    if wm_class:
                        for name in wm_class:
                            if name and name.lower() in TERMINAL_WM_CLASSES:
                                return True
                    tree = win.query_tree()
                    if not tree or tree.parent == tree.root or tree.parent == win:
                        break
                    win = tree.parent
                except Exception:
                    break
        except Exception:
            pass
        return False

    def paste_to_active_window(self, item_type=None, exclude_xid=None):
        """Simulate paste shortcut (Ctrl+V or Ctrl+Shift+V for terminals) into the active X11 window."""
        state = {"retries": 0}

        def _try_paste():
            try:
                disp = self.x11_file_clipboard.display
                keymap = disp.query_keymap()

                # Wait briefly if the user is still holding Enter or modifier keys
                watched_keysyms = (
                    XK.XK_Return,
                    XK.XK_KP_Enter,
                    XK.XK_Alt_L,
                    XK.XK_Alt_R,
                    XK.XK_Super_L,
                    XK.XK_Super_R,
                    XK.XK_Control_L,
                    XK.XK_Control_R,
                    XK.XK_Shift_L,
                    XK.XK_Shift_R,
                )
                keys_held = False
                for keysym in watched_keysyms:
                    keycode = disp.keysym_to_keycode(keysym)
                    if keycode and (keymap[keycode >> 3] & (1 << (keycode & 7))):
                        keys_held = True
                        break

                focus_reply = disp.get_input_focus()
                focus_win = focus_reply.focus
                focus_xid = getattr(focus_win, "id", None)
                focus_not_ready = (
                    focus_xid is None
                    or (exclude_xid is not None and focus_xid == exclude_xid)
                )

                if (keys_held or focus_not_ready) and state["retries"] < 20:
                    state["retries"] += 1
                    GLib.timeout_add(25, _try_paste)
                    return False

                ctrl_kc = disp.keysym_to_keycode(XK.XK_Control_L)
                shift_kc = disp.keysym_to_keycode(XK.XK_Shift_L)
                v_kc = disp.keysym_to_keycode(XK.XK_v)

                if not ctrl_kc or not v_kc:
                    return False

                use_shift = (
                    item_type == "text"
                    and bool(shift_kc)
                    and self._is_focused_window_terminal(disp)
                )

                xtest.fake_input(disp, X.KeyPress, ctrl_kc)
                if use_shift:
                    xtest.fake_input(disp, X.KeyPress, shift_kc)
                xtest.fake_input(disp, X.KeyPress, v_kc)
                xtest.fake_input(disp, X.KeyRelease, v_kc)
                if use_shift:
                    xtest.fake_input(disp, X.KeyRelease, shift_kc)
                xtest.fake_input(disp, X.KeyRelease, ctrl_kc)
                disp.flush()
            except Exception as e:
                logger.error("Failed to simulate paste: %s", e)

            return False

        GLib.timeout_add(80, _try_paste)

    
    def remove_item(self, item_id):
        """Remove an item from history and from SQLite when applicable."""
        removed_items = [item for item in self.history if item["id"] == item_id]
        self.history = [item for item in self.history if item["id"] != item_id]

        if self.db is not None:
            self.db.delete_item(item_id)

        for item in removed_items:
            if (
                self.db is not None
                and item.get("type") == "image"
                and item.get("data_path")
            ):
                path = item["data_path"]
                if not any(
                    history_item.get("data_path") == path
                    for history_item in self.history
                ):
                    if os.path.exists(path):
                        os.remove(path)

        self._notify_history_changed()


    def clear_history(self):
        """Clear unpinned history without deleting images still in use."""
        items_to_keep = [
            item for item in self.history
            if item.get("pinned", False)
        ]

        pinned_image_paths = {
            item["data_path"]
            for item in items_to_keep
            if item.get("type") == "image" and item.get("data_path")
        }

        for item in self.history:
            if item.get("pinned", False):
                continue

            if (
                self.db is not None
                and item.get("type") == "image"
                and item.get("data_path")
            ):
                path = item["data_path"]
                if path not in pinned_image_paths and os.path.exists(path):
                    os.remove(path)

        self.history = items_to_keep

        if self.db is not None:
            self.db.clear_all(keep_pinned=True)

        self._last_content_signature = None
        self._notify_history_changed()

