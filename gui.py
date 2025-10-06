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
from gui.layout import WhisprUILayout
from gui.message_styling import create_message_bubble

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
from utils.chat_manager import ChatManager
from utils.server_check import run_server_check_in_thread
from utils.message_handler import handle_send
from utils.key_manager import init_keypair


from datetime import datetime
import time  


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
    
    def load_theme_from_settings(self):
        """Load saved theme and apply appearance mode and color theme."""
        self.current_theme = "Dark"  # fallback
        self.theme_colors = {}

        # Load saved theme name
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    data = json.load(f)
                    self.current_theme = data.get("theme_name", "Dark")
            except Exception as e:
                print("Failed to load theme:", e)

        # Load all themes
        themes_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "config/themes.json"))
        if os.path.exists(themes_file):
            try:
                with open(themes_file, "r") as f:
                    self.theme_colors = json.load(f)
            except Exception as e:
                print("Failed to load themes.json:", e)

        # Apply appearance mode
        theme = self.theme_colors.get(self.current_theme, {})
        mode = theme.get("mode", "Dark")
        ctk.set_appearance_mode(mode.lower())

        # Apply accent color if present (default to blue)
        accent_color = theme.get("accent_color", "blue")
        ctk.set_default_color_theme(accent_color)


    def update_message_bubbles_theme(self):
        if not hasattr(self, "messages_container") or not hasattr(self, "theme_colors") or not hasattr(self, "current_theme"):
            return

        theme = self.theme_colors.get(self.current_theme, {})
        bubble_you_color = theme.get("bubble_you", "#7289da")
        bubble_other_color = theme.get("bubble_other", "#2f3136")
        text_color = theme.get("text", "white")

        for bubble in self.messages_container.winfo_children():
            if hasattr(bubble, "is_you") and hasattr(bubble, "sender_label") and hasattr(bubble, "msg_label"):
                bubble.configure(fg_color=bubble_you_color if bubble.is_you else bubble_other_color)
                bubble.sender_label.configure(text_color=text_color)
                bubble.msg_label.configure(text_color=text_color)


    def __init__(self):
        super().__init__()
        
        self.load_theme_from_settings()


        self.title("🕵️ Whispr")
        self.geometry("600x600")


        

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
        self.load_theme_from_settings()

        # Initialize keypair
        self.init_keypair()
        self.layout = WhisprUILayout(self)
        self.layout.create_widgets()
        self.update_message_bubbles_theme()


        self.chat_manager = ChatManager(self)

        # Start fetch loop
        self.stop_event = threading.Event()
        threading.Thread(target=self.chat_manager.fetch_loop, daemon=True).start()

        run_server_check_in_thread(self, interval=1.0)

        self.protocol("WM_DELETE_WINDOW", self.on_close)



# ---------------- Keypair ----------------
    def init_keypair(self):
        result = init_keypair(self.notifier, PinDialog, self)
        if not result:
            self.destroy()
            return

        self.private_key, self.signing_key, self.pin = result
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
                        self.display_message(msg["sender"], msg["text"], timestamp=msg.get("timestamp"))




    # ---------------- Public key ----------------
    def copy_pub_key(self):
        self.clipboard_clear()
        self.clipboard_append(self.my_pub_hex)
        self.notifier.show("Public key copied!", type_="success")
    # ---------------- Messages ----------------

    def display_message(self, sender_pub, text, timestamp=None):
        create_message_bubble(
            self.messages_container,
            sender_pub,
            text,
            self.my_pub_hex,
            self.pin,
            timestamp=timestamp
        )






    def on_send(self):
        handle_send(self)



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
