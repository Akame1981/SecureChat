import os
import tkinter as tk
import customtkinter as ctk

from gui.settings.keys_tab import KeysTab
from gui.settings.recipients_tab import RecipientsTab
from gui.settings.server_tab import ServerTab

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../config/settings.json"))

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.parent = parent
        self.app = app
        self.title("Whispr Settings")
        self.geometry("500x450")
        self.minsize(400, 350)
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

        # Pass the already-created tab frame to each tab class
        self.keys_tab = KeysTab(self.tabs.tab("Keys"), self.app)
        self.recipients_tab = RecipientsTab(self.tabs.tab("Recipients"), self.app)
        self.server_tab = ServerTab(self.tabs.tab("Server"), self.app, CONFIG_PATH)

        # --- Recipients Tab ---
        self.recipients_tab.refresh_list()  # initial refresh


        # Ensure all tabs expand correctly
        for tab_name in ["Keys", "Recipients", "Server"]:
            tab = self.tabs.tab(tab_name)
            tab.grid_rowconfigure(0, weight=1)
            tab.grid_columnconfigure(0, weight=1)
