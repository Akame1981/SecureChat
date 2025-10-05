import os
import threading
import time
import json
import requests
import sys
import tkinter as tk
from tkinter import simpledialog, Toplevel

import customtkinter as ctk

from gui.pin_dialog import PinDialog
from gui.settings.window import SettingsWindow
from gui.tooltip import ToolTip
from gui.widgets.notification import Notification, NotificationManager
from gui.widgets.sidebar import Sidebar

from utils.chat_storage import load_messages, save_message
from utils.crypto import (
    KEY_FILE,
    PrivateKey,
    SigningKey,
    decrypt_message,
    encrypt_message,
    load_key,
    save_key,
    sign_message,
    verify_signature,
)
from utils.network import fetch_messages, send_message
from utils.recipients import add_recipient, get_recipient_key, get_recipient_name, load_recipients
from datetime import datetime


CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "config/settings.json"))
def get_resource_path(relative_path):
    """Return absolute path to resource, works for dev and PyInstaller."""
    if getattr(sys, "_MEIPASS", False):
        # PyInstaller onefile mode
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

class WhisprApp(ctk.CTk):

    def update_recipient_list(self):
        """Refresh the sidebar recipient buttons."""
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.update_list(selected_pub=self.recipient_pub_hex)
    
    


    def __init__(self):
        super().__init__()
        self.title("🕵️ Whispr")
        self.geometry("600x600")

        
        ctk.set_appearance_mode("dark")     
        ctk.set_default_color_theme("blue")   

        self.private_key = None
        self.public_key = None
        self.my_pub_hex = None
        self.recipient_pub_hex = None


        self.notifier = NotificationManager(self)
        
        # Default server values (backup if config load fails)
        self.SERVER_URL = "https://34.61.34.132:8000"
        self.SERVER_CERT = get_resource_path("utils/cert.pem")


        # --- Load saved settings ---
        self.load_app_settings()

        # Initialize keypair
        self.init_keypair()
        self.create_widgets()

        # Start fetch loop
        self.stop_event = threading.Event()
        threading.Thread(target=self.fetch_loop, daemon=True).start()
        threading.Thread(target=self.check_server_loop, daemon=True).start()

        self.protocol("WM_DELETE_WINDOW", self.on_close)



