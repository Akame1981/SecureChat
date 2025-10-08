import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
from utils.recipients import add_recipient, load_recipients, delete_recipient
from gui.settings.dialogs import CTkDialog, CTkConfirmDialog

class RecipientsTab:
    def __init__(self, parent_frame, app):
        self.app = app
        self.frame = parent_frame  # Already the frame of the "Recipients" tab

        # Make the frame expandable
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)

        # Title
        # Title + help
        ctk.CTkLabel(
            self.frame,
            text="Manage Recipients",
            font=("Roboto", 16, "bold"),
            text_color="white"
        ).grid(row=0, column=0, columnspan=2, pady=(10, 2), padx=10, sticky="w")

        ctk.CTkLabel(self.frame, text="Add, edit, or remove recipients you trust.", text_color="#b2b8d6").grid(row=1, column=0, columnspan=2, sticky="w", padx=10)

        # Search box above the list
        self.search_var = tk.StringVar()
        search_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        search_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(8, 4))
        search_frame.grid_columnconfigure(0, weight=1)
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search recipients...", textvariable=self.search_var)
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.refresh_list())

        # List of recipients (rich rendering) — full width
        self.list_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.list_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=4)
        self.list_frame.grid_rowconfigure(1, weight=1)
        self.list_frame.grid_columnconfigure(0, weight=1)

        # Controls row above the list (search already exists above)
        controls = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        controls.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 4))
        controls.grid_columnconfigure(0, weight=1)
        # Add button moved to top controls for quick access
        self.add_btn = ctk.CTkButton(controls, text="Add", width=90, command=self.add_recipient_gui, fg_color="#4a90e2")
        self.add_btn.grid(row=0, column=1, sticky="e")

        self.list_container = ctk.CTkScrollableFrame(self.list_frame, fg_color="#1e1e2f")
        self.list_container.grid(row=1, column=0, sticky="nsew")
        self.list_container.grid_columnconfigure(0, weight=1)

        # Internal state
        self._recipients = {}  # name -> key
        self.selected_name = None

        # No right-side details panel — keep a single, full-width list
        # ensure layout grows
        try:
            self.frame.grid_columnconfigure(0, weight=1)
            self.frame.grid_rowconfigure(3, weight=1)
        except Exception:
            pass

    def refresh_list(self):
        # Clear previous items
        for child in self.list_container.winfo_children():
            child.destroy()

        # Check if PIN is available
        if not hasattr(self.app, "pin") or not self.app.pin:
            # show an informative label instead of list
            ctk.CTkLabel(self.list_container, text="Set your PIN to load recipients", text_color="#b2b8d6", fg_color="transparent").grid(padx=10, pady=10)
            return

        try:
            recipients = load_recipients(self.app.pin)
        except Exception as e:
            print("Failed to load recipients:", e)
            recipients = {}

        self._recipients = recipients

        # Filter by search
        q = self.search_var.get().strip().lower() if hasattr(self, 'search_var') else ""

        row = 0
        for name, key in recipients.items():
            if q and q not in name.lower() and q not in key.lower():
                continue

            row_frame = ctk.CTkFrame(self.list_container, fg_color="transparent")
            row_frame.grid(row=row, column=0, sticky="ew", padx=6, pady=2)
            row_frame.grid_columnconfigure(1, weight=1)

            name_label = ctk.CTkLabel(row_frame, text=name, text_color="#dbe4ff", fg_color="transparent")
            name_label.grid(row=0, column=0, sticky="w")

            short = key[:10] + "..." + key[-6:]
            key_label = ctk.CTkLabel(row_frame, text=short, text_color="#b2b8d6", fg_color="transparent")
            key_label.grid(row=0, column=1, sticky="w", padx=(8,0))

            # Action icons: copy, edit, delete
            copy_btn = ctk.CTkButton(row_frame, text="⎘", width=32, height=28, fg_color="#4a90e2", command=lambda k=key: self._copy_key(k))
            copy_btn.grid(row=0, column=2, padx=4)
            edit_btn = ctk.CTkButton(row_frame, text="✎", width=32, height=28, fg_color="#f0ad4e", command=lambda n=name, k=key: self._edit_quick(n, k))
            edit_btn.grid(row=0, column=3, padx=4)
            del_btn = ctk.CTkButton(row_frame, text="🗑", width=32, height=28, fg_color="#d9534f", command=lambda n=name: self._del_quick(n))
            del_btn.grid(row=0, column=4, padx=4)

            # Bind clicking row to populate details
            row_frame.bind("<Button-1>", lambda e, n=name, k=key: self._select_row(n, k))
            name_label.bind("<Button-1>", lambda e, n=name, k=key: self._select_row(n, k))
            key_label.bind("<Button-1>", lambda e, n=name, k=key: self._select_row(n, k))
            # Right-click context menu for this row
            row_frame.bind("<Button-3>", lambda e, n=name, k=key: self._show_context_menu(e, n, k))
            name_label.bind("<Button-3>", lambda e, n=name, k=key: self._show_context_menu(e, n, k))
            key_label.bind("<Button-3>", lambda e, n=name, k=key: self._show_context_menu(e, n, k))

            row += 1

        # After populating, if nothing selected just clear selection state
        if not self.selected_name:
            self.selected_name = None


    def add_recipient_gui(self):
        name = CTkDialog(self.frame, title="Add Recipient", label="Name:").result
        if not name:
            return

        pub_key = CTkDialog(self.frame, title="Add Recipient", label="Public Key (64 hex chars):").result
        if not pub_key or len(pub_key) != 64:
            messagebox.showerror("Error", "Invalid public key")
            return

        add_recipient(name, pub_key, self.app.pin)
        self.refresh_list()
        if hasattr(self.app, "update_recipient_list"):
            self.app.update_recipient_list()

    def edit_recipient(self):
        # Use selected_name from row-based UI
        name = self.selected_name
        if not name:
            messagebox.showwarning("Select", "Select a recipient to edit")
            return

        old_key = self._recipients.get(name, "")
        new_name = CTkDialog(self.frame, title="Edit Recipient", label="New Name:", initial_value=name).result
        if not new_name:
            return

        new_key = CTkDialog(self.frame, title="Edit Recipient", label="New Public Key:", initial_value=old_key).result
        if not new_key or len(new_key) != 64:
            messagebox.showerror("Error", "Invalid public key")
            return

        # replace entry
        try:
            delete_recipient(name, self.app.pin)
        except Exception:
            pass
        add_recipient(new_name, new_key, self.app.pin)
        self.selected_name = None
        self.refresh_list()
        if hasattr(self.app, "update_recipient_list"):
            self.app.update_recipient_list()

    # obsolete Listbox handlers removed; use _select_row/_copy_key/etc.

    def _show_context_menu(self, event, name=None, key=None):
        # Right-click context menu: Copy, Edit, Delete
        try:
            # event may include name/key if provided
            menu = tk.Menu(self.frame, tearoff=0)
            # determine current name/key
            cur_name = name or getattr(event, 'name', None) or self.selected_name
            cur_key = key or getattr(event, 'key', None) or (self._recipients.get(cur_name) if cur_name else None)
            menu.add_command(label="Copy Key", command=lambda: self._copy_key(cur_key) if cur_key else None)
            menu.add_command(label="Edit", command=lambda: self._edit_quick(cur_name, cur_key) if cur_name else None)
            menu.add_command(label="Delete", command=lambda: self._del_quick(cur_name) if cur_name else None)
            menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            pass

    # --- New helpers for rich list actions ---
    def _copy_key(self, key):
        try:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(key)
            if hasattr(self.app, "notifier"):
                self.app.notifier.show("Key copied!", type_="success")
        except Exception:
            pass

    def _edit_quick(self, name, key):
        # select then open edit dialog
        try:
            self._select_row(name, key)
            self.edit_recipient()
        except Exception:
            pass

    def _del_quick(self, name):
        try:
            # select
            self._select_row(name, self._recipients.get(name, ""))
            self.delete_recipient()
        except Exception:
            pass

    def _select_row(self, name, key):
        # update details panel and enable edit/delete
        try:
            # store selection; details panel removed, so only track selection
            self.selected_name = name
            # optional lightweight feedback
            if hasattr(self.app, "notifier"):
                self.app.notifier.show(f"Selected {name}")
        except Exception:
            pass

    def delete_recipient(self):
        name = self.selected_name
        if not name:
            messagebox.showwarning("Select", "Select a recipient to delete")
            return

        confirm = CTkConfirmDialog(self.frame, title="Delete Recipient", message=f"Delete {name}?")
        if confirm.result:
            try:
                delete_recipient(name, self.app.pin)
            except Exception:
                pass
            self.selected_name = None
            self.refresh_list()
            if hasattr(self.app, "update_recipient_list"):
                self.app.update_recipient_list()

    def _toggle_expand(self):
        # Toggle the list area to occupy the whole tab (hide/show details)
        try:
            if not self._expanded:
                # hide details
                self.details_frame.grid_remove()
                # let left column take all space
                self.frame.grid_columnconfigure(0, weight=1)
                self.frame.grid_columnconfigure(1, weight=0)
                self.expand_btn.configure(text="Collapse")
                self._expanded = True
            else:
                # show details again
                self.details_frame.grid()
                # restore columns
                self.frame.grid_columnconfigure(0, weight=1)
                self.frame.grid_columnconfigure(1, weight=0)
                self.expand_btn.configure(text="Expand")
                self._expanded = False
            # refresh to reflow
            self.refresh_list()
        except Exception:
            pass
