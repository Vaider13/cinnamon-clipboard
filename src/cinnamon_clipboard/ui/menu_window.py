import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gtk, Gdk, Pango, GLib


class QuickMenuWindow(Gtk.Window):
    """Ventana desplegable estilo menú nativo para la bandeja de Cinnamon."""

    def __init__(self, clipboard_manager, on_open_main_window_callback=None):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)

        self.clipboard_manager = clipboard_manager
        self.on_open_main_window_callback = on_open_main_window_callback

        # Configuración de pistas de ventana para Muffin (Cinnamon)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)
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

        self._fade_timer_id = None

        # Cierre automático
        self.connect("key-press-event", self._on_key_press)
        self.connect("focus-out-event", lambda w, e: self.hide_animated())

    def toggle_window(self):
        """Abre o cierra la ventana desplegable."""
        if self.get_visible() and self.get_opacity() > 0.1:
            self.hide_animated()
        else:
            self.refresh_and_show()

    def hide_animated(self):
        """Oculta la ventana mediante desvanecimiento suave."""
        if self._fade_timer_id:
            GLib.source_remove(self._fade_timer_id)

        def _fade_step():
            current_opacity = self.get_opacity()
            if current_opacity <= 0.1:
                self.hide()
                self._fade_timer_id = None
                return False
            self.set_opacity(current_opacity - 0.2)
            return True

        self._fade_timer_id = GLib.timeout_add(15, _fade_step)

    def _update_position(self):
        """Calcula y aplica la posición fija anclando siempre la base sobre el panel."""
        self.check_resize()  # Forzar a GTK a recalcular el tamaño del widget reducido
        screen = Gdk.Screen.get_default()
        monitor_geom = screen.get_monitor_geometry(0)

        # Obtener el tamaño preferido real actual
        _, req_height = self.get_preferred_height()
        win_w = 340
        win_h = max(req_height, 100)

        pos_x = monitor_geom.x + monitor_geom.width - win_w - 15
        pos_y = monitor_geom.y + monitor_geom.height - win_h - 50

        self.move(pos_x, pos_y)

    def refresh_and_show(self):
        """Reconstruye el contenido, posiciona y aplica fade-in."""
        for child in self.main_box.get_children():
            self.main_box.remove(child)

        history = self.clipboard_manager.history

        if not history:
            empty_label = Gtk.Label(label="Historial vacío")
            empty_label.set_margin_top(16)
            empty_label.set_margin_bottom(16)
            self.main_box.pack_start(empty_label, False, False, 0)
        else:
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scrolled.set_max_content_height(420)
            scrolled.set_propagate_natural_height(True)

            list_box = Gtk.ListBox()
            list_box.set_selection_mode(Gtk.SelectionMode.NONE)
            scrolled.add(list_box)

            for item in history:
                row_item = self._create_item_row(item)
                list_box.add(row_item)

            self.main_box.pack_start(scrolled, True, True, 0)

        self.main_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)

        # Barra inferior
        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        btn_clear = Gtk.Button(label="Vaciar todo")
        btn_clear.connect("clicked", self._on_clear_all)
        bottom_box.pack_start(btn_clear, False, False, 0)

        spacer = Gtk.Box()
        bottom_box.pack_start(spacer, True, True, 0)

        if self.on_open_main_window_callback:
            btn_app = Gtk.Button(label="Abrir aplicación")
            btn_app.connect("clicked", self._on_open_app)
            bottom_box.pack_end(btn_app, False, False, 0)

        self.main_box.pack_start(bottom_box, False, False, 0)

        self.show_all()

        # Ajustar posición anclada a la base
        self._update_position()

        if self.get_window():
            self.get_window().raise_()

        # Fade in si recién se abre
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

    def _create_item_row(self, item):
        """Crea un Gtk.ListBoxRow con soporte nativo de Hover y clic en 'X'."""
        list_row = Gtk.ListBoxRow()

        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        grid.set_row_spacing(4)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_top(6)
        grid.set_margin_bottom(6)

        # 1. CASO IMAGEN
        if item["type"] == "image":
            if item.get("pixbuf"):
                img_widget = Gtk.Image.new_from_pixbuf(item["pixbuf"])
                img_widget.set_hexpand(True)
                img_widget.set_halign(Gtk.Align.START)
                grid.attach(img_widget, 0, 0, 1, 1)
            else:
                label = Gtk.Label(label="[Imagen]", xalign=0)
                grid.attach(label, 0, 0, 1, 1)

        # 2. CASO ARCHIVOS
        elif item["type"] == "files":
            box_file = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            icon_file = Gtk.Image.new_from_icon_name("folder-documents-symbolic", Gtk.IconSize.BUTTON)
            box_file.pack_start(icon_file, False, False, 0)

            label = Gtk.Label(label=item["preview"], xalign=0)
            label.set_line_wrap(True)
            label.set_lines(2)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            box_file.pack_start(label, True, True, 0)

            grid.attach(box_file, 0, 0, 1, 1)

        # 3. CASO TEXTO
        else:
            full_text = item["data"].strip()
            truncated_text = full_text[:250] + "..." if len(full_text) > 250 else full_text

            label = Gtk.Label(label=truncated_text, xalign=0)
            label.set_line_wrap(True)
            label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            label.set_lines(3)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_max_width_chars(30)
            label.set_size_request(240, -1)
            grid.attach(label, 0, 0, 1, 1)

        grid.get_child_at(0, 0).set_hexpand(True)

        # Botón 'X'
        btn_delete = Gtk.Button.new_from_icon_name("window-close-symbolic", Gtk.IconSize.BUTTON)
        btn_delete.set_relief(Gtk.ReliefStyle.NONE)
        btn_delete.set_valign(Gtk.Align.CENTER)
        btn_delete.set_halign(Gtk.Align.END)
        btn_delete.connect("clicked", lambda b, i_id=item["id"]: self._on_delete_item(i_id))

        grid.attach(btn_delete, 1, 0, 1, 1)

        list_row.add(grid)
        list_row.connect("button-press-event", lambda w, e, it=item: self._on_select_item(it))

        return list_row

    def _on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide_animated()
            return True
        return False

    def _on_select_item(self, item):
        if item["type"] == "text":
            self.clipboard_manager.clipboard.set_text(item["data"], -1)
        self.hide_animated()

    def _on_delete_item(self, item_id):
        self.clipboard_manager.remove_item(item_id)
        self.refresh_and_show()

    def _on_clear_all(self, btn):
        self.clipboard_manager.clear_history()
        self.refresh_and_show()

    def _on_open_app(self, btn):
        self.hide_animated()
        if self.on_open_main_window_callback:
            self.on_open_main_window_callback()