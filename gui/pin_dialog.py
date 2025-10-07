import customtkinter as ctk
from tkinter import messagebox
from utils.crypto import is_strong_pin

class PinDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="Enter PIN", new_pin=False):
        super().__init__(parent)
        self.parent = parent
        self.new_pin = new_pin
        self.pin = None
        self.username = None

        # --- Window Setup ---
        self.title(title)
        self.geometry("380x320" if new_pin else "380x200")
        self.resizable(False, False)
        self.configure(fg_color="#1f1f2e")
        self.grab_set()

        # Title
        self.label = ctk.CTkLabel(self, text=title, font=("Segoe UI", 16, "bold"),
                                  text_color="white")
        self.label.pack(pady=(20, 15))

        # Username entry (optional)
        if self.new_pin:
            self.username_entry = ctk.CTkEntry(
                self, placeholder_text="Username (default: Anonymous)",
                height=40, corner_radius=12, fg_color="#2a2a3f", text_color="white",
                placeholder_text_color="gray70"
            )
            self.username_entry.pack(pady=5, padx=30, fill="x")
        else:
            self.username_entry = None

        # PIN entry
        self.entry = ctk.CTkEntry(
            self, show="*", placeholder_text="Enter PIN",
            height=40, corner_radius=12, fg_color="#2a2a3f", text_color="white",
            placeholder_text_color="gray70"
        )
        self.entry.pack(pady=5, padx=30, fill="x")
        self.entry.focus()

        # Confirm PIN + strength bar (new PIN)
        if self.new_pin:
            self.entry.bind("<KeyRelease>", self.update_strength)

            self.confirm_entry = ctk.CTkEntry(
                self, show="*", placeholder_text="Confirm PIN",
                height=40, corner_radius=12, fg_color="#2a2a3f", text_color="white",
                placeholder_text_color="gray70"
            )
            self.confirm_entry.pack(pady=5, padx=30, fill="x")

            # Strength text above the bar
            self.strength_label = ctk.CTkLabel(
                self, text="", font=("Segoe UI", 12, "bold"),
                text_color="white"
            )
            self.strength_label.pack(pady=(10, 2))

            # Small strength bar
            self.strength_frame = ctk.CTkFrame(self, fg_color="#2a2a3f", corner_radius=8, height=8)
            self.strength_frame.pack(padx=30, fill="x")
            self.strength_frame.pack_propagate(False)

            # Inner colored bar
            self.strength_bar = ctk.CTkFrame(self.strength_frame, width=0, fg_color="#e74c3c", corner_radius=8)
            self.strength_bar.place(relheight=1, x=0, y=0)
        else:
            self.confirm_entry = None
            self.strength_bar = None
            self.strength_label = None

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        self.ok_btn = ctk.CTkButton(
            btn_frame, text="OK", width=100, height=42, corner_radius=12,
            fg_color="#4a90e2", hover_color="#357ABD", command=self.on_ok
        )
        self.ok_btn.pack(side="left", padx=10)

        self.cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancel", width=100, height=42, corner_radius=12,
            fg_color="#d9534f", hover_color="#b03a2e", command=self.on_cancel
        )
        self.cancel_btn.pack(side="right", padx=10)

        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.on_cancel())

    # --- Animate strength bar smoothly 0-100% ---
    
    def animate_bar(self, target_width, color, text):
        current_width = self.strength_bar.winfo_width()
        steps = 20
        step = (target_width - current_width) / steps

        def step_animation(count=0):
            nonlocal current_width
            if count >= steps:
                return
            current_width += step
            self.strength_bar.configure(width=max(0, int(current_width)), fg_color=color)
            self.strength_label.configure(text=text, text_color=color)  # text color matches bar
            self.after(15, lambda: step_animation(count + 1))

        step_animation()

    def update_strength(self, event=None):
        if not self.new_pin:
            return

        pin = self.entry.get().strip()
        max_width = self.strength_frame.winfo_width() or 300

        if not pin:
            self.animate_bar(0, "#e74c3c", "")
            return

        ok, reason = is_strong_pin(pin)

        if not ok:
            color = "#e74c3c"
            width = max_width * 0.33
            text = reason  # show reason only
        elif len(pin) < 8:
            color = "#f1c40f"
            width = max_width * 0.66
            text = "Medium"
        else:
            color = "#2ecc71"
            width = max_width
            text = "Strong"

        self.animate_bar(width, color, text)


    # --- OK ---
    def on_ok(self):
        pin = self.entry.get().strip()
        if not pin:
            messagebox.showwarning("Warning", "PIN cannot be empty!")
            return

        if self.new_pin:
            confirm_pin = self.confirm_entry.get().strip()
            if pin != confirm_pin:
                messagebox.showwarning("Mismatch", "PINs do not match!")
                return

            ok, reason = is_strong_pin(pin)
            if not ok:
                messagebox.showwarning("Weak PIN", f"PIN rejected: {reason}")
                return

            username = self.username_entry.get().strip() if self.username_entry else ""
            if not username:
                username = "Anonymous"
            self.username = username

        self.pin = pin
        self.destroy()

    # --- Cancel ---
    def on_cancel(self):
        self.pin = None
        self.username = None
        self.destroy()
