"""Custom color picker widget used by the Theme Editor.

Provides a CTk modal with RGB sliders, hex input, live preview and preset swatches.
"""
import customtkinter as ctk


class CustomColorPicker(ctk.CTkToplevel):
    """A simple modal color picker implemented with customtkinter.

    Features:
    - RGB sliders
    - Hex input (validated)
    - Live preview
    - Preset swatches
    """
    def __init__(self, master, initial='#7289da'):
        super().__init__(master)
        self.title('Pick a color')
        self.resizable(False, False)
        self.chosen = None

        # Helpers
        def _hex_to_rgb(h):
            h = h.lstrip('#')
            if len(h) == 3:
                h = ''.join([c*2 for c in h])
            try:
                return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
            except Exception:
                return (114, 137, 218)

        def _rgb_to_hex(r, g, b):
            return '#%02x%02x%02x' % (int(r), int(g), int(b))

        # Layout
        pad = 8
        body = ctk.CTkFrame(self, fg_color='#2b2d3a')
        body.grid(row=0, column=0, padx=pad, pady=pad)

        # Preview
        self.preview = ctk.CTkFrame(body, width=120, height=60, corner_radius=6)
        self.preview.grid(row=0, column=0, columnspan=3, pady=(0, pad))

        # Sliders for R, G, B
        self.r_var = ctk.DoubleVar()
        self.g_var = ctk.DoubleVar()
        self.b_var = ctk.DoubleVar()

        def on_slider_change(_=None):
            r = int(self.r_var.get())
            g = int(self.g_var.get())
            b = int(self.b_var.get())
            hx = _rgb_to_hex(r, g, b)
            try:
                self.hex_entry.delete(0, ctk.END)
                self.hex_entry.insert(0, hx)
            except Exception:
                pass
            try:
                self.preview.configure(fg_color=hx)
            except Exception:
                pass

        lbl_r = ctk.CTkLabel(body, text='R')
        lbl_r.grid(row=1, column=0, sticky='w')
        s_r = ctk.CTkSlider(body, from_=0, to=255, variable=self.r_var, command=lambda v=None: on_slider_change())
        s_r.grid(row=1, column=1, columnspan=2, sticky='ew', padx=(4,0))

        lbl_g = ctk.CTkLabel(body, text='G')
        lbl_g.grid(row=2, column=0, sticky='w')
        s_g = ctk.CTkSlider(body, from_=0, to=255, variable=self.g_var, command=lambda v=None: on_slider_change())
        s_g.grid(row=2, column=1, columnspan=2, sticky='ew', padx=(4,0))

        lbl_b = ctk.CTkLabel(body, text='B')
        lbl_b.grid(row=3, column=0, sticky='w')
        s_b = ctk.CTkSlider(body, from_=0, to=255, variable=self.b_var, command=lambda v=None: on_slider_change())
        s_b.grid(row=3, column=1, columnspan=2, sticky='ew', padx=(4,0))

        # Hex entry
        ctk.CTkLabel(body, text='Hex').grid(row=4, column=0, sticky='w', pady=(6,0))
        self.hex_entry = ctk.CTkEntry(body, width=160)
        self.hex_entry.grid(row=4, column=1, columnspan=2, sticky='ew', pady=(6,0))

        def on_hex_edit(e=None):
            txt = self.hex_entry.get().strip()
            if not txt:
                return
            if not txt.startswith('#'):
                txt = '#' + txt
            rgb = _hex_to_rgb(txt)
            # update sliders and preview
            self.r_var.set(rgb[0]); self.g_var.set(rgb[1]); self.b_var.set(rgb[2])
            try:
                self.preview.configure(fg_color=_rgb_to_hex(*rgb))
            except Exception:
                pass

        self.hex_entry.bind('<KeyRelease>', on_hex_edit)

        # Preset swatches
        presets = ['#FFFFFF', '#000000', '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', '#7289da', '#2f3136', '#43b581', '#f04747']
        sw_frame = ctk.CTkFrame(body, fg_color='transparent')
        sw_frame.grid(row=5, column=0, columnspan=3, pady=(8,0))
        for i, c in enumerate(presets):
            def _make_cmd(col=c):
                return lambda: (self.hex_entry.delete(0, ctk.END), self.hex_entry.insert(0, col), on_hex_edit())
            b = ctk.CTkButton(sw_frame, text='', width=26, height=22, fg_color=c, command=_make_cmd())
            b.grid(row=0, column=i, padx=3)

        # Buttons
        btn_ok = ctk.CTkButton(body, text='OK', width=80, command=self._on_ok)
        btn_ok.grid(row=6, column=1, pady=(10,0), sticky='e')
        btn_cancel = ctk.CTkButton(body, text='Cancel', width=80, fg_color='#444b5e', command=self._on_cancel)
        btn_cancel.grid(row=6, column=2, pady=(10,0), sticky='w')

        # Initialize from initial value
        try:
            rgb = _hex_to_rgb(initial or '#7289da')
            self.r_var.set(rgb[0]); self.g_var.set(rgb[1]); self.b_var.set(rgb[2])
            self.hex_entry.delete(0, ctk.END); self.hex_entry.insert(0, _rgb_to_hex(*rgb))
            self.preview.configure(fg_color=_rgb_to_hex(*rgb))
        except Exception:
            pass

        # Make modal
        try:
            self.transient(master)
            self.grab_set()
        except Exception:
            pass

    def _on_ok(self):
        val = self.hex_entry.get().strip()
        if not val:
            return
        if not val.startswith('#'):
            val = '#' + val
        # basic validation
        if len(val) not in (4, 7):
            # try to normalize
            try:
                r = int(self.r_var.get()); g = int(self.g_var.get()); b = int(self.b_var.get())
                val = '#%02x%02x%02x' % (r, g, b)
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
