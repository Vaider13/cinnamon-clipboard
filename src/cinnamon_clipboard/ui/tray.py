import gi

gi.require_version("Gtk", "3.0")

try:
    gi.require_version("XApp", "1.0")
    from gi.repository import XApp
    HAS_XAPP = True
except (ValueError, ImportError):
    HAS_XAPP = False

class TrayIcon:
    """Gestiona el ícono nativo de la bandeja de Cinnamon con la ventana emergente nativa."""

    def __init__(self, app, clipboard_manager, menu_window):
        self.app = app
        self.clipboard_manager = clipboard_manager
        self.menu_window = menu_window

        if not HAS_XAPP:
            print("[ERROR] No se pudo cargar XApp. Verifica gir1.2-xapp-1.0.")
            return

        self.status_icon = XApp.StatusIcon.new()
        self.status_icon.set_name("cinnamon-clipboard")
        self.status_icon.set_icon_name("edit-paste-symbolic")
        self.status_icon.set_tooltip_text("Cinnamon Clipboard")
        self.status_icon.set_visible(True)

        self.status_icon.connect("activate", self._on_icon_clicked)
        self.status_icon.connect("button-release-event", self._on_button_release)

        print("[OK] Ícono nativo XApp registrado correctamente en Cinnamon.")

    def _on_icon_clicked(self, icon, button, time):
        """Abre o cierra la ventana emergente en una posición fija."""
        print(f"[DEBUG] StatusIcon primary menu = {self.status_icon.get_primary_menu()}")
        print(f"[DEBUG] StatusIcon secondary menu = {self.status_icon.get_secondary_menu()}")
        self.menu_window.toggle_window()

    def _on_button_release(self, icon, x, y, button, time, panel_position):
        """Guarda la posición y orientación del panel proporcionadas por XApp."""
        self.menu_window.panel_x = x
        self.menu_window.panel_y = y
        self.menu_window.panel_position = panel_position

        print(
            f"[DEBUG] XApp posición: x={x}, y={y}, "
            f"button={button}, panel_position={panel_position}"
        )

        if self.menu_window.get_visible():
            self.menu_window._update_position()

        return False