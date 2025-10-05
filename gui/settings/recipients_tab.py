import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from utils.recipients import add_recipient, load_recipients, delete_recipient
from gui.settings.dialogs import CTkDialog, CTkConfirmDialog

class RecipientsTab:
    def __init__(self, parent_frame, app):
        self.app = app
        self.frame = parent_frame  # Already the frame of the "Recipients" tab

        # Make the frame expandable
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(
            self.frame,
            text="Manage Recipients",
            font=("Roboto", 16, "bold"),
            text_color="white"
        ).grid(row=0, column=0, pady=(10, 5), padx=10, sticky="w")

        # Listbox
        self.rec_listbox = tk.Listbox(
            self.frame,
            bg="#1e1e2f",
            fg="white",
            bd=0,
            highlightthickness=0,
            selectbackground="#4a90e2",
            activestyle="none"
        )
        self.rec_listbox.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=5)

        scrollbar = tk.Scrollbar(self.frame, command=self.rec_listbox.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=5)
        self.rec_listbox.config(yscrollcommand=scrollbar.set)

        # Buttons
        btn_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(btn_frame, text="Add", command=self.add_recipient_gui, fg_color="#4a90e2").grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame, text="Edit", command=self.edit_recipient, fg_color="#f0ad4e").grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame, text="Delete", command=self.delete_recipient, fg_color="#d9534f").grid(row=0, column=2, padx=5, sticky="ew")

    def refresh_list(self):
        self.rec_listbox.delete(0, tk.END)

        # Check if PIN is available
        if not hasattr(self.app, "pin") or not self.app.pin:
            print("PIN not set yet, cannot load recipients")
            return

        try:
            recipients = load_recipients(self.app.pin)
        except Exception as e:
            print("Failed to load recipients:", e)
            recipients = {}

        for name, key in recipients.items():
            self.rec_listbox.insert(tk.END, f"{name}: {key}")


    def add_recipient_gui(self):
        name = CTkDialog(self.frame, title="Add Recipient", label="Name:").result
        if not name:
            return

        pub_key = CTkDialog(self.frame, title="Add Recipient", label="Public Key (64 hex chars):").result
        if not pub_key or len(pub_key) != 64:
            messagebox.showerror("Error", "Invalid public key")
            return

        add_recipient(name, pub_key, self.app.pin)
        self.refresh_list()
        if hasattr(self.app, "update_recipient_list"):
            self.app.update_recipient_list()

    def edit_recipient(self):
        sel = self.rec_listbox.curselection()
        if not sel:
            messagebox.showwarning("Select", "Select a recipient to edit")
            return

        entry = self.rec_listbox.get(sel[0])
        name, old_key = entry.split(":")
        name, old_key = name.strip(), old_key.strip()

        new_name = CTkDialog(self.frame, title="Edit Recipient", label="New Name:", initial_value=name).result
        if not new_name:
            return

        new_key = CTkDialog(self.frame, title="Edit Recipient", label="New Public Key:", initial_value=old_key).result
        if not new_key or len(new_key) != 64:
            messagebox.showerror("Error", "Invalid public key")
            return

        delete_recipient(name, self.app.pin)
        add_recipient(new_name, new_key, self.app.pin)
        self.refresh_list()
        if hasattr(self.app, "update_recipient_list"):
            self.app.update_recipient_list()

    def delete_recipient(self):
        sel = self.rec_listbox.curselection()
        if not sel:
            messagebox.showwarning("Select", "Select a recipient to delete")
            return

        entry = self.rec_listbox.get(sel[0])
        name = entry.split(":")[0].strip()

        confirm = CTkConfirmDialog(self.frame, title="Delete Recipient", message=f"Delete {name}?")
        if confirm.result:
            delete_recipient(name, self.app.pin)
            self.refresh_list()
            self.app.update_recipient_list()
