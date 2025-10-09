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

        # Build UI using a shared builder so we can reuse it for an in-place panel
        self._build_ui()

    def _build_ui(self):
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
        try:
            self.recipients_tab.refresh_list()  # initial refresh
        except Exception:
            pass

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


class SettingsPanel(ctk.CTkFrame):
    """An in-place settings panel that can be packed inside the main window instead of opening a new toplevel."""
    def __init__(self, parent, app, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.app = app
        self.configure(fg_color=kwargs.get('fg_color', 'transparent'))

        # Use the same internal builder but attach to this frame
        self._build_ui()

    def _build_ui(self):
        # --- Title ---
        ctk.CTkLabel(
            self,
            text="Settings",
            font=("Roboto", 20, "bold"),
            text_color="white"
        ).pack(pady=(12, 8))

        # --- Tab view ---
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=6)

        # Add tabs
        self.tabs.add("Keys")
        self.tabs.add("Recipients")
        self.tabs.add("Server")
        self.tabs.add("Appearance")

        # Create tab contents
        self.keys_tab = KeysTab(self.tabs.tab("Keys"), self.app)
        self.recipients_tab = RecipientsTab(self.tabs.tab("Recipients"), self.app)
        self.server_tab = ServerTab(self.tabs.tab("Server"), self.app, CONFIG_PATH)
        self.appearance_tab = AppearanceTab(self.tabs.tab("Appearance"), self.app, CONFIG_PATH)

        try:
            self.recipients_tab.refresh_list()
        except Exception:
            pass

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=10, pady=(6, 12))
        footer.grid_columnconfigure(0, weight=1)

        self.save_all_btn = ctk.CTkButton(footer, text="Save All", width=120, command=self.save_all, fg_color="#4a90e2")
        self.save_all_btn.pack(side="right", padx=(0, 8))

        self.close_btn = ctk.CTkButton(footer, text="Close", width=80, command=self.close, fg_color="#d9534f")
        self.close_btn.pack(side="right")

        # Keyboard shortcuts
        try:
            self.bind_all("<Control-s>", lambda e: self.save_all())
            self.bind_all("<Control-S>", lambda e: self.save_all())
            self.bind_all("<Escape>", lambda e: self.close())
        except Exception:
            pass

    def save_all(self):
        # reuse same logic as the toplevel save
        try:
            if hasattr(self, "appearance_tab") and hasattr(self.appearance_tab, "save_settings"):
                self.appearance_tab.save_settings()
        except Exception:
            pass
        try:
            if hasattr(self, "server_tab"):
                if hasattr(self.server_tab, "_save_server_settings"):
                    self.server_tab._save_server_settings()
                elif hasattr(self.server_tab, "save_settings"):
                    self.server_tab.save_settings()
        except Exception:
            pass
        try:
            if hasattr(self.app, "notifier"):
                self.app.notifier.show("Settings saved", type_="success")
        except Exception:
            pass

    def close(self):
        # Remove panel and restore main UI elements
        try:
            # destroy panel widget
            self.destroy()
        except Exception:
            pass
        # Let the app know panel closed so it can restore content
        try:
            if hasattr(self.app, 'on_settings_panel_closed'):
                self.app.on_settings_panel_closed()
        except Exception:
            pass

