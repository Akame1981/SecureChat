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
        """Build all widgets for the Whispr Server tab."""
        # Header
        ctk.CTkLabel(
            self.frame, text="Server Settings",
            font=("Roboto", 16, "bold"), text_color="white"
        ).grid(row=0, column=0, pady=(10, 6), padx=10, sticky="w")

        # Card container for better visual grouping
        card = ctk.CTkFrame(self.frame, fg_color="#1e1e2f", corner_radius=8)
        card.grid(row=1, column=0, padx=12, pady=(6, 12), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        # Radio buttons in a row
        radio_row = ctk.CTkFrame(card, fg_color="transparent")
        radio_row.grid(row=0, column=0, sticky="ew", padx=12, pady=(8,6))
        radio_row.grid_columnconfigure(0, weight=1)
        radio_row.grid_columnconfigure(1, weight=1)

        ctk.CTkRadioButton(radio_row, text="Public Server", variable=self.server_var, value="public").grid(row=0, column=0, sticky="w")
        ctk.CTkRadioButton(radio_row, text="Local / Custom Server", variable=self.server_var, value="local").grid(row=0, column=1, sticky="w")

        # Custom server URL
        self.url_row = ctk.CTkFrame(card, fg_color="transparent")
        self.url_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(6,6))
        self.url_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.url_row, text="Custom Server URL:", text_color="#b2b8d6").grid(row=0, column=0, sticky="w")
        self.custom_server_entry = ctk.CTkEntry(self.url_row, width=420)
        self.custom_server_entry.grid(row=1, column=0, sticky="ew", pady=6)
        self.custom_server_entry.insert(0, "http://127.0.0.1:8000")

        # Certificate controls inline
        self.cert_row = ctk.CTkFrame(card, fg_color="transparent")
        self.cert_row.grid(row=2, column=0, sticky="ew", padx=12, pady=(0,8))
        self.cert_row.grid_columnconfigure(0, weight=1)
        self.cert_row.grid_columnconfigure(1, weight=0)

        self.cert_checkbox = ctk.CTkCheckBox(self.cert_row, text="Use custom certificate", variable=self.use_cert_var)
        self.cert_checkbox.grid(row=0, column=0, sticky="w")

        self.cert_input_row = ctk.CTkFrame(card, fg_color="transparent")
        self.cert_input_row.grid(row=3, column=0, sticky="ew", padx=12, pady=(0,8))
        self.cert_input_row.grid_columnconfigure(0, weight=1)
        self.cert_input_row.grid_columnconfigure(1, weight=0)

        self.cert_entry = ctk.CTkEntry(self.cert_input_row)
        self.cert_entry.grid(row=0, column=0, sticky="ew")
        self.cert_entry.insert(0, "utils/cert.pem")

        self.browse_btn = ctk.CTkButton(self.cert_input_row, text="Browse", command=self._browse_cert, fg_color="#4a90e2", width=84)
        self.browse_btn.grid(row=0, column=1, sticky="e", padx=(8,0))

        # Server limits section
        limits_frame = ctk.CTkFrame(card, fg_color="transparent")
        limits_frame.grid(row=4, column=0, sticky="ew", padx=12, pady=(6,8))
        limits_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(limits_frame, text="Server Limits (for local server)", text_color="#b2b8d6").grid(row=0, column=0, sticky="w", pady=(0,6))

        self.max_per_recipient_var = tk.IntVar(value=20)
        self.max_per_second_var = tk.IntVar(value=10)
        self.msg_ttl_var = tk.IntVar(value=60)
        self.att_size_var = tk.IntVar(value=10 * 1024 * 1024)

        # Row 1
        row1 = ctk.CTkFrame(limits_frame, fg_color="transparent")
        row1.grid(row=1, column=0, sticky="ew")
        ctk.CTkLabel(row1, text="Max messages / recipient:", text_color="#b2b8d6").grid(row=0, column=0, sticky="w")
        self.max_per_recipient_entry = ctk.CTkEntry(row1, width=120, textvariable=self.max_per_recipient_var)
        self.max_per_recipient_entry.grid(row=0, column=1, sticky="e", padx=(8,0))

        # Row 2
        row2 = ctk.CTkFrame(limits_frame, fg_color="transparent")
        row2.grid(row=2, column=0, sticky="ew", pady=(6,0))
        ctk.CTkLabel(row2, text="Max messages / second:", text_color="#b2b8d6").grid(row=0, column=0, sticky="w")
        self.max_per_second_entry = ctk.CTkEntry(row2, width=120, textvariable=self.max_per_second_var)
        self.max_per_second_entry.grid(row=0, column=1, sticky="e", padx=(8,0))

        # Row 3
        row3 = ctk.CTkFrame(limits_frame, fg_color="transparent")
        row3.grid(row=3, column=0, sticky="ew", pady=(6,0))
        ctk.CTkLabel(row3, text="Message TTL (seconds):", text_color="#b2b8d6").grid(row=0, column=0, sticky="w")
        self.msg_ttl_entry = ctk.CTkEntry(row3, width=120, textvariable=self.msg_ttl_var)
        self.msg_ttl_entry.grid(row=0, column=1, sticky="e", padx=(8,0))

        # Row 4
        row4 = ctk.CTkFrame(limits_frame, fg_color="transparent")
        row4.grid(row=4, column=0, sticky="ew", pady=(6,0))
        ctk.CTkLabel(row4, text="Attachment max size (bytes):", text_color="#b2b8d6").grid(row=0, column=0, sticky="w")
        self.att_size_entry = ctk.CTkEntry(row4, width=180, textvariable=self.att_size_var)
        self.att_size_entry.grid(row=0, column=1, sticky="e", padx=(8,0))

        # Action row: Save + Reset
        action_row = ctk.CTkFrame(card, fg_color="transparent")
        action_row.grid(row=5, column=0, sticky="e", padx=12, pady=(4,12))
        ctk.CTkButton(action_row, text="Save", command=self._save_server_settings, fg_color="#4a90e2", width=120).grid(row=0, column=0, padx=(0,8))
        ctk.CTkButton(action_row, text="Reset", command=self._load_settings, fg_color="#6c6f76", width=90).grid(row=0, column=1)

        # Persistent status label (one place for messages)
        self.status_label = ctk.CTkLabel(self.frame, text="", text_color="green")
        self.status_label.grid(row=6, column=0, sticky="w", padx=20)

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

    def _set_status(self, text, color="green"):
        try:
            self.status_label.configure(text=text, text_color=color)
        except Exception:
            pass

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
                self._set_status("Invalid URL!", color="red")
                return

            self.app.SERVER_URL = url
            if self.use_cert_var.get():
                cert_path = self.cert_entry.get().strip()
                if not cert_path or not os.path.exists(cert_path):
                    self._set_status("Certificate file not found!", color="red")
                    return
                self.app.SERVER_CERT = cert_path
            else:
                self.app.SERVER_CERT = None
        self._set_status(f"Server set to: {self.app.SERVER_URL}", color="green")
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
                # Load server-side limits if present
                self.max_per_recipient_var.set(data.get("max_messages_per_recipient", 20))
                self.max_per_second_var.set(data.get("max_messages_per_second", 10))
                self.msg_ttl_var.set(data.get("message_ttl_seconds", 60))
                self.att_size_var.set(data.get("attachment_max_size_bytes", 10 * 1024 * 1024))
            except Exception as e:
                print("Failed to load settings:", e)

    def _save_settings_file(self):
        """Save current settings to config file."""
        data = {
            "server_type": self.server_var.get(),
            "custom_url": self.custom_server_entry.get().strip(),
            "use_cert": self.use_cert_var.get(),
            "cert_path": self.cert_entry.get().strip(),
            # include server-side limits so users can tune local server behavior file
            "max_messages_per_recipient": int(self.max_per_recipient_var.get()),
            "max_messages_per_second": int(self.max_per_second_var.get()),
            "message_ttl_seconds": int(self.msg_ttl_var.get()),
            "attachment_max_size_bytes": int(self.att_size_var.get()),
        }

        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(data, f, indent=4)
