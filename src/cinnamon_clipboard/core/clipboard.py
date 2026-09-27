import hashlib
import os
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

from .database import HistoryDatabase


class ClipboardManager:
    """Gestiona la comunicación con el portapapeles en GTK3 con deduplicación, almacenamiento permanente e integración SQLite."""

    def __init__(self, max_history=20):
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.change_count = 0
        self.max_history = max_history

        self._debounce_timer_id = None
        self._last_content_signature = None
        self.is_self_copying = False  # Bandera para evitar reinsertar ítems copiados desde el historial

        # Directorio de datos permanente para imágenes (junto a la base de datos)
        self.data_media_dir = Path.home() / ".local" / "share" / "cinnamon-clipboard" / "media"
        self.data_media_dir.mkdir(parents=True, exist_ok=True)

        # Base de datos SQLite
        self.db = HistoryDatabase()
        self.history = self._load_history_from_db()

    def _load_history_from_db(self):
        """Carga el historial guardado en SQLite y regenera los pixbufs de imágenes si corresponden."""
        items = self.db.load_history(limit=self.max_history)
        for item in items:
            if item.get("type") == "image" and item.get("data_path"):
                if os.path.exists(item["data_path"]):
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file(item["data_path"])
                        item["pixbuf"] = self._scale_pixbuf(pixbuf, target_size=140)
                    except Exception as e:
                        print(f"[ADVERTENCIA] No se pudo cargar la imagen guardada: {e}")
        return items

    def connect_to_changes(self):
        """Conecta la señal de cambio de dueño del portapapeles."""
        self.clipboard.connect("owner-change", self._on_clipboard_changed)

    def _on_clipboard_changed(self, clipboard, event):
        """Aplica un debounce de 150 ms antes de procesar el contenido."""
        if self._debounce_timer_id is not None:
            GLib.source_remove(self._debounce_timer_id)

        self._debounce_timer_id = GLib.timeout_add(150, self._process_clipboard_content)

    def _process_clipboard_content(self):
        self._debounce_timer_id = None

        # Si el cambio lo provocamos nosotros mismos desde el historial, no lo reinsertamos
        if self.is_self_copying:
            self.is_self_copying = False
            return False

        # -----------------------------------------------------------------
        # PRIORIDAD 1: ARCHIVOS Y CARPETAS (ej. copiados desde Nemo)
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

            if "text/uri-list" in target_names or "x-special/gnome-copied-files" in target_names:
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
                            "preview": preview_text
                        }
                        self._add_to_history(item)
                        print(f"[EVENTO #{self.change_count}] ARCHIVOS: {preview_text}")
                        return False

        # -----------------------------------------------------------------
        # PRIORIDAD 2: IMÁGENES
        # -----------------------------------------------------------------
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
                    "preview": f"Imagen ({w}x{h} px)"
                }
                self._add_to_history(item)
                print(f"[EVENTO #{self.change_count}] IMAGEN: {w}x{h} px [Hash: {img_hash[:8]}]")
                return False

        # -----------------------------------------------------------------
        # PRIORIDAD 3: TEXTO PLANO
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
                    "preview": text[:60].replace("\n", " ") + ("..." if len(text) > 60 else "")
                }
                self._add_to_history(item)
                print(f"[EVENTO #{self.change_count}] TEXTO: {item['preview']}")
                return False

        return False

    def set_files(self, file_paths):
        """Publica archivos en el portapapeles usando xclip con la cabecera x-special/gnome-copied-files requerida por Nemo."""
        uris = [GLib.filename_to_uri(p, None) for p in file_paths if os.path.exists(p)]
        if not uris:
            return

        gnome_payload = "copy\n" + "\n".join(uris)

        try:
            process = subprocess.Popen(
                ["xclip", "-selection", "clipboard", "-target", "x-special/gnome-copied-files"],
                stdin=subprocess.PIPE
            )
            process.communicate(input=gnome_payload.encode("utf-8"))

            self.is_self_copying = True
            print(f"[ARCHIVOS] {len(uris)} elemento(s) configurado(s) en el portapapeles.")
        except Exception as e:
            self.is_self_copying = False
            print(f"[ERROR] No se pudo publicar archivos con xclip: {e}")

    def _read_uri_list(self):
        """Extrae las rutas locales desde la selección de archivos text/uri-list o gnome-copied-files."""
        selection_data = self.clipboard.wait_for_contents(Gdk.Atom.intern("x-special/gnome-copied-files", False))
        if not selection_data or not selection_data.get_data():
            selection_data = self.clipboard.wait_for_contents(Gdk.Atom.intern("text/uri-list", False))

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
        """Genera el texto formateado y decodificado de vista previa de los archivos copiados."""
        count = len(file_paths)
        if count == 1:
            name = unquote(os.path.basename(file_paths[0]))
            return f"Archivo: {name}"
        else:
            first_name = unquote(os.path.basename(file_paths[0]))
            return f"{first_name} y {count - 1} archivo(s) más"

    def _scale_pixbuf(self, pixbuf, target_size=140):
        """Escala proporcionalmente la imagen para la miniatura del menú."""
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
        """Guarda en la base de datos y añade al historial en memoria."""
        db_id = self.db.add_item(
            item_type=item["type"],
            data=item["data"],
            preview=item["preview"],
            data_path=item.get("data_path")
        )
        item["id"] = db_id
        self.history.insert(0, item)

        if len(self.history) > self.max_history:
            removed_item = self.history.pop()
            self.db.delete_item(removed_item["id"])
            if removed_item.get("type") == "image" and "data_path" in removed_item:
                path = removed_item["data_path"]
                if not any(i.get("data_path") == path for i in self.history):
                    if os.path.exists(path):
                        os.remove(path)

    def remove_item(self, item_id):
        """Elimina un elemento del historial en RAM y en SQLite."""
        removed_items = [i for i in self.history if i["id"] == item_id]
        self.history = [i for i in self.history if i["id"] != item_id]

        self.db.delete_item(item_id)

        for item in removed_items:
            if item.get("type") == "image" and "data_path" in item:
                path = item["data_path"]
                if not any(i.get("data_path") == path for i in self.history):
                    if os.path.exists(path):
                        os.remove(path)

    def clear_history(self):
        """Vacía el historial en RAM, las imágenes guardadas y la base de datos SQLite."""
        for item in self.history:
            if item.get("type") == "image" and "data_path" in item:
                if os.path.exists(item["data_path"]):
                    os.remove(item["data_path"])

        self.history.clear()
        self.db.clear_all()
        self._last_content_signature = None

        git add .
git commit -m "feat: integrar persistencia SQLite y almacenamiento permanente de imagenes"