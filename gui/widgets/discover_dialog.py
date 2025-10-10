import customtkinter as ctk
from tkinter import Toplevel


class DiscoverDialog(Toplevel):
    def __init__(self, parent, gm, theme: dict | None = None):
        super().__init__(parent)
        self.gm = gm
        self.theme = theme or {}
        self.title("Discover Public Groups")
        self.geometry("420x480")
        self.transient(parent)
        self.grab_set()

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=10)
        self.q = ctk.CTkEntry(top, placeholder_text="Search public groups")
        self.q.pack(side="left", expand=True, fill="x")
        ctk.CTkButton(top, text="Search", command=self._do_search).pack(side="left", padx=6)

        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=self.theme.get("background", "#2e2e3f"))
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # initial
        self._render_items(self._discover_initial())

    def _discover_initial(self):
        try:
            res = self.gm.client.discover_public()
            return res.get("groups", [])
        except Exception:
            return []

    def _do_search(self):
        try:
            r = self.gm.client.discover_public(query=(self.q.get() or None))
            self._render_items(r.get("groups", []))
        except Exception:
            pass

    def _render_items(self, items):
        for w in self.list_frame.winfo_children():
            w.destroy()
        for g in items or []:
            row = ctk.CTkFrame(self.list_frame, fg_color=self.theme.get("input_bg", "#2e2e3f"))
            row.pack(fill="x", padx=6, pady=4)
            name = ctk.CTkLabel(row, text=g.get("name", "?"), font=("Segoe UI", 12, "bold"))
            name.pack(side="left", padx=8, pady=6)
            ctk.CTkButton(row, text="Join", width=80,
                          command=lambda inv=g.get("invite_code"), gid=g.get("id"): self._join(inv, gid)).pack(side="right", padx=6)

    def _join(self, invite_code: str | None, group_id: str | None):
        if not invite_code:
            return
        try:
            self.gm.join_group_via_invite(invite_code)
            try:
                # Notify through parent app if available
                parent_app = getattr(self.master, 'app', None) or getattr(self.master, 'app', None)
                if parent_app and hasattr(parent_app, 'notifier'):
                    parent_app.notifier.show("Joined group", type_="success")
            except Exception:
                pass
            self.destroy()
        except Exception:
            pass
