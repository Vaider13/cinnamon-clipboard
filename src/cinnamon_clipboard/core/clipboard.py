import urllib.parse
import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gdk, GdkPixbuf, GLib


class ClipboardManager:
    """Gestiona la lectura y almacenamiento del historial del portapapeles."""

    def __init__(self, max_history=20):
        display = Gdk.Display.get_default()

        if display is None:
            raise RuntimeError("No se pudo obtener la pantalla actual.")

        self.clipboard = display.get_clipboard()
        self.change_count = 0
        self.max_history = max_history

        # Lista de ítems: {"id": int, "type": "text"|"image"|"files", "data": obj, "preview": str, "pixbuf": GdkPixbuf}
        self.history = []

        self._debounce_timer_id = None
        self._last_content_signature = None

    def connect_to_changes(self, callback=None):
        """Escucha el evento 'changed' del portapapeles de GTK."""
        self.clipboard.connect("changed", self._on_clipboard_changed)

    def _on_clipboard_changed(self, clipboard):
        if self._debounce_timer_id is not None:
            GLib.source_remove(self._debounce_timer_id)

        self._debounce_timer_id = GLib.timeout_add(150, self._process_clipboard_content)

    def _process_clipboard_content(self):
        self._debounce_timer_id = None
        formats = self.clipboard.get_formats()

        contain_files = formats.contain_mime_type("text/uri-list")
        contain_image = formats.contain_mime_type("image/png") or formats.contain_mime_type("image/jpeg")
        contain_text = formats.contain_mime_type("text/plain") or formats.contain_mime_type("text/plain;charset=utf-8")

        # Prioridad: Archivos > Imágenes > Texto plano
        if contain_files:
            self.clipboard.read_value_async(GLib.Bytes, GLib.PRIORITY_DEFAULT, None, self._on_files_read)
        elif contain_image:
            self.clipboard.read_texture_async(None, self._on_texture_read)
        elif contain_text:
            self.clipboard.read_text_async(None, self._on_text_read)

        return False

    def _on_files_read(self, clipboard, result):
        """Procesa la lista de archivos (text/uri-list)."""
        try:
            # Leemos el buffer con las URIs de los archivos copiados
            gbytes = clipboard.read_value_finish(result)
            raw_data = gbytes.get_data().decode("utf-8", errors="ignore")
            
            # Las URIs vienen separadas por saltos de línea (file:///ruta/al/archivo)
            uris = [line.strip() for line in raw_data.splitlines() if line.startswith("file://")]
            paths = [urllib.parse.unquote(u.replace("file://", "")) for u in uris]
        except Exception:
            paths = []

        if not paths:
            return

        signature = ("files", tuple(paths))
        if signature == self._last_content_signature:
            return

        self._last_content_signature = signature
        self.change_count += 1

        # Nombre legible para el menú de la bandeja
        if len(paths) == 1:
            preview_str = f"Archivo: {paths[0].split('/')[-1]}"
        else:
            preview_str = f"{len(paths)} archivos copiados"

        item = {
            "id": self.change_count,
            "type": "files",
            "data": paths,        # Lista de rutas absolutas
            "preview": preview_str
        }

        self._add_to_history(item)
        print(f"\n[EVENTO #{self.change_count}] ARCHIVOS: {preview_str}")

    def _on_text_read(self, clipboard, result):
        try:
            text = clipboard.read_text_finish(result)
        except Exception:
            text = None

        if not text or not text.strip():
            return

        signature = ("text", text)
        if signature == self._last_content_signature:
            return

        self._last_content_signature = signature
        self.change_count += 1

        item = {
            "id": self.change_count,
            "type": "text",
            "data": text,
            "preview": text[:60].replace("\n", " ") + ("..." if len(text) > 60 else "")
        }

        self._add_to_history(item)
        print(f"\n[EVENTO #{self.change_count}] TEXTO: {item['preview']}")

    def _on_texture_read(self, clipboard, result):
        try:
            texture = clipboard.read_texture_finish(result)
        except Exception:
            texture = None

        if texture is None:
            return

        width = texture.get_width()
        height = texture.get_height()
        signature = ("image", width, height)

        if signature == self._last_content_signature:
            return

        self._last_content_signature = signature
        self.change_count += 1

        # Creamos una miniatura (Pixbuf) escalada a máximo 48x48 píxeles manteniendo la relación de aspecto
        pixbuf_preview = self._texture_to_scaled_pixbuf(texture, target_size=48)

        item = {
            "id": self.change_count,
            "type": "image",
            "data": texture,
            "pixbuf": pixbuf_preview,  # Miniatura lista para la interfaz gráfica
            "preview": f"Imagen ({width}x{height} px)"
        }

        self._add_to_history(item)
        print(f"\n[EVENTO #{self.change_count}] IMAGEN: {width}x{height} px (Miniatura generada)")

    def _texture_to_scaled_pixbuf(self, texture, target_size=48):
        """Convierte una Gdk.Texture a un GdkPixbuf.Pixbuf pequeño para miniaturas."""
        try:
            bytes_data = texture.save_to_png_bytes()
            loader = GdkPixbuf.PixbufLoader.new_with_type("png")
            loader.write(bytes_data.get_data())
            loader.close()
            pixbuf = loader.get_pixbuf()

            w = pixbuf.get_width()
            h = pixbuf.get_height()

            # Escalar manteniendo la proporción
            if w > h:
                new_w = target_size
                new_h = max(1, int(h * (target_size / w)))
            else:
                new_h = target_size
                new_w = max(1, int(w * (target_size / h)))

            return pixbuf.scale_simple(new_w, new_h, GdkPixbuf.InterpType.BILINEAR)
        except Exception as e:
            print(f"Error generando miniatura de imagen: {e}")
            return None

    def _add_to_history(self, item):
        self.history.insert(0, item)
        if len(self.history) > self.max_history:
            self.history.pop()

    def remove_item(self, item_id):
        self.history = [i for i in self.history if i["id"] != item_id]

    def clear_history(self):
        self.history.clear()
        self._last_content_signature = None