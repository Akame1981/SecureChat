import customtkinter as ctk
from tkinter import messagebox
from utils.crypto import is_strong_pin


class PinDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="Enter PIN", new_pin=False):
        super().__init__(parent)
        self.parent = parent
        self.new_pin = new_pin
        self.pin = None

        self.title(title)
        self.geometry("350x260" if new_pin else "350x180")
        self.resizable(False, False)
        self.grab_set()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=title, font=("Segoe UI", 14, "bold"))
        self.label.pack(pady=(15, 10))

        # Main PIN entry
        self.entry = ctk.CTkEntry(self, show="*", placeholder_text="Enter PIN")
        self.entry.pack(pady=5, padx=20, fill="x")
        self.entry.focus()

        # Confirmation + strength only if creating a new PIN
        if self.new_pin:
            self.entry.bind("<KeyRelease>", self.update_strength)


            self.confirm_entry = ctk.CTkEntry(self, show="*", placeholder_text="Confirm PIN")
            self.confirm_entry.pack(pady=5, padx=20, fill="x")

            self.strength_label = ctk.CTkLabel(self, text="Strength: ", font=("Segoe UI", 12))
            self.strength_label.pack(pady=(0, 8))
        else:
            self.confirm_entry = None
            self.strength_label = None

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        self.ok_btn = ctk.CTkButton(btn_frame, text="OK", width=80, command=self.on_ok, fg_color="#4a90e2")
        self.ok_btn.pack(side="left", padx=10)

        self.cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", width=80, command=self.on_cancel, fg_color="#d9534f")
        self.cancel_btn.pack(side="right", padx=10)

        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.on_cancel())

    def update_strength(self, event=None):
        """Live update PIN strength (only for new PINs)"""
        if not self.new_pin:
            return

        pin = self.entry.get().strip()
        if not pin:
            self.strength_label.configure(text="Strength: ", text_color="white")
            return

        ok, reason = is_strong_pin(pin)

        if not ok:
            self.strength_label.configure(text=f"Strength: Weak ({reason})", text_color="red")
        elif len(pin) < 8:
            self.strength_label.configure(text="Strength: Medium", text_color="orange")
        else:
            self.strength_label.configure(text="Strength: Strong", text_color="green")

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

        self.pin = pin
        self.destroy()

    def on_cancel(self):
        self.pin = None
        self.destroy()
