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

        # Window setup
        self.title(title)
        self.geometry("380x320" if new_pin else "380x200")
        self.resizable(False, False)
        self.configure(fg_color="#1f1f2e")  # dark background
        self.grab_set()

        # Grid for responsive layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Title ---
        self.label = ctk.CTkLabel(self, text=title, font=("Segoe UI", 16, "bold"),
                                  text_color="white")
        self.label.pack(pady=(20, 15))

        # --- Username (optional) ---
        if self.new_pin:
            self.username_entry = ctk.CTkEntry(
                self, placeholder_text="Username (default: Anonymous)",
                height=40, corner_radius=12, fg_color="#2a2a3f", text_color="white",
                placeholder_text_color="gray70"
            )
            self.username_entry.pack(pady=5, padx=30, fill="x")
        else:
            self.username_entry = None

        # --- PIN Entry ---
        self.entry = ctk.CTkEntry(
            self, show="*", placeholder_text="Enter PIN",
            height=40, corner_radius=12, fg_color="#2a2a3f", text_color="white",
            placeholder_text_color="gray70"
        )
        self.entry.pack(pady=5, padx=30, fill="x")
        self.entry.focus()

        # --- Confirm + Strength for new PINs ---
        if self.new_pin:
            self.entry.bind("<KeyRelease>", self.update_strength)

            self.confirm_entry = ctk.CTkEntry(
                self, show="*", placeholder_text="Confirm PIN",
                height=40, corner_radius=12, fg_color="#2a2a3f", text_color="white",
                placeholder_text_color="gray70"
            )
            self.confirm_entry.pack(pady=5, padx=30, fill="x")

            self.strength_label = ctk.CTkLabel(
                self, text="Strength: ", font=("Segoe UI", 12),
                text_color="white"
            )
            self.strength_label.pack(pady=(5, 10))
        else:
            self.confirm_entry = None
            self.strength_label = None

        # --- Buttons ---
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

        # Bind Enter & Escape keys
        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.on_cancel())

    # --- PIN Strength ---
    def update_strength(self, event=None):
        if not self.new_pin:
            return

        pin = self.entry.get().strip()
        if not pin:
            self.strength_label.configure(text="Strength: ", text_color="white")
            return

        ok, reason = is_strong_pin(pin)

        if not ok:
            self.strength_label.configure(text=f"Strength: Weak ({reason})", text_color="#e74c3c")
        elif len(pin) < 8:
            self.strength_label.configure(text="Strength: Medium", text_color="#f1c40f")
        else:
            self.strength_label.configure(text="Strength: Strong", text_color="#2ecc71")

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
