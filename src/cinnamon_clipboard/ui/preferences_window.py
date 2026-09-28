import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import Gtk, Gdk


class PreferencesWindow(Gtk.Window):
    """Ventana de configuración/preferencias de Cinnamon Clipboard."""

    def __init__(self, settings_manager, clipboard_manager, on_shortcut_changed_callback=None):
        super().__init__(title="Preferencias")
        self.settings = settings_manager
        self.clipboard_manager = clipboard_manager
        self.on_shortcut_changed_callback = on_shortcut_changed_callback

        self.set_default_size(520, 480)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        # Cargar valores temporales (para aplicar solo si da clic en "Guardar")
        self.temp_settings = {
            "enable_history": self.settings.get("enable_history"),
            "max_history": self.settings.get("max_history"),
            "save_images": self.settings.get("save_images"),
            "save_files": self.settings.get("save_files"),
            "autostart": self.settings.get("autostart"),
            "shortcut": self.settings.get("shortcut"),
        }

        self.is_capturing_shortcut = False

        # Contenedor principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        self.add(main_box)

        # Grid principal para alineación uniforme de filas
        grid = Gtk.Grid()
        grid.set_column_spacing(24)
        grid.set_row_spacing(14)
        grid.set_hexpand(True)
        main_box.pack_start(grid, True, True, 0)

        row = 0

        # --- SECCIÓN 1: HISTORIAL Y PRIVACIDAD ---
        lbl_sec1 = Gtk.Label(xalign=0)
        lbl_sec1.set_markup("<b>Historial y Privacidad</b>")
        grid.attach(lbl_sec1, 0, row, 2, 1)
        row += 1

        lbl_enable = Gtk.Label(label="Guardar historial (Modo Privado):", xalign=0)
        self.switch_enable = Gtk.Switch()
        self.switch_enable.set_halign(Gtk.Align.END)
        self.switch_enable.set_active(self.temp_settings["enable_history"])
        self.switch_enable.connect("state-set", lambda s, state: self._set_temp("enable_history", state))
        grid.attach(lbl_enable, 0, row, 1, 1)
        grid.attach(self.switch_enable, 1, row, 1, 1)
        row += 1

        lbl_limit = Gtk.Label(label="Límite del historial:", xalign=0)
        box_radio = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box_radio.set_halign(Gtk.Align.END)

        current_limit = self.temp_settings["max_history"]
        self.radio_10 = Gtk.RadioButton.new_with_label(None, "10")
        self.radio_25 = Gtk.RadioButton.new_with_label_from_widget(self.radio_10, "25")
        self.radio_50 = Gtk.RadioButton.new_with_label_from_widget(self.radio_10, "50")

        if current_limit == 10:
            self.radio_10.set_active(True)
        elif current_limit == 25:
            self.radio_25.set_active(True)
        else:
            self.radio_50.set_active(True)

        self.radio_10.connect("toggled", lambda b: b.get_active() and self._set_temp("max_history", 10))
        self.radio_25.connect("toggled", lambda b: b.get_active() and self._set_temp("max_history", 25))
        self.radio_50.connect("toggled", lambda b: b.get_active() and self._set_temp("max_history", 50))

        box_radio.pack_start(self.radio_10, False, False, 0)
        box_radio.pack_start(self.radio_25, False, False, 0)
        box_radio.pack_start(self.radio_50, False, False, 0)

        grid.attach(lbl_limit, 0, row, 1, 1)
        grid.attach(box_radio, 1, row, 1, 1)
        row += 1

        sep1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep1.set_margin_top(4)
        sep1.set_margin_bottom(4)
        grid.attach(sep1, 0, row, 2, 1)
        row += 1

        # --- SECCIÓN 2: CAPTURA DE CONTENIDO ---
        lbl_sec2 = Gtk.Label(xalign=0)
        lbl_sec2.set_markup("<b>Captura de Contenido</b>")
        grid.attach(lbl_sec2, 0, row, 2, 1)
        row += 1

        lbl_img = Gtk.Label(label="Capturar imágenes:", xalign=0)
        self.switch_images = Gtk.Switch()
        self.switch_images.set_halign(Gtk.Align.END)
        self.switch_images.set_active(self.temp_settings["save_images"])
        self.switch_images.connect("state-set", lambda s, state: self._set_temp("save_images", state))
        grid.attach(lbl_img, 0, row, 1, 1)
        grid.attach(self.switch_images, 1, row, 1, 1)
        row += 1

        lbl_files = Gtk.Label(label="Capturar archivos y carpetas:", xalign=0)
        self.switch_files = Gtk.Switch()
        self.switch_files.set_halign(Gtk.Align.END)
        self.switch_files.set_active(self.temp_settings["save_files"])
        self.switch_files.connect("state-set", lambda s, state: self._set_temp("save_files", state))
        grid.attach(lbl_files, 0, row, 1, 1)
        grid.attach(self.switch_files, 1, row, 1, 1)
        row += 1

        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep2.set_margin_top(4)
        sep2.set_margin_bottom(4)
        grid.attach(sep2, 0, row, 2, 1)
        row += 1

        # --- SECCIÓN 3: SISTEMA Y ATAJO ---
        lbl_sec3 = Gtk.Label(xalign=0)
        lbl_sec3.set_markup("<b>Sistema y Atajo</b>")
        grid.attach(lbl_sec3, 0, row, 2, 1)
        row += 1

        lbl_auto = Gtk.Label(label="Iniciar con la sesión:", xalign=0)
        self.switch_autostart = Gtk.Switch()
        self.switch_autostart.set_halign(Gtk.Align.END)
        self.switch_autostart.set_active(self.temp_settings["autostart"])
        self.switch_autostart.connect("state-set", lambda s, state: self._set_temp("autostart", state))
        grid.attach(lbl_auto, 0, row, 1, 1)
        grid.attach(self.switch_autostart, 1, row, 1, 1)
        row += 1

        lbl_shortcut = Gtk.Label(label="Atajo del menú de la bandeja:", xalign=0)
        self.btn_shortcut = Gtk.Button(label=self._format_shortcut_label(self.temp_settings["shortcut"]))
        self.btn_shortcut.set_halign(Gtk.Align.END)
        self.btn_shortcut.connect("clicked", self._start_capturing_shortcut)
        grid.attach(lbl_shortcut, 0, row, 1, 1)
        grid.attach(self.btn_shortcut, 1, row, 1, 1)
        row += 1

        # BARRA INFERIOR DE ACCIONES (CANCELAR / GUARDAR)
        main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)

        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bottom_box.set_halign(Gtk.Align.END)

        btn_cancel = Gtk.Button(label="Cancelar")
        btn_cancel.connect("clicked", lambda b: self.destroy())
        bottom_box.pack_start(btn_cancel, False, False, 0)

        btn_save = Gtk.Button(label="Guardar")
        btn_save.get_style_context().add_class("suggested-action")
        btn_save.connect("clicked", self._on_save_clicked)
        bottom_box.pack_start(btn_save, False, False, 0)

        main_box.pack_start(bottom_box, False, False, 0)

        self.connect("key-press-event", self._on_key_press_event)
        self.show_all()

    def _set_temp(self, key, value):
        self.temp_settings[key] = value
        return False

    def _format_shortcut_label(self, shortcut_str):
        if not shortcut_str:
            return "Haz clic para asignar"
        return shortcut_str.replace("<Super>", "Super + ").replace("<Ctrl>", "Ctrl + ").replace("<Alt>", "Alt + ").replace("<Shift>", "Shift + ")

    def _start_capturing_shortcut(self, btn):
        self.is_capturing_shortcut = True
        self.btn_shortcut.set_label("Presione una combinación...")

    def _on_key_press_event(self, widget, event):
        if not self.is_capturing_shortcut:
            return False

        keyval = event.keyval
        state = event.state

        # Ignorar presiones de modificadores aislados
        if keyval in (Gdk.KEY_Control_L, Gdk.KEY_Control_R,
                      Gdk.KEY_Shift_L, Gdk.KEY_Shift_R,
                      Gdk.KEY_Alt_L, Gdk.KEY_Alt_R,
                      Gdk.KEY_Super_L, Gdk.KEY_Super_R):
            return True

        # Esc para cancelar captura
        if keyval == Gdk.KEY_Escape:
            self.is_capturing_shortcut = False
            self.btn_shortcut.set_label(self._format_shortcut_label(self.temp_settings["shortcut"]))
            return True

        modifiers = []
        if state & Gdk.ModifierType.SUPER_MASK or state & Gdk.ModifierType.MOD4_MASK:
            modifiers.append("<Super>")
        if state & Gdk.ModifierType.CONTROL_MASK:
            modifiers.append("<Ctrl>")
        if state & Gdk.ModifierType.MOD1_MASK:
            modifiers.append("<Alt>")
        if state & Gdk.ModifierType.SHIFT_MASK:
            modifiers.append("<Shift>")

        key_name = Gdk.keyval_name(keyval)
        if key_name:
            key_str = key_name.lower()
            shortcut_code = "".join(modifiers) + key_str
            self.temp_settings["shortcut"] = shortcut_code
            self.btn_shortcut.set_label(self._format_shortcut_label(shortcut_code))

        self.is_capturing_shortcut = False
        return True

    def _on_save_clicked(self, btn):
        # Guardar permanentemente en SettingsManager
        for k, v in self.temp_settings.items():
            if k == "autostart":
                self.settings.set_autostart(v)
            else:
                self.settings.set(k, v)

        # Actualizar valores en ClipboardManager
        self.clipboard_manager.apply_max_history(self.temp_settings["max_history"])

        # Notificar atajo global a App
        if self.on_shortcut_changed_callback:
            self.on_shortcut_changed_callback(self.temp_settings["shortcut"])

        self.destroy()
