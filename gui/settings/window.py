import os
import tkinter as tk
import customtkinter as ctk

from gui.settings.keys_tab import KeysTab
from gui.settings.recipients_tab import RecipientsTab
from gui.settings.server_tab import ServerTab
from gui.settings.appearance_tab import AppearanceTab


CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../config/settings.json"))

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.parent = parent
        self.app = app
        self.title("Whispr Settings")
        self.geometry("500x450")
        self.minsize(600, 550)
        self.configure(bg="#1e1e2f")

        # Make window resizable
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Title ---
        ctk.CTkLabel(
            self,
            text="Settings",
            font=("Roboto", 20, "bold"),
            text_color="white"
        ).grid(row=0, column=0, pady=(15, 10))

        # --- Tab view ---
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Add tabs
        self.tabs.add("Keys")
        self.tabs.add("Recipients")
        self.tabs.add("Server")
        self.tabs.add("Appearance")

        # Pass the already-created tab frame to each tab class
        self.keys_tab = KeysTab(self.tabs.tab("Keys"), self.app)
        self.recipients_tab = RecipientsTab(self.tabs.tab("Recipients"), self.app)
        self.server_tab = ServerTab(self.tabs.tab("Server"), self.app, CONFIG_PATH)
        self.appearance_tab = AppearanceTab(self.tabs.tab("Appearance"), self.app, CONFIG_PATH)

        # --- Recipients Tab ---
        self.recipients_tab.refresh_list()  # initial refresh


        # Ensure all tabs expand correctly
        for tab_name in ["Keys", "Recipients", "Server", "Appearance"]:
            tab = self.tabs.tab(tab_name)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)

        # --- Footer with actions ---
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 12))
        footer.grid_columnconfigure(0, weight=1)

        self.save_all_btn = ctk.CTkButton(footer, text="Save All", width=120, command=self.save_all, fg_color="#4a90e2")
        self.save_all_btn.grid(row=0, column=1, sticky="e", padx=(0, 8))

        self.close_btn = ctk.CTkButton(footer, text="Close", width=80, command=self.destroy, fg_color="#d9534f")
        self.close_btn.grid(row=0, column=2, sticky="e")

        # Keyboard shortcuts: Ctrl+S to save, Escape to close
        try:
            self.bind_all("<Control-s>", lambda e: self.save_all())
            self.bind_all("<Control-S>", lambda e: self.save_all())
            self.bind_all("<Escape>", lambda e: self.destroy())
        except Exception:
            pass

    def save_all(self):
        """Call save operations on each tab where available and notify the user."""
        # AppearanceTab: has save_settings
        try:
            if hasattr(self, "appearance_tab") and hasattr(self.appearance_tab, "save_settings"):
                self.appearance_tab.save_settings()
        except Exception:
            pass

        # ServerTab: expose its save method if present
        try:
            if hasattr(self, "server_tab"):
                # prefer explicit save method
                if hasattr(self.server_tab, "_save_server_settings"):
                    self.server_tab._save_server_settings()
                elif hasattr(self.server_tab, "save_settings"):
                    self.server_tab.save_settings()
        except Exception:
            pass

        # Notify user
        try:
            if hasattr(self.app, "notifier"):
                self.app.notifier.show("Settings saved", type_="success")
        except Exception:
            pass

