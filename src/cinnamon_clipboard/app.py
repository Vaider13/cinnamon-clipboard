import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk

from .core.clipboard import ClipboardManager
from .ui.main_window import MainWindow
from .ui.tray import TrayIcon


class ClipboardApp(Gtk.Application):
    """Aplicación principal de Cinnamon Clipboard en GTK3."""

    def __init__(self):
        super().__init__(
            application_id="com.github.vaider13.CinnamonClipboard"
        )
        self.clipboard_manager = ClipboardManager()
        self.tray_icon = None
        self.main_window = None

    def open_main_window(self):
        """Abre la ventana principal o la trae al frente si ya está abierta."""
        if self.main_window is None or not self.main_window.get_visible():
            self.main_window = MainWindow(self.clipboard_manager)
            self.main_window.set_application(self)
            self.main_window.connect("destroy", self._on_main_window_destroyed)
            self.main_window.show_all()
        else:
            self.main_window.present()

    def _on_main_window_destroyed(self, widget):
        self.main_window = None

    def do_activate(self):
        # 1. Inicializar el ícono de la bandeja del sistema si no existe
        if self.tray_icon is None:
            self.tray_icon = TrayIcon(
                app=self,
                clipboard_manager=self.clipboard_manager,
                on_open_app_callback=self.open_main_window
            )

        # 2. Iniciar el monitoreo del portapapeles
        self.clipboard_manager.connect_to_changes()

        # 3. Abrir la ventana principal al activar la app
        self.open_main_window()


def main():
    app = ClipboardApp()
    return app.run(None)


if __name__ == "__main__":
    main()