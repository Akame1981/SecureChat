import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from gui.tooltip import ToolTip
from gui.widgets.sidebar import Sidebar

class WhisprUILayout:
    def __init__(self, app):
        """
        Handles all UI setup for WhisprApp.
        'app' is the main WhisprApp instance.
        """
        self.app = app

    def create_widgets(self):
        app = self.app

        # --- Main Frame ---
        main_frame = ctk.CTkFrame(app, fg_color="transparent")
        main_frame.pack(fill="both", expand=True)

        # --- Sidebar ---
        sidebar_bg = app.theme_colors.get(app.current_theme, {}).get("sidebar_bg", "#2a2a3a")
        sidebar_text = app.theme_colors.get(app.current_theme, {}).get("sidebar_text", "white")
        app.sidebar = Sidebar(
            main_frame,
            select_callback=app.select_recipient,
            add_callback=app.add_new_recipient,
            pin=app.pin,
            theme_colors=app.theme_colors.get(app.current_theme, {})
        )

        # --- Chat Frame ---
        chat_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        chat_frame.pack(side="right", fill="both", expand=True)

        theme = app.theme_colors.get(app.current_theme, {})
        pub_bg = theme.get("pub_frame_bg", "#2e2e3f")
        pub_text = theme.get("pub_text", "white")

        # --- Public Key Frame ---
        pub_frame = ctk.CTkFrame(chat_frame, fg_color=pub_bg, corner_radius=10)
        pub_frame.pack(fill="x", padx=10, pady=10)
        pub_frame.grid_columnconfigure(0, weight=1)

        app.pub_label = ctk.CTkLabel(pub_frame, text="", justify="left", anchor="w", text_color=pub_text)
        app.pub_label.grid(row=0, column=0, padx=10, pady=10, sticky="we")

        app.copy_btn = ctk.CTkButton(pub_frame, text="Copy", command=app.copy_pub_key,
                                     fg_color=theme.get("button_send", "#4a90e2"),
                                     hover_color=theme.get("button_send_hover", "#357ABD"))
        app.copy_btn.grid(row=0, column=1, padx=5, pady=10)

        app.settings_btn = ctk.CTkButton(pub_frame, text="Settings", command=app.open_settings,
                                         fg_color=theme.get("button_send", "#4a90e2"),
                                         hover_color=theme.get("button_send_hover", "#357ABD"))
        app.settings_btn.grid(row=0, column=2, padx=5, pady=10)

        # --- Public Key Tooltip ---
        def update_pub_label(event=None):
            pub_frame.update_idletasks()
            frame_width = pub_frame.winfo_width() - app.copy_btn.winfo_width() - app.settings_btn.winfo_width() - 30
            approx_char_width = 7
            max_chars = max(10, frame_width // approx_char_width)
            truncated = app.my_pub_hex
            if len(truncated) > max_chars:
                truncated = truncated[:max_chars-3] + "..."
            app.pub_label.configure(text=f"My Public Key: {truncated}")
            if not hasattr(app, 'pub_tooltip'):
                app.pub_tooltip = ToolTip(app.pub_label, app.my_pub_hex)
            else:
                app.pub_tooltip.text = app.my_pub_hex

        pub_frame.bind("<Configure>", update_pub_label)
        app.after(200, update_pub_label)

        # --- Messages Container ---
        app.messages_container = ctk.CTkScrollableFrame(chat_frame, fg_color=theme.get("background", "#2e2e3f"), corner_radius=10)
        app.messages_container.pack(padx=10, pady=10, fill="both", expand=True)
        app.messages_container.grid_columnconfigure(0, weight=1)

        # --- Input Frame ---
        input_frame = ctk.CTkFrame(chat_frame, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=(0,10))

        app.input_box = ctk.CTkEntry(input_frame,
                                     placeholder_text="Type a message...",
                                     fg_color=theme.get("input_bg", "#2e2e3f"),
                                     text_color=theme.get("input_text", "white"))
        app.input_box.pack(side="left", expand=True, fill="x", padx=(0,5), pady=5)

        def on_enter_pressed(event):
            text = app.input_box.get().strip()
            if text:
                app.chat_manager.send(text)
                app.input_box.delete(0, tk.END)
        app.input_box.bind("<Return>", on_enter_pressed)

        ctk.CTkButton(
            input_frame,
            text="Send",
            command=lambda: [app.chat_manager.send(app.input_box.get().strip()), app.input_box.delete(0, tk.END)],
            fg_color=theme.get("button_send", "#4a90e2"),
            hover_color=theme.get("button_send_hover", "#357ABD")
        ).pack(side="right", padx=(0,5), pady=5)

        # --- Server Status ---
        app.server_status = ctk.CTkLabel(pub_frame, text="●", font=("Roboto", 16),
                                        text_color=theme.get("server_offline", "red"))
        app.server_status.grid(row=0, column=3, padx=5)

        # Update server status color function
        def update_status_color(online):
            color = theme.get("server_online", "green") if online else theme.get("server_offline", "red")
            app.server_status.configure(text="●", text_color=color)
        app.update_status_color = update_status_color
