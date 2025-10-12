import tkinter as tk
import customtkinter as ctk
from customtkinter import CTkImage
from datetime import datetime
from gui.tooltip import ToolTip
from gui.widgets.sidebar import Sidebar
from gui.widgets.groups_panel import GroupsPanel
from PIL import Image, ImageEnhance, ImageDraw, ImageOps
from tkinter import filedialog
import os
from utils.network import send_attachment
from utils.crypto import encrypt_blob
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
            theme_colors=theme
        )
        # Modern toggle to switch between Recipients (DMs) and Groups
        try:
            toggle_bg = theme.get("toggle_bg", "#1f2230")
            toggle_active = theme.get("toggle_active", theme.get("sidebar_button", "#4a90e2"))
            toggle_inactive_text = theme.get("muted_text", "gray70")

            toggle_frame = ctk.CTkFrame(app.sidebar, fg_color=toggle_bg, corner_radius=12)
            toggle_frame.pack(side="top", fill="x", padx=12, pady=(6, 8))

            def make_toggle_button(parent, text, is_active=False, cmd=None):
                fg = toggle_active if is_active else "transparent"
                txt_col = theme.get("sidebar_text", "white") if is_active else toggle_inactive_text
                btn = ctk.CTkButton(parent, text=text, width=100, height=36, corner_radius=10,
                                    fg_color=fg, hover_color=theme.get("sidebar_button_hover", "#357ABD"),
                                    text_color=txt_col, command=cmd)
                return btn

            # Create buttons and an update function to switch styles
            def _show_dms():
                try:
                    getattr(app, 'show_direct_messages', lambda: None)()
                except Exception:
                    pass
                # style update
                try:
                    dms_btn.configure(fg_color=toggle_active, text_color=theme.get("sidebar_text", "white"))
                    groups_btn.configure(fg_color="transparent", text_color=toggle_inactive_text)
                except Exception:
                    pass

            def _show_groups():
                try:
                    getattr(app, 'show_groups_panel', lambda: None)()
                except Exception:
                    pass
                try:
                    groups_btn.configure(fg_color=toggle_active, text_color=theme.get("sidebar_text", "white"))
                    dms_btn.configure(fg_color="transparent", text_color=toggle_inactive_text)
                except Exception:
                    pass

            # Default to recipients view active
            dms_btn = make_toggle_button(toggle_frame, "DMs", is_active=True, cmd=_show_dms)
            dms_btn.pack(side="left", padx=(8, 6), pady=6)

            groups_btn = make_toggle_button(toggle_frame, "Groups", is_active=False, cmd=_show_groups)
            groups_btn.pack(side="left", padx=(6, 8), pady=6)
        except Exception:
            pass

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

        # Call button (starts a WebRTC call)
        def _start_call():
            if not app.recipient_pub_hex:
                try:
                    app.notifier.show("Select a recipient first", type_="warning")
                except Exception:
                    pass
                return
            try:
                from utils.rtc_manager import RTCManager
                from gui.call_window import CallWindow
                if not hasattr(app, 'rtc'):
                    app.rtc = RTCManager(app)
                cw = CallWindow(app, title="Calling…")
                try:
                    app.rtc.start_call(app.recipient_pub_hex, cw.video_label)
                except Exception as e:
                    print("call start error", e)
                    try:
                        app.notifier.show("Call failed", type_="error")
                    except Exception:
                        pass
            except Exception as e:
                print("RTC init error", e)

        app.call_btn = ctk.CTkButton(pub_frame, text="Call", command=_start_call,
                                      fg_color=theme.get("button_send", "#4a90e2"),
                                      hover_color=theme.get("button_send_hover", "#357ABD"))
        app.call_btn.grid(row=0, column=3, padx=5, pady=10)


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
        send_btn.bind("<Button-1>", lambda e: [app.chat_manager.send(app.input_box.get().strip()), app.input_box.delete(0, tk.END)])

        # --- Bind hover effects ---
        def on_enter(e):
            send_btn.configure(image=send_btn.hover_image)

        def on_leave(e):
            send_btn.configure(image=send_btn.image)

        send_btn.bind("<Enter>", on_enter)
        send_btn.bind("<Leave>", on_leave)

        # --- Attachment Button ---
        try:
            attach_img_path = "gui/src/images/attach_btn.png"
            if os.path.exists(attach_img_path):
                a_img = Image.open(attach_img_path).resize((40,40), Image.Resampling.LANCZOS)
            else:
                # fallback: reuse send image dimmed
                a_img = ImageEnhance.Brightness(send_img).enhance(0.5)
            attach_icon = CTkImage(light_image=a_img, dark_image=a_img, size=(40,40))
            attach_btn = ctk.CTkLabel(input_frame, image=attach_icon, text="", fg_color="transparent")
            attach_btn.image = attach_icon
            attach_btn.pack(side="right", padx=(0,5), pady=5)

            def do_attach(_=None):
                if not app.recipient_pub_hex:
                    try:
                        app.notifier.show("Select a recipient first", type_="warning")
                    except Exception:
                        pass
                    return
                paths = filedialog.askopenfilenames(title="Select files to send")
                for p in paths:
                    if not p:
                        continue
                    try:
                        sz = os.path.getsize(p)
                        max_size = 5 * 1024 * 1024  # 5MB basic guard
                        if sz > max_size:
                            app.notifier.show(f"Skip {os.path.basename(p)} (>5MB)", type_="warning")
                            continue
                        with open(p, 'rb') as f:
                            data = f.read()
                        # Persist locally so optimistic UI can render blob immediately
                        try:
                            store_attachment(data, app.pin)
                        except Exception:
                            pass

                        # Show placeholder immediately (non-blocking UX) then send in background
                        import threading
                        from utils.attachments import store_attachment
                        human = app.chat_manager._human_size(len(data)) if hasattr(app, 'chat_manager') else f"{len(data)} bytes"
                        placeholder = f"[Attachment] {os.path.basename(p)} ({human})"
                        ts = __import__('time').time()
                        from utils.chat_storage import save_message
                        # Temporary client-side id (hash) for placeholder; network layer will persist
                        import hashlib
                        att_id = hashlib.sha256(data).hexdigest()
                        meta = {"name": os.path.basename(p), "size": len(data), "att_id": att_id, "type": "file"}
                        save_message(app.recipient_pub_hex, "You", placeholder, app.pin, timestamp=ts, attachment=meta)
                        app.display_message(app.my_pub_hex, placeholder, ts, attachment_meta=meta)

                        def _bg_send():
                            ok = send_attachment(
                                app,
                                to_pub=app.recipient_pub_hex,
                                signing_pub=app.signing_pub_hex,
                                filename=os.path.basename(p),
                                data=data,
                                signing_key=app.signing_key,
                                enc_pub=app.my_pub_hex
                            )
                            if not ok:
                                try:
                                    app.notifier.show(f"Failed to send {os.path.basename(p)}", type_="error")
                                except Exception:
                                    pass
                        threading.Thread(target=_bg_send, daemon=True).start()
                    except Exception as e:
                        print("Attachment send error", e)
                        try:
                            app.notifier.show("Attachment error", type_="error")
                        except Exception:
                            pass

            attach_btn.bind("<Button-1>", do_attach)
            # Basic tooltip reuse
            ToolTip(attach_btn, "Send attachment")
        except Exception as e:
            print("Attach button init failed", e)



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

        # Instantiate but keep hidden the Groups panel; app.show_groups_panel() will swap views
        try:
            app.groups_panel = GroupsPanel(chat_frame, app, theme)
            app.groups_panel.pack_forget()
            app.show_groups_panel = lambda: self._switch_to_groups()
            app.show_direct_messages = lambda: self._switch_to_dm()
        except Exception as e:
            print("Failed to init GroupsPanel", e)

    def _switch_to_groups(self):
        app = self.app
        try:
            # Hide direct messages widgets
            for w in [getattr(app, 'pub_frame', None), getattr(app, 'messages_container', None), getattr(app, 'input_frame', None)]:
                if w and w.winfo_ismapped():
                    w.pack_forget()
            # Hide the main sidebar entirely in groups mode
            if hasattr(app, 'sidebar') and app.sidebar.winfo_ismapped():
                app.sidebar.pack_forget()
            # Show groups panel
            app.groups_panel.pack(fill="both", expand=True)
            # Show GroupsPanel's own left sidebar (it replaces the main sidebar)
            if hasattr(app.groups_panel, 'set_sidebar_visible'):
                app.groups_panel.set_sidebar_visible(True)
            if hasattr(app.groups_panel, 'refresh_groups'):
                app.groups_panel.refresh_groups()
        except Exception:
            pass

    def _switch_to_dm(self):
        app = self.app
        try:
            # Hide groups panel
            if hasattr(app, 'groups_panel') and app.groups_panel.winfo_ismapped():
                app.groups_panel.pack_forget()
                # Restore left panel when re-entering groups later
                if hasattr(app.groups_panel, 'set_sidebar_visible'):
                    app.groups_panel.set_sidebar_visible(True)
            # Show the main sidebar again
            if hasattr(app, 'sidebar') and not app.sidebar.winfo_ismapped():
                app.sidebar.pack(side="left", fill="y")
            # Show DM widgets
            app.pub_frame.pack(fill="x", padx=10, pady=10)
            app.messages_container.pack(padx=10, pady=10, fill="both", expand=True)
            app.input_frame.pack(fill="x", padx=10, pady=(0,10))
        except Exception:
            pass

    def _open_group_from_sidebar(self, group_id: str, name: str):
        # Ensure groups view is active and open the selected group in the panel
        try:
            if hasattr(self.app, 'sidebar'):
                self.app.sidebar.show_groups_view()
        except Exception:
            pass
        try:
            self._switch_to_groups()
            if hasattr(self.app, 'groups_panel'):
                self.app.groups_panel._select_group(group_id, name)
        except Exception:
            pass

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
