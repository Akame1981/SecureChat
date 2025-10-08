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

        # Scrollable content area so the tab scales on small windows
        content = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=10, pady=(6,10))
        content.grid_columnconfigure(0, weight=1)

        # Primary actions card
        top_card = ctk.CTkFrame(content, fg_color="#1e1e2f", corner_radius=8)
        top_card.grid(row=0, column=0, padx=10, pady=(0, 12), sticky="ew")
        top_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(top_card, text="Account keys", font=("Roboto", 12, "bold"), text_color="#dbe4ff").grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))
        ctk.CTkLabel(top_card, text="Generate or rotate your keypair and change the PIN used to encrypt them.", font=("Roboto", 10), text_color="#b2b8d6", justify="left").grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))

        # Action buttons inside card
        btn_frame = ctk.CTkFrame(top_card, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(btn_frame, text="Generate New Keypair", command=self.new_key, fg_color="#4a90e2").grid(row=0, column=0, sticky="ew", padx=(0,8))
        ctk.CTkButton(btn_frame, text="Change PIN", command=self.change_pin, fg_color="#4a90e2").grid(row=0, column=1, sticky="ew", padx=(8,0))

        # Public key display (read-only)
        pub_frame = ctk.CTkFrame(content, fg_color="#1a1a26", corner_radius=6)
        pub_frame.grid(row=1, column=0, padx=10, sticky="ew", pady=(0, 12))
        pub_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(pub_frame, text="My Public Key", font=("Roboto", 11, "bold"), text_color="#dbe4ff").grid(row=0, column=0, sticky="w", padx=12, pady=(8,4))
        pub_hex = getattr(self.app, "my_pub_hex", None) or "(not available)"
        self.pub_label = ctk.CTkLabel(pub_frame, text=pub_hex, font=("Roboto", 10), text_color="#9fb0ff", wraplength=800, anchor="w", justify="left")
        self.pub_label.grid(row=1, column=0, sticky="ew", padx=12, pady=(0,8))

        copy_frame = ctk.CTkFrame(pub_frame, fg_color="transparent")
        copy_frame.grid(row=2, column=0, sticky="e", padx=12, pady=(0,8))
        ctk.CTkButton(copy_frame, text="Copy Public Key", command=self._copy_pub, width=160, fg_color="#4a90e2").grid(row=0, column=0)

        # Export / Import card
        warn_card = ctk.CTkFrame(content, fg_color="#1e1e2f", corner_radius=8)
        warn_card.grid(row=2, column=0, padx=10, pady=(0, 12), sticky="ew")
        warn_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(warn_card, text="Backup / Restore", font=("Roboto", 12, "bold"), text_color="#dbe4ff").grid(row=0, column=0, sticky="w", padx=12, pady=(8,4))
        ctk.CTkLabel(warn_card, text=("⚠ Exporting or importing your account will create or overwrite a backup containing your encrypted keys and messages.\nKeep the exported file safe and make sure you have the original PIN."), font=("Roboto", 10), text_color="orange", justify="left", wraplength=800).grid(row=1, column=0, sticky="w", padx=12, pady=(0,8))

        exp_frame = ctk.CTkFrame(warn_card, fg_color="transparent")
        exp_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0,12))
        exp_frame.grid_columnconfigure(0, weight=1)
        exp_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(exp_frame, text="Export Account", command=self.export_account, fg_color="#4a90e2").grid(row=0, column=0, sticky="ew", padx=(0,8))
        ctk.CTkButton(exp_frame, text="Import Account", command=self.import_account, fg_color="#4a90e2").grid(row=0, column=1, sticky="ew", padx=(8,0))


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
        except FileNotFoundError:
            CTkDialog(self.frame, title="Error", label="Key file not found. Generate a new keypair.").result
            return
        except ValueError:
            CTkDialog(self.frame, title="Error", label="Incorrect PIN or corrupted key file!").result
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
        except FileNotFoundError:
            CTkDialog(self.frame, title="Error", label="Key file not found. Cannot export.").result
            return
        except ValueError:
            CTkDialog(self.frame, title="Error", label="Incorrect PIN or corrupted key file!").result
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
            try:
                load_key(pin)
            except FileNotFoundError:
                CTkDialog(self.frame, title="Error", label="Key file not found after import.").result
                return
            except ValueError:
                CTkDialog(self.frame, title="Error", label="Incorrect PIN for imported account!").result
                return
            CTkDialog(self.frame, title="Import Success", label="Account imported successfully!").result
        except Exception as e:
            CTkDialog(self.frame, title="Error", label=f"Failed to import account:\n{str(e)}").result

    def _copy_pub(self):
        try:
            pub = getattr(self.app, "my_pub_hex", None)
            if not pub:
                CTkDialog(self.frame, title="Info", label="Public key not available.").result
                return
            self.frame.clipboard_clear()
            self.frame.clipboard_append(pub)
            if hasattr(self.app, "notifier"):
                self.app.notifier.show("Public key copied", type_="success")
        except Exception:
            pass
