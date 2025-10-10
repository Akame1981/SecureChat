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
        self.grab_set()

        # Header with invite code
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header, text="Invite Code:").pack(side="left")
        self.code_var = tk.StringVar(value="...")
        self.code_entry = ctk.CTkEntry(header, textvariable=self.code_var, width=320)
        self.code_entry.pack(side="left", padx=6)
        ctk.CTkButton(header, text="Copy", command=self._copy_code).pack(side="left")
        ctk.CTkButton(self, text="Rotate Invite", command=self._rotate_invite).pack(padx=10, pady=(0, 10), anchor="w")

        # Members list
        self.members_frame = ctk.CTkScrollableFrame(self, fg_color=self.theme.get("background", "#2e2e3f"))
        self.members_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self._load_members()

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
