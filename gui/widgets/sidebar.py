# gui/widgets/sidebar.py
import customtkinter as ctk
from PIL import Image, ImageEnhance
from utils.path_utils import get_resource_path
from gui.identicon import generate_identicon
from utils.recipients import add_recipient, load_recipients
from gui.widgets.notification import NotificationManager
from gui.profile_window import open_profile

# Import AddRecipientDialog from this module
class AddRecipientDialog(ctk.CTkToplevel):
    def __init__(self, parent, notifier, update_list_callback, add_callback=None, pin=None, theme=None):
        super().__init__(parent)
        self.title("Add Recipient")
        self.geometry("360x260")
        self.resizable(False, False)
        self.grab_set()
        self.pin = pin

        # Resolve theme (prefer app.theme_manager)
        app_obj = getattr(parent, "app", parent)
        resolved = {}
        if hasattr(app_obj, "theme_manager"):
            tm = app_obj.theme_manager
            resolved = tm.theme_colors.get(tm.current_theme, {})
        else:
            resolved = theme or {}

        self.theme = resolved
        self.notifier = notifier
        self.update_list_callback = update_list_callback
        self.add_callback = add_callback

        title_color = self.theme.get("text", "white")
        entry_bg = self.theme.get("input_bg", "#2a2a3f")
        entry_text = self.theme.get("input_text", "white")
        btn_fg = self.theme.get("sidebar_button", "#4a90e2")
        btn_hover = self.theme.get("sidebar_button_hover", "#357ABD")
        cancel_fg = self.theme.get("cancel_button", "#9a9a9a")
        cancel_hover = self.theme.get("cancel_button_hover", "#7a7a7a")

        # Title
        ctk.CTkLabel(self, text="Add New Recipient", font=("Segoe UI", 16, "bold"), text_color=title_color).pack(pady=(20, 10))

        # Name
        ctk.CTkLabel(self, text="Recipient Name:", font=("Segoe UI", 12), text_color=title_color).pack(anchor="w", padx=20)
        self.name_entry = ctk.CTkEntry(self, placeholder_text="e.g. John Doe", height=40, font=("Segoe UI", 12), fg_color=entry_bg, text_color=entry_text)
        self.name_entry.pack(padx=20, pady=(0, 10), fill="x")

        # Key
        ctk.CTkLabel(self, text="Recipient Key:", font=("Segoe UI", 12), text_color=title_color).pack(anchor="w", padx=20)
        self.key_entry = ctk.CTkEntry(self, placeholder_text="e.g. ABC123XYZ", height=40, font=("Segoe UI", 12), fg_color=entry_bg, text_color=entry_text)
        self.key_entry.pack(padx=20, pady=(0, 15), fill="x")

        # Buttons frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)

        # Cancel button
        ctk.CTkButton(
            btn_frame, text="Cancel",
            fg_color=cancel_fg, hover_color=cancel_hover,
            font=("Segoe UI", 12, "bold"), width=140, height=48,
            command=self.destroy
        ).pack(side="left", padx=10)

        # Add button
        ctk.CTkButton(
            btn_frame, text="Add",
            fg_color=btn_fg, hover_color=btn_hover,
            font=("Segoe UI", 12, "bold"), width=140, height=48,
            command=self.confirm
        ).pack(side="left", padx=10)

        self.bind("<Return>", lambda e: self.confirm())

    def confirm(self):
        name = self.name_entry.get().strip()
        key = self.key_entry.get().strip()
        if not name or not key:
            self.notifier.show("Please fill both fields!", type_="warning")
            return

        try:
            add_recipient(name, key, self.pin)
            if self.update_list_callback:
                self.update_list_callback(selected_pub=key)
            self.notifier.show(f"Recipient '{name}' added!", type_="success")
            self.unbind("<Return>")
            self.after(10, self.destroy)
        except ValueError as e:
            self.notifier.show(str(e), type_="error")

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, app, *, select_callback, add_callback=None, pin=None, theme_colors=None):
        # Resolve theme (prefer app.theme_manager)
        resolved = {}
        if hasattr(app, "theme_manager"):
            tm = app.theme_manager
            resolved = tm.theme_colors.get(tm.current_theme, {})
        else:
            resolved = theme_colors or {}

        sidebar_bg = resolved.get("sidebar_bg", "#2a2a3a")
        super().__init__(parent, width=240, fg_color=sidebar_bg, corner_radius=0)
        self.app = app
        self.select_callback = select_callback
        self.add_callback = add_callback
        self.pin = pin
        self.theme = resolved
        self.pack(side="left", fill="y")

        self.notifier = NotificationManager(parent)

        title_color = self.theme.get("sidebar_text", "white")
        list_bg = self.theme.get("sidebar_bg", "#2a2a3a")
        avatar_bg = self.theme.get("sidebar_button", "#4a90e2")
        avatar_text = self.theme.get("sidebar_text", "white")
        add_fg = self.theme.get("sidebar_button", "#4a90e2")
        add_hover = self.theme.get("sidebar_button_hover", "#357ABD")

        # --- Section title ---
        ctk.CTkLabel(
            self, text="Recipients", font=("Segoe UI", 16, "bold"),
            text_color=title_color
        ).pack(pady=(12, 10))

        # --- Scrollable recipient list ---
        self.recipient_listbox = ctk.CTkScrollableFrame(
            self, fg_color=list_bg, width=220
        )
        self.recipient_listbox.pack(fill="both", expand=True, padx=12, pady=(0,10))
        self.update_list()

        # --- Bottom user frame (add button + avatar + username) ---
        user_frame = ctk.CTkFrame(self, fg_color="transparent")
        user_frame.pack(side="bottom", pady=15, padx=12, fill="x")

        # Avatar (identicon) - clickable, fully visible
        try:
            ident_size = 40
            avatar_img = generate_identicon(getattr(app, 'my_pub_hex', ''), size=ident_size)
            # Wrap the PIL image in a CTkImage so CTkLabel can scale it on HighDPI displays
            ctk_img = ctk.CTkImage(light_image=avatar_img, size=(ident_size, ident_size))
            avatar_label = ctk.CTkLabel(user_frame, image=ctk_img, text="", width=ident_size, height=ident_size)
            avatar_label.image = ctk_img
            avatar_label.pack(side="left")
            avatar_label.bind("<Button-1>", lambda e: open_profile(
                self.app, self.app.my_pub_hex, self.app.signing_pub_hex, self.app.copy_pub_key
            ))
            # Make cursor indicate clickable
            avatar_label.configure(cursor="hand2")
        except Exception:
            # Fallback to a simple initial button if identicon generation fails
            avatar_btn = ctk.CTkButton(
                user_frame, text=(getattr(app, 'username', 'A')[0].upper()),
                width=36, height=36, corner_radius=18, fg_color=avatar_bg,
                hover_color=add_hover, text_color=avatar_text,
                font=("Segoe UI", 12, "bold"),
                command=lambda: open_profile(
                    self.app, self.app.my_pub_hex, self.app.signing_pub_hex, self.app.copy_pub_key
                )
            )
            avatar_btn.pack(side="left")

        # Username label (middle)
        username_label = ctk.CTkLabel(
            user_frame, text=getattr(app, 'username', 'Anonymous'),
            font=("Segoe UI", 12, "bold"), text_color=title_color
        )
        username_label.pack(side="left", padx=8)
        username_label.bind("<Button-1>", lambda e: open_profile(
            self.app, self.app.my_pub_hex, self.app.signing_pub_hex, self.app.copy_pub_key
        ))

        # Settings and Add Recipient Buttons (rightmost)
        # Load settings icon
        try:
            # load smaller icon and prepare hover (darker) variant
            base_img = Image.open(get_resource_path("gui/data/images/settings_btn.png")).resize((28, 28), Image.Resampling.LANCZOS)
            # darker hover image
            hover_pil = ImageEnhance.Brightness(base_img).enhance(0.78)
            settings_ctk = ctk.CTkImage(light_image=base_img, dark_image=base_img, size=(28, 28))
            settings_hover_ctk = ctk.CTkImage(light_image=hover_pil, dark_image=hover_pil, size=(28, 28))

            # Use a label for image-only, borderless, clickable icon
            self.settings_btn = ctk.CTkLabel(user_frame, image=settings_ctk, text="", fg_color="transparent")
            # keep references
            self.settings_btn.image = settings_ctk
            self.settings_btn.hover_image = settings_hover_ctk

            # Bind click and hover
            self.settings_btn.bind("<Button-1>", lambda e: self.app.open_settings())
            self.settings_btn.bind("<Enter>", lambda e: self.settings_btn.configure(image=self.settings_btn.hover_image))
            self.settings_btn.bind("<Leave>", lambda e: self.settings_btn.configure(image=self.settings_btn.image))
            self.settings_btn.configure(cursor="hand2")
        except Exception:
            # Fallback to a minimal text label if image missing; make it smaller
            self.settings_btn = ctk.CTkLabel(user_frame, text="⚙️", fg_color="transparent", text_color=avatar_text, font=("Segoe UI", 12))
            self.settings_btn.bind("<Button-1>", lambda e: self.app.open_settings())
            # hover behavior for fallback
            self.settings_btn.bind("<Enter>", lambda e: self.settings_btn.configure(text_color=self.theme.get("button_send_hover", "#357ABD")))
            self.settings_btn.bind("<Leave>", lambda e: self.settings_btn.configure(text_color=avatar_text))
            self.settings_btn.configure(cursor="hand2")

        # Add button (to the left of settings)
        self.add_btn = ctk.CTkButton(
            user_frame, text="➕", width=36, height=36, corner_radius=18,
            fg_color=add_fg, hover_color=add_hover, text_color=avatar_text,
            font=("Segoe UI", 18, "bold"), command=self.open_add_dialog
        )

        # Pack order: pack settings first (rightmost), then add button (left of settings)
        self.settings_btn.pack(side="right", padx=(8, 0))
        self.add_btn.pack(side="right", padx=(8, 0))

    # ---------------- Recipient List ----------------
    def update_list(self, selected_pub=None):
        pin = self.pin
        recipients = load_recipients(pin) if pin else {}

        for widget in self.recipient_listbox.winfo_children():
            widget.destroy()

        sel_bg = self.theme.get("bubble_you", "#7289da")
        item_bg = self.theme.get("bubble_other", "#2a2a3a")
        avatar_bg = self.theme.get("sidebar_button", "#4a90e2")
        text_color = self.theme.get("sidebar_text", "white")

        for name, key in recipients.items():
            is_selected = (key == selected_pub)
            # Small frame for each recipient
            frame = ctk.CTkFrame(
                self.recipient_listbox,
                fg_color=item_bg if not is_selected else sel_bg,
                corner_radius=12, height=40
            )
            frame.pack(fill="x", pady=4, padx=4)

            # Avatar circle
            avatar = ctk.CTkLabel(
                frame, text=name[0].upper(), width=32, height=32,
                fg_color=avatar_bg, text_color=text_color, corner_radius=16
            )
            avatar.pack(side="left", padx=8, pady=4)

            # Name label
            label = ctk.CTkLabel(frame, text=name, font=("Segoe UI", 12, "bold"),
                                 text_color=text_color)
            label.pack(side="left", padx=6)

            # Click binding
            frame.bind("<Button-1>", lambda e, n=name: self.select_callback(n))
            avatar.bind("<Button-1>", lambda e, n=name: self.select_callback(n))
            label.bind("<Button-1>", lambda e, n=name: self.select_callback(n))

    def open_add_dialog(self):
        # Use the custom dialog instead of add_callback
        AddRecipientDialog(
            self,
            self.notifier,
            self.update_list,
            self.add_callback,
            pin=self.pin,
            theme=self.theme
        )
