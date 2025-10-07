import tkinter as tk
import customtkinter as ctk
from customtkinter import CTkImage
from datetime import datetime
from gui.tooltip import ToolTip
from gui.widgets.sidebar import Sidebar
from PIL import Image, ImageEnhance, ImageDraw, ImageOps
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
        # Expose for theme refresh
        app.main_frame = main_frame

        # --- Sidebar ---
        # Support new ThemeManager (preferred) or fallback to legacy attributes
        if hasattr(app, "theme_manager"):
            current_theme = getattr(app.theme_manager, "current_theme", "Dark")
            theme = getattr(app.theme_manager, "theme_colors", {}).get(current_theme, {})
        else:
            current_theme = getattr(app, "current_theme", "Dark")
            theme = getattr(app, "theme_colors", {}).get(current_theme, {})

        sidebar_bg = theme.get("sidebar_bg", "#2a2a3a")
        sidebar_text = theme.get("sidebar_text", "white")
        app.sidebar = Sidebar(
            main_frame,
            app,  # <-- pass the main app instance here
            select_callback=app.select_recipient,
            add_callback=app.add_new_recipient,
            pin=app.pin,
            theme_colors=theme,
        )

        # --- Chat Frame ---
        chat_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        chat_frame.pack(side="right", fill="both", expand=True)
        app.chat_frame = chat_frame

        pub_bg = theme.get("pub_frame_bg", "#2e2e3f")
        pub_text = theme.get("pub_text", "white")

        # --- Public Key Frame ---
        pub_frame = ctk.CTkFrame(chat_frame, fg_color=pub_bg, corner_radius=10)
        pub_frame.pack(fill="x", padx=10, pady=10)
        pub_frame.grid_columnconfigure(0, weight=1)
        app.pub_frame = pub_frame

        app.pub_label = ctk.CTkLabel(pub_frame, text="", justify="left", anchor="w", text_color=pub_text)
        app.pub_label.grid(row=0, column=0, padx=10, pady=10, sticky="we")

        app.copy_btn = ctk.CTkButton(pub_frame, text="Copy", command=app.copy_pub_key,
                                     fg_color=theme.get("button_send", "#4a90e2"),
                                     hover_color=theme.get("button_send_hover", "#357ABD"))
        app.copy_btn.grid(row=0, column=1, padx=5, pady=10)


        # --- Public Key Tooltip ---
        def update_pub_label(event=None):
            pub_frame.update_idletasks()
            # Subtract the copy button width and some padding to calculate available space
            frame_width = pub_frame.winfo_width() - app.copy_btn.winfo_width() - 30
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
        app.input_frame = input_frame

        # Chat input box
        app.input_box = ctk.CTkEntry(
            input_frame,
            placeholder_text="Type a message...",
            fg_color=theme.get("input_bg", "#2e2e3f"),
            text_color=theme.get("input_text", "white"),
            corner_radius=20, 
            border_width=0,
            height=40
        )
        app.input_box.pack(side="left", expand=True, fill="x", padx=(0,5), pady=5)

        def on_enter_pressed(event):
            text = app.input_box.get().strip()
            if text:
                app.chat_manager.send(text)
                app.input_box.delete(0, tk.END)
        app.input_box.bind("<Return>", on_enter_pressed)


        # --- Load and prepare images ---
        send_img = Image.open("gui/src/images/send_btn.png").resize((48, 48), Image.Resampling.LANCZOS)

        # Normal icon
        send_icon = CTkImage(light_image=send_img, dark_image=send_img, size=(48, 48))

        # Darker icon for hover
        enhancer = ImageEnhance.Brightness(send_img)
        dark_img = enhancer.enhance(0.7)  # 0.7 = 30% darker
        send_hover_icon = CTkImage(light_image=dark_img, dark_image=dark_img, size=(48, 48))

        # --- Create clickable label ---
        send_btn = ctk.CTkLabel(
            input_frame,
            image=send_icon,
            text="",
            fg_color="transparent"
        )
        send_btn.pack(side="right", padx=(0,5), pady=5)

        # Keep references
        send_btn.image = send_icon
        send_btn.hover_image = send_hover_icon

        # --- Bind click ---
        send_btn.bind("<Button-1>", lambda e: [
            app.chat_manager.send(app.input_box.get().strip()),
            app.input_box.delete(0, tk.END)
        ])

        # --- Bind hover effects ---
        def on_enter(e):
            send_btn.configure(image=send_btn.hover_image)

        def on_leave(e):
            send_btn.configure(image=send_btn.image)

        send_btn.bind("<Enter>", on_enter)
        send_btn.bind("<Leave>", on_leave)



        # --- Server Status ---
        app.server_status = ctk.CTkLabel(pub_frame, text="●", font=("Roboto", 16),
                                        text_color=theme.get("server_offline", "red"))
        # Moved to column 2 after removing the settings button
        app.server_status.grid(row=0, column=2, padx=5)

        # Update server status color function
        def update_status_color(online):
            color = theme.get("server_online", "green") if online else theme.get("server_offline", "red")
            app.server_status.configure(text="●", text_color=color)
        app.update_status_color = update_status_color

    def refresh_theme(self, theme: dict):
        """Update top-level layout frame colors when theme changes."""
        app = self.app
        try:
            if hasattr(app, 'pub_frame'):
                app.pub_frame.configure(fg_color=theme.get('pub_frame_bg', '#2e2e3f'))
        except Exception:
            pass
        try:
            if hasattr(app, 'messages_container'):
                app.messages_container.configure(fg_color=theme.get('background', '#2e2e3f'))
        except Exception:
            pass
        try:
            if hasattr(app, 'input_box'):
                app.input_box.configure(fg_color=theme.get('input_bg', '#2e2e3f'),
                                        text_color=theme.get('input_text', 'white'))
        except Exception:
            pass
