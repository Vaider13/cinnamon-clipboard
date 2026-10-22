import logging
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Pango", "1.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib

try:
    gi.require_version("GdkX11", "3.0")
    from gi.repository import GdkX11
    HAS_GDKX11 = True
except (ValueError, ImportError):
    HAS_GDKX11 = False

from ..i18n import _

logger = logging.getLogger(__name__)



class QuickMenuWindow(Gtk.Window):
    """Native menu-style dropdown window for the Cinnamon tray."""

    def __init__(self, clipboard_manager):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.clipboard_manager = clipboard_manager
        self.panel_x = None
        self.panel_y = None
        self.panel_position = None

        # Configuration for Muffin (Cinnamon)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DROPDOWN_MENU)
        self.set_keep_above(True)

        self.set_default_size(340, -1)

        # Outer frame with native shadow
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.OUT)
        self.add(frame)

        # Main container
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.main_box.set_margin_top(8)
        self.main_box.set_margin_bottom(8)
        self.main_box.set_margin_start(8)
        self.main_box.set_margin_end(8)
        frame.add(self.main_box)

        # 1. Static search bar
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(_("Search.."))
        self.search_entry.connect("changed", self._on_search_changed)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.main_box.pack_start(self.search_entry, False, False, 0)

        # 2. Scrollable list area
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_propagate_natural_height(True)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.connect("row-activated", self._on_row_activated)
        self.list_box.set_filter_func(self._filter_list_func)
        self.scrolled.add(self.list_box)

        self.main_box.pack_start(self.scrolled, True, True, 0)

        # 3. Divider and inner section
        self.separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_box.pack_start(self.separator, False, False, 0)

        self.bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self.btn_clear = Gtk.Button(label=_("Clear history"))
        self.btn_clear.set_tooltip_text(_("Delete all unpinned history items"))
        self.btn_clear.connect("clicked", self._on_clear_all)
        self.bottom_box.pack_start(self.btn_clear, False, False, 0)

        btn_pref = Gtk.Button.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.BUTTON)
        btn_pref.set_tooltip_text(_("Preferences"))
        btn_pref.connect("clicked", self._open_preferences)
        self.bottom_box.pack_start(btn_pref, False, False, 0)

        # Button to exit/close the app completely
        btn_exit = Gtk.Button.new_from_icon_name("application-exit-symbolic", Gtk.IconSize.BUTTON)
        btn_exit.set_tooltip_text(_("Close Cinnamon Clipboard"))
        btn_exit.connect("clicked", self._on_quit_app)
        self.bottom_box.pack_start(btn_exit, False, False, 0)

        spacer = Gtk.Box()
        self.bottom_box.pack_start(spacer, True, True, 0)

        btn_app = Gtk.Button(label=_("Open application"))
        btn_app.connect("clicked", self._on_open_app)
        self.bottom_box.pack_end(btn_app, False, False, 0)

        self.main_box.pack_start(self.bottom_box, False, False, 0)

        self._fade_timer_id = None
        self._seat_grabbed = False

        # Subscribe to history events to update in real time
        self.clipboard_manager.add_history_listener(self._on_history_updated_external)

        # Keyboard, click, and lifecycle events
        self.connect("key-press-event", self._on_key_press)
        self.connect("button-press-event", self._on_button_press)
        self.connect("focus-out-event", self._on_focus_out)
        self.connect("destroy", self._on_destroy)

    def _on_destroy(self, widget):
        """Unsubscribe from the history listener when the window is destroyed to avoid memory leaks."""
        self.clipboard_manager.remove_history_listener(self._on_history_updated_external)

    def _open_preferences(self, btn):
        self.hide_animated()

        app = self.get_application()
        if app:
            app.open_preferences()

    def _filter_list_func(self, row):
        """Filter rows dynamically without rebuilding widgets."""
        query = self.search_entry.get_text().strip().lower()
        if not query:
            return True

        item = getattr(row, "item_data", None)
        if not item:
            return True

        preview = str(item.get("preview", "")).lower()
        data_str = str(item.get("data", "")).lower()
        return query in preview or query in data_str

    def _get_visible_rows(self):
        """Return all rows currently matching the search filter."""
        return [
            row for row in self.list_box.get_children()
            if self._filter_list_func(row)
        ]

    def _select_first_visible_row(self, grab_focus=False):
        """Select the first visible row in the list and optionally focus it."""
        visible_rows = self._get_visible_rows()
        if visible_rows:
            first_row = visible_rows[0]
            self.list_box.select_row(first_row)
            if grab_focus:
                first_row.grab_focus()
            return first_row

        self.list_box.unselect_all()
        return None

    def _scroll_to_row(self, row):
        """Ensure the given row is visible within the scrolled window."""
        vadj = self.scrolled.get_vadjustment()
        if not vadj:
            return
        alloc = row.get_allocation()
        if alloc.height <= 0:
            return
        page_size = vadj.get_page_size()
        val = vadj.get_value()
        if alloc.y < val:
            vadj.set_value(alloc.y)
        elif alloc.y + alloc.height > val + page_size:
            vadj.set_value(alloc.y + alloc.height - page_size)

    def _on_search_changed(self, entry):
        """Apply the native filter without touching GTK memory."""
        self.list_box.invalidate_filter()
        self._select_first_visible_row(grab_focus=False)

    def _on_history_updated_external(self):
        """Refresh the window when it is visible and external changes occur."""
        if self.get_visible():
            self.refresh_and_show()

    def toggle_window(self):
        """Open or close the dropdown window."""
        if self.get_visible() and self.get_opacity() > 0.1:
            self.hide_animated()
        else:
            if self.search_entry.get_text():
                self.search_entry.set_text("")
            self.refresh_and_show()

    def _release_grab(self):
        """Safely release the X11/GDK input device grab."""
        if not self._seat_grabbed:
            return

        display = Gdk.Display.get_default()
        if display:
            seat = display.get_default_seat()
            if seat:
                seat.ungrab()

        self._seat_grabbed = False

    def hide_animated(self):
        """Hide the window with a smooth fade-out."""
        self._release_grab()

        if self._fade_timer_id:
            GLib.source_remove(self._fade_timer_id)

        def _fade_step():
            current_opacity = self.get_opacity()
            if current_opacity <= 0.1:
                self.hide()
                self.set_opacity(1.0)  # Leave opacity clean
                self._fade_timer_id = None
                return False
            self.set_opacity(current_opacity - 0.2)
            return True

        self._fade_timer_id = GLib.timeout_add(15, _fade_step)

    def _on_focus_out(self, widget, event):
        """If focus is lost, check whether the click was outside to close."""
        if self.get_visible():
            self.hide_animated()
        return False

    def _on_button_press(self, widget, event):
        """Close the menu when the pointer is clicked outside the menu window."""
        window = self.get_window()

        if window is None:
            return False

        win_x, win_y = self.get_position()
        allocation = self.get_allocation()

        inside = (
            win_x <= event.x_root < win_x + allocation.width
            and win_y <= event.y_root < win_y + allocation.height
        )

        if not inside:
            self.hide_animated()
            return True

        return False

    def _update_position(self):
        """Calculate the menu position according to the panel orientation and position."""
        self.check_resize()

        screen = Gdk.Screen.get_default()
        monitor_geom = screen.get_monitor_geometry(0)

        # Maximum menu height limit.
        _, req_height = self.get_preferred_height()

        win_w = 340

        # Calculate how much vertical space we actually have
        # based on the panel position.
        if self.panel_position == Gtk.PositionType.BOTTOM and self.panel_y is not None:
            max_allowed_height = self.panel_y - monitor_geom.y

        elif self.panel_position == Gtk.PositionType.TOP and self.panel_y is not None:
            max_allowed_height = (monitor_geom.y + monitor_geom.height) - self.panel_y

        else:
            # Fallback when the panel position is still unknown.
            max_allowed_height = min(500, int(monitor_geom.height * 0.45))

        # Leave a small safety margin.
        max_allowed_height = max(90, max_allowed_height - 5)

        win_h = min(max(req_height, 90), max_allowed_height)


        # If we still do not have XApp information,
        # use the previous position as a fallback.
        if self.panel_x is None or self.panel_y is None:
            pos_x = monitor_geom.x + monitor_geom.width - win_w - 15
            pos_y = monitor_geom.y + monitor_geom.height - win_h - 50
            self.move(pos_x, pos_y)

            return

        # XApp uses Gtk.PositionType to indicate where the panel is.
        if self.panel_position == Gtk.PositionType.BOTTOM:
            # Panel at bottom → menu above the panel.
            pos_x = self.panel_x - (win_w // 2)
            pos_y = self.panel_y - win_h

        elif self.panel_position == Gtk.PositionType.TOP:
            # Panel at top → menu below the panel.
            pos_x = self.panel_x - (win_w // 2)
            pos_y = self.panel_y

        elif self.panel_position == Gtk.PositionType.LEFT:
            # Panel on the left → menu to the right of the panel.
            pos_x = self.panel_x
            pos_y = self.panel_y - (win_h // 2)

        elif self.panel_position == Gtk.PositionType.RIGHT:
            # Panel on the right → menu to the left of the panel.
            pos_x = self.panel_x - win_w
            pos_y = self.panel_y - (win_h // 2)

        else:
            # Unknown orientation → fallback.
            pos_x = monitor_geom.x + monitor_geom.width - win_w - 15
            pos_y = monitor_geom.y + monitor_geom.height - win_h - 50

        # Keep the menu within the monitor bounds.
        pos_x = max(monitor_geom.x, min(pos_x, monitor_geom.x + monitor_geom.width - win_w))
        pos_y = max(monitor_geom.y, min(pos_y, monitor_geom.y + monitor_geom.height - win_h))

        self.move(pos_x, pos_y)

    def refresh_and_show(self):
        """Safely populate or update the list and show the menu."""

        for child in self.list_box.get_children():
            self.list_box.remove(child)

        history = self.clipboard_manager.history

        if not history:
            self.btn_clear.set_sensitive(False)
        else:
            self.btn_clear.set_sensitive(True)

            screen = Gdk.Screen.get_default()
            monitor_geom = screen.get_monitor_geometry(0)
            max_height_limit = min(460, int(monitor_geom.height * 0.42))

            self.scrolled.set_min_content_height(1)
            self.scrolled.set_max_content_height(max_height_limit)

            size_group_btn = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

            for item in history:
                row_item = self._create_item_row(item, size_group_btn)
                self.list_box.add(row_item)

        self.list_box.invalidate_filter()
        self.show_all()

        # Always start the menu at the top of the history.
        vadjustment = self.scrolled.get_vadjustment()
        vadjustment.set_value(vadjustment.get_lower())

        self._update_position()

        if self.get_window():
            self.get_window().raise_()

        self._activate_and_focus_window()

        # Try to grab the Seat. If Cinnamon keeps it, it will be retried via GLib timeout
        GLib.timeout_add(30, self._grab_seat)

        # Smooth fade-in
        if not self.get_visible() or self.get_opacity() < 0.9:
            self.set_opacity(0.0)
            if self._fade_timer_id:
                GLib.source_remove(self._fade_timer_id)

            def _fade_in_step():
                current_opacity = self.get_opacity()
                if current_opacity >= 1.0:
                    self.set_opacity(1.0)
                    self._fade_timer_id = None
                    return False
                self.set_opacity(current_opacity + 0.2)
                return True

            self._fade_timer_id = GLib.timeout_add(15, _fade_in_step)

    def _get_x11_timestamp(self):
        """Obtain a current X11 server timestamp so Muffin grants focus."""
        window = self.get_window()
        if window is not None and HAS_GDKX11 and isinstance(window, GdkX11.X11Window):
            try:
                return GdkX11.x11_get_server_time(window)
            except Exception:
                pass
        return Gdk.CURRENT_TIME

    def _apply_initial_focus(self):
        """Focus and select the first item or the search field according to user preference."""
        if self.clipboard_manager.settings.get("focus_first_item"):
            first_row = self._select_first_visible_row(grab_focus=True)
            if first_row is None:
                self.search_entry.grab_focus()
        else:
            self._select_first_visible_row(grab_focus=False)
            self.search_entry.grab_focus()

    def _activate_and_focus_window(self):
        """Activate the top-level window with a valid X11 timestamp and focus the target widget."""
        window = self.get_window()
        timestamp = self._get_x11_timestamp()
        if window is not None and timestamp != Gdk.CURRENT_TIME:
            try:
                window.set_user_time(timestamp)
            except Exception:
                pass
            self.present_with_time(timestamp)
            window.focus(timestamp)
        else:
            self.present()

        self._apply_initial_focus()

    def _grab_seat(self):
        """Attempts to grab the Seat (pointer and keyboard). Returns True to retry if captured."""
        if not self.get_visible():
            return False

        window = self.get_window()

        if window and not self._seat_grabbed:
            timestamp = self._get_x11_timestamp()
            if timestamp != Gdk.CURRENT_TIME:
                try:
                    window.set_user_time(timestamp)
                except Exception:
                    pass
                window.focus(timestamp)

            display = Gdk.Display.get_default()

            if display:
                seat = display.get_default_seat()

                if seat:
                    status = seat.grab(
                        window,
                        Gdk.SeatCapabilities.ALL,
                        True,
                        None,
                        None,
                        None
                    )

                    if status == Gdk.GrabStatus.SUCCESS:
                        self._seat_grabbed = True
                        if not self.search_entry.has_focus():
                            self._apply_initial_focus()
                        return False  # Success: stops the retry loop
                    elif status in (
                        Gdk.GrabStatus.ALREADY_GRABBED,
                        Gdk.GrabStatus.NOT_VIEWABLE,
                    ):
                        return True  # Retry automatically on the next 30ms cycle

        return False

    def _create_item_row(self, item, size_group_btn):
        """Create a history row with a clean preview and strict alignment."""
        list_row = Gtk.ListBoxRow()
        list_row.item_data = item
        list_row.set_can_focus(True)
        list_row.set_activatable(True)

        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        grid.set_row_spacing(4)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_top(6)
        grid.set_margin_bottom(6)

        # 1. IMAGE
        if item["type"] == "image":
            if item.get("pixbuf"):
                img_widget = Gtk.Image.new_from_pixbuf(item["pixbuf"])
                img_widget.set_halign(Gtk.Align.START)
                grid.attach(img_widget, 0, 0, 1, 1)
            else:
                label = Gtk.Label(label="[Imagen]", xalign=0)
                grid.attach(label, 0, 0, 1, 1)

            # Spacer in column 1 with hexpand=True
            spacer = Gtk.Box()
            spacer.set_hexpand(True)
            size_group_btn.add_widget(spacer)
            grid.attach(spacer, 1, 0, 1, 1)

        # 2. FILES / FOLDERS
        elif item["type"] == "files":
            box_file = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            icon_file = Gtk.Image.new_from_icon_name("folder-documents-symbolic", Gtk.IconSize.BUTTON)
            box_file.pack_start(icon_file, False, False, 0)

            label = Gtk.Label(label=item["preview"], xalign=0)
            label.set_line_wrap(True)
            label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            label.set_max_width_chars(22)
            label.set_ellipsize(Pango.EllipsizeMode.END)

            box_file.pack_start(label, True, True, 0)
            grid.attach(box_file, 0, 0, 1, 1)

            spacer = Gtk.Box()
            size_group_btn.add_widget(spacer)
            spacer.set_hexpand(True)
            size_group_btn.add_widget(spacer)
            grid.attach(spacer, 1, 0, 1, 1)

        # 3. TEXT
        else:
            full_text = item["data"].strip()

            raw_lines = full_text.splitlines()
            preview_lines = []

            for line in raw_lines:
                if len(line) > 70:
                    chunks = [line[i:i + 70] for i in range(0, len(line), 70)]
                    preview_lines.extend(chunks)
                else:
                    preview_lines.append(line)

                if len(preview_lines) >= 3:
                    break

            preview_lines = preview_lines[:3]
            preview_text = "\n".join(preview_lines)

            needs_expand = len(raw_lines) > 3 or len(full_text) > 210

            if needs_expand:
                preview_text = preview_text.rstrip() + "..."

            # Text indicator icon
            icon_text = Gtk.Image.new_from_icon_name("edit-paste-symbolic", Gtk.IconSize.BUTTON)
            icon_text.set_valign(Gtk.Align.CENTER)

            label = Gtk.Label(label=preview_text, xalign=0)
            label.set_line_wrap(True)
            label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)

            label.set_size_request(190, -1)
            label.set_hexpand(True)
            label.set_halign(Gtk.Align.START)
            label.set_valign(Gtk.Align.CENTER)
            label.set_selectable(False)

            box_text = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            box_text.pack_start(icon_text, False, False, 0)
            box_text.pack_start(label, True, True, 0)

            grid.attach(box_text, 0, 0, 1, 1)

            if needs_expand:
                btn_expand = Gtk.Button.new_from_icon_name("pan-down-symbolic", Gtk.IconSize.BUTTON)
                btn_expand.set_relief(Gtk.ReliefStyle.NONE)
                btn_expand.set_valign(Gtk.Align.CENTER)
                btn_expand.set_halign(Gtk.Align.CENTER)
                btn_expand.set_can_focus(False)

                btn_expand.expanded = False
                btn_expand.connect(
                    "clicked",
                    self._toggle_text_expand,
                    label,
                    full_text,
                    preview_text
                )

                size_group_btn.add_widget(btn_expand)
                grid.attach(btn_expand, 1, 0, 1, 1)
            else:
                spacer = Gtk.Box()
                size_group_btn.add_widget(spacer)
                grid.attach(spacer, 1, 0, 1, 1)

        # PIN BUTTON (COLUMN 2)
        is_pinned = item.get("pinned", False)
        btn_pin = Gtk.Button.new_from_icon_name("view-pin-symbolic", Gtk.IconSize.BUTTON)
        btn_pin.set_relief(Gtk.ReliefStyle.NONE)
        btn_pin.set_valign(Gtk.Align.CENTER)
        btn_pin.set_halign(Gtk.Align.CENTER)
        btn_pin.set_can_focus(False)

        if not is_pinned:
            btn_pin.set_opacity(0.30)
        else:
            btn_pin.set_opacity(1.0)

        btn_pin.set_tooltip_text(_("Unpin") if is_pinned else _("Pin to top"))
        btn_pin.connect("clicked", lambda b, i_id=item["id"]: self._on_toggle_pin(i_id))

        grid.attach(btn_pin, 2, 0, 1, 1)

        # DELETE BUTTON (COLUMN 3)
        btn_delete = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.BUTTON)
        btn_delete.set_relief(Gtk.ReliefStyle.NONE)
        btn_delete.set_valign(Gtk.Align.CENTER)
        btn_delete.set_halign(Gtk.Align.CENTER)
        btn_delete.set_can_focus(False)
        btn_delete.connect("clicked", lambda b, i_id=item["id"]: self._on_delete_item(i_id))

        grid.attach(btn_delete, 3, 0, 1, 1)

        list_row.add(grid)
        return list_row

    def _toggle_text_expand(self, button, label, full_text, preview_text):
        """Expand or collapse text by showing the full content or its 3-line preview."""
        if not getattr(button, "expanded", False):
            button.expanded = True
            label.set_text(full_text)
            button.set_image(Gtk.Image.new_from_icon_name("pan-up-symbolic", Gtk.IconSize.BUTTON))
        else:
            button.expanded = False
            label.set_text(preview_text)
            button.set_image(Gtk.Image.new_from_icon_name("pan-down-symbolic", Gtk.IconSize.BUTTON))

        GLib.idle_add(self._update_position)

    def _on_row_activated(self, list_box, row):
        """Action executed when any list row is clicked or activated with Enter."""
        item = getattr(row, "item_data", None)
        if not item:
            logger.warning("[QuickMenu] Row activated but no item_data found.")
            return

        # 1. Release the X11 grab and hide immediately and synchronously
        gdk_window = self.get_window()
        menu_xid = (
            gdk_window.get_xid()
            if gdk_window is not None and hasattr(gdk_window, "get_xid")
            else None
        )
        self._release_grab()
        self.hide()  # Hide the window immediately without leaving room for thread interruptions

        # 2. Delegate the copy to the backend
        copied = self.clipboard_manager.copy_item_to_system(item)

        # 3. Paste automatically into the active window if configured
        if copied and self.clipboard_manager.settings.get("paste_on_select"):
            self.clipboard_manager.paste_to_active_window(
                item_type=item.get("type"),
                exclude_xid=menu_xid,
            )

    def _on_toggle_pin(self, item_id):
        self.clipboard_manager.toggle_pin_item(item_id)
        self.refresh_and_show()

    def _on_key_press(self, widget, event):
        keyval = event.keyval

        if keyval == Gdk.KEY_Escape:
            self.hide_animated()
            return True

        # Activate the selected (or first visible) history item on Enter
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_ISO_Enter):
            focused = self.get_focus()
            if isinstance(focused, Gtk.Button):
                return False

            selected_row = self.list_box.get_selected_row()
            if selected_row is None or not self._filter_list_func(selected_row):
                visible_rows = self._get_visible_rows()
                selected_row = visible_rows[0] if visible_rows else None

            if selected_row is not None:
                self._on_row_activated(self.list_box, selected_row)
                return True
            return False

        # Navigate visible history rows with Up/Down arrows
        if keyval in (Gdk.KEY_Down, Gdk.KEY_KP_Down, Gdk.KEY_Up, Gdk.KEY_KP_Up):
            visible_rows = self._get_visible_rows()
            if not visible_rows:
                return True

            current_row = self.list_box.get_selected_row()
            if current_row not in visible_rows:
                target_row = visible_rows[0]
            else:
                idx = visible_rows.index(current_row)
                if keyval in (Gdk.KEY_Down, Gdk.KEY_KP_Down):
                    target_row = visible_rows[min(idx + 1, len(visible_rows) - 1)]
                else:
                    target_row = visible_rows[max(idx - 1, 0)]

            self.list_box.select_row(target_row)
            target_row.grab_focus()
            self._scroll_to_row(target_row)
            return True

        # Type-to-search when the search entry does not currently have focus
        if not self.search_entry.has_focus():
            disallowed_mods = (
                Gdk.ModifierType.CONTROL_MASK
                | Gdk.ModifierType.MOD1_MASK
                | Gdk.ModifierType.SUPER_MASK
                | Gdk.ModifierType.MOD4_MASK
            )
            if not (event.state & disallowed_mods):
                if keyval == Gdk.KEY_BackSpace:
                    current_text = self.search_entry.get_text()
                    self.search_entry.grab_focus()
                    if current_text:
                        self.search_entry.set_text(current_text[:-1])
                    self.search_entry.select_region(-1, -1)
                    self.search_entry.set_position(-1)
                    return True

                if keyval not in (
                    Gdk.KEY_Tab,
                    Gdk.KEY_ISO_Left_Tab,
                    Gdk.KEY_Left,
                    Gdk.KEY_Right,
                    Gdk.KEY_Home,
                    Gdk.KEY_End,
                    Gdk.KEY_Page_Up,
                    Gdk.KEY_Page_Down,
                    Gdk.KEY_Delete,
                ):
                    unichar = Gdk.keyval_to_unicode(keyval)
                    if unichar:
                        char = chr(unichar)
                        if char.isprintable():
                            current_text = self.search_entry.get_text()
                            self.search_entry.grab_focus()
                            self.search_entry.set_text(current_text + char)
                            self.search_entry.select_region(-1, -1)
                            self.search_entry.set_position(-1)
                            return True

        return False

    def _on_delete_item(self, item_id):
        self.clipboard_manager.remove_item(item_id)
        self.refresh_and_show()

    def _on_clear_all(self, btn):
        self.clipboard_manager.clear_history()
        self.refresh_and_show()

    def _on_open_app(self, btn):
        self._release_grab()
        self.hide()

        app = self.get_application()
        if app:
            app.open_main_window()

    def _on_quit_app(self, btn):
        self._release_grab()
        self.hide()

        app = self.get_application()
        if app:
            app.quit_app()