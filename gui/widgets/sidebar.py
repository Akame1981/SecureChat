# gui/widgets/sidebar.py
import customtkinter as ctk
import tkinter as tk
import os
from PIL import Image, ImageEnhance
from utils.path_utils import get_resource_path
from gui.identicon import generate_identicon
from utils.recipients import add_recipient, load_recipients, set_recipient_name_for_key
from gui.widgets.notification import NotificationManager
from utils.group_manager import GroupManager
from tkinter import simpledialog
from gui.profile_window import open_profile

# Import AddRecipientDialog from this module
class AddRecipientDialog(ctk.CTkToplevel):
    def __init__(self, parent, notifier, update_list_callback, add_callback=None, pin=None, theme=None):
        super().__init__(parent)
        self.title("Add Recipient")
        self.geometry("360x260")
        self.resizable(False, False)
        # Only attempt to grab input if the dialog/parent is viewable.
        # Calling grab_set when the parent window isn't viewable raises
        # "grab failed: window not viewable" on some platforms/Timings.
        try:
            # prefer checking this Toplevel's visibility; fall back to parent
            if getattr(self, 'winfo_viewable', lambda: False)() or getattr(self.master, 'winfo_viewable', lambda: False)():
                try:
                    self.grab_set()
                except tk.TclError:
                    # If grab fails, ignore and continue without modal grab
                    pass
        except Exception:
            # keep construction robust if any check fails
            pass
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
            # Try to add; if key already exists, fall back to renaming that entry
            try:
                add_recipient(name, key, self.pin)
                msg = f"Recipient '{name}' added!"
            except ValueError as e:
                # If the key already exists, update its name to the requested name
                recs = load_recipients(self.pin)
                exists = any(k.strip().lower() == key.strip().lower() for k in recs.values())
                if exists:
                    set_recipient_name_for_key(key, name, self.pin)
                    msg = f"Recipient saved as '{name}'"
                else:
                    # Re-raise for other validation errors (e.g., duplicate name with different key)
                    raise e
            if self.update_list_callback:
                self.update_list_callback(selected_pub=key)
            # Also try to update the app-level banner if available
            try:
                if hasattr(self.app, 'update_unknown_contact_banner'):
                    self.app.update_unknown_contact_banner()
            except Exception:
                pass
            self.notifier.show(msg, type_="success")
            self.unbind("<Return>")
            self.after(10, self.destroy)
        except ValueError as e:
            self.notifier.show(str(e), type_="error")

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, app, *, select_callback, add_callback=None, pin=None, theme_colors=None, open_group_callback=None):
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
        self.open_group_callback = open_group_callback
        self.pin = pin
        self.theme = resolved
        self.pack(side="left", fill="y")
        # Cache for recipient identicon images: pub_key -> CTkImage
        self.recipient_avatar_cache = {}
        # Group manager for groups listing/creation
        try:
            self.gm = GroupManager(app)
        except Exception:
            self.gm = None
        self.view_mode = "recipients"  # or "groups"

        # Register with theme manager for live updates
        if hasattr(app, "theme_manager"):
            try:
                app.theme_manager.register_listener(self.refresh_theme)
            except Exception:
                pass

        self.notifier = NotificationManager(parent)
        # search state
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_search_change())

        title_color = self.theme.get("sidebar_text", "white")
        list_bg = self.theme.get("sidebar_bg", "#2a2a3a")
        avatar_bg = self.theme.get("sidebar_button", "#4a90e2")
        avatar_text = self.theme.get("sidebar_text", "white")
        add_fg = self.theme.get("sidebar_button", "#4a90e2")
        add_hover = self.theme.get("sidebar_button_hover", "#357ABD")

        # --- Top bar: segmented toggle (Contacts / Groups) ---
        topbar = ctk.CTkFrame(self, fg_color="transparent")
        topbar.pack(fill="x", padx=12, pady=(10, 6))
        self.topbar = topbar

        self.section_toggle = ctk.CTkSegmentedButton(
            topbar,
            values=["Contacts", "Groups"],
            command=lambda v: self._on_section_change(v),
        )
        # style segmented button via theme
        try:
            self.section_toggle.configure(
                fg_color=self.theme.get("sidebar_bg", "#2a2a3a"),
                selected_color=self.theme.get("bubble_you", "#7289da"),
                selected_hover_color=self.theme.get("button_send_hover", "#357ABD"),
                unselected_color=self.theme.get("bubble_other", "#2a2a3a"),
                unselected_hover_color=self.theme.get("hover_bg", "#3a3a55"),
                text_color=self.theme.get("sidebar_text", "white"),
            )
        except Exception:
            pass
        self.section_toggle.set("Contacts")
        self.section_toggle.pack(side="left")

        # --- Search ---
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=12, pady=(0, 8))
        self.search_frame = search_frame

        # try to load a search icon, else fallback to text
        self._search_icon_label = None
        try:
            icon_path = get_resource_path("gui/src/images/search.png")
            if not icon_path or not os.path.exists(icon_path):
                raise FileNotFoundError
            base_img = Image.open(icon_path).resize((18, 18), Image.Resampling.LANCZOS)
            search_ctk = ctk.CTkImage(light_image=base_img, dark_image=base_img, size=(18, 18))
            self._search_icon_label = ctk.CTkLabel(search_frame, image=search_ctk, text="", width=20)
            self._search_icon_label.image = search_ctk
        except Exception:
            self._search_icon_label = ctk.CTkLabel(search_frame, text="🔍", width=20, text_color=title_color)
        self._search_icon_label.pack(side="left", padx=(0, 6))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search...",
            textvariable=self.search_var,
            height=32,
            fg_color=self.theme.get("input_bg", "#2a2a3f"),
            text_color=self.theme.get("input_text", "white"),
        )
        self.search_entry.pack(side="left", fill="x", expand=True)

        # --- Scrollable recipient list ---
        self.recipient_listbox = ctk.CTkScrollableFrame(
            self, fg_color=list_bg, width=220
        )
        self.recipient_listbox.pack(fill="both", expand=True, padx=12, pady=(0,10))
        self.update_list()

        # --- Scrollable groups list (hidden by default) ---
        self.groups_listbox = ctk.CTkScrollableFrame(
            self, fg_color=list_bg, width=220
        )
        self.groups_listbox.pack_forget()

    # --- Bottom user frame (add button + avatar + username) ---
        user_frame = ctk.CTkFrame(self, fg_color="transparent")
        user_frame.pack(side="bottom", pady=15, padx=12, fill="x")
        self.user_frame = user_frame

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
            self.avatar_widget = avatar_label
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
            self.avatar_widget = avatar_btn

        # Username label (middle)
        self.username_label = ctk.CTkLabel(
            user_frame, text=getattr(app, 'username', 'Anonymous'),
            font=("Segoe UI", 12, "bold"), text_color=title_color
        )
        self.username_label.pack(side="left", padx=8)
        self.username_label.bind("<Button-1>", lambda e: open_profile(
            self.app, self.app.my_pub_hex, self.app.signing_pub_hex, self.app.copy_pub_key
        ))

        # Settings and Add Recipient Buttons (rightmost)
        # Load settings icon
        try:
            # load smaller icon and prepare hover (darker) variant
            # NOTE: fixed path typo gui/scr -> gui/src
            base_img = Image.open(get_resource_path("gui/src/images/settings_btn.png")).resize((28, 28), Image.Resampling.LANCZOS)
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

        # Add button (to the left of settings) - prefer an image icon if available
        try:
            add_path = get_resource_path("gui/src/images/add_friend.png")
            if not add_path or not os.path.exists(add_path):
                raise FileNotFoundError
            add_img = Image.open(add_path).resize((36, 36), Image.Resampling.LANCZOS)
            add_ctk = ctk.CTkImage(light_image=add_img, dark_image=add_img, size=(36, 36))

            # darker hover variant
            darker = ImageEnhance.Brightness(add_img).enhance(0.78)
            add_hover_ctk = ctk.CTkImage(light_image=darker, dark_image=darker, size=(36, 36))

            self.add_btn = ctk.CTkLabel(user_frame, image=add_ctk, text="", fg_color="transparent")
            self.add_btn.image = add_ctk
            self.add_btn.hover_image = add_hover_ctk
            self.add_btn.configure(cursor="hand2")
            # bind action separately for reuse across views
            self._set_add_btn_action(self.open_add_dialog)
        except Exception:
            # Fallback to a simple CTkButton with a plus sign
            self.add_btn = ctk.CTkButton(
                user_frame, text="➕", width=36, height=36, corner_radius=18,
                fg_color=add_fg, hover_color=add_hover, text_color=avatar_text,
                font=("Segoe UI", 18, "bold"), command=self.open_add_dialog
            )

        # Pack order: pack settings first (rightmost), then add button (left of settings)
        self.settings_btn.pack(side="right", padx=(8, 0))
        self.add_btn.pack(side="right", padx=(8, 0))

    def refresh_theme(self, theme: dict):
        """Update colors of sidebar when theme changes (registered as ThemeManager listener)."""
        if not theme:
            return
        self.theme = theme
        try:
            self.configure(fg_color=theme.get("sidebar_bg", "#2a2a3a"))
        except Exception:
            pass
        # Topbar segmented toggle
        if hasattr(self, 'section_toggle'):
            try:
                self.section_toggle.configure(
                    fg_color=theme.get("sidebar_bg", "#2a2a3a"),
                    selected_color=theme.get("bubble_you", "#7289da"),
                    selected_hover_color=theme.get("button_send_hover", "#357ABD"),
                    unselected_color=theme.get("bubble_other", "#2a2a3a"),
                    unselected_hover_color=theme.get("hover_bg", "#3a3a55"),
                    text_color=theme.get("sidebar_text", "white"),
                )
            except Exception:
                pass
        # Search entry
        if hasattr(self, 'search_entry'):
            try:
                self.search_entry.configure(
                    fg_color=theme.get("input_bg", "#2a2a3f"),
                    text_color=theme.get("input_text", "white"),
                )
                if getattr(self, '_search_icon_label', None) and isinstance(self._search_icon_label, ctk.CTkLabel):
                    self._search_icon_label.configure(text_color=theme.get("sidebar_text", "white"))
            except Exception:
                pass
        # Username
        if hasattr(self, 'username_label'):
            try:
                self.username_label.configure(text_color=theme.get("sidebar_text", "white"))
            except Exception:
                pass
        # Add button
        if hasattr(self, 'add_btn'):
            try:
                self.add_btn.configure(fg_color=theme.get("sidebar_button", "#4a90e2"),
                                       hover_color=theme.get("sidebar_button_hover", "#357ABD"),
                                       text_color=theme.get("sidebar_text", "white"))
            except Exception:
                pass
        # Recipient list container
        if hasattr(self, 'recipient_listbox'):
            try:
                self.recipient_listbox.configure(fg_color=theme.get("sidebar_bg", "#2a2a3a"))
            except Exception:
                pass
        # Groups list container
        if hasattr(self, 'groups_listbox'):
            try:
                self.groups_listbox.configure(fg_color=theme.get("sidebar_bg", "#2a2a3a"))
            except Exception:
                pass
        # Avatar widget (only recolor text fg for fallback button)
        if hasattr(self, 'avatar_widget'):
            try:
                if isinstance(self.avatar_widget, ctk.CTkButton):
                    self.avatar_widget.configure(fg_color=theme.get("sidebar_button", "#4a90e2"),
                                                 hover_color=theme.get("sidebar_button_hover", "#357ABD"),
                                                 text_color=theme.get("sidebar_text", "white"))
            except Exception:
                pass
        # Rebuild current view entries with new colors
        try:
            if self.view_mode == "recipients":
                self.update_list(selected_pub=getattr(self.app, 'recipient_pub_hex', None))
            else:
                self.update_groups_list()
        except Exception:
            pass

    # ---------------- Recipient List ----------------
    def update_list(self, selected_pub=None):
        pin = self.pin
        recipients = load_recipients(pin) if pin else {}

        for widget in self.recipient_listbox.winfo_children():
            widget.destroy()

        sel_bg = self.theme.get("bubble_you", "#7289da")
        item_bg = self.theme.get("bubble_other", "#2a2a3a")
        hover_bg = self.theme.get("hover_bg", "#3a3a55")
        avatar_bg = self.theme.get("sidebar_button", "#4a90e2")
        text_color = self.theme.get("sidebar_text", "white")

        # filter by search
        q = (self.search_var.get() or "").strip().lower()
        items = [(n, k) for n, k in recipients.items() if (not q or q in n.lower() or q in (k or "").lower())]
        if not items:
            ctk.CTkLabel(self.recipient_listbox, text="No contacts found", text_color=text_color).pack(pady=12)
            return

        for name, key in items:
            is_selected = (key == selected_pub)
            # Small frame for each recipient
            frame = ctk.CTkFrame(
                self.recipient_listbox,
                fg_color=item_bg if not is_selected else sel_bg,
                corner_radius=12, height=40
            )
            frame.pack(fill="x", pady=4, padx=4)

            # Avatar identicon (fallback to initial if generation fails)
            avatar_label = None
            ident_size = 32
            try:
                if key not in self.recipient_avatar_cache:
                    pil_img = generate_identicon(key, size=ident_size)
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(ident_size, ident_size))
                    self.recipient_avatar_cache[key] = ctk_img
                ctk_img = self.recipient_avatar_cache[key]
                avatar_label = ctk.CTkLabel(frame, image=ctk_img, text="", width=ident_size, height=ident_size)
                avatar_label.image = ctk_img
            except Exception:
                avatar_label = ctk.CTkLabel(
                    frame, text=name[0].upper(), width=32, height=32,
                    fg_color=avatar_bg, text_color=text_color, corner_radius=16
                )
            avatar_label.pack(side="left", padx=8, pady=4)

            # Name label
            label = ctk.CTkLabel(frame, text=name, font=("Segoe UI", 12, "bold"),
                                 text_color=text_color)
            label.pack(side="left", padx=6)

            # Click binding
            frame.bind("<Button-1>", lambda e, n=name: self.select_callback(n))
            avatar_label.bind("<Button-1>", lambda e, n=name: self.select_callback(n))
            label.bind("<Button-1>", lambda e, n=name: self.select_callback(n))

            # Hover effect for non-selected
            if not is_selected:
                frame.bind("<Enter>", lambda e, f=frame: f.configure(fg_color=hover_bg))
                frame.bind("<Leave>", lambda e, f=frame: f.configure(fg_color=item_bg))

    # ---------------- Groups List ----------------
    def update_groups_list(self):
        # Clear existing
        for widget in self.groups_listbox.winfo_children():
            widget.destroy()

        list_bg = self.theme.get("sidebar_bg", "#2a2a3a")
        item_bg = self.theme.get("bubble_other", "#2a2a3a")
        sel_bg = self.theme.get("bubble_you", "#7289da")
        hover_bg = self.theme.get("hover_bg", "#3a3a55")
        text_color = self.theme.get("sidebar_text", "white")

        groups = []
        try:
            if self.gm:
                data = self.gm.list_groups()
                groups = data.get("groups", [])
        except Exception:
            groups = []

        # filter by search
        q = (self.search_var.get() or "").strip().lower()
        groups = [g for g in groups if (not q or q in g.get("name", "").lower())]
        if not groups:
            ctk.CTkLabel(self.groups_listbox, text="No groups found", text_color=text_color).pack(pady=12)
            return

        for g in groups:
            frame = ctk.CTkFrame(self.groups_listbox, fg_color=item_bg, corner_radius=12, height=40)
            frame.pack(fill="x", pady=4, padx=4)
            name = ctk.CTkLabel(frame, text=g.get("name", "?"), font=("Segoe UI", 12, "bold"), text_color=text_color)
            name.pack(side="left", padx=8, pady=6)
            tag_txt = "Public" if g.get("is_public") else "Private"
            tag = ctk.CTkLabel(frame, text=tag_txt, fg_color="#3b3b52", corner_radius=8, width=60)
            tag.pack(side="left", padx=6)

            def open_group(gid=g.get("id"), n=g.get("name")):
                if callable(self.open_group_callback):
                    try:
                        self.open_group_callback(gid, n)
                    except Exception:
                        pass
                else:
                    # fallback: use app.groups_panel if present
                    try:
                        if hasattr(self.app, 'show_groups_panel'):
                            self.app.show_groups_panel()
                        if hasattr(self.app, 'groups_panel'):
                            self.app.groups_panel._select_group(gid, n)
                    except Exception:
                        pass

            frame.bind("<Button-1>", lambda e: open_group())
            name.bind("<Button-1>", lambda e: open_group())
            tag.bind("<Button-1>", lambda e: open_group())

            # Hover
            frame.bind("<Enter>", lambda e, f=frame: f.configure(fg_color=hover_bg))
            frame.bind("<Leave>", lambda e, f=frame: f.configure(fg_color=item_bg))

    # ---------------- View Toggles ----------------


    def show_recipients_view(self):
        self.view_mode = "recipients"
        # Ensure main app switches to direct messages view
        try:
            if hasattr(self.app, 'show_direct_messages'):
                self.app.show_direct_messages()
        except Exception:
            pass
        try:
            if self.groups_listbox.winfo_ismapped():
                self.groups_listbox.pack_forget()
            if not self.recipient_listbox.winfo_ismapped():
                self.recipient_listbox.pack(fill="both", expand=True, padx=12, pady=(0,10))
            # Restore add button behavior
            self._set_add_btn_action(self.open_add_dialog)
        except Exception:
            pass
        # Rebuild recipient list
        self.update_list(selected_pub=getattr(self.app, 'recipient_pub_hex', None))

    def show_groups_view(self):
        """Route to the main Groups panel instead of showing a groups list here."""
        self.view_mode = "groups"
        try:
            if hasattr(self.app, 'show_groups_panel'):
                self.app.show_groups_panel()
        except Exception:
            pass
        # The main sidebar is hidden in groups panel; no need to render local groups list

    def _create_group(self):
        if not self.gm:
            return
        name = simpledialog.askstring("Create Group", "Group name:", parent=self)
        if not name:
            return
        try:
            res = self.gm.create_group(name, is_public=False)
            # update and open
            self.update_groups_list()
            gid = res.get("id")
            if gid:
                if callable(self.open_group_callback):
                    self.open_group_callback(gid, name)
                else:
                    try:
                        if hasattr(self.app, 'show_groups_panel'):
                            self.app.show_groups_panel()
                        if hasattr(self.app, 'groups_panel'):
                            self.app.groups_panel._select_group(gid, name)
                    except Exception:
                        pass
            try:
                self.notifier.show(f"Group '{name}' created", type_="success")
            except Exception:
                pass
        except Exception as e:
            try:
                self.notifier.show(f"Create failed: {e}", type_="error")
            except Exception:
                pass

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

    # ---------------- Helpers ----------------
    def _on_section_change(self, value: str):
        if value == "Groups":
            # Send user to the Groups panel
            self.show_groups_view()
        else:
            # Back to direct messages view
            self.show_recipients_view()

    def _on_search_change(self):
        # Refresh current view based on search text
        if self.view_mode == "recipients":
            self.update_list(selected_pub=getattr(self.app, 'recipient_pub_hex', None))
        else:
            self.update_groups_list()

    def _set_add_btn_action(self, func):
        """Bind the add button (label or button) to call func on click, preserving hover images for label variant."""
        if not hasattr(self, 'add_btn') or self.add_btn is None:
            return
        # Label variant
        if isinstance(self.add_btn, ctk.CTkLabel):
            try:
                # Clear previous bindings
                self.add_btn.unbind("<Button-1>")
            except Exception:
                pass
            self.add_btn.bind("<Button-1>", lambda e: func())
            # ensure hover bindings exist
            try:
                self.add_btn.unbind("<Enter>")
                self.add_btn.unbind("<Leave>")
            except Exception:
                pass
            if hasattr(self.add_btn, 'hover_image') and hasattr(self.add_btn, 'image'):
                self.add_btn.bind("<Enter>", lambda e: self.add_btn.configure(image=self.add_btn.hover_image))
                self.add_btn.bind("<Leave>", lambda e: self.add_btn.configure(image=self.add_btn.image))
            self.add_btn.configure(cursor="hand2")
        else:
            # CTkButton
            try:
                self.add_btn.configure(command=func)
            except Exception:
                pass
