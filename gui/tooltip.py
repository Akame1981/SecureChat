import tkinter as tk
import customtkinter as ctk


class ToolTip:
    """A modern tooltip that uses CustomTkinter styling.

    Features:
    - Small show delay to avoid flicker
    - Rounded background with subtle border
    - Automatic repositioning to keep tooltip on-screen
    - Follow widget motion (if the widget moves)
    - Wraps long text
    """
    def __init__(self, widget, text, delay=400, wraplength=300):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.wraplength = wraplength

        self._after_id = None
        self.tipwindow = None

        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._cancel)
        widget.bind("<ButtonPress>", self._cancel)
        widget.bind("<Motion>", self._on_motion)

    def _schedule(self, event=None):
        # schedule show after delay
        self._cancel()
        try:
            self._after_id = self.widget.after(self.delay, self._show)
        except Exception:
            self._show()

    def _cancel(self, event=None):
        if self._after_id:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self._hide()

    def _on_motion(self, event=None):
        # If tooltip already shown, reposition following the cursor
        if self.tipwindow:
            self._position()

    def _show(self):
        if self.tipwindow or not self.text:
            return
        # Create a CTk Toplevel so styling matches the app
        tw = ctk.CTkToplevel(self.widget)
        try:
            tw.overrideredirect(True)
        except Exception:
            # fallback
            tw.wm_overrideredirect(True)
        self.tipwindow = tw

        # Frame with rounded corners
        frame = ctk.CTkFrame(tw, fg_color="#23232b", corner_radius=8, border_width=1, border_color="#3a3a4a")
        frame.pack(fill="both", expand=True)

        label = ctk.CTkLabel(frame, text=self.text, text_color="#e8e8ee", wraplength=self.wraplength, justify="left", font=("Segoe UI", 10))
        label.pack(padx=10, pady=6)

        # small arrow: a thin canvas triangle under the frame to point to widget
        try:
            canvas = tk.Canvas(tw, width=16, height=8, bg='transparent', highlightthickness=0)
            canvas.configure(bg='')
            # draw triangle (will be placed after positioning)
            canvas.create_polygon((0,0, 8,8, 16,0), fill='#23232b', outline='#3a3a4a')
            canvas.pack()
        except Exception:
            canvas = None

        self._position()

    def _position(self):
        if not self.tipwindow:
            return
        try:
            tw = self.tipwindow
            w = tw.winfo_reqwidth()
            h = tw.winfo_reqheight()
            # Determine preferred location below widget cursor
            x = self.widget.winfo_rootx() + 20
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
            sw = tw.winfo_screenwidth()
            sh = tw.winfo_screenheight()
            # adjust if off-screen to the right
            if x + w + 8 > sw:
                x = max(8, sw - w - 8)
            # adjust if bottom would go off-screen
            if y + h + 8 > sh:
                # try placing above the widget
                y = self.widget.winfo_rooty() - h - 8
            tw.geometry(f"+{x}+{y}")
            # If we drew an arrow canvas, move it to be centered under the frame
            for child in tw.winfo_children():
                if isinstance(child, tk.Canvas):
                    try:
                        # place the canvas at the bottom center
                        cw = child.winfo_reqwidth()
                        child.place(x=max(8, (w - cw) // 2), y=h - 2)
                    except Exception:
                        pass
        except Exception:
            pass

    def _hide(self):
        if self.tipwindow:
            try:
                self.tipwindow.destroy()
            except Exception:
                pass
            self.tipwindow = None
