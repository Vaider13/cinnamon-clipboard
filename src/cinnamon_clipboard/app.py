import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class ClipboardApp(Gtk.Application):
    """Aplicación principal de Cinnamon Clipboard."""

    def __init__(self):
        """Inicializa la aplicación GTK y configura su identificador único."""
        super().__init__(
            application_id="com.github.vaider13.CinnamonClipboard"
        )

    def do_activate(self):
        """Crea y muestra la ventana principal cuando se activa la aplicación."""
        window = Gtk.ApplicationWindow(application=self)

        # Configuramos las propiedades básicas de la ventana.
        window.set_title("Cinnamon Clipboard")
        window.set_default_size(600, 500)

        # Mostramos la ventana y todos sus elementos hijos.
        window.present()


def main():
    """Crea la aplicación y ejecuta su bucle principal."""
    app = ClipboardApp()
    return app.run(None)