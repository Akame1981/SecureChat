# gui/widgets/sidebar.py
import customtkinter as ctk
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
        self.theme = theme or {}

        self.notifier = notifier
        self.update_list_callback = update_list_callback
        self.add_callback = add_callback

        # Title
        ctk.CTkLabel(self, text="Add New Recipient", font=("Segoe UI", 16, "bold")).pack(pady=(20, 10))

        # Name
        ctk.CTkLabel(self, text="Recipient Name:", font=("Segoe UI", 12)).pack(anchor="w", padx=20)
        self.name_entry = ctk.CTkEntry(self, placeholder_text="e.g. John Doe", height=40, font=("Segoe UI", 12))
        self.name_entry.pack(padx=20, pady=(0, 10), fill="x")

        # Key
        ctk.CTkLabel(self, text="Recipient Key:", font=("Segoe UI", 12)).pack(anchor="w", padx=20)
        self.key_entry = ctk.CTkEntry(self, placeholder_text="e.g. ABC123XYZ", height=40, font=("Segoe UI", 12))
        self.key_entry.pack(padx=20, pady=(0, 15), fill="x")

        # Buttons frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)

        # Cancel button
        ctk.CTkButton(
            btn_frame, text="Cancel",
            fg_color="gray40", hover_color="gray25",
            font=("Segoe UI", 12, "bold"), width=140, height=48,
            command=self.destroy
        ).pack(side="left", padx=10)

        # Add button
        ctk.CTkButton(
            btn_frame, text="Add",
            fg_color="#4a90e2", hover_color="#357ABD",
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
        super().__init__(parent, width=240, fg_color="#1f1f2e", corner_radius=0)
        self.app = app
        self.select_callback = select_callback
        self.add_callback = add_callback
        self.pin = pin
        self.theme = theme_colors or {}
        self.pack(side="left", fill="y")

        self.notifier = NotificationManager(parent)

        # --- Section title ---
        ctk.CTkLabel(
            self, text="Recipients", font=("Segoe UI", 16, "bold"),
            text_color=self.theme.get("sidebar_text", "white")
        ).pack(pady=(12, 10))

        # --- Scrollable recipient list ---
        self.recipient_listbox = ctk.CTkScrollableFrame(
            self, fg_color=self.theme.get("sidebar_bg", "#2a2a3a"), width=220
        )
        self.recipient_listbox.pack(fill="both", expand=True, padx=12, pady=(0,10))
        self.update_list()

        # --- Bottom user frame (add button + avatar + username) ---
        user_frame = ctk.CTkFrame(self, fg_color="transparent")
        user_frame.pack(side="bottom", pady=15, padx=12, fill="x")

        # Avatar button (left)
        avatar_btn = ctk.CTkButton(
            user_frame, text=(getattr(app, 'username', 'A')[0].upper()),
            width=36, height=36, corner_radius=18, fg_color="#4a90e2",
            hover_color="#357ABD", text_color="white",
            font=("Segoe UI", 12, "bold"),
            command=lambda: open_profile(
                self.app, self.app.my_pub_hex, self.app.signing_pub_hex, self.app.copy_pub_key
            )
        )
        avatar_btn.pack(side="left")

        # Username label (middle)
        username_label = ctk.CTkLabel(
            user_frame, text=getattr(app, 'username', 'Anonymous'),
            font=("Segoe UI", 12, "bold"), text_color="white"
        )
        username_label.pack(side="left", padx=8)
        username_label.bind("<Button-1>", lambda e: open_profile(
            self.app, self.app.my_pub_hex, self.app.signing_pub_hex, self.app.copy_pub_key
        ))

        # Add Recipient Button (rightmost)
        self.add_btn = ctk.CTkButton(
            user_frame, text="➕", width=36, height=36, corner_radius=18,
            fg_color="#4a90e2", hover_color="#357ABD", text_color="white",
            font=("Segoe UI", 18, "bold"), command=self.open_add_dialog
        )
        self.add_btn.pack(side="right", padx=(8, 0))

    # ---------------- Recipient List ----------------
    def update_list(self, selected_pub=None):
        pin = self.pin
        recipients = load_recipients(pin) if pin else {}

        for widget in self.recipient_listbox.winfo_children():
            widget.destroy()

        for name, key in recipients.items():
            is_selected = (key == selected_pub)
            # Small frame for each recipient
            frame = ctk.CTkFrame(
                self.recipient_listbox,
                fg_color="#2a2a3a" if not is_selected else "#7289da",
                corner_radius=12, height=40
            )
            frame.pack(fill="x", pady=4, padx=4)

            # Avatar circle
            avatar = ctk.CTkLabel(
                frame, text=name[0].upper(), width=32, height=32,
                fg_color="#4a90e2", text_color="white", corner_radius=16
            )
            avatar.pack(side="left", padx=8, pady=4)

            # Name label
            label = ctk.CTkLabel(frame, text=name, font=("Segoe UI", 12, "bold"),
                                 text_color="white")
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
