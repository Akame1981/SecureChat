"""Advanced dynamic Theme Editor for Whispr.

Features:
 - Dynamic field generation for every key in the theme JSON.
 - Grouping by key prefixes (sidebar_, bubble_, menu_, font_, server_, strength_, etc.).
 - Supports: colors (#hex), booleans, numbers, strings, font arrays.
 - Live preview panel that updates on change.
 - Add / Delete / Duplicate themes.
 - Export single theme / Import theme.
 - Revert unsaved changes.
 - Highlight changed fields.
"""

import json
import os
import re
import copy
import customtkinter as ctk
from tkinter import filedialog, Menu
from .color_picker import CustomColorPicker

HEX_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class ThemeEditor(ctk.CTkToplevel):
    def __init__(self, master, themes_file, on_save=None, app=None):
        super().__init__(master)
        self.title("Theme Editor")
        self.geometry("1100x640")
        self.minsize(960, 560)
        self.themes_file = themes_file
        self.on_save = on_save
        self.app = app

        self.themes = self._load_themes()
        self.current_name = next(iter(self.themes), None)
        self.original_snapshot = copy.deepcopy(self.themes)

        # widget registries / state
        self.fields = {}
        self.group_members = {}
        self.group_collapsed = {}
        self.theme_items = {}
        self.search_var = ctk.StringVar(value='')

        self._build_layout()
        if self.current_name:
            self._load_theme_into_fields(self.current_name)
        self._update_preview()

    # ---------- Data IO ----------
    def _load_themes(self):
        if os.path.exists(self.themes_file):
            try:
                with open(self.themes_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _write_themes(self):
        try:
            os.makedirs(os.path.dirname(self.themes_file), exist_ok=True)
            with open(self.themes_file, 'w') as f:
                json.dump(self.themes, f, indent=4)
            if self.on_save:
                try:
                    self.on_save()
                except Exception:
                    pass
            if self.app and hasattr(self.app, 'notifier'):
                self.app.notifier.show('Themes saved', type_='success')
            self.original_snapshot = copy.deepcopy(self.themes)
        except Exception as e:
            if self.app and hasattr(self.app, 'notifier'):
                self.app.notifier.show(f'Save failed: {e}', type_='error')

    # ---------- Layout ----------
    def _build_layout(self):
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        # Sidebar (themes list and actions) - modernized with search and compact action bar
        sidebar = ctk.CTkFrame(self, fg_color="#14141a", corner_radius=8)
        sidebar.grid(row=0, column=0, sticky='nsw', padx=8, pady=8)
        sidebar.grid_rowconfigure(2, weight=1)

        # Header
        hdr = ctk.CTkFrame(sidebar, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky='ew', padx=8, pady=(8,6))
        ctk.CTkLabel(hdr, text="Themes", font=("Segoe UI", 15, "bold")).pack(side='left')

        # Search box for themes
        search_wr = ctk.CTkFrame(sidebar, fg_color="#0f0f13")
        search_wr.grid(row=1, column=0, sticky='ew', padx=8, pady=(0,8))
        search_wr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(search_wr, text="🔎", width=20).grid(row=0, column=0, sticky='w', padx=(6,4))
        search_entry = ctk.CTkEntry(search_wr, textvariable=self.search_var, placeholder_text="Search themes...", width=160)
        search_entry.grid(row=0, column=1, sticky='ew', padx=(0,6))
        search_entry.bind('<KeyRelease>', lambda e: self._populate_theme_list())

        self.theme_listbox = ctk.CTkScrollableFrame(sidebar, width=220, fg_color="transparent")
        self.theme_listbox.grid(row=2, column=0, sticky='nsew', padx=8, pady=(0,8))
        self._populate_theme_list()

        # Compact vertical action bar at the bottom of the sidebar
        action_bar = ctk.CTkFrame(sidebar, fg_color="transparent")
        action_bar.grid(row=3, column=0, sticky='ew', padx=8, pady=6)
        ctk.CTkButton(action_bar, text="➕", command=self._add_theme, width=40, height=34, corner_radius=8).grid(row=0, column=0, padx=(0,6))
        ctk.CTkButton(action_bar, text="⧉", command=self._duplicate_theme, width=40, height=34, corner_radius=8).grid(row=0, column=1, padx=6)
        ctk.CTkButton(action_bar, text="🗑", command=self._delete_theme, fg_color="#d9534f", width=40, height=34, corner_radius=8).grid(row=0, column=2, padx=(6,0))

        # Preview area - emphasized, centered live preview with cleaner look
        preview = ctk.CTkFrame(self, fg_color="#0f1720", corner_radius=8)
        preview.grid(row=0, column=1, sticky='ns', padx=(8,8), pady=8)
        preview.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(preview, text="Live Preview", font=("Segoe UI", 14, "bold")).grid(row=0, column=0, pady=(12,6), padx=12, sticky='w')
        self.preview_canvas = ctk.CTkFrame(preview, fg_color="#0b0d11", corner_radius=10)
        self.preview_canvas.grid(row=1, column=0, padx=12, pady=8, sticky='nsew')
        self.preview_canvas.grid_columnconfigure(0, weight=1)
        self.preview_canvas.grid_rowconfigure(0, weight=1)
        self._build_preview_widgets()

        # Editor area (scrollable)
        editor_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        editor_container.grid(row=0, column=2, sticky='nsew', padx=(0,8), pady=8)
        editor_container.grid_columnconfigure(0, weight=1)
        self.editor_container = editor_container

        # Bottom toolbar spans across columns 1 & 2 (primary action left, utilities right)
        toolbar = ctk.CTkFrame(self, fg_color="#071016")
        toolbar.grid(row=1, column=0, columnspan=3, sticky='ew', padx=8, pady=(0,8))
        toolbar.grid_columnconfigure(0, weight=1)
        # Primary action on the left
        self.save_btn = ctk.CTkButton(toolbar, text="Save", command=self._save_current_theme, fg_color="#2ea44f", width=120, corner_radius=10)
        self.save_btn.grid(row=0, column=0, pady=8, padx=12, sticky='w')
        # Utilities grouped on the right
        util_wr = ctk.CTkFrame(toolbar, fg_color="transparent")
        util_wr.grid(row=0, column=1, sticky='e')
        ctk.CTkButton(util_wr, text="Revert", command=self._revert_changes, width=90, fg_color="#6c6f76").grid(row=0, column=0, pady=6, padx=6)
        ctk.CTkButton(util_wr, text="Export", command=self._export_theme, width=90).grid(row=0, column=1, pady=6, padx=6)
        ctk.CTkButton(util_wr, text="Import", command=self._import_theme, width=90).grid(row=0, column=2, pady=6, padx=6)
        self.preview_toggle = ctk.CTkSwitch(util_wr, text="Preview", command=self._update_preview)
        self.preview_toggle.grid(row=0, column=3, pady=6, padx=10)

    # ---------- Preview ----------
    def _build_preview_widgets(self):
        # Resizable columns
        self.preview_canvas.grid_columnconfigure(1, weight=1)
        self.preview_canvas.grid_rowconfigure(0, weight=1)

        # Sidebar mock
        self.preview_sidebar = ctk.CTkFrame(self.preview_canvas, width=140, fg_color="#2a2a3a", corner_radius=8)
        self.preview_sidebar.grid(row=0, column=0, sticky='ns', padx=(4,6), pady=6)
        self.preview_sidebar.grid_propagate(False)
        ctk.CTkLabel(self.preview_sidebar, text="Recipients", font=("Segoe UI", 13, "bold")).pack(anchor='w', padx=8, pady=(8,4))


        # Main area container
        self.preview_main = ctk.CTkFrame(self.preview_canvas, fg_color="#1e1e2f", corner_radius=8)
        self.preview_main.grid(row=0, column=1, sticky='nsew', padx=(0,6), pady=6)
        self.preview_main.grid_columnconfigure(0, weight=1)

        # Chat area container (will hold realistic bubble mocks)
        self.preview_chat = ctk.CTkFrame(self.preview_main, fg_color="transparent")
        self.preview_chat.grid(row=0, column=0, sticky='ew', padx=10, pady=(8,4))
        self.preview_chat.pack_propagate(False)
        # We'll create two bubble frames representing you and other.
        self.prev_timestamp = ctk.CTkLabel(self.preview_chat, text="12:34", font=("Segoe UI", 10))
        self.prev_timestamp.pack(anchor='w', padx=8, pady=(0,4))

        # Bubble containers for user and other
        self.bubble_you_container = ctk.CTkFrame(self.preview_chat, fg_color="transparent")
        self.bubble_other_container = ctk.CTkFrame(self.preview_chat, fg_color="transparent")
        self.bubble_you_container.pack(fill='x', padx=2, pady=(2,2))
        self.bubble_other_container.pack(fill='x', padx=2, pady=(2,6))

        # Actual bubble frames
        self.prev_you = ctk.CTkFrame(self.bubble_you_container, corner_radius=16, border_width=1)
        self.prev_other = ctk.CTkFrame(self.bubble_other_container, corner_radius=16, border_width=1)
        self.prev_you.pack(anchor='e', padx=8)
        self.prev_other.pack(anchor='w', padx=8)
        # Sender labels and message labels
        self.prev_you_sender = ctk.CTkLabel(self.prev_you, text="You", font=("Roboto", 9, 'bold'))
        self.prev_you_msg = ctk.CTkLabel(self.prev_you, text="Hello! This is a preview message.", wraplength=220, justify='right', font=("Roboto", 12))
        self.prev_other_sender = ctk.CTkLabel(self.prev_other, text="Alice", font=("Roboto", 9, 'bold'))
        self.prev_other_msg = ctk.CTkLabel(self.prev_other, text="Hi there! Theme editing rocks.", wraplength=220, justify='left', font=("Roboto", 12))
        for w in (self.prev_you_sender, self.prev_you_msg):
            w.pack(anchor='e', padx=10, pady=(6,2) if w is self.prev_you_sender else (0,6))
        for w in (self.prev_other_sender, self.prev_other_msg):
            w.pack(anchor='w', padx=10, pady=(6,2) if w is self.prev_other_sender else (0,6))

        # Hover simulation labels (appear when we enter bubble to show hover colors)
        def _make_hover(frame, base_getter):
            meta = base_getter()  # Expect a dict with keys: key, hover_key, fallback, fallback_hover
            def on_enter(_):
                try:
                    theme = self._collect_temp_theme()
                    frame.configure(fg_color=theme.get(meta.get('hover_key'), meta.get('fallback_hover')))
                except Exception:
                    pass
            def on_leave(_):
                try:
                    theme = self._collect_temp_theme()
                    base_col = 'transparent' if self._is_transparent(theme) else theme.get(meta.get('key'), meta.get('fallback'))
                    frame.configure(fg_color=base_col)
                except Exception:
                    pass
            frame.bind('<Enter>', on_enter)
            frame.bind('<Leave>', on_leave)
        # Utility to detect transparent mode
        self._is_transparent = lambda th: bool(th.get('bubble_transparent'))
        # Provide metadata via lambdas
        _make_hover(self.prev_you, lambda: {
            'key': 'bubble_you', 'hover_key': 'bubble_hover_you', 'fallback': '#7289da', 'fallback_hover': '#7d8fe0'
        })
        _make_hover(self.prev_other, lambda: {
            'key': 'bubble_other', 'hover_key': 'bubble_hover_other', 'fallback': '#2f3136', 'fallback_hover': '#3a3c45'
        })

        # Input area mock
        self.preview_input_frame = ctk.CTkFrame(self.preview_main, corner_radius=6)
        self.preview_input_frame.grid(row=1, column=0, sticky='ew', padx=10, pady=4)
        self.preview_input_frame.grid_columnconfigure(0, weight=1)
        self.preview_input = ctk.CTkLabel(self.preview_input_frame, text="Type a message...", anchor='w')
        self.preview_input.grid(row=0, column=0, sticky='ew', padx=8, pady=6)
        self.preview_send_btn = ctk.CTkButton(self.preview_input_frame, text="Send", width=70)
        self.preview_send_btn.grid(row=0, column=1, padx=6, pady=6)





    def _update_preview(self, *_):
        if not self.current_name or self.current_name not in self.themes:
            return
        theme = self._collect_temp_theme()
        # background / sidebar
        bg = theme.get('background', '#1e1e2f')
        sidebar_bg = theme.get('sidebar_bg', '#2a2a3a')
        you = theme.get('bubble_you', '#7289da')
        other = theme.get('bubble_other', '#2f3136')
        try:
            # Containers
            self.preview_canvas.configure(fg_color=bg)
            self.preview_main.configure(fg_color=bg)
            self.preview_sidebar.configure(fg_color=sidebar_bg)

            # Sidebar buttons
            active_bg = theme.get('menu_active_bg', theme.get('sidebar_button_hover', '#3d7ddb'))
            active_fg = theme.get('menu_active_fg', theme.get('sidebar_text', '#ffffff'))
            idle_bg = theme.get('sidebar_button', '#5a9bf6')
            idle_fg = theme.get('sidebar_text', '#f0f0f5')
            self.sidebar_btn_active.configure(fg_color=active_bg, text_color=active_fg)
            self.sidebar_btn_idle.configure(fg_color=idle_bg, text_color=idle_fg)
            self.sidebar_btn_more.configure(fg_color=idle_bg, text_color=idle_fg)

            # Bubbles, borders & timestamp
            transparent = bool(theme.get('bubble_transparent', False))
            bubble_you_border = theme.get('bubble_border_you', '#5b6fb3')
            bubble_other_border = theme.get('bubble_border_other', '#2e3038')
            self.prev_you.configure(fg_color=('transparent' if transparent else you),
                                    border_color=bubble_you_border)
            self.prev_other.configure(fg_color=('transparent' if transparent else other),
                                      border_color=bubble_other_border)
            self.prev_you_sender.configure(text_color=theme.get('bubble_you_text', '#ffffff'))
            self.prev_you_msg.configure(text_color=theme.get('bubble_you_text', '#ffffff'))
            self.prev_other_sender.configure(text_color=theme.get('bubble_other_text', '#e6e6e6'))
            self.prev_other_msg.configure(text_color=theme.get('bubble_other_text', '#e6e6e6'))
            self.prev_timestamp.configure(text_color=theme.get('timestamp_text', '#b6b6c2'))

            # Alignment toggle if bubble_align_both_left set
            align_both = bool(theme.get('bubble_align_both_left', False))
            # Repack bubbles if alignment changed
            for container, bubble, sender, msg, is_you in (
                (self.bubble_you_container, self.prev_you, self.prev_you_sender, self.prev_you_msg, True),
                (self.bubble_other_container, self.prev_other, self.prev_other_sender, self.prev_other_msg, False),
            ):
                # Clear existing pack side
                try:
                    bubble.pack_forget()
                except Exception:
                    pass
                side = 'w' if (align_both or not is_you) else 'e'
                bubble.pack(anchor=side, padx=8)
                # Adjust justification of message labels
                try:
                    if is_you and not align_both:
                        msg.configure(justify='right')
                        sender.configure(anchor='e')
                    else:
                        msg.configure(justify='left')
                        sender.configure(anchor='w')
                except Exception:
                    pass

            # Input area
            self.preview_input_frame.configure(fg_color=theme.get('input_bg', '#2f2f44'))
            self.preview_input.configure(text_color=theme.get('placeholder_text', '#a8a8b3'))
            self.preview_send_btn.configure(fg_color=theme.get('button_send', '#5a9bf6'),
                                            hover_color=theme.get('button_send_hover', '#3d7ddb'),
                                            text_color=theme.get('menu_fg', '#ffffff'))

            # Strength bars
            self.str_bar_weak.configure(fg_color=theme.get('strength_weak', '#e74c3c'))
            self.str_bar_med.configure(fg_color=theme.get('strength_medium', '#f1c40f'))
            self.str_bar_str.configure(fg_color=theme.get('strength_strong', '#2ecc71'))

            # Server status
            self.server_online_lbl.configure(fg_color=theme.get('server_online', '#00ff88'), text_color='#000000')
            self.server_offline_lbl.configure(fg_color=theme.get('server_offline', '#ff5555'), text_color='#000000')

            # Public key panel
            self.pub_panel.configure(fg_color=theme.get('pub_frame_bg', '#2f2f44'))
            self.pub_label.configure(text_color=theme.get('pub_text', '#ffffff'))
            self.pub_key_text.configure(text_color=theme.get('pub_text', '#ffffff'))

            # Fonts
            def _font_or(default):
                # Expect [family, size, *style]
                f = theme.get(default)
                if isinstance(f, list) and len(f) >= 2:
                    fam = f[0]
                    size = f[1]
                    style = f[2] if len(f) > 2 else None
                    return (fam, size, style) if style else (fam, size)
                return None
            main_font = _font_or('font_main')
            title_font = _font_or('font_title')
            btn_font = _font_or('font_buttons')
            if main_font:
                for w in (self.prev_you, self.prev_other, self.prev_timestamp, self.preview_input, self.pub_key_text):
                    try: w.configure(font=main_font)
                    except Exception: pass
            if title_font:
                try: self.pub_label.configure(font=title_font)
                except Exception: pass
            if btn_font:
                for b in (self.sidebar_btn_active, self.sidebar_btn_idle, self.sidebar_btn_more, self.preview_send_btn):
                    try: b.configure(font=btn_font)
                    except Exception: pass
        except Exception:
            pass

    # ---------- Theme list ----------
    def _populate_theme_list(self):
        for child in self.theme_listbox.winfo_children():
            child.destroy()
        self.theme_items.clear()
        for name in sorted(self.themes.keys(), key=str.lower):
            data = self.themes[name]
            swatch_bg = data.get('background', '#222')
            accent = data.get('bubble_you', data.get('sidebar_button', '#555'))
            item = ctk.CTkFrame(self.theme_listbox, fg_color="#333541", corner_radius=6)
            item.pack(fill='x', padx=4, pady=4)
            item.bind('<Button-1>', lambda e, n=name: self._select_theme(n))
            # Right-click context menu
            item.bind('<Button-3>', lambda e, n=name: self._show_theme_context(n, e))
            # swatches
            swatch = ctk.CTkFrame(item, width=18, height=18, fg_color=swatch_bg, corner_radius=4)
            swatch.grid(row=0, column=0, padx=6, pady=6)
            accent_box = ctk.CTkFrame(item, width=18, height=18, fg_color=accent, corner_radius=4)
            accent_box.grid(row=0, column=1, padx=(0,6), pady=6)
            lbl = ctk.CTkLabel(item, text=name)
            lbl.grid(row=0, column=2, sticky='w', padx=4)
            for w in (swatch, accent_box, lbl):
                w.bind('<Button-1>', lambda e, n=name: self._select_theme(n))
                w.bind('<Button-3>', lambda e, n=name: self._show_theme_context(n, e))
            self.theme_items[name] = item
        self._highlight_selected_theme()

    def _select_theme(self, name):
        self.current_name = name
        self._load_theme_into_fields(name)
        self._highlight_changes()
        self._update_preview()
        self._highlight_selected_theme()

    # ---------- Field generation ----------
    def _group_for_key(self, key):
        groups = {
            'sidebar_': 'Sidebar',
            'bubble_': 'Bubbles',
            'menu_': 'Menu',
            'strength_': 'Strength Meter',
            'server_': 'Server Status',
            'font_': 'Fonts',
            'pub_': 'Public Key Panel',
            'button_': 'Buttons',
            'input_': 'Inputs',
            'timestamp': 'Timestamps',
        }
        for prefix, g in groups.items():
            if key.startswith(prefix):
                return g
        if key in ('mode', 'text', 'placeholder_text', 'bubble_transparent', 'bubble_align_both_left'):
            return 'General'
        return 'Other'

    def _clear_fields(self):
        # Ensure editor container exists (some callers may run before layout completes)
        if not hasattr(self, 'editor_container') or self.editor_container is None:
            try:
                self.editor_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
                self.editor_container.grid(row=0, column=2, sticky='nsew', padx=(0,8), pady=8)
                self.editor_container.grid_columnconfigure(0, weight=1)
            except Exception:
                # As a final fallback, create a simple frame to avoid attribute errors
                self.editor_container = ctk.CTkFrame(self, fg_color="transparent")
        for child in self.editor_container.winfo_children():
            child.destroy()
        self.fields.clear()
        self.group_members.clear()
        self.group_collapsed.clear()
        # Search bar
        search_row = ctk.CTkFrame(self.editor_container, fg_color="#262833")
        search_row.grid(row=0, column=0, sticky='ew', padx=8, pady=(6,2))
        search_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(search_row, text="Search", width=60).grid(row=0, column=0, padx=6, pady=6)
        entry = ctk.CTkEntry(search_row, textvariable=self.search_var)
        entry.grid(row=0, column=1, sticky='ew', padx=(0,6), pady=6)
        entry.bind('<KeyRelease>', lambda e: self._apply_search_filter())

    def _load_theme_into_fields(self, name):
        if name not in self.themes:
            return
        self._clear_fields()
        data = self.themes[name]
        # group keys
        grouped = {}
        for k in sorted(data.keys()):
            grouped.setdefault(self._group_for_key(k), []).append(k)

        row = 1  # leave space for search row
        for group, keys in grouped.items():
            header = ctk.CTkLabel(self.editor_container, text=f"▼ {group}", font=("Roboto", 13, "bold"))
            header.grid(row=row, column=0, sticky='w', padx=8, pady=(12,4))
            header.bind('<Button-1>', lambda e, g=group, h=header: self._toggle_group(g, h))
            self.group_members[group] = []
            self.group_collapsed[group] = False
            row += 1
            for key in keys:
                val = data[key]
                self._create_field(row, key, val, group)
                row += 1
        self._highlight_changes()
        self._apply_search_filter()

    def _create_field(self, row, key, value, group=None):
        frame = ctk.CTkFrame(self.editor_container, fg_color="#292b36")
        frame.grid(row=row, column=0, sticky='ew', padx=8, pady=3)
        frame.grid_columnconfigure(2, weight=1)
        label = ctk.CTkLabel(frame, text=key, text_color="#b2b8d6")
        label.grid(row=0, column=0, sticky='w', padx=6, pady=6)

        widget = None
        meta = {'type': None}

        def bind_change(w):
            try:
                w.bind('<KeyRelease>', lambda e: (self._highlight_changes(), self._update_preview()))
            except Exception:
                pass

        # Determine type
        if isinstance(value, bool):
            meta['type'] = 'bool'
            var = ctk.BooleanVar(value=value)
            widget = ctk.CTkSwitch(frame, text='', variable=var, command=lambda: (self._highlight_changes(), self._update_preview()))
            widget.grid(row=0, column=1, padx=6)
            self.fields[key] = (widget, var, meta)
            return
        if isinstance(value, (int, float)):
            meta['type'] = 'number'
            widget = ctk.CTkEntry(frame)
            widget.insert(0, str(value))
            widget.grid(row=0, column=1, padx=6, pady=6, sticky='ew')
            bind_change(widget)
            self.fields[key] = (widget, None, meta)
            return
        if isinstance(value, list):  # font arrays
            meta['type'] = 'font_list'
            # expect [family, size, *style]
            fam = value[0] if value else 'Segoe UI'
            size = value[1] if len(value) > 1 else 12
            style = value[2] if len(value) > 2 else ''
            fam_entry = ctk.CTkEntry(frame, width=110)
            fam_entry.insert(0, fam)
            fam_entry.grid(row=0, column=1, padx=4, pady=6)
            size_entry = ctk.CTkEntry(frame, width=50)
            size_entry.insert(0, str(size))
            size_entry.grid(row=0, column=2, padx=4, pady=6, sticky='w')
            style_entry = ctk.CTkEntry(frame, width=70)
            style_entry.insert(0, style)
            style_entry.grid(row=0, column=3, padx=4, pady=6)
            for w in (fam_entry, size_entry, style_entry):
                bind_change(w)
            self.fields[key] = ((fam_entry, size_entry, style_entry), None, meta)
            return
        if isinstance(value, str) and value.startswith('#'):
            meta['type'] = 'color'
            entry = ctk.CTkEntry(frame)
            entry.insert(0, value)
            entry.grid(row=0, column=1, padx=6, pady=6, sticky='ew')
            btn = ctk.CTkButton(frame, text='🎨', width=34, command=lambda e=entry: self._pick_color(e))
            btn.grid(row=0, column=2, padx=4, pady=6, sticky='e')
            bind_change(entry)
            self.fields[key] = (entry, None, meta)
            return
        # fallback string
        meta['type'] = 'string'
        entry = ctk.CTkEntry(frame)
        entry.insert(0, str(value))
        entry.grid(row=0, column=1, padx=6, pady=6, sticky='ew')
        bind_change(entry)
        self.fields[key] = (entry, None, meta)
        # Per-field reset button
        try:
            reset_btn = ctk.CTkButton(frame, text='↺', width=30, fg_color="#444b5e", command=lambda k=key: self._reset_field(k))
            reset_btn.grid(row=0, column=4, padx=4, pady=4)
        except Exception:
            pass
        if group:
            self.group_members.setdefault(group, []).append(frame)

    def _pick_color(self, entry_widget):
        # Open the custom modal color picker and update the entry when the
        # user confirms a color. This keeps the UI consistent across OSes.
        try:
            picker = CustomColorPicker(self, initial=entry_widget.get())
            # wait for the modal to close; picker.chosen will be set to a hex
            # string or None.
            picker.grab_set()
            self.wait_window(picker)
            color = getattr(picker, 'chosen', None)
            if color:
                entry_widget.delete(0, ctk.END)
                entry_widget.insert(0, color)
                self._highlight_changes()
                self._update_preview()
        except Exception:
            pass

    # ---------- Collection & Save ----------
    def _collect_temp_theme(self):
        if not self.current_name:
            return {}
        base = copy.deepcopy(self.themes.get(self.current_name, {}))
        for key, (widget, var, meta) in self.fields.items():
            t = meta['type']
            if t == 'bool':
                base[key] = bool(var.get())
            elif t == 'number':
                txt = widget.get().strip()
                if txt.isdigit():
                    base[key] = int(txt)
                else:
                    try:
                        base[key] = float(txt)
                    except ValueError:
                        pass
            elif t == 'font_list':
                fam, size, style = widget
                try:
                    size_val = int(size.get().strip())
                except ValueError:
                    size_val = 12
                parts = [fam.get().strip(), size_val]
                st = style.get().strip()
                if st:
                    parts.append(st)
                base[key] = parts
            else:
                # string or color
                base[key] = widget.get().strip()
        return base

    def _save_current_theme(self):
        if not self.current_name:
            return
        self.themes[self.current_name] = self._collect_temp_theme()
        self._write_themes()
        self._populate_theme_list()
        self._highlight_changes()

    def _revert_changes(self):
        if not self.current_name:
            return
        # restore from original snapshot
        orig_theme = self.original_snapshot.get(self.current_name, {})
        self.themes[self.current_name] = copy.deepcopy(orig_theme)
        self._load_theme_into_fields(self.current_name)
        self._update_preview()

    def _export_theme(self):
        if not self.current_name:
            return
        path = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON','*.json')], title='Export Theme')
        if not path:
            return
        try:
            with open(path, 'w') as f:
                json.dump(self._collect_temp_theme(), f, indent=4)
        except Exception:
            pass

    def _import_theme(self):
        path = filedialog.askopenfilename(filetypes=[('JSON','*.json')], title='Import Theme')
        if not path:
            return
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            # require dict at top-level
            if isinstance(data, dict):
                # generate unique name
                base = data.get('name') or 'Imported'
                idx = 1
                new_name = base
                while new_name in self.themes:
                    idx += 1
                    new_name = f"{base} {idx}"
                self.themes[new_name] = data
                self.current_name = new_name
                self._populate_theme_list()
                self._load_theme_into_fields(new_name)
                self._update_preview()
        except Exception:
            pass

    # ---------- Theme operations ----------
    def _add_theme(self):
        base_name = 'New Theme'
        i = 1
        name = base_name
        while name in self.themes:
            i += 1
            name = f"{base_name} {i}"
        # Determine a full template: prefer the built-in 'Dark' theme if present.
        if 'Dark' in self.themes and isinstance(self.themes['Dark'], dict):
            template = copy.deepcopy(self.themes['Dark'])
        else:
            # Fallback: merge keys from all existing themes to build a superset template
            template = {}
            for tdata in self.themes.values():
                if isinstance(tdata, dict):
                    for k, v in tdata.items():
                        # only set if not already present to keep first encountered default
                        if k not in template:
                            template[k] = copy.deepcopy(v)
            # Ensure some critical defaults if themes were sparse
            template.setdefault('mode', 'Dark')
            template.setdefault('background', '#1c1c28')
            template.setdefault('sidebar_bg', '#252536')
            template.setdefault('bubble_you', '#7289da')
            template.setdefault('bubble_other', '#34344a')
        self.themes[name] = template
        self.current_name = name
        # Add baseline to original snapshot so fields are not marked changed immediately
        self.original_snapshot[name] = copy.deepcopy(template)
        self._populate_theme_list()
        self._load_theme_into_fields(name)
        self._update_preview()

    def _duplicate_theme(self):
        if not self.current_name:
            return
        base = self.current_name
        idx = 1
        new_name = f"{base} Copy"
        while new_name in self.themes:
            idx += 1
            new_name = f"{base} Copy {idx}"
        self.themes[new_name] = copy.deepcopy(self.themes[base])
        self.current_name = new_name
        self._populate_theme_list()
        self._load_theme_into_fields(new_name)
        self._update_preview()

    def _delete_theme(self):
        if not self.current_name or len(self.themes) <= 1:
            return
        try:
            # Remove from themes and snapshot
            name = self.current_name
            del self.themes[name]
            if name in self.original_snapshot:
                del self.original_snapshot[name]
        except KeyError:
            return
        self.current_name = next(iter(self.themes), None)
        self._populate_theme_list()
        if self.current_name:
            self._load_theme_into_fields(self.current_name)
            self._update_preview()
        # Persist deletion immediately
        self._write_themes()
        if self.app and hasattr(self.app, 'notifier'):
            self.app.notifier.show('Theme deleted', type_='info')

    # ---------- Change highlighting ----------
    def _highlight_changes(self):
        if not self.current_name:
            return
        current_temp = self._collect_temp_theme()
        original = self.original_snapshot.get(self.current_name, self.themes.get(self.current_name, {}))
        any_changed = False
        for key, (widget, var, meta) in self.fields.items():
            changed = key not in original or current_temp.get(key) != original.get(key)
            any_changed = any_changed or changed
            color = '#394155' if changed else '#292b36'
            # container frame is parent
            try:
                container = widget.master if not isinstance(widget, tuple) else widget[0].master
                container.configure(fg_color=color)
                if meta['type'] == 'color':
                    val = widget.get().strip()
                    if val and not HEX_RE.match(val):
                        container.configure(border_width=1, border_color='#d9534f')
                    else:
                        container.configure(border_width=0)
            except Exception:
                pass
        # Unsaved indicator
        try:
            if any_changed:
                self.save_btn.configure(text='💾 Save *')
                if not self.title().endswith('*'):
                    self.title(self.title().rstrip('* ') + ' *')
            else:
                self.save_btn.configure(text='💾 Save')
                if self.title().endswith('*'):
                    self.title(self.title().rstrip('* '))
        except Exception:
            pass

    # ---------- Context menu operations ----------
    def _show_theme_context(self, name, event):
        # Ensure selection before showing menu
        self._select_theme(name)
        menu = Menu(self, tearoff=0)
        menu.add_command(label="Rename Theme", command=lambda n=name: self._rename_theme(n))
        if len(self.themes) > 1:
            menu.add_command(label="Delete Theme", command=self._delete_theme)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _rename_theme(self, name):
        # Use CTkInputDialog if available; fallback to simpledialog if needed
        new_name = None
        try:
            dlg = ctk.CTkInputDialog(text="Enter new theme name:", title="Rename Theme")
            new_name = dlg.get_input()
        except Exception:
            # fallback minimal prompt
            from tkinter import simpledialog
            new_name = simpledialog.askstring("Rename Theme", "Enter new theme name:")
        if not new_name:
            return
        new_name = new_name.strip()
        if not new_name:
            return
        if new_name in self.themes and new_name != name:
            # notify conflict
            if self.app and hasattr(self.app, 'notifier'):
                self.app.notifier.show('Name already exists', type_='warning')
            return
        if new_name == name:
            return
        # Rename in themes and original snapshot
        self.themes[new_name] = self.themes.pop(name)
        if name in self.original_snapshot:
            self.original_snapshot[new_name] = self.original_snapshot.pop(name)
        if self.current_name == name:
            self.current_name = new_name
        self._populate_theme_list()
        self._load_theme_into_fields(self.current_name)
        self._update_preview()
        # Auto-save rename so themes.json reflects change
        self._write_themes()
        if self.app and hasattr(self.app, 'notifier'):
            self.app.notifier.show('Theme renamed', type_='success')
        self._populate_theme_list()
        self._highlight_selected_theme()

    # ---------- Field utilities / helpers ----------
    def _reset_field(self, key):
        if not self.current_name:
            return
        orig = self.original_snapshot.get(self.current_name, {}).get(key)
        if orig is None and key in self.themes.get(self.current_name, {}):
            orig = self.themes[self.current_name][key]
        if orig is None:
            return
        widget, var, meta = self.fields.get(key, (None, None, {}))
        t = meta.get('type')
        try:
            if t == 'bool':
                var.set(bool(orig))
            elif t == 'number':
                widget.delete(0, ctk.END); widget.insert(0, str(orig))
            elif t == 'font_list':
                fam, size, style = widget
                fam.delete(0, ctk.END); fam.insert(0, orig[0])
                size.delete(0, ctk.END); size.insert(0, orig[1])
                if len(orig) > 2:
                    style.delete(0, ctk.END); style.insert(0, orig[2])
            else:
                widget.delete(0, ctk.END); widget.insert(0, str(orig))
        except Exception:
            pass
        self._highlight_changes(); self._update_preview()

    def _toggle_group(self, group, header_widget):
        collapsed = self.group_collapsed.get(group, False)
        new_state = not collapsed
        self.group_collapsed[group] = new_state
        for frame in self.group_members.get(group, []):
            try:
                if new_state:
                    frame.grid_remove()
                else:
                    frame.grid()
            except Exception:
                pass
        try:
            header_widget.configure(text=("► " if new_state else "▼ ") + group)
        except Exception:
            pass

    def _apply_search_filter(self):
        query = self.search_var.get().strip().lower()
        for key, (widget, var, meta) in self.fields.items():
            container = widget.master if not isinstance(widget, tuple) else widget[0].master
            try:
                if (not query or query in key.lower()) and self._container_visible_in_group(container):
                    container.grid()
                else:
                    container.grid_remove()
            except Exception:
                pass

    def _container_visible_in_group(self, container):
        for group, members in self.group_members.items():
            if container in members:
                return not self.group_collapsed.get(group, False)
        return True

    def _highlight_selected_theme(self):
        for name, frame in self.theme_items.items():
            try:
                frame.configure(fg_color="#475068" if name == self.current_name else "#333541")
            except Exception:
                pass

