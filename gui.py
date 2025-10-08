# --- Standard library ---
import os
import sys
import time
import json
import threading
from datetime import datetime
import tkinter as tk
from tkinter import simpledialog, Toplevel

# --- Third-party ---
import requests
import customtkinter as ctk

# --- GUI modules ---
from gui.pin_dialog import PinDialog
from gui.settings.window import SettingsWindow
from gui.tooltip import ToolTip
from gui.widgets.notification import Notification, NotificationManager
from gui.widgets.sidebar import Sidebar
from gui.layout import WhisprUILayout
from gui.message_styling import create_message_bubble
from gui.message_styling import recolor_message_bubble
from gui.profile_window import open_profile
from gui.theme_manager import ThemeManager
from gui.locked_screen import show_locked_screen

# --- Utils modules ---
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
from utils.app_settings import load_app_settings
from utils.path_utils import get_resource_path



CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "config/settings.json"))

class WhisprApp(ctk.CTk):

    def update_recipient_list(self):
        """Refresh the sidebar recipient buttons."""
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.update_list(selected_pub=self.recipient_pub_hex)
    
    def update_message_bubbles_theme(self):
        if not hasattr(self, "messages_container") or not hasattr(self, "theme_manager"):
            return
        # Ask ThemeManager for the full theme dict and use the message_styling recolor helper
        theme = self.theme_manager.theme_colors.get(self.theme_manager.current_theme, {})
        for bubble in self.messages_container.winfo_children():
            try:
                # Use recolor helper when available for consistent behavior
                recolor_message_bubble(bubble, theme)
            except Exception:
                # Fallback to minimal updates
                try:
                    bubble.configure(fg_color=theme.get('bubble_you' if getattr(bubble, 'is_you', False) else 'bubble_other'))
                except Exception:
                    pass


    def __init__(self):
        super().__init__()
        # Load settings and theme manager
        self.app_settings = load_app_settings()
        self.SERVER_URL = self.app_settings.get("server_url")
        self.SERVER_CERT = self.app_settings.get("server_cert")

        self.theme_manager = ThemeManager()
        # If config provided a theme name, apply it
        cfg_theme = self.app_settings.get("theme_name")
        if cfg_theme:
            self.theme_manager.set_theme_by_name(cfg_theme)

        # Force a full appearance mode + color theme apply right away to avoid
        # any brief mix of default/system + custom colors before widgets mount.
        try:
            self.theme_manager.apply()
        except Exception:
            pass

        # Register a listener so future theme changes apply live
        try:
            self.theme_manager.register_listener(self._on_theme_changed)
        except Exception:
            pass


        self.title("🕵️ Whispr")
        self.geometry("600x600")

        # Apply root background color from theme immediately so window does not flash default color
        try:
            bg = self.theme_manager.theme_colors.get(self.theme_manager.current_theme, {}).get("background")
            if bg:
                self.configure(fg_color=bg)
        except Exception:
            pass


        

        self.private_key = None
        self.public_key = None
        self.my_pub_hex = None
        self.recipient_pub_hex = None
        self.username = "Anonymous"

        self.notifier = NotificationManager(self)




        # Default server values (backup if config load fails)
        if not getattr(self, "SERVER_URL", None):
            self.SERVER_URL = "https://34.61.34.132:8000"
        if not getattr(self, "SERVER_CERT", None):
            # Use packaged cert as fallback
            try:
                self.SERVER_CERT = get_resource_path("utils/cert.pem")
            except Exception:
                self.SERVER_CERT = None


    # --- Settings and theme already loaded above ---

        # Initialize keypair
        self.init_keypair()

        # If keypair failed to load (incorrect PIN or user cancelled), show a
        # locked placeholder UI so the app remains open and user can retry.
        if not getattr(self, "private_key", None):
            show_locked_screen(self)
        else:
            self._post_key_init()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _post_key_init(self):
        """Run initialization steps that require a loaded keypair."""
        self.layout = WhisprUILayout(self)
        self.layout.create_widgets()
        # Re-apply theme after widgets were created to propagate colors to all
        # newly added components (some custom widgets read global appearance
        # only at construction time).
        try:
            self.theme_manager.apply()
        except Exception:
            pass
        self.update_message_bubbles_theme()

        self.chat_manager = ChatManager(self)

        # Start fetch loop
        self.stop_event = threading.Event()
        threading.Thread(target=self.chat_manager.fetch_loop, daemon=True).start()

        run_server_check_in_thread(self, interval=1.0)

    # locked screen UI moved to gui/locked_screen.show_locked_screen

    def _try_unlock(self):
        """Prompt for PIN again and initialize the app if successful."""
        self.init_keypair()
        if getattr(self, "private_key", None):
            # Remove locked UI and continue initialization
            try:
                self.lock_frame.destroy()
            except Exception:
                pass

    def _on_theme_changed(self, theme):
        """Callback invoked by ThemeManager when theme changes; update all dynamic widget colors."""
        try:
            self.configure(fg_color=theme.get("background", "#1c1c28"))
        except Exception:
            pass

        # Sidebar
        if hasattr(self, "sidebar"):
            try:
                self.sidebar.configure(fg_color=theme.get("sidebar_bg", "#252536"))
                # force relist to recolor entries
                self.sidebar.theme = theme
                self.sidebar.update_list(selected_pub=self.recipient_pub_hex)
            except Exception:
                pass

        # Layout-level frames (pub_frame, messages container, etc.)
        if hasattr(self, 'layout') and hasattr(self.layout, 'refresh_theme'):
            try:
                self.layout.refresh_theme(theme)
            except Exception:
                pass

        # Public key frame / labels
        try:
            if hasattr(self, "pub_label") and self.pub_label.winfo_exists():
                self.pub_label.configure(text_color=theme.get("pub_text", "white"))
        except Exception:
            pass

        try:
            if hasattr(self, "copy_btn"):
                self.copy_btn.configure(fg_color=theme.get("button_send", "#5a9bf6"),
                                        hover_color=theme.get("button_send_hover", "#3d7ddb"))
        except Exception:
            pass

        # Messages container background
        if hasattr(self, "messages_container"):
            try:
                self.messages_container.configure(fg_color=theme.get("background", "#2e2e3f"))
            except Exception:
                pass

        # Input box
        if hasattr(self, "input_box"):
            try:
                self.input_box.configure(fg_color=theme.get("input_bg", "#2e2e3f"),
                                         text_color=theme.get("input_text", "white"))
            except Exception:
                pass

        # Server status dot color might depend on online/offline state; just re-run update if function exists
        if hasattr(self, "update_status_color"):
            try:
                # if we tracked online state, we could store it; for now assume offline->online refresh not critical
                pass
            except Exception:
                pass

        # Update existing message bubbles colors/text
        self.update_message_bubbles_theme()



