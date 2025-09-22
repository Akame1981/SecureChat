import customtkinter as ctk

class Notification(ctk.CTkToplevel):
    COLORS = {
        "info": {"bg": "#2e2e3f", "fg": "white"},
        "warning": {"bg": "#f0ad4e", "fg": "black"},
        "error": {"bg": "#d9534f", "fg": "white"},
        "success": {"bg": "#5cb85c", "fg": "white"}
    }

    def __init__(self, parent, message: str, manager, type_: str = "info", duration=2500):
        super().__init__(parent)
        self.manager = manager
        self.message = message  # store message for copying
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)

        colors = self.COLORS.get(type_, self.COLORS["info"])
        bg, fg = colors["bg"], colors["fg"]
        self.configure(bg=bg)

        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        width, height = 280, 55
        x = parent_x + parent_w - width - 20
        y = parent_y + parent_h - height - 20
        self.geometry(f"{width}x{height}+{x}+{y}")



        label = ctk.CTkLabel(self, text=message, text_color=fg, fg_color=bg, anchor="w")
        label.pack(expand=True, fill="both", padx=10, pady=10)

        # Bind click to copy message 
        label.bind("<Button-1>", self.copy_to_clipboard)


        self._fade_in()
        self.after(duration, self._fade_out)

    def copy_to_clipboard(self, event=None):
        self.clipboard_clear()
        self.clipboard_append(self.message)
        # Show a small "Copied!" notification
        if hasattr(self.manager.parent, "notifier"):
            self.manager.parent.notifier.show("Copied!", type_="success", duration=1000)

    def _fade_in(self, step=0.07):
        alpha = self.attributes("-alpha")
        if alpha < 1.0:
            self.attributes("-alpha", min(alpha + step, 1.0))
            self.after(30, self._fade_in)

    def _fade_out(self, step=0.07):
        alpha = self.attributes("-alpha")
        if alpha > 0.0:
            self.attributes("-alpha", max(alpha - step, 0.0))
            self.after(30, self._fade_out)
        else:
            self.manager.remove(self)
            self.destroy()


class NotificationManager:
    def __init__(self, parent):
        self.parent = parent
        self.active_notifications = []

    def show(self, message: str, type_: str = "info", duration=2500):
        notif = Notification(self.parent, message, self, type_, duration)
        self.active_notifications.append(notif)
        self._rearrange()

    def remove(self, notif):
        """Remove destroyed notification and rearrange remaining"""
        if notif in self.active_notifications:
            self.active_notifications.remove(notif)
            self._rearrange()

    def _rearrange(self):
        width, height = 280, 55
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        base_x = parent_x + parent_w - width - 20
        base_y = parent_y + parent_h - height - 20

        for i, notif in enumerate(self.active_notifications):
            y = base_y - (i * 65)
            notif.geometry(f"{width}x{height}+{base_x}+{y}")
