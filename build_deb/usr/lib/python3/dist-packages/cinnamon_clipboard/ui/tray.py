import gi

import logging

logger = logging.getLogger(__name__)

gi.require_version("Gtk", "3.0")

try:
    gi.require_version("XApp", "1.0")
    from gi.repository import XApp
    HAS_XAPP = True
except (ValueError, ImportError):
    HAS_XAPP = False

class TrayIcon:
    """Manages the native Cinnamon tray icon with the native popup window."""

    def __init__(self, app, clipboard_manager, menu_window):
        self.app = app
        self.clipboard_manager = clipboard_manager
        self.menu_window = menu_window

        if not HAS_XAPP:
            logger.error("Failed to load XApp. Please verify that gir1.2-xapp-1.0 is installed.")
            return

        self.status_icon = XApp.StatusIcon.new()
        self.status_icon.set_name("cinnamon-clipboard")
        self.status_icon.set_icon_name("edit-paste-symbolic")
        self.status_icon.set_tooltip_text("Cinnamon Clipboard")
        self.status_icon.set_visible(True)

        self.status_icon.connect("activate", self._on_icon_clicked)
        self.status_icon.connect("button-release-event", self._on_button_release)

    def _on_icon_clicked(self, icon, button, time):
        """Open or close the popup window in a fixed position."""
        self.menu_window.toggle_window()

    def _on_button_release(self, icon, x, y, button, time, panel_position):
        """Save the panel position and orientation provided by XApp."""
        self.menu_window.panel_x = x
        self.menu_window.panel_y = y
        self.menu_window.panel_position = panel_position

        if self.menu_window.get_visible():
            self.menu_window._update_position()

        return False