try:
    import setproctitle

    setproctitle.setproctitle("cinnamon-clipboard")
except ImportError:
    pass

import gi

import logging

logger = logging.getLogger(__name__)

gi.require_version("Gtk", "3.0")
try:
    gi.require_version("Keybinder", "3.0")
    from gi.repository import Keybinder
    KEYBINDER_AVAILABLE = True
except Exception:
    KEYBINDER_AVAILABLE = False

from gi.repository import GLib, Gtk

from .i18n import _

from .core.clipboard import ClipboardManager
from .ui.main_window import MainWindow
from .ui.menu_window import QuickMenuWindow
from .ui.tray import TrayIcon


class ClipboardApp(Gtk.Application):
    """Main Cinnamon Clipboard application in GTK3."""

    def __init__(self):
        super().__init__(
            application_id="com.github.vaider13.CinnamonClipboard"
        )
        self.clipboard_manager = ClipboardManager()
        self.tray_icon = None
        self.main_window = None
        self.quick_menu = None
        self.current_shortcut = None
        self._keybinder_initialized = False

    def open_main_window(self):
        """Open the main window with a single click or bring it to the front."""
        if self.main_window is None:
            self.main_window = MainWindow(
                self.clipboard_manager,
                on_quit_app_callback=self.quit_app,
            )
            self.main_window.set_application(self)
            self.main_window.set_wmclass("cinnamon-clipboard", "CinnamonClipboard")
            self.main_window.connect("destroy", self._on_main_window_destroyed)
            self.main_window.show_all()
            self.main_window.present()
        else:
            self.main_window.show_all()
            self.main_window.present()

    def _on_main_window_destroyed(self, widget):
        self.main_window = None

    def quit_app(self):
        """Fully close the application and release the service."""
        if self.quick_menu:
            self.quick_menu.destroy()
        if self.main_window:
            self.main_window.destroy()
        self.release()  # Releases self.hold() to exit the GTK main loop
        self.quit()

    def update_global_shortcut(self, shortcut_str):
        """Update the registered global shortcut when the user changes it in preferences."""
        self._setup_global_shortcut(shortcut_str)

    def _setup_global_shortcut(self, shortcut_str):
        """Register or update the global keyboard shortcut with Keybinder safely."""
        if not KEYBINDER_AVAILABLE:
            logger.warning("gir1.2-keybinder-3.0 is not installed. Global shortcut disabled.")
            return

        if not self._keybinder_initialized:
            try:
                Keybinder.init()
                Keybinder.set_use_cooked_accelerators(False)
                self._keybinder_initialized = True
            except Exception as e:
                logger.error("Failed to initialize Keybinder: %s", e)
                return

        # Avoid re-registering if it is exactly the same combination
        if self.current_shortcut == shortcut_str and shortcut_str is not None:
            return

        # Unbind the previous shortcut safely
        if self.current_shortcut:
            try:
                Keybinder.unbind(self.current_shortcut)
            except Exception:
                pass
            self.current_shortcut = None

        if not shortcut_str:
            return

        try:
            success = Keybinder.bind(shortcut_str, self._on_shortcut_triggered, None)
            if success:
                self.current_shortcut = shortcut_str
                logger.info(
                    "Global shortcut registered successfully: %s",
                    shortcut_str,
                )
            else:
                logger.warning(
                    "Failed to register global shortcut: %s",
                    shortcut_str,
                )
        except Exception as e:
            logger.error("Failed to bind shortcut %s: %s", shortcut_str, e)

    def _on_shortcut_triggered(self, keystring, user_data):
        """Callback executed when the global key combination is pressed."""
        logger.debug("Global shortcut triggered: %s", keystring)
        if self.quick_menu:
            GLib.idle_add(self.quick_menu.toggle_window)

    def do_activate(self):
        # Keep the process alive in the background
        self.hold()

        # Show a warning if the configuration was restored automatically
        if self.clipboard_manager.settings.config_was_reset:
            dialog = Gtk.MessageDialog(
                parent=None,
                flags=0,
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.OK,
                text=_("Configuration restored"),
            )
            dialog.format_secondary_text(
                _("The configuration file contained invalid data and was reset to the default "
                  "values.")
            )
            dialog.run()
            dialog.destroy()

            self.clipboard_manager.settings.config_was_reset = False

        # 1. Tray dropdown menu
        if self.quick_menu is None:
            self.quick_menu = QuickMenuWindow(
                clipboard_manager=self.clipboard_manager,
                on_open_main_window_callback=self.open_main_window,
                on_quit_app_callback=self.quit_app,
            )
            self.quick_menu.set_application(self)

        # 2. Initialize the system tray icon if it does not exist
        if self.tray_icon is None:
            self.tray_icon = TrayIcon(
                app=self,
                clipboard_manager=self.clipboard_manager,
                menu_window=self.quick_menu,
            )

        # 3. Register the global keyboard shortcut from the configuration
        shortcut = self.clipboard_manager.settings.get("shortcut")
        self._setup_global_shortcut(shortcut)

        # 4. Start monitoring the clipboard
        self.clipboard_manager.connect_to_changes()


def main():
    app = ClipboardApp()
    return app.run(None)


if __name__ == "__main__":
    main()