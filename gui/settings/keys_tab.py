import customtkinter as ctk
from gui.settings.dialogs import CTkDialog
from utils.crypto import PrivateKey, SigningKey, save_key, load_key

class KeysTab:
    def __init__(self, parent_frame, app):
        self.app = app
        self.frame = parent_frame  # This is already a CTkFrame from the tabview

        # Make the frame expandable
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(
            self.frame,
            text="Key Management",
            font=("Roboto", 16, "bold"),
            text_color="white"
        ).grid(row=0, column=0, pady=(10, 10), padx=10)

        # Buttons
        ctk.CTkButton(
            self.frame,
            text="Generate New Keypair",
            command=self.new_key,
            fg_color="#4a90e2"
        ).grid(row=1, column=0, pady=5, padx=20, sticky="ew")

        ctk.CTkButton(
            self.frame,
            text="Change Pincode",
            command=self.change_pin,
            fg_color="#4a90e2"
        ).grid(row=2, column=0, pady=5, padx=20, sticky="ew")

    def new_key(self):
        confirm = CTkDialog(self.frame, title="New Key", label="Generate new keypair? (OK to confirm)").result
        if not confirm:
            return

        pin = CTkDialog(self.frame, title="Set PIN", label="Enter PIN for new keypair:", show="*").result
        if not pin:
            return

        # Generate keys
        self.app.private_key = PrivateKey.generate()
        self.app.signing_key = SigningKey.generate()
        save_key(self.app.private_key, self.app.signing_key, pin)
        self.app.public_key = self.app.private_key.public_key
        self.app.my_pub_hex = self.app.public_key.encode().hex()
        self.app.pub_label.configure(text=f"My Public Key: {self.app.my_pub_hex}")

        CTkDialog(self.frame, title="New Key", label="New keypair generated!").result

    def change_pin(self):
        old_pin = CTkDialog(self.frame, title="Current PIN", label="Enter current PIN:", show="*").result
        if not old_pin:
            return

        try:
            priv, sign = load_key(old_pin)
        except ValueError:
            CTkDialog(self.frame, title="Error", label="Incorrect PIN!").result
            return

        new_pin = CTkDialog(self.frame, title="New PIN", label="Enter new PIN:", show="*").result
        if not new_pin:
            return

        save_key(priv, sign, new_pin)
        CTkDialog(self.frame, title="Success", label="PIN updated!").result