# ---------------- Keypair ----------------
    def init_keypair(self):
        if os.path.exists(KEY_FILE):
            dlg = PinDialog(self, "Enter PIN to unlock keypair")
            self.wait_window(dlg)
            pin = dlg.pin
            if not pin:
                self.destroy()
                return
            try:
                self.private_key, self.signing_key = load_key(pin)
                self.pin = pin  # <-- save PIN for chat encryption
            except ValueError:
                self.notifier.show("Incorrect PIN or corrupted key!", type_="error")
                self.destroy()
                return
        else:
            dlg = PinDialog(self, "Set a new PIN", new_pin=True)
            self.wait_window(dlg)
            pin = dlg.pin
            if not pin:
                self.destroy()
                return

            self.private_key = PrivateKey.generate()
            self.signing_key = SigningKey.generate()
            save_key(self.private_key, self.signing_key, pin)
            self.pin = pin  # <-- save PIN for chat encryption
            self.notifier.show("New keypair generated!", type_="success")

        self.public_key = self.private_key.public_key
        self.my_pub_hex = self.public_key.encode().hex()
        self.signing_pub_hex = self.signing_key.verify_key.encode().hex()


    def select_recipient(self, name):
        # Pass self.pin to get_recipient_key
        self.recipient_pub_hex = get_recipient_key(name, self.pin)
        self.sidebar.update_list(selected_pub=self.recipient_pub_hex)

        # Clear previous messages
        for widget in self.messages_container.winfo_children():
            widget.destroy()

        # Load messages for this recipient
        if self.recipient_pub_hex:
            messages = load_messages(self.recipient_pub_hex, self.pin)
            for msg in messages:
                self.display_message(msg["sender"], msg["text"])




    # ---------------- GUI ----------------
    def create_widgets(self):
        # ---------------- Main Layout ----------------
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True)






        def update_status_color(online):
            color = "green" if online else "red"
            self.server_status.configure(text="●", text_color=color)

        self.update_status_color = update_status_color  # store method



        # Sidebar (left)
        self.sidebar = Sidebar(
            main_frame,
            select_callback=self.select_recipient,
            add_callback=self.add_new_recipient,
            pin=self.pin
        )
        # ---------------- Chat Area (right) ----------------
        chat_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        chat_frame.pack(side="right", fill="both", expand=True)


        # ---------------- Public Key Frame ----------------f
        pub_frame = ctk.CTkFrame(chat_frame, fg_color="#2e2e3f", corner_radius=10)
        pub_frame.pack(fill="x", padx=10, pady=10)
        pub_frame.grid_columnconfigure(0, weight=1)
        pub_frame.grid_columnconfigure(1, weight=0)
        pub_frame.grid_columnconfigure(2, weight=0)





        # Then the label
        self.pub_label = ctk.CTkLabel(pub_frame, text="", justify="left", anchor="w")
        self.pub_label.grid(row=0, column=0, padx=10, pady=10, sticky="we")

        def update_pub_label(event=None):
            pub_frame.update_idletasks()
            frame_width = pub_frame.winfo_width() - self.copy_btn.winfo_width() - self.settings_btn.winfo_width() - 30
            approx_char_width = 7
            max_chars = max(10, frame_width // approx_char_width)

            truncated = self.my_pub_hex
            if len(truncated) > max_chars:
                truncated = truncated[:max_chars-3] + "..."
            
            self.pub_label.configure(text=f"My Public Key: {truncated}")

            # Add tooltip for full key
            if not hasattr(self, 'pub_tooltip'):
                self.pub_tooltip = ToolTip(self.pub_label, self.my_pub_hex)
            else:
                self.pub_tooltip.text = self.my_pub_hex



        pub_frame.bind("<Configure>", update_pub_label)
        self.after(200, update_pub_label)  # initial update



        self.copy_btn = ctk.CTkButton(pub_frame, text="Copy", command=self.copy_pub_key, fg_color="#4a4a6a")
        self.copy_btn.grid(row=0, column=1, padx=5, pady=10)

        self.settings_btn = ctk.CTkButton(pub_frame, text="Settings", command=self.open_settings, fg_color="#4a90e2")
        self.settings_btn.grid(row=0, column=2, padx=5, pady=10)


        # Messages Box
        self.messages_container = ctk.CTkScrollableFrame(chat_frame, fg_color="#2e2e3f", corner_radius=10)
        self.messages_container.pack(padx=10, pady=10, fill="both", expand=True)
        self.messages_container.grid_columnconfigure(0, weight=1)

        # Input Frame
        input_frame = ctk.CTkFrame(chat_frame, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=(0,10))

        self.input_box = ctk.CTkEntry(input_frame, placeholder_text="Type a message...")
        self.input_box.pack(side="left", expand=True, fill="x", padx=(0,5), pady=5)
        self.input_box.bind("<Return>", lambda event: self.on_send())

        ctk.CTkButton(input_frame, text="Send", command=self.on_send, fg_color="#4a90e2").pack(side="right", padx=(0,5), pady=5)



        # Server status (top-right corner)
        self.server_status = ctk.CTkLabel(pub_frame, text="●", font=("Roboto", 16))
        self.server_status.grid(row=0, column=3, padx=5)
    # ---------------- Public key ----------------
    def copy_pub_key(self):
        self.clipboard_clear()
        self.clipboard_append(self.my_pub_hex)
        self.notifier.show("Public key copied!", type_="success")
    # ---------------- Messages ----------------

    def display_message(self, sender_pub, text):
        display_sender = "You" if sender_pub == self.my_pub_hex else get_recipient_name(sender_pub, self.pin) or sender_pub

        is_you = display_sender == "You"

        bubble_color = "#7289da" if is_you else "#2f3136"


        bubble_frame = ctk.CTkFrame(
            self.messages_container,
            fg_color=bubble_color,
            corner_radius=20  #
        )

        # Sender + timestamp (soon gonna add the timestamp really its a placeholder)
        timestamp = datetime.now().strftime("%H:%M")
        sender_label = ctk.CTkLabel(
            bubble_frame,
            text=f"{display_sender} • {timestamp}",
            text_color="white",
            font=("Roboto", 10, "bold")
        )
        sender_label.pack(anchor="w" if not is_you else "e", pady=(0, 5), padx=20)

        # Message text
        msg_label = ctk.CTkLabel(
            bubble_frame,
            text=text,
            wraplength=400,
            justify="left" if not is_you else "right",
            text_color="white",
            font=("Roboto", 12)
        )
        msg_label.pack(anchor="w" if not is_you else "e", padx=20, pady=(0,10))


        bubble_frame.pack(
            anchor="w" if not is_you else "e",
            pady=8,
            padx=20,  
            fill="x"
        )

        # Auto-scroll
        self.messages_container._parent_canvas.update_idletasks()
        self.messages_container._parent_canvas.yview_moveto(1.0)





    def on_send(self):
        text = self.input_box.get().strip()
        if not text:
            return

        # Handle special commands
        if text.startswith("/new"):
            self.add_new_recipient()
            self.input_box.delete(0, tk.END)
            return
        if text.startswith("/choose"):
            self.choose_recipient()
            self.input_box.delete(0, tk.END)
            return

        # No recipient selected
        if not self.recipient_pub_hex:
            self.notifier.show("Select a recipient first", type_="warning")
            return

        # Send the message, passing both signing and encryption keys
        if send_message(
            self,  # pass the app instance
            to_pub=self.recipient_pub_hex,
            signing_pub=self.signing_pub_hex,
            text=text,
            signing_key=self.signing_key,
            enc_pub=self.my_pub_hex
        ):

            # Display the message locally
            self.display_message(self.my_pub_hex, text)

            # Save message to local chat storage
            save_message(self.recipient_pub_hex, "You", text, self.pin)


        # Clear input box after sending
        self.input_box.delete(0, tk.END)



    def load_app_settings(self):
        """Load server settings and other configurations at startup."""
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    data = json.load(f)
                
                # Apply server type
                server_type = data.get("server_type", "public")
                custom_url = data.get("custom_url", "http://127.0.0.1:8000")
                use_cert = data.get("use_cert", True)
                cert_path = data.get("cert_path", "utils/cert.pem")

                if server_type == "public":
                    self.SERVER_URL = "https://34.61.34.132:8000"
                    self.SERVER_CERT = get_resource_path("utils/cert.pem")  
                else:
                    self.SERVER_URL = custom_url
                    self.SERVER_CERT = get_resource_path(cert_path) if use_cert else None


            except Exception as e:
                print("Failed to load app settings:", e)


    def fetch_loop(self):
        while not self.stop_event.is_set():
            msgs = fetch_messages(self, self.my_pub_hex, self.private_key)
            for msg in msgs:
                sender_pub = msg["from_enc"]  
                encrypted_message = msg["message"]
                signature = msg.get("signature")

                # Verify signature using signing key
                if signature and verify_signature(msg["from_sign"], encrypted_message, signature):
                    decrypted = decrypt_message(encrypted_message, self.private_key)
                    
                    # Display in GUI
                    self.after(0, self.display_message, sender_pub, decrypted)
                    
                    # Save to local chat storage
                    save_message(sender_pub, get_recipient_name(sender_pub, self.pin) or sender_pub, decrypted, self.pin)


            time.sleep(1)



    def check_server_loop(self):
        while not self.stop_event.is_set():
            online = False
            try:
                # Simple GET request to server root
                resp = requests.get(self.SERVER_URL, verify=self.SERVER_CERT, timeout=3)
                online = True  # Server is online if request succeeds
            except requests.exceptions.ConnectionError as e:
                msg = f"⚠ Server offline (connection refused): {e}"
                print(msg)
                if hasattr(self, 'notifier') and self.notifier:
                    self.notifier.show(msg, type_="error")
                online = False
            except requests.exceptions.SSLError as e:
                msg = f"⚠ SSL verification failed: {e}"
                print(msg)
                if hasattr(self, 'notifier') and self.notifier:
                    self.notifier.show(msg, type_="warning")
                online = False
            except requests.exceptions.RequestException as e:
                msg = f"⚠ Server check failed: {e}"
                print(msg)
                if hasattr(self, 'notifier') and self.notifier:
                    self.notifier.show(msg, type_="error")
                online = False

            # Update GUI indicator
            self.after(0, self.update_status_color, online)
            time.sleep(1)



    # ---------------- Settings ----------------



    def open_settings(self):
        SettingsWindow(self, self)


    # ---------------- Recipients ----------------
    def add_new_recipient(self):
        name = simpledialog.askstring("Name", "Recipient name:")
        if not name:
            return
        pub_hex = simpledialog.askstring("Public Key", f"Public key for {name}:")
        if not pub_hex or len(pub_hex) != 64:
            self.notifier.show("Invalid public key", type_="error")
            return
        
        try:
            add_recipient(name, pub_hex, self.pin)
        except ValueError as e:
            self.notifier.show(str(e), type_="error")
            return

        self.recipient_pub_hex = pub_hex
        self.update_recipient_list()
        self.notifier.show(f"{name} saved and selected.")





    def choose_recipient(self):
        recipients = load_recipients(self.pin)  # <-- load recipients dynamically
        if not recipients:
            self.notifier.show("Add a recipient first", type_="warning")
            return

        choose_win = Toplevel(self)
        choose_win.title("Choose Recipient")
        choose_win.geometry("300x300")
        choose_win.configure(bg="#1e1e2f")

        listbox = tk.Listbox(choose_win, bg="#2e2e3f", fg="white")
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for name in recipients:
            listbox.insert(tk.END, name)

        def select():
            sel = listbox.curselection()
            if sel:
                name = listbox.get(sel[0])
                self.recipient_pub_hex = get_recipient_key(name, self.pin)
                choose_win.destroy()

        tk.Button(choose_win, text="Select", command=select, bg="#4a90e2", fg="white").pack(pady=5)

    # ---------------- Close ----------------

    
    def on_close(self):
        self.stop_event.set()
        self.destroy()



if __name__ == "__main__":
    app = WhisprApp()
    app.mainloop()
