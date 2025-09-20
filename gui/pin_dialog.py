import customtkinter as ctk
from tkinter import messagebox

class PinDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="Enter PIN", new_pin=False):
        super().__init__(parent)
        self.parent = parent
        self.new_pin = new_pin
        self.pin = None

        self.title(title)
        self.geometry("350x180")
        self.resizable(False, False)
        self.grab_set()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=title, font=("Segoe UI", 14, "bold"))
        self.label.pack(pady=(15, 10))

        self.entry = ctk.CTkEntry(self, show="*", placeholder_text="Enter PIN")
        self.entry.pack(pady=5, padx=20, fill="x")
        self.entry.focus()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        self.ok_btn = ctk.CTkButton(btn_frame, text="OK", width=80, command=self.on_ok, fg_color="#4a90e2")
        self.ok_btn.pack(side="left", padx=10)

        self.cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", width=80, command=self.on_cancel, fg_color="#d9534f")
        self.cancel_btn.pack(side="right", padx=10)

        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.on_cancel())

    def on_ok(self):
        pin = self.entry.get().strip()
        if not pin:
            messagebox.showwarning("Warning", "PIN cannot be empty!")
            return
        if len(pin) < 6:
            messagebox.showwarning("Warning", "PIN too short. Must be at least 6 characters.")
            return
        self.pin = pin
        self.destroy()

    def on_cancel(self):
        self.pin = None
        self.destroy()
