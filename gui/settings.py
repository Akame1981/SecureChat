import tkinter as tk
from tkinter import simpledialog, messagebox, Toplevel
import customtkinter as ctk
from utils.crypto import load_key, save_key, PrivateKey, SigningKey
from utils.recipients import recipients, add_recipient, get_recipient_key

class SettingsWindow(Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.parent = parent
        self.app = app
        self.title("Settings")
        self.geometry("500x450")
        self.minsize(400, 350)
        self.configure(bg="#1e1e2f")

        # Make the window resizable
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(self, text="Settings", font=("Roboto", 20, "bold"), text_color="white").grid(row=0, column=0, pady=(15, 10))

        # --- Tab view ---
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.tabs.add("Keys")
        self.tabs.add("Recipients")

        # Make tabs expandable
        self.tabs.tab("Keys").grid_rowconfigure(1, weight=1)
        self.tabs.tab("Keys").grid_columnconfigure(0, weight=1)
        self.tabs.tab("Recipients").grid_rowconfigure(1, weight=1)
        self.tabs.tab("Recipients").grid_columnconfigure(0, weight=1)

        # --- Keys Tab ---
        self.keys_tab = self.tabs.tab("Keys")
        ctk.CTkLabel(self.keys_tab, text="Key Management", font=("Roboto", 16, "bold"), text_color="white").grid(row=0, column=0, pady=(10, 10), padx=10)

        ctk.CTkButton(self.keys_tab, text="Generate New Keypair", command=self.new_key, fg_color="#4a90e2").grid(row=1, column=0, pady=5, padx=20, sticky="ew")
        ctk.CTkButton(self.keys_tab, text="Change Pincode", command=self.change_pin, fg_color="#4a90e2").grid(row=2, column=0, pady=5, padx=20, sticky="ew")

        # --- Recipients Tab ---
        self.recipients_tab = self.tabs.tab("Recipients")
        ctk.CTkLabel(self.recipients_tab, text="Manage Recipients", font=("Roboto", 16, "bold"), text_color="white").grid(row=0, column=0, pady=(10,5), padx=10, sticky="w")

        # Recipient list (scrollable)
        self.rec_listbox = tk.Listbox(self.recipients_tab, bg="#1e1e2f", fg="white", bd=0, highlightthickness=0,
                                      selectbackground="#4a90e2", activestyle="none")
        self.rec_listbox.grid(row=1, column=0, sticky="nsew", padx=(10,0), pady=5)
        scrollbar = tk.Scrollbar(self.recipients_tab, command=self.rec_listbox.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=5)
        self.rec_listbox.config(yscrollcommand=scrollbar.set)

        # Buttons frame
        btn_frame = ctk.CTkFrame(self.recipients_tab, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")
        btn_frame.grid_columnconfigure((0,1,2), weight=1)

        ctk.CTkButton(btn_frame, text="Add", command=self.add_recipient_gui, fg_color="#4a90e2").grid(row=0, column=0, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame, text="Edit", command=self.edit_recipient, fg_color="#f0ad4e").grid(row=0, column=1, padx=5, sticky="ew")
        ctk.CTkButton(btn_frame, text="Delete", command=self.delete_recipient, fg_color="#d9534f").grid(row=0, column=2, padx=5, sticky="ew")

        self.refresh_list()

    # --- Key management methods ---
    def new_key(self):
        
        confirm = CTkDialog(self, title="New Key", label="Generate new keypair? (OK to confirm)").result
        if not confirm:
            return

       
        pin = CTkDialog(self, title="Set PIN", label="Enter PIN for new keypair:", show="*").result
        if not pin:
            return

        # Generate and save keys
        self.app.private_key = PrivateKey.generate()
        self.app.signing_key = SigningKey.generate()
        save_key(self.app.private_key, self.app.signing_key, pin)
        self.app.public_key = self.app.private_key.public_key
        self.app.my_pub_hex = self.app.public_key.encode().hex()
        self.app.pub_label.configure(text=f"My Public Key: {self.app.my_pub_hex}")

        
        CTkDialog(self, title="New Key", label="New keypair generated!").result


    def change_pin(self):
        old_pin = CTkDialog(self, title="Current PIN", label="Enter current PIN:", show="*").result
        if not old_pin:
            return

        try:
            priv, sign = load_key(old_pin) 
        except ValueError:
            CTkDialog(self, title="Error", label="Incorrect PIN!").result
            return

        new_pin = CTkDialog(self, title="New PIN", label="Enter new PIN:", show="*").result
        if not new_pin:
            return

        
        save_key(priv, sign, new_pin)

       
        CTkDialog(self, title="Success", label="PIN updated!").result


    # --- Recipient management methods ---
    def refresh_list(self):
        self.rec_listbox.delete(0, tk.END)
        for name, key in recipients.items():
            self.rec_listbox.insert(tk.END, f"{name}: {key}")

    def add_recipient_gui(self):
        # Custom dialog for recipient name
        name = CTkDialog(self, title="Add Recipient", label="Name:").result
        if not name:
            return

        # Custom dialog for recipient public key
        pub_key = CTkDialog(self, title="Add Recipient", label="Public Key (64 hex chars):").result
        if not pub_key or len(pub_key) != 64:
            messagebox.showerror("Error", "Invalid public key")
            return

        add_recipient(name, pub_key)
        self.refresh_list()

        # Safely update main app sidebar
        if hasattr(self.app, "update_recipient_list"):
            self.app.update_recipient_list()


    def edit_recipient(self):
        sel = self.rec_listbox.curselection()
        if not sel:
            
            messagebox.showwarning("Select", "Select a recipient to edit")
            return

        entry = self.rec_listbox.get(sel[0])
        name, old_key = entry.split(":")
        name = name.strip()
        old_key = old_key.strip()

        # Custom dialog for new name
        new_name = CTkDialog(self, title="Edit Recipient", label="New Name:", initial_value=name).result
        if not new_name:
            return

        # Custom dialog for new public key
        new_key = CTkDialog(self, title="Edit Recipient", label="New Public Key:", initial_value=old_key).result
        if not new_key or len(new_key) != 64:
            messagebox.showerror("Error", "Invalid public key")
            return

        recipients.pop(name)
        add_recipient(new_name, new_key)
        self.refresh_list()

        # Safely update main app sidebar
        if hasattr(self.app, "update_recipient_list"):
            self.app.update_recipient_list()


    def delete_recipient(self):
        sel = self.rec_listbox.curselection()
        if not sel:
            
            messagebox.showwarning("Select", "Select a recipient to delete")
            return
        entry = self.rec_listbox.get(sel[0])
        name = entry.split(":")[0].strip()

        confirm = CTkConfirmDialog(self, title="Delete Recipient", message=f"Delete {name}?")
        if confirm.result:
            from utils.recipients import delete_recipient as del_rec
            del_rec(name)
            self.refresh_list()
            self.app.update_recipient_list()


class CTkConfirmDialog(ctk.CTkToplevel):
    """Custom yes/no confirmation dialog."""
    def __init__(self, parent, title="Confirm", message="Are you sure?"):
        super().__init__(parent)
        self.title(title)
        self.geometry("350x150")
        self.configure(bg="#1e1e2f")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self.result = False

        # Message
        ctk.CTkLabel(self, text=message, font=("Roboto", 14), text_color="white", wraplength=300).pack(pady=(30,10), padx=10)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="Yes", command=self.yes, fg_color="#4a90e2").pack(side="left", padx=5, expand=True, fill="x")
        ctk.CTkButton(btn_frame, text="No", command=self.no, fg_color="#d9534f").pack(side="left", padx=5, expand=True, fill="x")

        self.bind("<Return>", lambda e: self.yes())
        self.bind("<Escape>", lambda e: self.no())

        self.wait_window()

    def yes(self):
        self.result = True
        self.destroy()

    def no(self):
        self.result = False
        self.destroy()
# CTkDialog class definition
class CTkDialog(ctk.CTkToplevel):
    """Custom input dialog with a label and entry."""
    def __init__(self, parent, title="Input", label="Enter value:", show=None, initial_value=""):
        super().__init__(parent)
        self.title(title)
        self.geometry("350x150")
        self.configure(bg="#1e1e2f")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self.result = None

        # Label
        ctk.CTkLabel(self, text=label, font=("Roboto", 14), text_color="white").pack(pady=(20,5))

        # Entry
        self.entry_var = tk.StringVar(value=initial_value)
        self.entry = ctk.CTkEntry(self, textvariable=self.entry_var, show=show, width=250)
        self.entry.pack(pady=5)
        self.entry.focus()

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="OK", command=self.ok, fg_color="#4a90e2").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.cancel, fg_color="#d9534f").pack(side="left", padx=5)

        self.bind("<Return>", lambda e: self.ok())
        self.bind("<Escape>", lambda e: self.cancel())

        self.wait_window()

    def ok(self):
        self.result = self.entry_var.get()
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()
