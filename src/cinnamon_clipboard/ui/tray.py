import gi

gi.require_version("Gtk", "3.0")

try:
    gi.require_version("XApp", "1.0")
    from gi.repository import XApp
    HAS_XAPP = True
except (ValueError, ImportError):
    HAS_XAPP = False

from .menu_window import QuickMenuWindow


class TrayIcon:
    """Gestiona el ícono nativo de la bandeja de Cinnamon con la ventana emergente nativa."""

    def __init__(self, app, clipboard_manager, on_open_app_callback=None):
        self.app = app
        self.clipboard_manager = clipboard_manager
        self.on_open_app_callback = on_open_app_callback

        if not HAS_XAPP:
            print("[ERROR] No se pudo cargar XApp. Verifica gir1.2-xapp-1.0.")
            return

        self.menu_window = QuickMenuWindow(
            clipboard_manager=self.clipboard_manager,
            on_open_main_window_callback=self.on_open_app_callback
        )

        self.status_icon = XApp.StatusIcon.new()
        self.status_icon.set_name("cinnamon-clipboard")
        self.status_icon.set_icon_name("edit-paste-symbolic")
        self.status_icon.set_tooltip_text("Cinnamon Clipboard")
        self.status_icon.set_visible(True)

        self.status_icon.connect("activate", self._on_icon_clicked)

        print("[OK] Ícono nativo XApp registrado correctamente en Cinnamon.")

    def _on_icon_clicked(self, icon, button, time):
        """Abre o cierra la ventana emergente en una posición fija."""
        self.menu_window.toggle_window()