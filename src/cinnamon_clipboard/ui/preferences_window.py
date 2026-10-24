import gi
import logging

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")

from gi.repository import Gtk, Gdk

logger = logging.getLogger(__name__)

from ..i18n import _
from ..update_checker import check_for_updates
from ..installation import PACKAGE_MANAGED


class PreferencesWindow(Gtk.Window):
    """Cinnamon Clipboard configuration/preferences window."""

    def __init__(
        self,
        settings_manager,
        clipboard_manager,
        on_shortcut_changed_callback=None,
        app=None,
    ):
        super().__init__(title=_("Preferences"))

        self.set_wmclass("cinnamon-clipboard", "CinnamonClipboard")
        
        self.settings = settings_manager
        self.clipboard_manager = clipboard_manager
        self.on_shortcut_changed_callback = on_shortcut_changed_callback
        self.app = app

        self.set_default_size(520, 620)
        self.set_resizable(True)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        # Load temporary values (to apply only if the user clicks "Save")
        self.temp_settings = {
            "enable_history": self.settings.get("enable_history"),
            "history_mode": self.settings.get("history_mode") or "persistent",
            "max_history": self.settings.get("max_history"),
            "save_images": self.settings.get("save_images"),
            "save_files": self.settings.get("save_files"),
            "autostart": self.settings.get("autostart"),
            "focus_first_item": self.settings.get("focus_first_item"),
            "paste_on_select": self.settings.get("paste_on_select"),
            "shortcut": self.settings.get("shortcut"),
            "check_updates": self.settings.get("check_updates"),
        }

        self.is_capturing_shortcut = False

        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        main_box.set_margin_top(16)
        main_box.set_margin_bottom(16)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        self.add(main_box)

        # Main grid for uniform row alignment
        grid = Gtk.Grid()
        grid.set_column_spacing(24)
        grid.set_row_spacing(14)
        grid.set_hexpand(True)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC,
        )
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.add(grid)
        main_box.pack_start(scrolled_window, True, True, 0)

        row = 0

                # --- SECTION 1: HISTORY AND PRIVACY ---
        lbl_sec1 = Gtk.Label(xalign=0)
        lbl_sec1.set_markup(
            f'<span size="large"><b>🕘 {_("History and Privacy")}</b></span>'
        )
        grid.attach(lbl_sec1, 0, row, 2, 1)
        row += 1

        # Indent the section contents
        lbl_enable = Gtk.Label(
            label=_("Save history (Private Mode):"), xalign=0
        )
        lbl_enable.set_margin_start(18)

        self.switch_enable = Gtk.Switch()
        self.switch_enable.set_halign(Gtk.Align.END)
        self.switch_enable.set_active(self.temp_settings["enable_history"])
        self.switch_enable.connect(
            "state-set",
            lambda s, state: self._set_temp("enable_history", state)
        )

        grid.attach(lbl_enable, 0, row, 1, 1)
        grid.attach(self.switch_enable, 1, row, 1, 1)
        row += 1

        # History storage mode
        lbl_mode = Gtk.Label(xalign=0)
        lbl_mode.set_markup(f'<b>{_("History mode")}</b>')
        lbl_mode.set_margin_start(18)
        lbl_mode.set_halign(Gtk.Align.START)
        grid.attach(lbl_mode, 0, row, 2, 1)
        row += 1

        self.radio_persistent = Gtk.RadioButton.new_with_label(
            None, _("Persistent history")
        )
        self.radio_persistent.set_halign(Gtk.Align.START)
        self.radio_persistent.set_margin_start(36)

        self.radio_temporary = Gtk.RadioButton.new_with_label_from_widget(
            self.radio_persistent, _("Temporary history")
        )
        self.radio_temporary.set_halign(Gtk.Align.START)
        self.radio_temporary.set_margin_start(36)

        current_mode = self.temp_settings.get("history_mode") or "persistent"
        self.radio_persistent.set_active(current_mode == "persistent")
        self.radio_temporary.set_active(current_mode == "temporary")

        self.radio_persistent.connect(
            "toggled",
            lambda b: b.get_active() and self._set_temp(
                "history_mode", "persistent"
            )
        )
        self.radio_temporary.connect(
            "toggled",
            lambda b: b.get_active() and self._set_temp(
                "history_mode", "temporary"
            )
        )

        lbl_persistent_desc = Gtk.Label(
            label=_(
                "The history is stored in an SQLite database on disk, "
                "along with images. Items are preserved when closing "
                "the application or restarting the PC."
            ),
            xalign=0
        )
        lbl_persistent_desc.set_line_wrap(True)
        lbl_persistent_desc.set_max_width_chars(55)
        lbl_persistent_desc.set_halign(Gtk.Align.START)
        lbl_persistent_desc.set_margin_start(60)

        lbl_temporary_desc = Gtk.Label(
            label=_(
                "The history is kept in RAM and is lost when closing "
                "the application or shutting down or restarting the PC. "
                "No persistent copy of the history is saved to disk."
            ),
            xalign=0
        )
        lbl_temporary_desc.set_line_wrap(True)
        lbl_temporary_desc.set_max_width_chars(55)
        lbl_temporary_desc.set_halign(Gtk.Align.START)
        lbl_temporary_desc.set_margin_start(60)

        grid.attach(self.radio_persistent, 0, row, 2, 1)
        row += 1

        grid.attach(lbl_persistent_desc, 0, row, 2, 1)
        row += 1

        grid.attach(self.radio_temporary, 0, row, 2, 1)
        row += 1

        grid.attach(lbl_temporary_desc, 0, row, 2, 1)
        row += 1

        lbl_limit = Gtk.Label(label=_("History limit:"), xalign=0)
        lbl_limit.set_margin_start(18)

        box_radio = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=12
        )
        box_radio.set_halign(Gtk.Align.END)

        current_limit = self.temp_settings["max_history"]
        self.radio_10 = Gtk.RadioButton.new_with_label(None, "10")
        self.radio_25 = Gtk.RadioButton.new_with_label_from_widget(
            self.radio_10, "25"
        )
        self.radio_50 = Gtk.RadioButton.new_with_label_from_widget(
            self.radio_10, "50"
        )
        self.radio_75 = Gtk.RadioButton.new_with_label_from_widget(
            self.radio_10, "75"
        )
        self.radio_100 = Gtk.RadioButton.new_with_label_from_widget(
            self.radio_10, "100"
        )

        if current_limit == 10:
            self.radio_10.set_active(True)
        elif current_limit == 25:
            self.radio_25.set_active(True)
        elif current_limit == 75:
            self.radio_75.set_active(True)
        elif current_limit == 100:
            self.radio_100.set_active(True)
        else:
            self.radio_50.set_active(True)

        self.radio_10.connect(
            "toggled",
            lambda b: b.get_active() and self._set_temp("max_history", 10)
        )
        self.radio_25.connect(
            "toggled",
            lambda b: b.get_active() and self._set_temp("max_history", 25)
        )
        self.radio_50.connect(
            "toggled",
            lambda b: b.get_active() and self._set_temp("max_history", 50)
        )
        self.radio_75.connect(
            "toggled",
            lambda b: b.get_active() and self._set_temp("max_history", 75)
        )
        self.radio_100.connect(
            "toggled",
            lambda b: b.get_active() and self._set_temp("max_history", 100)
        )

        box_radio.pack_start(self.radio_10, False, False, 0)
        box_radio.pack_start(self.radio_25, False, False, 0)
        box_radio.pack_start(self.radio_50, False, False, 0)
        box_radio.pack_start(self.radio_75, False, False, 0)
        box_radio.pack_start(self.radio_100, False, False, 0)

        grid.attach(lbl_limit, 0, row, 1, 1)
        grid.attach(box_radio, 1, row, 1, 1)
        row += 1

        sep1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep1.set_margin_top(4)
        sep1.set_margin_bottom(4)
        grid.attach(sep1, 0, row, 2, 1)
        row += 1

        # --- SECTION 2: CONTENT CAPTURE ---
        lbl_sec2 = Gtk.Label(xalign=0)
        lbl_sec2.set_markup(
            f'<span size="large"><b>📥 {_("Content Capture")}</b></span>'
        )
        grid.attach(lbl_sec2, 0, row, 2, 1)
        row += 1

        lbl_img = Gtk.Label(label=_("Capture images:"), xalign=0)
        lbl_img.set_margin_start(18)

        self.switch_images = Gtk.Switch()
        self.switch_images.set_halign(Gtk.Align.END)
        self.switch_images.set_active(self.temp_settings["save_images"])
        self.switch_images.connect(
            "state-set",
            lambda s, state: self._set_temp("save_images", state)
        )

        grid.attach(lbl_img, 0, row, 1, 1)
        grid.attach(self.switch_images, 1, row, 1, 1)
        row += 1

        lbl_files = Gtk.Label(
            label=_("Capture files and folders:"), xalign=0
        )
        lbl_files.set_margin_start(18)

        self.switch_files = Gtk.Switch()
        self.switch_files.set_halign(Gtk.Align.END)
        self.switch_files.set_active(self.temp_settings["save_files"])
        self.switch_files.connect(
            "state-set",
            lambda s, state: self._set_temp("save_files", state)
        )

        grid.attach(lbl_files, 0, row, 1, 1)
        grid.attach(self.switch_files, 1, row, 1, 1)
        row += 1

        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep2.set_margin_top(4)
        sep2.set_margin_bottom(4)
        grid.attach(sep2, 0, row, 2, 1)
        row += 1

        # --- SECTION 3: SYSTEM AND SHORTCUT ---
        lbl_sec3 = Gtk.Label(xalign=0)
        lbl_sec3.set_markup(
            f'<span size="large"><b>⚙️ {_("System and Shortcut")}</b></span>'
        )
        grid.attach(lbl_sec3, 0, row, 2, 1)
        row += 1

        lbl_auto = Gtk.Label(label=_("Start with session:"), xalign=0)
        lbl_auto.set_margin_start(18)

        self.switch_autostart = Gtk.Switch()
        self.switch_autostart.set_halign(Gtk.Align.END)
        self.switch_autostart.set_active(self.temp_settings["autostart"])
        self.switch_autostart.connect(
            "state-set",
            lambda s, state: self._set_temp("autostart", state)
        )

        grid.attach(lbl_auto, 0, row, 1, 1)
        grid.attach(self.switch_autostart, 1, row, 1, 1)
        row += 1

        lbl_shortcut = Gtk.Label(label=_("Tray menu shortcut:"), xalign=0)
        lbl_shortcut.set_margin_start(18)

        self.btn_shortcut = Gtk.Button(
            label=self._format_shortcut_label(
                self.temp_settings["shortcut"]
            )
        )
        self.btn_shortcut.set_halign(Gtk.Align.END)
        self.btn_shortcut.connect(
            "clicked", self._start_capturing_shortcut
        )

        grid.attach(lbl_shortcut, 0, row, 1, 1)
        grid.attach(self.btn_shortcut, 1, row, 1, 1)
        row += 1

        lbl_focus_first = Gtk.Label(
            label=_("Focus first item when opening menu:"), xalign=0
        )
        lbl_focus_first.set_margin_start(18)

        self.switch_focus_first = Gtk.Switch()
        self.switch_focus_first.set_halign(Gtk.Align.END)
        self.switch_focus_first.set_active(
            self.temp_settings["focus_first_item"]
        )
        self.switch_focus_first.connect(
            "state-set",
            lambda s, state: self._set_temp("focus_first_item", state)
        )

        grid.attach(lbl_focus_first, 0, row, 1, 1)
        grid.attach(self.switch_focus_first, 1, row, 1, 1)
        row += 1

        lbl_paste_select = Gtk.Label(
            label=_("Paste automatically when selecting an item:"),
            xalign=0
        )
        lbl_paste_select.set_margin_start(18)

        self.switch_paste_select = Gtk.Switch()
        self.switch_paste_select.set_halign(Gtk.Align.END)
        self.switch_paste_select.set_active(
            self.temp_settings["paste_on_select"]
        )
        self.switch_paste_select.connect(
            "state-set",
            lambda s, state: self._set_temp("paste_on_select", state)
        )

        grid.attach(lbl_paste_select, 0, row, 1, 1)
        grid.attach(self.switch_paste_select, 1, row, 1, 1)
        row += 1

        # --- SECTION 4: UPDATES ---
        sep3 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep3.set_margin_top(4)
        sep3.set_margin_bottom(4)
        grid.attach(sep3, 0, row, 2, 1)
        row += 1

        lbl_sec4 = Gtk.Label(xalign=0)
        lbl_sec4.set_markup(
            f'<span size="large"><b>🔄 {_("Updates")}</b></span>'
        )
        grid.attach(lbl_sec4, 0, row, 2, 1)
        row += 1

        lbl_check_updates = Gtk.Label(
            label=_("Check for updates at startup:"),
            xalign=0,
        )
        lbl_check_updates.set_margin_start(18)

        self.switch_check_updates = Gtk.Switch()
        self.switch_check_updates.set_halign(Gtk.Align.END)
        self.switch_check_updates.set_active(
            self.temp_settings["check_updates"]
        )
        self.switch_check_updates.connect(
            "state-set",
            lambda switch, state: self._set_temp("check_updates", state),
        )

        grid.attach(lbl_check_updates, 0, row, 1, 1)
        grid.attach(self.switch_check_updates, 1, row, 1, 1)
        row += 1

        self.btn_check_updates = Gtk.Button(
            label=_("Check for updates now")
        )
        self.btn_check_updates.connect(
            "clicked",
            self._on_check_updates_clicked,
        )

        self.lbl_update_status = Gtk.Label(xalign=0)
        self.lbl_update_status.set_line_wrap(True)
        self.lbl_update_status.set_margin_start(18)

        grid.attach(self.lbl_update_status, 0, row, 1, 1)
        grid.attach(self.btn_check_updates, 1, row, 1, 1)
        row += 1

        if PACKAGE_MANAGED:
            self.switch_check_updates.set_sensitive(False)
            self.btn_check_updates.set_sensitive(False)
            self.lbl_update_status.set_text(
                _("Updates are managed by APT.")
            )


        # LOWER ACTION BAR (CANCEL / SAVE)
        main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)

        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bottom_box.set_halign(Gtk.Align.END)

        btn_cancel = Gtk.Button(label=_("Cancel"))
        btn_cancel.connect("clicked", lambda b: self.destroy())
        bottom_box.pack_start(btn_cancel, False, False, 0)

        btn_save = Gtk.Button(label=_("Save"))
        btn_save.get_style_context().add_class("suggested-action")
        btn_save.connect("clicked", self._on_save_clicked)
        bottom_box.pack_start(btn_save, False, False, 0)

        main_box.pack_start(bottom_box, False, False, 0)

        self.connect("key-press-event", self._on_key_press_event)

    def _set_temp(self, key, value):
        self.temp_settings[key] = value
        return False

    def _on_check_updates_clicked(self, button):
        if self.app is None:
            self.lbl_update_status.set_text(
                _("Unable to check for updates.")
            )
            return

        self.btn_check_updates.set_sensitive(False)
        self.lbl_update_status.set_text(_("Checking for updates..."))

        check_for_updates(
            self.app,
            callback=self._on_manual_update_result,
            notify_if_new=False,
        )

    def _on_manual_update_result(self, status, release):
        self.btn_check_updates.set_sensitive(True)

        if status == "current":
            self.lbl_update_status.set_text(
                _("Cinnamon Clipboard is up to date.")
            )
            return

        if status == "error":
            self.lbl_update_status.set_text(
                _("Unable to check for updates.")
            )
            return

        self.lbl_update_status.set_text(
            _("A new version is available.")
        )

        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.NONE,
            text=_("A new version of Cinnamon Clipboard is available."),
        )

        dialog.format_secondary_text(
            _("Version %(version)s is available.")
            % {"version": release["version"]}
        )

        changelog = release.get("body", "").strip()
        if changelog:
            dialog.get_message_area().pack_start(
                Gtk.Label(label=changelog, xalign=0),
                False,
                False,
                8,
            )
            dialog.get_message_area().show_all()

        dialog.add_button(_("Later"), Gtk.ResponseType.CANCEL)
        dialog.add_button(_("View release"), Gtk.ResponseType.ACCEPT)

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            import webbrowser
            webbrowser.open(release["url"])

    def _format_shortcut_label(self, shortcut_str):
        if not shortcut_str:
            return _("Click to assign")
        return shortcut_str.replace("<Super>", "Super + ").replace("<Ctrl>", "Ctrl + ").replace("<Alt>", "Alt + ").replace("<Shift>", "Shift + ")

    def _start_capturing_shortcut(self, btn):
        self.is_capturing_shortcut = True
        self.btn_shortcut.set_label(_("Press a key combination..."))

    def _on_key_press_event(self, widget, event):
        if not self.is_capturing_shortcut:
            return False

        keyval = event.keyval
        state = event.state

        # Ignore isolated modifier key presses
        if keyval in (Gdk.KEY_Control_L, Gdk.KEY_Control_R,
                      Gdk.KEY_Shift_L, Gdk.KEY_Shift_R,
                      Gdk.KEY_Alt_L, Gdk.KEY_Alt_R,
                      Gdk.KEY_Super_L, Gdk.KEY_Super_R):
            return True

        # Esc to cancel capture
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

    def _confirm_history_mode_change(self, old_mode, new_mode):
        if old_mode == "persistent" and new_mode == "temporary":
            title = _("Switch to temporary history?")
            explanation = _(
                "The saved clipboard history database and its images "
                "will be permanently deleted. The application will restart "
                "with an empty history stored only in memory."
            )
            message_type = Gtk.MessageType.WARNING
            continue_label = _("Delete history and switch")
        else:
            title = _("Switch to persistent history?")
            explanation = _(
                "The temporary history will be lost when the application "
                "restarts. Persistent history will start empty."
            )
            message_type = Gtk.MessageType.QUESTION
            continue_label = _("Restart and switch")

        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=message_type,
            buttons=Gtk.ButtonsType.NONE,
            text=title,
        )
        dialog.format_secondary_text(explanation)
        dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        dialog.add_button(continue_label, Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.CANCEL)

        response = dialog.run()
        dialog.destroy()

        return response == Gtk.ResponseType.OK

    def _delete_persistent_history(self):
        """Remove persistent history using ClipboardManager's implementation."""
        self.clipboard_manager._clean_persistent_storage()

    def _show_history_delete_error(self, error):
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=_("Could not delete the saved history"),
        )
        dialog.format_secondary_text(
            _(
                "The history mode has not been changed. "
                "Check the file permissions and try again."
            )
            + "\n\n"
            + str(error)
        )
        dialog.run()
        dialog.destroy()


    def _show_settings_save_error(self):
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=_("Could not save preferences"),
        )
        dialog.format_secondary_text(
            _(
                "The preferences could not be saved. "
                "Check the file permissions and try again."
            )
        )
        dialog.run()
        dialog.destroy()


    def _on_save_clicked(self, btn):
        old_settings = dict(self.settings.settings)
        old_mode = old_settings.get("history_mode") or "persistent"
        new_mode = self.temp_settings.get("history_mode") or "persistent"
        mode_changed = old_mode != new_mode
        old_autostart = old_settings.get("autostart", False)
        new_autostart = self.temp_settings["autostart"]
        autostart_snapshot = None

        if mode_changed:
            if not self._confirm_history_mode_change(old_mode, new_mode):
                self.temp_settings["history_mode"] = old_mode
                self.radio_persistent.set_active(old_mode == "persistent")
                self.radio_temporary.set_active(old_mode == "temporary")
                return

        if new_autostart != old_autostart:
            try:
                autostart_snapshot = (
                    self.settings.snapshot_autostart_file()
                )
            except OSError:
                logger.exception("Could not inspect autostart file")
                self._show_settings_save_error()
                return

            if not self.settings.set_autostart(new_autostart):
                self.settings.settings["autostart"] = old_autostart
                self.settings.restore_autostart_file(autostart_snapshot)
                self._show_settings_save_error()
                return

        self.settings.settings.update(self.temp_settings)
        if not self.settings.save():
            self.settings.settings.clear()
            self.settings.settings.update(old_settings)
            config_restored = self.settings.save()

            autostart_restored = True
            if autostart_snapshot is not None:
                autostart_restored = (
                    self.settings.restore_autostart_file(
                        autostart_snapshot
                    )
                )

            if not config_restored or not autostart_restored:
                logger.critical(
                    "Could not fully restore preferences after save failure"
                )

            self._show_settings_save_error()
            return

        if mode_changed:
            try:
                self._delete_persistent_history()
            except OSError as error:
                self.settings.settings.clear()
                self.settings.settings.update(old_settings)
                self.settings.save()

                if autostart_snapshot is not None:
                    self.settings.restore_autostart_file(
                        autostart_snapshot
                    )

                self.temp_settings["history_mode"] = old_mode
                self.radio_persistent.set_active(old_mode == "persistent")
                self.radio_temporary.set_active(old_mode == "temporary")
                self._show_history_delete_error(error)
                return

        self.clipboard_manager.apply_max_history(
            self.temp_settings["max_history"]
        )

        if self.on_shortcut_changed_callback:
            self.on_shortcut_changed_callback(
                self.temp_settings["shortcut"]
            )

        self.destroy()

        if mode_changed and self.app is not None:
            self.app.restart_app()

