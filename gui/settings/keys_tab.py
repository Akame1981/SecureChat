import os
import zipfile
import customtkinter as ctk
from tkinter import filedialog
from gui.settings.dialogs import CTkDialog
from utils.crypto import PrivateKey, SigningKey, save_key, load_key, KEY_FILE, DATA_DIR

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


        ctk.CTkLabel(
            self.frame,
            text=(
                "⚠ Exporting your account will create a backup containing your encrypted keys and messages.\n"
                "Keep this file safe. You will need your original PIN to import it."
            ),
            font=("Roboto", 11),
            text_color="orange",
            justify="left"
        ).grid(row=3, column=0, pady=(10, 2), padx=20, sticky="w")

        # Export Account button
        ctk.CTkButton(
            self.frame,
            text="Export Account",
            command=self.export_account,
            fg_color="#4a90e2"
        ).grid(row=4, column=0, pady=5, padx=20, sticky="ew")


        ctk.CTkLabel(
            self.frame,
            text=(
                "⚠ Importing an account will overwrite your existing keys and messages.\n"
                "Make sure this is a valid backup. You will need the original PIN."
            ),
            font=("Roboto", 11),
            text_color="orange",
            justify="left"
        ).grid(row=5, column=0, pady=(10, 2), padx=20, sticky="w")

        # Import Account button
        ctk.CTkButton(
            self.frame,
            text="Import Account",
            command=self.import_account,
            fg_color="#4a90e2"
        ).grid(row=6, column=0, pady=5, padx=20, sticky="ew")


    # --- Existing methods ---
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
        if hasattr(self.app, "pub_label"):
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


    def export_account(self):
        pin = CTkDialog(self.frame, title="PIN", label="Enter your PIN to export account:", show="*").result
        if not pin:
            return

        try:
            # verify PIN
            load_key(pin)
        except ValueError:
            CTkDialog(self.frame, title="Error", label="Incorrect PIN!").result
            return

        export_path = filedialog.asksaveasfilename(
            title="Export Account",
            defaultextension=".whispr",
            filetypes=[("Whispr Account", "*.whispr")]
        )
        if not export_path:
            return

        try:
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Include key file
                if os.path.exists(KEY_FILE):
                    zipf.write(KEY_FILE, os.path.basename(KEY_FILE))
                # Include data directory (messages, recipients, etc.)
                for root, dirs, files in os.walk(DATA_DIR):
                    for file in files:
                        zipf.write(os.path.join(root, file),
                                   os.path.relpath(os.path.join(root, file), DATA_DIR))
            CTkDialog(self.frame, title="Export Success", label=f"Account exported to:\n{export_path}").result
        except Exception as e:
            CTkDialog(self.frame, title="Error", label=f"Failed to export account:\n{str(e)}").result

    def import_account(self):
        import_path = filedialog.askopenfilename(
            title="Import Account",
            filetypes=[("Whispr Account", "*.whispr")]
        )
        if not import_path:
            return

        pin = CTkDialog(self.frame, title="PIN", label="Enter your PIN to import account:", show="*").result
        if not pin:
            return

        try:
            with zipfile.ZipFile(import_path, 'r') as zipf:
                zipf.extractall(DATA_DIR)
            # verify PIN
            load_key(pin)
            CTkDialog(self.frame, title="Import Success", label="Account imported successfully!").result
        except Exception as e:
            CTkDialog(self.frame, title="Error", label=f"Failed to import account:\n{str(e)}").result
