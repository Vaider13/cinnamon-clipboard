import gi
from pathlib import Path

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Gtk, GdkPixbuf

from ..i18n import _


class AboutWindow(Gtk.AboutDialog):
    """Muestra la información de Cinnamon Clipboard."""

    def __init__(self, parent=None):
        super().__init__()

        self.set_transient_for(parent)
        self.set_modal(True)

        self.set_program_name("Cinnamon Clipboard")
        self.set_version("1.0.0 RC1")
        self.set_comments(_("Clipboard manager for Linux desktops."))
        self.set_copyright("© 2026 Vaider13")
        self.set_website("https://github.com/Vaider13/cinnamon-clipboard")
        self.set_website_label("GitHub")
        self.set_authors(["Pablo / Vaider13"])

        # 1. Cargar el ícono nativo de la app usando Pixbuf
        icon_path = Path("/usr/share/icons/hicolor/512x512/apps/cinnamon-clipboard.png")
        if not icon_path.exists():
            # Fallback para el entorno de desarrollo local
            icon_path = Path(__file__).parent.parent.parent / "data" / "icons" / "cinnamon-clipboard.png"

        if icon_path.exists():
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(icon_path), 128, 128, True
                )
                self.set_logo(pixbuf)
            except Exception as e:
                print(f"[ADVERTENCIA] No se pudo cargar el ícono en AboutDialog: {e}")
        else:
            self.set_logo_icon_name("cinnamon-clipboard")

        # 2. Asignar el texto explícito de la licencia para que el botón "Licencia" responda
        license_text = _(
            "Cinnamon Clipboard es software libre: usted puede redistribuirlo y/o modificarlo "
            "bajo los términos de la Licencia Pública General GNU publicada por la "
            "Free Software Foundation, ya sea la versión 3 de la Licencia, o (a su elección) "
            "cualquier versión posterior.\n\n"
            "Este programa se distribuye con la esperanza de que sea útil, pero SIN NINGUNA GARANTÍA; "
            "sin siquiera la garantía implícita de COMERCIABILIDAD o IDONEIDAD PARA UN PROPÓSITO PARTICULAR. "
            "Vea la Licencia Pública General GNU para más detalles."
        )
        self.set_license(license_text)
        self.set_wrap_license(True)

        self.connect("response", self._on_response)

    def _on_response(self, dialog, response_id):
        """Cierra la ventana cuando el usuario responde al diálogo."""
        self.destroy()