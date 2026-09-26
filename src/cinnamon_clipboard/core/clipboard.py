import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib


class ClipboardManager:
    """Gestiona la comunicación con el portapapeles en GTK3."""

    def __init__(self, max_history=20):
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.change_count = 0
        self.max_history = max_history
        self.history = []

        self._debounce_timer_id = None
        self._last_content_signature = None

    def connect_to_changes(self, callback=None):
        self.clipboard.connect("owner-change", self._on_clipboard_changed)

    def _on_clipboard_changed(self, clipboard, event):
        if self._debounce_timer_id is not None:
            GLib.source_remove(self._debounce_timer_id)

        self._debounce_timer_id = GLib.timeout_add(150, self._process_clipboard_content)

    def _process_clipboard_content(self):
        self._debounce_timer_id = None

        # 1. Lectura de Texto
        text = self.clipboard.wait_for_text()
        if text and text.strip():
            signature = ("text", text)
            if signature != self._last_content_signature:
                self._last_content_signature = signature
                self.change_count += 1

                item = {
                    "id": self.change_count,
                    "type": "text",
                    "data": text,
                    "preview": text[:60].replace("\n", " ") + ("..." if len(text) > 60 else "")
                }
                self._add_to_history(item)
                print(f"[EVENTO #{self.change_count}] TEXTO: {item['preview']}")
                return False

        # 2. Lectura de Imagen
        pixbuf = self.clipboard.wait_for_image()
        if pixbuf:
            w = pixbuf.get_width()
            h = pixbuf.get_height()
            signature = ("image", w, h)

            if signature != self._last_content_signature:
                self._last_content_signature = signature
                self.change_count += 1

                scaled_pixbuf = self._scale_pixbuf(pixbuf, target_size=140)

                item = {
                    "id": self.change_count,
                    "type": "image",
                    "data": pixbuf,
                    "pixbuf": scaled_pixbuf,
                    "preview": f"Imagen ({w}x{h} px)"
                }
                self._add_to_history(item)
                print(f"[EVENTO #{self.change_count}] IMAGEN: {w}x{h} px")

        return False

    def _scale_pixbuf(self, pixbuf, target_size=140):
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
        self.history.insert(0, item)
        if len(self.history) > self.max_history:
            self.history.pop()

    def remove_item(self, item_id):
        self.history = [i for i in self.history if i["id"] != item_id]

    def clear_history(self):
        self.history.clear()
        self._last_content_signature = None