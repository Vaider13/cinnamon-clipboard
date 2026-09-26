from dasbus.connection import SessionMessageBus
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gio", "2.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gtk, Gio, GLib


class StatusNotifierItemDBus:
    """Implementa la interfaz DBus org.kde.StatusNotifierItem para la bandeja de Cinnamon."""

    __dbus_xml__ = """
    <node>
        <interface name="org.kde.StatusNotifierItem">
            <property name="Category" type="s" access="read"/>
            <property name="Id" type="s" access="read"/>
            <property name="Title" type="s" access="read"/>
            <property name="Status" type="s" access="read"/>
            <property name="IconName" type="s" access="read"/>
            <property name="OverlayIconName" type="s" access="read"/>
            <property name="ToolTip" type="(sa{sv}ss)" access="read"/>
            <method name="Activate">
                <arg direction="in" type="i" name="x"/>
                <arg direction="in" type="i" name="y"/>
            </method>
            <method name="ContextMenu">
                <arg direction="in" type="i" name="x"/>
                <arg direction="in" type="i" name="y"/>
            </method>
            <method name="SecondaryActivate">
                <arg direction="in" type="i" name="x"/>
                <arg direction="in" type="i" name="y"/>
            </method>
        </interface>
    </node>
    """

    def __init__(self, on_activate_callback):
        self.on_activate_callback = on_activate_callback

    @property
    def Category(self) -> str:
        return "ApplicationStatus"

    @property
    def Id(self) -> str:
        return "cinnamon-clipboard"

    @property
    def Title(self) -> str:
        return "Cinnamon Clipboard"

    @property
    def Status(self) -> str:
        return "Active"

    @property
    def IconName(self) -> str:
        return "edit-paste-symbolic"

    @property
    def OverlayIconName(self) -> str:
        return ""

    @property
    def ToolTip(self):
        return ("edit-paste-symbolic", {}, "Cinnamon Clipboard", "Historial de portapapeles")

    def Activate(self, x: int, y: int):
        """Clic izquierdo en el ícono del panel."""
        if self.on_activate_callback:
            GLib.idle_add(self.on_activate_callback)

    def ContextMenu(self, x: int, y: int):
        """Clic derecho en el ícono del panel."""
        if self.on_activate_callback:
            GLib.idle_add(self.on_activate_callback)

    def SecondaryActivate(self, x: int, y: int):
        """Clic secundario."""
        if self.on_activate_callback:
            GLib.idle_add(self.on_activate_callback)


class TrayIcon:
    """Registra el ícono en la bandeja del sistema de Cinnamon vía DBus StatusNotifierItem."""

    def __init__(self, app, clipboard_manager, on_open_app_callback=None):
        self.app = app
        self.clipboard_manager = clipboard_manager
        self.on_open_app_callback = on_open_app_callback

        try:
            self.session_bus = SessionMessageBus()
            self.sni = StatusNotifierItemDBus(on_activate_callback=self._on_tray_click)

            # Publicar objeto en DBus
            self.session_bus.publish_object("/StatusNotifierItem", self.sni)
            self.session_bus.register_service("com.github.vaider13.CinnamonClipboard.StatusNotifierItem")

            # Registrar en el Watcher de la bandeja de Cinnamon
            watcher = self.session_bus.get_proxy(
                "org.kde.StatusNotifierWatcher",
                "/StatusNotifierWatcher"
            )
            watcher.RegisterStatusNotifierItem("/StatusNotifierItem")

            print("[OK] Ícono registrado nativamente vía DBus (StatusNotifierItem) en Cinnamon.")
        except Exception as e:
            print(f"[ERROR] No se pudo registrar el ícono en la bandeja por DBus: {e}")

    def _on_tray_click(self):
        """Callback al presionar el ícono en el panel."""
        print("[EVENTO] Se hizo clic en el ícono de la bandeja.")
        if self.on_open_app_callback:
            self.on_open_app_callback()