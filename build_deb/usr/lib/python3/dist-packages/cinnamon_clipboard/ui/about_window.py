import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk

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
        self.set_license_type(Gtk.License.GPL_3_0)
        self.set_copyright("© 2026 Vaider13")
        self.set_website("https://github.com/Vaider13/cinnamon-clipboard")
        self.set_website_label("GitHub")
        self.set_authors(["Pablo / Vaider13"])

        self.connect("response", self._on_response)

    def _on_response(self, dialog, response_id):
        """Cierra la ventana cuando el usuario responde al diálogo."""
        self.destroy()
