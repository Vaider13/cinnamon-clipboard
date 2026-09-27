import gi

gi.require_version("Gtk", "3.0")
try:
    gi.require_version("Keybinder", "3.0")
    from gi.repository import Keybinder
    KEYBINDER_AVAILABLE = True
except Exception:
    KEYBINDER_AVAILABLE = False

from gi.repository import GLib, Gtk

from .core.clipboard import ClipboardManager
from .ui.main_window import MainWindow
from .ui.menu_window import QuickMenuWindow
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
        self.quick_menu = None
        self.current_shortcut = None
        self._keybinder_initialized = False

    def open_main_window(self):
        """Abre la ventana principal con un solo clic o la trae al frente."""
        if self.main_window is None:
            self.main_window = MainWindow(self.clipboard_manager)
            self.main_window.set_application(self)
            self.main_window.connect("destroy", self._on_main_window_destroyed)
            self.main_window.show_all()
            self.main_window.present()
        else:
            self.main_window.show_all()
            self.main_window.present()

    def _on_main_window_destroyed(self, widget):
        self.main_window = None

    def quit_app(self):
        """Cierra completamente la aplicación y libera el servicio."""
        print("[DEBUG] quit_app() FUE LLAMADO")
        if self.quick_menu:
            self.quick_menu.destroy()
        if self.main_window:
            self.main_window.destroy()
        self.release()  # Cancela el self.hold() para salir del loop principal de GTK
        self.quit()

    def update_global_shortcut(self, shortcut_str):
        """Actualiza el atajo global registrado cuando el usuario lo cambia en preferencias."""
        self._setup_global_shortcut(shortcut_str)

    def _setup_global_shortcut(self, shortcut_str):
        """Registra o actualiza el atajo de teclado global con Keybinder de forma segura."""
        if not KEYBINDER_AVAILABLE:
            print("[ADVERTENCIA] gir1.2-keybinder-3.0 no está instalado. Atajo global desactivado.")
            return

        if not self._keybinder_initialized:
            try:
                Keybinder.init()
                self._keybinder_initialized = True
            except Exception as e:
                print(f"[ERROR] Falló la inicialización de Keybinder: {e}")
                return

        # Evitar re-registrar si es exactamente la misma combinación
        if self.current_shortcut == shortcut_str and shortcut_str is not None:
            return

        # Desvincular atajo anterior de forma segura
        if self.current_shortcut:
            try:
                Keybinder.unbind(self.current_shortcut)
                print(f"[ATAJO GLOBAL] Desvinculado atajo previo: {self.current_shortcut}")
            except Exception:
                pass
            self.current_shortcut = None

        if not shortcut_str:
            return

        try:
            success = Keybinder.bind(shortcut_str, self._on_shortcut_triggered, None)
            if success:
                self.current_shortcut = shortcut_str
                print(f"[ATAJO GLOBAL] Registrado con éxito: {shortcut_str}")
            else:
                print(f"[ERROR] No se pudo vincular el atajo: {shortcut_str}")
        except Exception as e:
            print(f"[ERROR] Fallo al vincular atajo {shortcut_str}: {e}")

    def _on_shortcut_triggered(self, keystring, user_data):
        """Callback ejecutado al presionar la combinación de teclas global."""
        print(f"[DIAGNÓSTICO ATAJO] Evento Keybinder capturado: {keystring}")
        if self.quick_menu:
            GLib.idle_add(self.quick_menu.toggle_window)

    def do_activate(self):
        # Mantiene el proceso activo en segundo plano
        self.hold()

        # 1. Menú desplegable del Tray
        if self.quick_menu is None:
            self.quick_menu = QuickMenuWindow(
                clipboard_manager=self.clipboard_manager,
                on_open_main_window_callback=self.open_main_window,
                on_quit_app_callback=self.quit_app,
            )
            self.quick_menu.set_application(self)

        # 2. Inicializar el ícono de la bandeja del sistema si no existe
        if self.tray_icon is None:
            self.tray_icon = TrayIcon(
                app=self,
                clipboard_manager=self.clipboard_manager,
                menu_window=self.quick_menu,
            )

        # 3. Registrar atajo de teclado global desde la configuración
        shortcut = self.clipboard_manager.settings.get("shortcut")
        self._setup_global_shortcut(shortcut)

        # 4. Iniciar el monitoreo del portapapeles
        self.clipboard_manager.connect_to_changes()


def main():
    app = ClipboardApp()
    return app.run(None)


if __name__ == "__main__":
    main()