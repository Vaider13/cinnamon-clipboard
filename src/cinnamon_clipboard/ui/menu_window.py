import os
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Pango", "1.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gtk, Gdk, GdkPixbuf, Pango, GLib

from ..i18n import _
from .preferences_window import PreferencesWindow



class QuickMenuWindow(Gtk.Window):
    """Ventana desplegable estilo menú nativo para la bandeja de Cinnamon."""

    def __init__(self, clipboard_manager, on_open_main_window_callback=None, on_quit_app_callback=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.clipboard_manager = clipboard_manager
        self.on_open_main_window_callback = on_open_main_window_callback
        self.on_quit_app_callback = on_quit_app_callback
        print(f"[DEBUG] CALLBACK RECIBIDO EN __init__ = {on_quit_app_callback}")
        print(f"[DEBUG] QuickMenuWindow creado. callback = {on_quit_app_callback}")
        self.pref_window = None
        self.panel_x = None
        self.panel_y = None
        self.panel_position = None

        # Configuración para Muffin (Cinnamon)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DROPDOWN_MENU)
        self.set_keep_above(True)

        self.set_default_size(340, -1)

        # Marco exterior con sombra nativa
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.OUT)
        self.add(frame)

        # Contenedor principal
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.main_box.set_margin_top(8)
        self.main_box.set_margin_bottom(8)
        self.main_box.set_margin_start(8)
        self.main_box.set_margin_end(8)
        frame.add(self.main_box)

        # 1. Barra de búsqueda estática
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(_("Search.."))
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.main_box.pack_start(self.search_entry, False, False, 0)

        # 2. Área de lista scrolleable
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_propagate_natural_height(True)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.connect("row-activated", self._on_row_activated)
        self.list_box.set_filter_func(self._filter_list_func)
        self.scrolled.add(self.list_box)

        self.main_box.pack_start(self.scrolled, True, True, 0)

        # 3. Separador e interior
        self.separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_box.pack_start(self.separator, False, False, 0)

        self.bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self.btn_clear = Gtk.Button(label=_("Clear all"))
        self.btn_clear.connect("clicked", self._on_clear_all)
        self.bottom_box.pack_start(self.btn_clear, False, False, 0)

        btn_pref = Gtk.Button.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.BUTTON)
        btn_pref.set_tooltip_text(_("Preferences"))
        btn_pref.connect("clicked", self._open_preferences)
        self.bottom_box.pack_start(btn_pref, False, False, 0)

        # Botón para salir/cerrar la app completamente
        btn_exit = Gtk.Button.new_from_icon_name("application-exit-symbolic", Gtk.IconSize.BUTTON)
        btn_exit.set_tooltip_text(_("Close Cinnamon Clipboard"))
        btn_exit.connect("clicked", self._on_quit_app)
        self.bottom_box.pack_start(btn_exit, False, False, 0)

        spacer = Gtk.Box()
        self.bottom_box.pack_start(spacer, True, True, 0)

        if self.on_open_main_window_callback:
            btn_app = Gtk.Button(label=_("Open application"))
            btn_app.connect("clicked", self._on_open_app)
            self.bottom_box.pack_end(btn_app, False, False, 0)

        self.main_box.pack_start(self.bottom_box, False, False, 0)

        self._fade_timer_id = None
        self._seat_grabbed = False

        # Suscribir a eventos del historial para actualizar en tiempo real
        self.clipboard_manager.add_history_listener(self._on_history_updated_external)

        # Eventos de teclado y clics
        self.connect("key-press-event", self._on_key_press)
        self.connect("button-press-event", self._on_button_press)
        self.connect("focus-out-event", self._on_focus_out)

    def _open_preferences(self, btn):
        self.hide_animated()
        if self.pref_window is None or not self.pref_window.get_visible():
            app = self.get_application()
            shortcut_cb = app.update_global_shortcut if app else None
            self.pref_window = PreferencesWindow(
                self.clipboard_manager.settings,
                self.clipboard_manager,
                on_shortcut_changed_callback=shortcut_cb
            )
            self.pref_window.show_all()
        else:
            self.pref_window.present()

    def _filter_list_func(self, row):
        """Filtra dinámicamente las filas sin reconstruir los widgets."""
        query = self.search_entry.get_text().strip().lower()
        if not query:
            return True

        item = getattr(row, "item_data", None)
        if not item:
            return True

        preview = str(item.get("preview", "")).lower()
        data_str = str(item.get("data", "")).lower()
        return query in preview or query in data_str

    def _on_search_changed(self, entry):
        """Aplica el filtro nativo sin tocar la memoria de GTK."""
        self.list_box.invalidate_filter()

    def _on_history_updated_external(self):
        """Si la ventana está visible, la refresca ante cambios externos."""
        if self.get_visible():
            self.refresh_and_show()

    def toggle_window(self):
        """Abre o cierra la ventana desplegable."""
        if self.get_visible() and self.get_opacity() > 0.1:
            self.hide_animated()
        else:
            self.refresh_and_show()

    def _release_grab(self):
        """Libera la captura del dispositivo de entrada X11/GDK de forma segura."""
        if not self._seat_grabbed:
            return

        display = Gdk.Display.get_default()
        if display:
            seat = display.get_default_seat()
            if seat:
                seat.ungrab()

        self._seat_grabbed = False

    def hide_animated(self):
        """Oculta la ventana mediante desvanecimiento suave."""
        self._release_grab()

        if self._fade_timer_id:
            GLib.source_remove(self._fade_timer_id)

        def _fade_step():
            current_opacity = self.get_opacity()
            if current_opacity <= 0.1:
                self.hide()
                self.set_opacity(1.0)  # Dejar opacidad limpia
                self._fade_timer_id = None
                return False
            self.set_opacity(current_opacity - 0.2)
            return True

        self._fade_timer_id = GLib.timeout_add(15, _fade_step)

    def _on_focus_out(self, widget, event):
        """Si pierde el foco, verifica si el clic fue afuera para cerrar."""
        if self.get_visible():
            self.hide_animated()
        return False

    def _on_button_press(self, widget, event):
        """Si el evento de clic ocurrió fuera del rectángulo del menú, se cierra."""
        alloc = self.get_allocation()
        if event.x < 0 or event.x >= alloc.width or event.y < 0 or event.y >= alloc.height:
            self.hide_animated()
            return True
        return False

    def _update_position(self):
        """Calcula la posición del menú según la orientación y posición del panel."""
        self.check_resize()

        screen = Gdk.Screen.get_default()
        monitor_geom = screen.get_monitor_geometry(0)

        # Límite máximo de altura del menú.
        _, req_height = self.get_preferred_height()

        win_w = 340

        # Calculamos cuánto espacio vertical tenemos realmente
        # según la posición del panel.
        if self.panel_position == Gtk.PositionType.BOTTOM and self.panel_y is not None:
            max_allowed_height = self.panel_y - monitor_geom.y

        elif self.panel_position == Gtk.PositionType.TOP and self.panel_y is not None:
            max_allowed_height = (monitor_geom.y + monitor_geom.height) - self.panel_y

        else:
            # Fallback para cuando todavía no conocemos la posición del panel.
            max_allowed_height = min(500, int(monitor_geom.height * 0.45))

        # Dejamos un pequeño margen de seguridad.
        max_allowed_height = max(90, max_allowed_height - 5)

        win_h = min(max(req_height, 90), max_allowed_height)

        print(
            f"[DEBUG] ESPACIO MONITOR: "
            f"alto={monitor_geom.height}, "
            f"máximo_actual={max_allowed_height}, "
            f"preferido={req_height}, "
            f"final={win_h}"
        )

        # Si todavía no tenemos información de XApp,
        # usamos la posición anterior como fallback.
        if self.panel_x is None or self.panel_y is None:
            pos_x = monitor_geom.x + monitor_geom.width - win_w - 15
            pos_y = monitor_geom.y + monitor_geom.height - win_h - 50
            self.move(pos_x, pos_y)

            return

        # XApp usa Gtk.PositionType para indicar dónde está el panel.
        if self.panel_position == Gtk.PositionType.BOTTOM:
            # Panel abajo → menú encima del panel.
            pos_x = self.panel_x - (win_w // 2)
            pos_y = self.panel_y - win_h

        elif self.panel_position == Gtk.PositionType.TOP:
            # Panel arriba → menú debajo del panel.
            pos_x = self.panel_x - (win_w // 2)
            pos_y = self.panel_y

        elif self.panel_position == Gtk.PositionType.LEFT:
            # Panel izquierdo → menú a la derecha del panel.
            pos_x = self.panel_x
            pos_y = self.panel_y - (win_h // 2)

        elif self.panel_position == Gtk.PositionType.RIGHT:
            # Panel derecho → menú a la izquierda del panel.
            pos_x = self.panel_x - win_w
            pos_y = self.panel_y - (win_h // 2)

        else:
            # Orientación desconocida → fallback.
            pos_x = monitor_geom.x + monitor_geom.width - win_w - 15
            pos_y = monitor_geom.y + monitor_geom.height - win_h - 50

        # Evitar que el menú se salga de los límites del monitor.
        pos_x = max(monitor_geom.x, min(pos_x, monitor_geom.x + monitor_geom.width - win_w))
        pos_y = max(monitor_geom.y, min(pos_y, monitor_geom.y + monitor_geom.height - win_h))

        print(
            f"[DEBUG] POSICIÓN CALCULADA: "
            f"x={pos_x}, y={pos_y}, "
            f"ancho={win_w}, alto={win_h}, "
            f"panel_position={self.panel_position}"
    )

        self.move(pos_x, pos_y)

    def refresh_and_show(self):
        """Puebla o actualiza la lista de forma segura y muestra el menú."""
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
            self.scrolled.set_max_content_height(max_height_limit - 50)

            size_group_btn = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

            for item in history:
                row_item = self._create_item_row(item, size_group_btn)
                self.list_box.add(row_item)

        self.list_box.invalidate_filter()
        self.show_all()
        self._update_position()

        if self.get_window():
            self.get_window().raise_()

        self.present()

        # Posicionar cursor en el buscador si está abierto
        self.search_entry.grab_focus()

        # Intentar capturar el Seat. Si Cinnamon lo retiene, se reintentará mediante GLib timeout
        GLib.timeout_add(30, self._grab_seat)

        # Fade-in suave
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

    def _grab_seat(self):
        """Intenta capturar el Seat. Devuelve True para reintentar si Cinnamon tenía el clic capturado."""
        if not self.get_visible():
            return False

        window = self.get_window()

        if window and not self._seat_grabbed:
            display = Gdk.Display.get_default()

            if display:
                seat = display.get_default_seat()

                if seat:
                    status = seat.grab(
                        window,
                        Gdk.SeatCapabilities.POINTER,
                        True,
                        None,
                        None,
                        None
                    )

                    if status == Gdk.GrabStatus.SUCCESS:
                        self._seat_grabbed = True
                        return False  # Éxito: detiene el ciclo de reintentos
                    elif status == Gdk.GrabStatus.ALREADY_GRABBED:
                        return True  # Reintenta automáticamente en el próximo ciclo de 30ms

        return False

    def _create_item_row(self, item, size_group_btn):
        """Crea una fila del historial con vista previa limpia y alineación estricta."""
        list_row = Gtk.ListBoxRow()
        list_row.item_data = item

        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        grid.set_row_spacing(4)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_top(6)
        grid.set_margin_bottom(6)

        # 1. IMAGEN
        if item["type"] == "image":
            if item.get("pixbuf"):
                img_widget = Gtk.Image.new_from_pixbuf(item["pixbuf"])
                img_widget.set_halign(Gtk.Align.START)
                grid.attach(img_widget, 0, 0, 1, 1)
            else:
                label = Gtk.Label(label="[Imagen]", xalign=0)
                grid.attach(label, 0, 0, 1, 1)

            # Espaciador en columna 1 con hexpand=True
            spacer = Gtk.Box()
            spacer.set_hexpand(True)
            size_group_btn.add_widget(spacer)
            grid.attach(spacer, 1, 0, 1, 1)

        # 2. ARCHIVOS / CARPETAS
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
            grid.attach(spacer, 1, 0, 1, 1)

        # 3. TEXTO
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

            # Ícono indicativo de texto
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

        # BOTÓN ANCLAR / PIN (COLUMNA 2)
        is_pinned = item.get("pinned", False)
        btn_pin = Gtk.Button.new_from_icon_name("view-pin-symbolic", Gtk.IconSize.BUTTON)
        btn_pin.set_relief(Gtk.ReliefStyle.NONE)
        btn_pin.set_valign(Gtk.Align.CENTER)
        btn_pin.set_halign(Gtk.Align.CENTER)

        if not is_pinned:
            btn_pin.set_opacity(0.30)
        else:
            btn_pin.set_opacity(1.0)

        btn_pin.set_tooltip_text(_("Unpin") if is_pinned else _("Pin to top"))
        btn_pin.connect("clicked", lambda b, i_id=item["id"]: self._on_toggle_pin(i_id))

        grid.attach(btn_pin, 2, 0, 1, 1)

        # BOTÓN ELIMINAR (COLUMNA 3)
        btn_delete = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.BUTTON)
        btn_delete.set_relief(Gtk.ReliefStyle.NONE)
        btn_delete.set_valign(Gtk.Align.CENTER)
        btn_delete.set_halign(Gtk.Align.CENTER)
        btn_delete.connect("clicked", lambda b, i_id=item["id"]: self._on_delete_item(i_id))

        grid.attach(btn_delete, 3, 0, 1, 1)

        list_row.add(grid)
        return list_row

    def _toggle_text_expand(self, button, label, full_text, preview_text):
        """Expande o contrae el texto mostrando el contenido completo o su vista previa de 3 líneas."""
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
        """Acción ejecutada al hacer clic en cualquier fila de la lista."""
        item = getattr(row, "item_data", None)
        if not item:
            return

        self.clipboard_manager.copy_item_to_system(item)
        self.hide_animated()

    def _on_toggle_pin(self, item_id):
        self.clipboard_manager.toggle_pin_item(item_id)
        self.refresh_and_show()

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide_animated()
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
        if self.on_open_main_window_callback:
            self.on_open_main_window_callback()

    def _on_quit_app(self, btn):
        print("[DEBUG] BOTÓN SALIR PRESIONADO")
        self.hide_animated()

        print(f"[DEBUG] CALLBACK SALIDA = {self.on_quit_app_callback}")

        if self.on_quit_app_callback:
            self.on_quit_app_callback()