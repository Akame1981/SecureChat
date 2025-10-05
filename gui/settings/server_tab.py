import os
import json
import tkinter as tk
import tkinter.filedialog as fd
import customtkinter as ctk

CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../config/settings.json")
)

class ServerTab:
    def __init__(self, parent, app, config_path=CONFIG_PATH):
        self.app = app
        self.frame = parent  

        # Variables
        self.server_var = tk.StringVar(value="public") 
        self.use_cert_var = tk.BooleanVar(value=True)

        # Build UI
        self._build_ui()

        # Load settings from file
        self._load_settings()

        # Initial update
        self._update_cert_visibility()

        # Watch for changes
        self.server_var.trace_add("write", lambda *_: self._update_cert_visibility())
        self.use_cert_var.trace_add("write", lambda *_: self._update_cert_visibility())

    def _build_ui(self):
        """Build all widgets for the Server tab."""

        ctk.CTkLabel(
            self.frame, text="Server Settings",
            font=("Roboto", 16, "bold"), text_color="white"
        ).grid(row=0, column=0, pady=(10, 5), padx=10, sticky="w")

        # --- Radio buttons for server type ---
        ctk.CTkRadioButton(
            self.frame, text="Public Server",
            variable=self.server_var, value="public"
        ).grid(row=1, column=0, sticky="w", padx=20, pady=5)

        ctk.CTkRadioButton(
            self.frame, text="Local Server",
            variable=self.server_var, value="local"
        ).grid(row=2, column=0, sticky="w", padx=20, pady=5)

        # --- Custom server URL ---
        ctk.CTkLabel(
            self.frame, text="Custom Server URL:",
            text_color="white"
        ).grid(row=3, column=0, sticky="w", padx=20, pady=(10, 0))

        self.custom_server_entry = ctk.CTkEntry(self.frame, width=300)
        self.custom_server_entry.grid(row=4, column=0, sticky="w", padx=20, pady=5)
        self.custom_server_entry.insert(0, "http://127.0.0.1:8000")

        # --- Certificate checkbox ---
        self.cert_checkbox = ctk.CTkCheckBox(
            self.frame, text="Use custom certificate", variable=self.use_cert_var
        )
        self.cert_checkbox.grid(row=5, column=0, sticky="w", padx=20, pady=5)

        # --- Certificate entry + browse button ---
        self.cert_entry = ctk.CTkEntry(self.frame, width=300)
        self.cert_entry.grid(row=6, column=0, sticky="w", padx=20, pady=5)
        self.cert_entry.insert(0, "utils/cert.pem")

        self.browse_btn = ctk.CTkButton(
            self.frame, text="Browse", command=self._browse_cert, fg_color="#4a90e2"
        )
        self.browse_btn.grid(row=6, column=1, sticky="w", padx=5)

        # --- Save button ---
        ctk.CTkButton(
            self.frame, text="Save",
            command=self._save_server_settings,
            fg_color="#4a90e2"
        ).grid(row=7, column=0, sticky="w", padx=20, pady=10)

    def _update_cert_visibility(self):
        """Show/hide fields depending on server type + cert usage."""
        if self.server_var.get() == "public":
            self.cert_checkbox.grid_remove()
            self.cert_entry.grid_remove()
            self.browse_btn.grid_remove()
            self.custom_server_entry.configure(state="disabled")
        else:
            self.cert_checkbox.grid()
            self.custom_server_entry.configure(state="normal")
            if self.use_cert_var.get():
                self.cert_entry.grid()
                self.browse_btn.grid()
            else:
                self.cert_entry.grid_remove()
                self.browse_btn.grid_remove()

    def _browse_cert(self):
        """Browse for a certificate file."""
        path = fd.askopenfilename(
            filetypes=[("PEM files", "*.pem"), ("All files", "*.*")]
        )
        if path:
            self.cert_entry.delete(0, tk.END)
            self.cert_entry.insert(0, path)

    def _save_server_settings(self):
        """Apply and save settings to app + JSON file."""
        selection = self.server_var.get()
        url = self.custom_server_entry.get().strip()

        if selection == "public":
            self.app.SERVER_URL = "https://34.61.34.132:8000"
            self.app.SERVER_CERT = "utils/cert.pem"
        else:
            if not url.startswith("http"):
                ctk.CTkLabel(
                    self.frame, text="Invalid URL!", text_color="red"
                ).grid(row=8, column=0, padx=20)
                return

            self.app.SERVER_URL = url
            if self.use_cert_var.get():
                cert_path = self.cert_entry.get().strip()
                if not cert_path or not os.path.exists(cert_path):
                    ctk.CTkLabel(
                        self.frame, text="Certificate file not found!", text_color="red"
                    ).grid(row=8, column=0, padx=20)
                    return
                self.app.SERVER_CERT = cert_path
            else:
                self.app.SERVER_CERT = None

        ctk.CTkLabel(
            self.frame,
            text=f"Server set to: {self.app.SERVER_URL}",
            text_color="green"
        ).grid(row=8, column=0, padx=20)

        self._save_settings_file()

    def _load_settings(self):
        """Load saved settings from config file."""
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    data = json.load(f)
                self.server_var.set(data.get("server_type", "public"))
                self.custom_server_entry.delete(0, tk.END)
                self.custom_server_entry.insert(
                    0, data.get("custom_url", "http://127.0.0.1:8000")
                )
                self.use_cert_var.set(data.get("use_cert", True))
                self.cert_entry.delete(0, tk.END)
                self.cert_entry.insert(0, data.get("cert_path", "utils/cert.pem"))
            except Exception as e:
                print("Failed to load settings:", e)

    def _save_settings_file(self):
        """Save current settings to config file."""
        data = {
            "server_type": self.server_var.get(),
            "custom_url": self.custom_server_entry.get().strip(),
            "use_cert": self.use_cert_var.get(),
            "cert_path": self.cert_entry.get().strip(),
        }

        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=4)
