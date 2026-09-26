import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk

from .core.clipboard import ClipboardManager
from .ui.tray import TrayIcon


class ClipboardApp(Gtk.Application):
    """Aplicación principal de Cinnamon Clipboard en GTK3."""

    def __init__(self):
        super().__init__(
            application_id="com.github.vaider13.CinnamonClipboard"
        )
        self.clipboard_manager = ClipboardManager()
        self.tray_icon = None

    def do_activate(self):
        window = Gtk.ApplicationWindow(application=self)
        window.set_title("Cinnamon Clipboard")
        window.set_default_size(600, 500)

        if self.tray_icon is None:
            self.tray_icon = TrayIcon(
                app=self,
                clipboard_manager=self.clipboard_manager,
                on_open_app_callback=window.present
            )

        # Escuchar eventos del portapapeles
        self.clipboard_manager.connect_to_changes()

        window.present()


def main():
    app = ClipboardApp()
    return app.run(None)


if __name__ == "__main__":
    main()