# ---------------- Keypair ----------------
    def init_keypair(self):
        result = init_keypair(self.notifier, PinDialog, self)
        # If init_keypair returned None, it means the user cancelled or the PIN
        # was incorrect. Don't destroy the application here — just return and
        # let the caller decide how to proceed. This prevents an immediate
        # crash caused by continuing initialization after destroying the root.
        if not result:
            return

        self.private_key, self.signing_key, self.pin, self.username = result
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
            app=self,
            timestamp=timestamp
        )






    def on_send(self):
        handle_send(self)



    def load_app_settings(self):
        """Load server settings and other configurations at startup."""
        # Settings are handled by utils.app_settings.load_app_settings
        # This method is retained for backward compatibility but does nothing.
        return









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
        recipients = load_recipients(self.pin)  
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

    



    def open_profile(self):
        open_profile(self, self.my_pub_hex, self.signing_pub_hex, self.copy_pub_key, username=self.username)







    def on_close(self):
        # Stop background loops if they were started
        try:
            if hasattr(self, "stop_event") and self.stop_event:
                self.stop_event.set()
        except Exception:
            pass

        try:
            if hasattr(self, "chat_manager") and self.chat_manager:
                # ChatManager.stop sets its internal event
                self.chat_manager.stop()
        except Exception:
            pass

        # Finally destroy the window
        try:
            self.destroy()
        except Exception:
            # Last resort: quit the Tk mainloop
            try:
                self.quit()
            except Exception:
                pass



if __name__ == "__main__":
    app = WhisprApp()
    app.mainloop()
