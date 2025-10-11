import customtkinter as ctk
import tkinter as tk


class GroupSettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, app, group_manager, group_id: str, theme: dict | None = None):
        super().__init__(parent)
        self.app = app
        self.gm = group_manager
        self.gid = group_id
        self.theme = theme or {}

        self.title("Group Settings")
        self.geometry("520x520")
        self.transient(parent)
        # Try to grab focus for modal behavior. On some Linux WMs this can
        # fail with "grab failed: window not viewable" if the parent isn't
        # currently mapped. Attempt once and, if parent is not viewable,
        # schedule a single retry shortly after.
        try:
            try:
                self.grab_set()
            except Exception:
                try:
                    if getattr(parent, "winfo_viewable", None) and not parent.winfo_viewable():
                        def _retry():
                            try:
                                if getattr(self, "winfo_exists", None) and self.winfo_exists():
                                    self.grab_set()
                            except Exception:
                                pass
                        try:
                            self.after(150, _retry)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            # Keep construction robust if any check unexpectedly fails
            pass

        # Header with invite code
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text="Invite Code:").pack(side="left")
        self.code_var = tk.StringVar(value="...")
        self.code_entry = ctk.CTkEntry(header, textvariable=self.code_var, width=320)
        self.code_entry.pack(side="left", padx=6)
        ctk.CTkButton(header, text="Copy", command=self._copy_code).pack(side="left")
        ctk.CTkButton(self, text="Rotate Invite", command=self._rotate_invite).pack(padx=10, pady=(0, 10), anchor="w")

        # Group name (rename)
        name_frame = ctk.CTkFrame(self, fg_color="transparent")
        name_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(name_frame, text="Group Name:").pack(side="left")
        self.name_var = tk.StringVar(value="")
        self.name_entry = ctk.CTkEntry(name_frame, textvariable=self.name_var, width=320)
        self.name_entry.pack(side="left", padx=6)
        ctk.CTkButton(name_frame, text="Rename", command=self._rename_group).pack(side="left")

        # Public toggle
        pub_frame = ctk.CTkFrame(self, fg_color="transparent")
        pub_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(pub_frame, text="Public (discoverable)").pack(side="left")
        self.is_public_var = tk.BooleanVar(value=False)
        self.public_switch = ctk.CTkSwitch(pub_frame, text="", variable=self.is_public_var, command=self._toggle_public)
        self.public_switch.pack(side="left", padx=8)

        # Rekey controls
        rekey_frame = ctk.CTkFrame(self, fg_color="transparent")
        rekey_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(rekey_frame, text="Force Rekey", command=self._rekey_group).pack(side="left", padx=(0, 8))

        # Approvals (enter user id to approve)
        appr_frame = ctk.CTkFrame(self, fg_color="transparent")
        appr_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(appr_frame, text="Approve User ID:").pack(side="left")
        self.appr_var = tk.StringVar(value="")
        ctk.CTkEntry(appr_frame, textvariable=self.appr_var, width=300).pack(side="left", padx=6)
        ctk.CTkButton(appr_frame, text="Approve", command=self._approve_member).pack(side="left")

        # Members list
        self.members_frame = ctk.CTkScrollableFrame(self, fg_color=self.theme.get("background", "#2e2e3f"))
        self.members_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._load_members()
        self._hydrate_public_and_name()

        # Channels management
        chan_frame = ctk.CTkFrame(self, fg_color="transparent")
        chan_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(chan_frame, text="New Channel:").pack(side="left")
        self.chan_var = tk.StringVar(value="")
        ctk.CTkEntry(chan_frame, textvariable=self.chan_var, width=240).pack(side="left", padx=6)
        ctk.CTkButton(chan_frame, text="Create", command=self._create_channel).pack(side="left")

    def _rename_group(self):
        try:
            # If server supports rename, you'd call a route here. Placeholder UX.
            new_name = (self.name_var.get() or "").strip()
            if not new_name:
                return
            self.app.notifier.show("Rename requested (server route TBD)", type_="info")
        except Exception as e:
            self.app.notifier.show(str(e), type_="error")

    def _hydrate_public_and_name(self):
        """Initialize current is_public and name using list_groups (cheap and available)."""
        try:
            data = self.gm.list_groups()
            groups = data.get("groups", [])
            me = next((g for g in groups if g.get("id") == self.gid), None)
            if me:
                self.is_public_var.set(bool(me.get("is_public")))
                self.name_var.set(me.get("name") or "")
        except Exception:
            pass

    def _toggle_public(self):
        try:
            new_val = bool(self.is_public_var.get())
            res = self.gm.client.set_group_public(self.gid, new_val)
            self.is_public_var.set(bool(res.get("is_public", new_val)))
            self.app.notifier.show("Group visibility updated", type_="success")
        except Exception as e:
            # revert UI switch on failure
            self.is_public_var.set(not self.is_public_var.get())
            self.app.notifier.show(f"Failed to update visibility: {e}", type_="error")

    def _rekey_group(self):
        try:
            self.gm.client.rekey(self.gid)
            self.app.notifier.show("Rekey requested", type_="success")
        except Exception as e:
            self.app.notifier.show(f"Rekey failed: {e}", type_="error")

    def _approve_member(self):
        uid = (self.appr_var.get() or "").strip()
        if not uid:
            return
        try:
            self.gm.client.approve_member(self.gid, uid)
            self.app.notifier.show("User approved", type_="success")
        except Exception as e:
            self.app.notifier.show(f"Approve failed: {e}", type_="error")

    def _create_channel(self):
        name = (self.chan_var.get() or "").strip()
        if not name:
            return
        try:
            self.gm.client.create_channel(self.gid, name)
            self.app.notifier.show("Channel created", type_="success")
        except Exception as e:
            self.app.notifier.show(f"Create channel failed: {e}", type_="error")

    def _copy_code(self):
        try:
            self.app.clipboard_clear()
            self.app.clipboard_append(self.code_entry.get())
            self.app.notifier.show("Invite copied", type_="success")
        except Exception:
            pass

    def _rotate_invite(self):
        try:
            res = self.gm.client.rotate_invite(self.gid)
            self.code_var.set(res.get("invite_code", ""))
            self.app.notifier.show("Invite rotated", type_="success")
        except Exception as e:
            self.app.notifier.show(f"Rotate failed: {e}", type_="error")

    def _load_members(self):
        for w in self.members_frame.winfo_children():
            w.destroy()
        try:
            info = self.gm.client.get_member_keys(self.gid)
            members = info.get("members", []) if info else []
        except Exception:
            members = []
        for m in members:
            row = ctk.CTkFrame(self.members_frame, fg_color=self.theme.get("input_bg", "#2e2e3f"))
            row.pack(fill="x", padx=6, pady=4)
            ctk.CTkLabel(row, text=m.get("user_id", "?")[:16] + "…").pack(side="left", padx=8, pady=6)
            ctk.CTkLabel(row, text=m.get("role", "member"), fg_color="#3b3b52", corner_radius=8, width=70).pack(side="left", padx=6)
            ctk.CTkButton(row, text="Ban", width=60,
                          command=lambda uid=m.get("user_id"): self._ban_member(uid)).pack(side="right", padx=6)

    def _ban_member(self, user_id: str):
        try:
            self.gm.client.ban_member(self.gid, user_id)
            self.app.notifier.show("Member removed. Rekey required.", type_="warning")
            self._load_members()
        except Exception as e:
            self.app.notifier.show(f"Ban failed: {e}", type_="error")
