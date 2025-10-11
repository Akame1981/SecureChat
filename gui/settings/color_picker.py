"""Modernized CustomColorPicker for the Theme Editor.

This version keeps the original behavior but updates the layout and
controls to look more contemporary:
- Large preview with rounded border
- Hue slider plus RGB sliders (keeps HSV/RGB in sync)
- Larger, rounded preset swatches and a "copy hex" button
- Cleaner spacing and labels
"""
import customtkinter as ctk
import colorsys


def _hex_to_rgb(h):
    h = h.lstrip('#')
    if len(h) == 3:
        h = ''.join([c * 2 for c in h])
    try:
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        return (114, 137, 218)


def _rgb_to_hex(r, g, b):
    return '#%02x%02x%02x' % (int(r), int(g), int(b))


class CustomColorPicker(ctk.CTkToplevel):
    def __init__(self, master, initial='#7289da'):
        super().__init__(master)
        self.title('Pick a color')
        self.resizable(False, False)
        self.chosen = None

        # Core state (RGB and HSV)
        self.r_var = ctk.DoubleVar()
        self.g_var = ctk.DoubleVar()
        self.b_var = ctk.DoubleVar()
        self.h_var = ctk.DoubleVar()
        self.s_var = ctk.DoubleVar()
        self.v_var = ctk.DoubleVar()

        pad = 12
        body = ctk.CTkFrame(self, fg_color='#242631', corner_radius=8)
        body.grid(row=0, column=0, padx=pad, pady=pad)

        # Two-column layout: preview on left, controls on right
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)

        # Left: large preview and hex
        left = ctk.CTkFrame(body, fg_color='transparent')
        left.grid(row=0, column=0, sticky='ns', padx=(0,12))

        self.preview = ctk.CTkFrame(left, width=160, height=160, corner_radius=12, fg_color=initial)
        self.preview.grid(row=0, column=0, pady=(0, 10))
        self.preview.grid_propagate(False)

        # Hex + copy button
        hex_row = ctk.CTkFrame(left, fg_color='transparent')
        hex_row.grid(row=1, column=0, sticky='ew')
        self.hex_entry = ctk.CTkEntry(hex_row, width=110, justify='center')
        self.hex_entry.grid(row=0, column=0, padx=(0,6))
        copy_btn = ctk.CTkButton(hex_row, text='Copy', width=56, command=self._copy_hex, fg_color='#3b82f6')
        copy_btn.grid(row=0, column=1)

        # Right: sliders and presets
        right = ctk.CTkFrame(body, fg_color='transparent')
        right.grid(row=0, column=1, sticky='nsew')
        right.grid_columnconfigure(0, weight=1)

        # Hue slider (0-360)
        ctk.CTkLabel(right, text='Hue').grid(row=0, column=0, sticky='w')
        hue = ctk.CTkSlider(right, from_=0, to=360, variable=self.h_var, command=lambda v=None: self._hsv_changed())
        hue.grid(row=1, column=0, sticky='ew', pady=(0,8))

        # RGB sliders
        for i, (label_text, var) in enumerate((('R', self.r_var), ('G', self.g_var), ('B', self.b_var))):
            ctk.CTkLabel(right, text=label_text).grid(row=2 + i*2, column=0, sticky='w')
            s = ctk.CTkSlider(right, from_=0, to=255, variable=var, command=lambda v=None: self._rgb_changed())
            s.grid(row=3 + i*2, column=0, sticky='ew', pady=(0,8))

        # Presets area
        ctk.CTkLabel(right, text='Presets').grid(row=8, column=0, sticky='w', pady=(6,4))
        presets = ['#7289da', '#2f3136', '#43b581', '#f04747', '#ffd166', '#06d6a0', '#ef476f', '#118ab2']
        sw_frame = ctk.CTkFrame(right, fg_color='transparent')
        sw_frame.grid(row=9, column=0, sticky='w')
        for i, col in enumerate(presets):
            btn = ctk.CTkButton(sw_frame, text='', width=36, height=28, fg_color=col, corner_radius=8,
                                command=lambda c=col: self._apply_preset(c))
            btn.grid(row=0, column=i, padx=6)

        # Buttons row
        btn_row = ctk.CTkFrame(body, fg_color='transparent')
        btn_row.grid(row=1, column=0, columnspan=2, pady=(12, 0), sticky='e')
        ok = ctk.CTkButton(btn_row, text='OK', width=90, command=self._on_ok, fg_color='#10b981')
        ok.grid(row=0, column=0, padx=(0,8))
        cancel = ctk.CTkButton(btn_row, text='Cancel', width=90, command=self._on_cancel, fg_color='#6c757d')
        cancel.grid(row=0, column=1)

        # Initialization: set state from initial hex
        try:
            r, g, b = _hex_to_rgb(initial or '#7289da')
        except Exception:
            r, g, b = (114, 137, 218)
        self._set_rgb(r, g, b)
        # bind hex edits
        self.hex_entry.bind('<KeyRelease>', lambda e: self._hex_edited())

        # Modal: try grabbing input, but avoid crashing if parent isn't viewable
        try:
            self.transient(master)
            try:
                self.grab_set()
            except Exception:
                try:
                    if getattr(master, "winfo_viewable", None) and not master.winfo_viewable():
                        def _retry():
                            try:
                                if getattr(self, "winfo_exists", None) and self.winfo_exists():
                                    self.grab_set()
                            except Exception:
                                pass
                        try:
                            self.after(150, _retry)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    # -- state sync helpers -------------------------------------------------
    def _set_rgb(self, r, g, b):
        # set internal vars and update HSV & preview
        self.r_var.set(r); self.g_var.set(g); self.b_var.set(b)
        h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
        self.h_var.set(h * 360)
        self.s_var.set(s)
        self.v_var.set(v)
        self._update_preview()

    def _set_hsv(self, h, s, v):
        self.h_var.set(h); self.s_var.set(s); self.v_var.set(v)
        r, g, b = colorsys.hsv_to_rgb(h/360.0, s, v)
        self.r_var.set(int(r * 255)); self.g_var.set(int(g * 255)); self.b_var.set(int(b * 255))
        self._update_preview()

    def _update_preview(self):
        try:
            r = int(self.r_var.get()); g = int(self.g_var.get()); b = int(self.b_var.get())
            hx = _rgb_to_hex(r, g, b)
            self.preview.configure(fg_color=hx)
            # update hex entry without moving cursor
            self.hex_entry.delete(0, ctk.END); self.hex_entry.insert(0, hx)
        except Exception:
            pass

    def _rgb_changed(self):
        # user moved RGB sliders -> update HSV and preview
        try:
            r = int(self.r_var.get()); g = int(self.g_var.get()); b = int(self.b_var.get())
            h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
            self.h_var.set(h * 360)
            self.s_var.set(s); self.v_var.set(v)
            self._update_preview()
        except Exception:
            pass

    def _hsv_changed(self):
        try:
            h = float(self.h_var.get())
            s = float(self.s_var.get())
            v = float(self.v_var.get())
            self._set_hsv(h, s, v)
        except Exception:
            # Only hue slider is interactive; derive s/v from current rgb
            try:
                r = int(self.r_var.get()); g = int(self.g_var.get()); b = int(self.b_var.get())
                h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
                self.s_var.set(s); self.v_var.set(v)
            except Exception:
                pass

    def _hex_edited(self):
        txt = self.hex_entry.get().strip()
        if not txt:
            return
        if not txt.startswith('#'):
            txt = '#' + txt
        try:
            r, g, b = _hex_to_rgb(txt)
            self._set_rgb(r, g, b)
        except Exception:
            pass

    def _apply_preset(self, hexcol):
        try:
            r, g, b = _hex_to_rgb(hexcol)
            self._set_rgb(r, g, b)
        except Exception:
            pass

    def _copy_hex(self):
        try:
            hx = self.hex_entry.get().strip()
            if hx:
                self.clipboard_clear(); self.clipboard_append(hx)
        except Exception:
            pass

    def _on_ok(self):
        val = self.hex_entry.get().strip()
        if not val:
            return
        if not val.startswith('#'):
            val = '#' + val
        # normalize length
        if len(val) not in (4, 7):
            try:
                r = int(self.r_var.get()); g = int(self.g_var.get()); b = int(self.b_var.get())
                val = _rgb_to_hex(r, g, b)
            except Exception:
                val = '#7289da'
        self.chosen = val
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _on_cancel(self):
        self.chosen = None
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
