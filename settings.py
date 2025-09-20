import tkinter as tk
from tkinter import simpledialog, messagebox, Toplevel
import customtkinter as ctk
from crypto import load_key, save_key, PrivateKey, SigningKey
from recipients import recipients, add_recipient, get_recipient_key

class SettingsWindow(Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.parent = parent
        self.app = app  # reference to main app to update UI
        self.title("Settings")
        self.geometry("400x300")
        self.configure(bg="#1e1e2f")

        # Generate new key
        ctk.CTkButton(self, text="Generate New Keypair", command=self.new_key, fg_color="#4a90e2").pack(pady=10)

        # Change PIN
        ctk.CTkButton(self, text="Change Pincode", command=self.change_pin, fg_color="#4a90e2").pack(pady=10)

        # Manage recipients
        ctk.CTkButton(self, text="Manage Recipients", command=self.show_recipients, fg_color="#4a90e2").pack(pady=10)

    def new_key(self):
        if messagebox.askyesno("New Key", "Generate new keypair?"):
            pin = simpledialog.askstring("Set PIN", "Enter PIN for new keypair:", show="*")
            if not pin:
                return
            self.app.private_key = PrivateKey.generate()
            self.app.signing_key = SigningKey.generate()
            save_key(self.app.private_key, self.app.signing_key, pin)
            self.app.public_key = self.app.private_key.public_key
            self.app.my_pub_hex = self.app.public_key.encode().hex()
            self.app.pub_label.configure(text=f"My Public Key: {self.app.my_pub_hex}")
            messagebox.showinfo("New Key", "New keypair generated!")

    def change_pin(self):
        old_pin = simpledialog.askstring("Current PIN", "Enter current PIN:", show="*")
        if not old_pin:
            return
        try:
            priv = load_key(old_pin)
        except ValueError:
            messagebox.showerror("Error", "Incorrect PIN!")
            return
        new_pin = simpledialog.askstring("New PIN", "Enter new PIN:", show="*")
        if not new_pin:
            return
        save_key(priv, new_pin)
        messagebox.showinfo("Success", "PIN updated!")

    def show_recipients(self):
        rec_window = Toplevel(self)
        rec_window.title("Recipients")
        rec_window.geometry("400x400")
        rec_window.configure(bg="#1e1e2f")

        frame = ctk.CTkFrame(rec_window, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        listbox = tk.Listbox(frame, bg="#2e2e3f", fg="white")
        listbox.pack(side="left", fill="both", expand=True, pady=5)

        scrollbar = tk.Scrollbar(frame, command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.config(yscrollcommand=scrollbar.set)

        def refresh_list():
            listbox.delete(0, tk.END)
            for name, key in recipients.items():
                listbox.insert(tk.END, f"{name}: {key}")
        refresh_list()

        def add_recipient_gui():
            name = simpledialog.askstring("Add Recipient", "Name:")
            if not name:
                return
            pub_key = simpledialog.askstring("Add Recipient", "Public Key (64 hex chars):")
            if not pub_key or len(pub_key) != 64:
                messagebox.showerror("Error", "Invalid public key")
                return
            add_recipient(name, pub_key)
            refresh_list()
            self.app.update_recipient_list()

        def edit_recipient():
            sel = listbox.curselection()
            if not sel:
                messagebox.showwarning("Select", "Select a recipient to edit")
                return
            entry = listbox.get(sel[0])
            name, old_key = entry.split(":")
            name = name.strip()
            old_key = old_key.strip()
            new_name = simpledialog.askstring("Edit Recipient", "New Name:", initialvalue=name)
            if not new_name:
                return
            new_key = simpledialog.askstring("Edit Recipient", "New Public Key:", initialvalue=old_key)
            if not new_key or len(new_key) != 64:
                messagebox.showerror("Error", "Invalid public key")
                return
            recipients.pop(name)
            add_recipient(new_name, new_key)
            refresh_list()
            self.app.update_recipient_list()

        def delete_recipient():
            sel = listbox.curselection()
            if not sel:
                messagebox.showwarning("Select", "Select a recipient to delete")
                return
            entry = listbox.get(sel[0])
            name = entry.split(":")[0].strip()
            if messagebox.askyesno("Delete", f"Delete {name}?"):
                recipients.pop(name)
                refresh_list()
                self.app.update_recipient_list()

        btn_frame = ctk.CTkFrame(rec_window, fg_color="transparent")
        btn_frame.pack(pady=5)
        ctk.CTkButton(btn_frame, text="Add", command=add_recipient_gui, fg_color="#4a90e2").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Edit", command=edit_recipient, fg_color="#f0ad4e").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Delete", command=delete_recipient, fg_color="#d9534f").pack(side="left", padx=5)
