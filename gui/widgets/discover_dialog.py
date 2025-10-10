import customtkinter as ctk
import tkinter as tk
from gui.identicon import generate_identicon


class DiscoverDialog(ctk.CTkToplevel):
    def __init__(self, parent, app, gm, theme: dict | None = None, on_join=None):
        super().__init__(parent)
        self.app = app
        self.gm = gm
        self.theme = theme or {}
        self.on_join = on_join
        self.avatar_cache = {}
        self._search_after = None

        self.title("Discover Public Groups")
        self.geometry("520x560")
        self.transient(parent)
        self.grab_set()

        # Top controls
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=10)
        self.q = ctk.CTkEntry(top, placeholder_text="Search public groups",
                              fg_color=self.theme.get("input_bg", "#2e2e3f"))
        self.q.pack(side="left", expand=True, fill="x")
        self.q.bind("<KeyRelease>", self._schedule_search)
        ctk.CTkButton(top, text="Search", command=self._do_search,
                      fg_color=self.theme.get("sidebar_button", "#4a90e2"),
                      hover_color=self.theme.get("sidebar_button_hover", "#357ABD")).pack(side="left", padx=6)
        ctk.CTkButton(top, text="Close", command=self.destroy,
                      fg_color=self.theme.get("cancel_button", "#9a9a9a"),
                      hover_color=self.theme.get("cancel_button_hover", "#7a7a7a")).pack(side="left")

        # Status
        self.status_var = tk.StringVar(value="")
        self.status = ctk.CTkLabel(self, textvariable=self.status_var,
                                   text_color=self.theme.get("sidebar_text", "white"))
        self.status.pack(fill="x", padx=12)

        # List
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color=self.theme.get("background", "#2e2e3f"))
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=(6, 10))

        # Load initial in background
        self._load_initial()

    # ----- UI helpers -----
    def _set_status(self, msg: str):
        try:
            self.status_var.set(msg or "")
        except Exception:
            pass

    def _set_loading(self, loading: bool):
        self._set_status("Loading…" if loading else "")

    def _schedule_search(self, _event=None):
        try:
            if self._search_after:
                self.after_cancel(self._search_after)
        except Exception:
            pass
        self._search_after = self.after(400, self._do_search)

    # ----- Data loading -----
    def _load_initial(self):
        def work():
            try:
                return self.gm.client.discover_public()
            except Exception as e:
                return e

        def done(res):
            if isinstance(res, Exception):
                self._set_status(f"Failed to load: {res}")
                return
            items = (res or {}).get("groups", [])
            self._render_items(items)
            self._set_status(f"{len(items)} result(s)")

        self._set_loading(True)
        self._run_bg(work, done)

    def _do_search(self):
        query = (self.q.get() or None)

        def work():
            try:
                return self.gm.client.discover_public(query=query)
            except Exception as e:
                return e

        def done(res):
            if isinstance(res, Exception):
                self._set_status(f"Search failed: {res}")
                return
            items = (res or {}).get("groups", [])
            self._render_items(items)
            self._set_status(f"{len(items)} result(s)")

        self._set_loading(True)
        self._run_bg(work, done)

    def _run_bg(self, func, callback):
        def runner():
            try:
                res = func()
            except Exception as e:
                res = e
            self.after(0, lambda: callback(res) if callable(callback) else None)
        import threading
        threading.Thread(target=runner, daemon=True).start()

    # ----- Rendering -----
    def _render_items(self, items):
        for w in self.list_frame.winfo_children():
            w.destroy()
        if not items:
            ctk.CTkLabel(self.list_frame, text="No public groups found",
                         text_color=self.theme.get("sidebar_text", "white")).pack(pady=12)
            return
        for g in items or []:
            gid = g.get("id")
            name = g.get("name", "?")
            invite = g.get("invite_code")

            row = ctk.CTkFrame(self.list_frame, fg_color=self.theme.get("input_bg", "#2e2e3f"), corner_radius=12)
            row.pack(fill="x", padx=6, pady=6)

            # Avatar
            avatar_label = None
            try:
                if gid not in self.avatar_cache:
                    pil_img = generate_identicon(gid or name or "?", size=26)
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(26, 26))
                    self.avatar_cache[gid] = ctk_img
                ctk_img = self.avatar_cache[gid]
                avatar_label = ctk.CTkLabel(row, image=ctk_img, text="", width=26, height=26)
                avatar_label.image = ctk_img
            except Exception:
                avatar_label = ctk.CTkLabel(row, text=name[:1].upper(), width=26, height=26,
                                            fg_color=self.theme.get("sidebar_button", "#4a90e2"), corner_radius=13)
            avatar_label.pack(side="left", padx=8, pady=6)

            # Name + meta
            col = ctk.CTkFrame(row, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(col, text=name, font=("Segoe UI", 12, "bold"),
                         text_color=self.theme.get("sidebar_text", "white")).pack(anchor="w", pady=(6, 0))
            sub = f"{gid[:8]}…" if gid and len(gid) > 9 else (gid or "")
            ctk.CTkLabel(col, text=sub, font=("Segoe UI", 10),
                         text_color=self.theme.get("pub_text", "#cfcfe1")).pack(anchor="w", pady=(0, 6))

            # Actions
            actions = ctk.CTkFrame(row, fg_color="transparent")
            actions.pack(side="right", padx=8)
            join_state = "normal" if invite else "disabled"
            ctk.CTkButton(actions, text="Join", width=70, state=join_state,
                          command=lambda inv=invite, gid=gid: self._join(inv, gid)).pack(side="left", padx=4, pady=6)
            ctk.CTkButton(actions, text="Copy", width=60,
                          command=lambda inv=invite: self._copy_invite(inv),
                          fg_color=self.theme.get("button_send", "#4a90e2"),
                          hover_color=self.theme.get("button_send_hover", "#357ABD")).pack(side="left", padx=4, pady=6)

    # ----- Actions -----
    def _copy_invite(self, invite_code: str | None):
        if not invite_code:
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(invite_code)
            if hasattr(self.app, 'notifier'):
                self.app.notifier.show("Invite copied", type_="info")
        except Exception:
            pass

    def _join(self, invite_code: str | None, group_id: str | None):
        if not invite_code:
            return
        def work():
            try:
                return self.gm.join_group_via_invite(invite_code)
            except Exception as e:
                return e
        def done(res):
            if isinstance(res, Exception):
                try:
                    if hasattr(self.app, 'notifier'):
                        self.app.notifier.show(f"Join failed: {res}", type_="error")
                except Exception:
                    pass
                return
            status = (res or {}).get('status')
            if status == 'joined':
                try:
                    if hasattr(self.app, 'notifier'):
                        self.app.notifier.show("Joined group", type_="success")
                except Exception:
                    pass
                try:
                    if callable(self.on_join):
                        self.on_join(group_id)
                except Exception:
                    pass
                self.destroy()
            elif status == 'pending':
                try:
                    if hasattr(self.app, 'notifier'):
                        self.app.notifier.show("Join request sent (pending)", type_="info")
                except Exception:
                    pass
            else:
                try:
                    if hasattr(self.app, 'notifier'):
                        self.app.notifier.show(str(res), type_="info")
                except Exception:
                    pass
        self._set_loading(True)
        self._run_bg(work, done)
