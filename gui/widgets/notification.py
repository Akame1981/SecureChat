import customtkinter as ctk
import tkinter as tk


def _darken_hex(hex_color: str, factor: float = 0.9) -> str:
    """Return a darker hex color (no alpha). Expects #RRGGBB format."""
    try:
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return hex_color
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))
        b = max(0, min(255, int(b * factor)))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color


class Notification(ctk.CTkToplevel):
    COLORS = {
        "info": {"bg": "#2e2e3f", "fg": "white", "icon": "ℹ️"},
        "warning": {"bg": "#f0ad4e", "fg": "black", "icon": "⚠️"},
        "error": {"bg": "#d9534f", "fg": "white", "icon": "❌"},
        "success": {"bg": "#5cb85c", "fg": "white", "icon": "✔️"}
    }

    PADDING = 12

    def __init__(self, parent, message: str, manager, type_: str = "info", duration=3000):
        super().__init__(parent)
        self.manager = manager
        self.message = message
        self.type_ = type_
        self.duration = max(500, int(duration))

        # Track whether per-window alpha is supported by this WM
        self._alpha_supported = True

        # Window setup: be defensive — some Linux WMs/compositors don't support
        # overrideredirect/attributes exactly the same way as Windows.
        try:
            self.overrideredirect(True)
        except Exception:
            try:
                # fallback name used by some tkinter builds
                self.wm_overrideredirect(True)
            except Exception:
                pass
        try:
            self.attributes("-topmost", True)
        except Exception:
            try:
                self.wm_attributes("-topmost", True)
            except Exception:
                pass
        try:
            self.attributes("-alpha", 0.0)
            self._alpha_supported = True
        except Exception:
            # mark unsupported; skip fade animations
            self._alpha_supported = False

        colors = self.COLORS.get(type_, self.COLORS["info"])
        bg, fg = colors["bg"], colors["fg"]

        # Ensure the Toplevel background is set (avoids a black background on some WMs)
        try:
            self.configure(bg=bg)
        except Exception:
            try:
                self['bg'] = bg
            except Exception:
                pass

        width, height = 320, 70

        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        x = parent_x + parent_w - width - 20
        y = parent_y + parent_h - height - 20
        self.geometry(f"{width}x{height}+{x}+{y}")

        # Outer frame for rounded look and consistent CTk styling. Use the
        # background color instead of 'transparent' which can cause an
        # unstyled/black area on some Linux compositors.
        try:
            container = ctk.CTkFrame(self, fg_color=bg, corner_radius=12)
            container.pack(expand=True, fill="both", padx=6, pady=6)
        except Exception:
            container = tk.Frame(self, bg=bg)
            container.pack(expand=True, fill="both", padx=6, pady=6)

        # Layout: icon | message | close. Avoid transparent inner frames.
        try:
            inner = ctk.CTkFrame(container, fg_color=bg)
            inner.pack(side="top", fill="both", expand=True, padx=self.PADDING, pady=(8, 4))
            inner.grid_columnconfigure(1, weight=1)
        except Exception:
            inner = tk.Frame(container, bg=bg)
            inner.pack(fill="both", expand=True)

        icon_label = ctk.CTkLabel(inner, text=colors.get("icon", ""), width=30, anchor="w")
        icon_label.grid(row=0, column=0, sticky="w")

        # Use non-transparent fg color to avoid invisible text on some setups
        try:
            label = ctk.CTkLabel(inner, text=message, text_color=fg, fg_color=bg, anchor="w", justify="left")
        except Exception:
            label = tk.Label(inner, text=message, bg=bg, fg=fg, justify="left")
        label.grid(row=0, column=1, sticky="we", padx=(8, 4))
        label.bind("<Button-1>", self.copy_to_clipboard)

        # Close button (small) on the right; compute a hover color from the bg
        close_hover = _darken_hex(bg, 0.75)
        close_btn = ctk.CTkButton(inner, text="✕", width=28, height=28, fg_color="transparent", hover_color=close_hover, command=self._close)
        close_btn.grid(row=0, column=2, sticky="e")

        # Progress bar at the bottom (use a darkened bg for contrast)
        bar_bg_color = _darken_hex(bg, 0.88)
        try:
            bar_bg = ctk.CTkFrame(container, fg_color=bar_bg_color, height=6, corner_radius=8)
            bar_bg.pack(side="bottom", fill="x", padx=self.PADDING, pady=(0, 8))
            self.bar = ctk.CTkFrame(bar_bg, fg_color=fg, corner_radius=8, width=0)
            self.bar.place(relheight=1, x=0, y=0)
        except Exception:
            try:
                self.bar = tk.Frame(container, bg=fg, height=6)
                self.bar.pack(side="bottom", fill="x", padx=self.PADDING, pady=(0, 8))
            except Exception:
                self.bar = None

        # Animation / timing state
        self._start_time = None
        self._paused = False
        self._remaining = self.duration
        self._progress_after = None
        self._fade_after = None

        # Hover to pause (guard binds)
        try:
            container.bind("<Enter>", lambda e: self._pause())
            container.bind("<Leave>", lambda e: self._resume())
            inner.bind("<Enter>", lambda e: self._pause())
            inner.bind("<Leave>", lambda e: self._resume())
        except Exception:
            pass

        # Start: only run fade animation if alpha is supported
        if self._alpha_supported:
            try:
                self._fade_in()
            except Exception:
                pass

        self._start_progress()

    def copy_to_clipboard(self, event=None):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.message)
        except Exception:
            pass
        # Show quick confirmation
        if hasattr(self.manager.parent, "notifier"):
            self.manager.parent.notifier.show("Copied!", type_="success", duration=1000)

    def _fade_in(self, step=0.08):
        alpha = self.attributes("-alpha")
        if alpha < 1.0:
            self.attributes("-alpha", min(alpha + step, 1.0))
            self.after(20, self._fade_in)

    def _fade_out(self):
        # Smooth fade then destroy
        def _step():
            alpha = self.attributes("-alpha")
            if alpha > 0:
                self.attributes("-alpha", max(alpha - 0.08, 0.0))
                self.after(20, _step)
            else:
                try:
                    self.manager.remove(self)
                except Exception:
                    pass
                try:
                    self.destroy()
                except Exception:
                    pass

        _step()

    def _start_progress(self):
        # Kick off progress updates; manage remaining time in ms
        self._start_time = self.after(0, lambda: None)
        self._tick_start = self._now_ms()
        self._progress_step()

    def _now_ms(self):
        import time
        return int(time.time() * 1000)

    def _progress_step(self):
        if self._paused:
            return
        elapsed = self._now_ms() - self._tick_start
        frac = min(1.0, elapsed / self.duration)
        width = self.winfo_width() - (self.PADDING * 2 + 12)
        try:
            self.bar.configure(width=int(width * frac))
        except Exception:
            pass

        if frac >= 1.0:
            self._fade_out()
            return

        # schedule next step
        self._progress_after = self.after(30, self._progress_step)

    def _pause(self):
        if self._paused:
            return
        self._paused = True
        if self._progress_after:
            try:
                self.after_cancel(self._progress_after)
                self._progress_after = None
            except Exception:
                pass

    def _resume(self):
        if not self._paused:
            return
        self._paused = False
        # restart tick start to account for pause duration
        self._tick_start = self._now_ms() - int(self.winfo_width() > 0 and (self.bar.winfo_width() / (self.winfo_width() - (self.PADDING * 2 + 12))) * self.duration or 0)
        self._progress_step()

    def _close(self):
        # immediate close
        if self._progress_after:
            try:
                self.after_cancel(self._progress_after)
            except Exception:
                pass
        self._fade_out()



class NotificationManager:
    MAX_VISIBLE = 6

    def __init__(self, parent):
        self.parent = parent
        self.active_notifications = []

    def show(self, message: str, type_: str = "info", duration=3000):
        # Limit how many notifications stack; if too many, remove the oldest
        if len(self.active_notifications) >= self.MAX_VISIBLE:
            old = self.active_notifications.pop(0)
            try:
                old.destroy()
            except Exception:
                pass

        notif = Notification(self.parent, message, self, type_, duration)
        self.active_notifications.append(notif)
        self._rearrange()

    def remove(self, notif):
        if notif in self.active_notifications:
            try:
                self.active_notifications.remove(notif)
            except Exception:
                pass
            self._rearrange()

    def _rearrange(self):
        width, height = 320, 70
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        base_x = parent_x + parent_w - width - 20
        base_y = parent_y + parent_h - height - 20

        for i, notif in enumerate(self.active_notifications):
            # Stack upward with spacing
            y = base_y - (i * (height + 10))
            try:
                notif.geometry(f"{width}x{height}+{base_x}+{y}")
            except Exception:
                pass
