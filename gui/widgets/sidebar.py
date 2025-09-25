import customtkinter as ctk
from utils.recipients import add_recipient, get_recipient_key, get_recipient_name, load_recipients
from gui.widgets.notification import Notification, NotificationManager

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, select_callback, add_callback=None, pin=None):
        super().__init__(parent, width=220, corner_radius=0)
        self.select_callback = select_callback
        self.add_callback = add_callback
        self.pin = pin 
        self.pack(side="left", fill="y")

        self.notifier = NotificationManager(parent)

        # Title
        ctk.CTkLabel(self, text="Recipients", font=("Segoe UI", 16, "bold")).pack(pady=12)

        # Scrollable list
        self.recipient_listbox = ctk.CTkScrollableFrame(self, width=200)
        self.recipient_listbox.pack(fill="y", expand=True, padx=10, pady=(0, 10))
        self.update_list()

        # Add Recipient button
        self.add_btn = ctk.CTkButton(
            self,
            text="➕ Add Recipient",
            command=self.open_add_dialog,
            fg_color="#4a90e2",
            hover_color="#357ABD",
            text_color="white",
            font=("Segoe UI", 14, "bold"),
            corner_radius=20,
            height=48
        )
        self.add_btn.pack(pady=12, padx=12, fill="x")

    def update_list(self, selected_pub=None):
        # get current PIN from your app/session
        pin = self.pin 
        recipients = load_recipients(pin)

        for widget in self.recipient_listbox.winfo_children():
            widget.destroy()

        for name, key in recipients.items():
            is_selected = (key == selected_pub)
            btn = ctk.CTkButton(
                self.recipient_listbox,
                text=name,
                fg_color="#4a90e2" if is_selected else "#3e3e50",
                hover_color="#4a4a6a",
                font=("Segoe UI", 12),
                height=40,
                command=lambda n=name: self.select_callback(n)
            )
            btn.pack(fill="x", pady=4, padx=5)


    def open_add_dialog(self):
        AddRecipientDialog(
            self, 
            self.notifier, 
            self.update_list, 
            self.add_callback,
            pin=self.pin
        )



class AddRecipientDialog(ctk.CTkToplevel):
    def __init__(self, parent, notifier, update_list_callback, add_callback=None, pin=None):
        super().__init__(parent)
        self.title("Add Recipient")
        self.geometry("360x260")
        self.resizable(False, False)
        self.grab_set()  # modal
        self.pin = pin

        self.parent = parent
        self.notifier = notifier
        self.update_list_callback = update_list_callback
        self.add_callback = add_callback

        # Title
        ctk.CTkLabel(self, text="Add New Recipient", font=("Segoe UI", 16, "bold")).pack(pady=(20, 10))

        # Name
        ctk.CTkLabel(self, text="Recipient Name:", font=("Segoe UI", 12)).pack(anchor="w", padx=20)
        self.name_entry = ctk.CTkEntry(self, placeholder_text="e.g. John Doe", height=40, font=("Segoe UI", 12))
        self.name_entry.pack(padx=20, pady=(0, 10), fill="x")

        # Key
        ctk.CTkLabel(self, text="Recipient Key:", font=("Segoe UI", 12)).pack(anchor="w", padx=20)
        self.key_entry = ctk.CTkEntry(self, placeholder_text="e.g. ABC123XYZ", height=40, font=("Segoe UI", 12))
        self.key_entry.pack(padx=20, pady=(0, 15), fill="x")

        # Buttons frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)

        # Cancel button
        ctk.CTkButton(
            btn_frame, text="Cancel",
            fg_color="gray40", hover_color="gray25",
            font=("Segoe UI", 12, "bold"), width=140, height=48,
            command=self.destroy
        ).pack(side="left", padx=10)

        # Add button
        ctk.CTkButton(
            btn_frame, text="Add",
            fg_color="#4a90e2", hover_color="#357ABD",
            font=("Segoe UI", 12, "bold"), width=140, height=48,
            command=self.confirm
        ).pack(side="left", padx=10)

        self.bind("<Return>", lambda e: self.confirm())
    def confirm(self):
        name = self.name_entry.get().strip()
        key = self.key_entry.get().strip()
        if name and key:
            try:
                add_recipient(name, key, self.pin) 
                print(f"Added recipient: {name} / {key}")
                self.update_list_callback(selected_pub=key)
                self.notifier.show(f"Recipient '{name}' added!", type_="success")
                
                # safely destroy dialog
                self.unbind("<Return>")
                self.after(10, self.destroy)

            except ValueError as e:
                self.notifier.show(str(e), type_="error")
        else:
            self.notifier.show("Please fill both fields!", type_="warning")
