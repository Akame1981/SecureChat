import customtkinter as ctk
import tkinter as tk
from tkinter import simpledialog, Toplevel
from gui.widgets.group_settings import GroupSettingsDialog

from utils.group_manager import GroupManager
from utils.db import store_my_group_key


class GroupsPanel(ctk.CTkFrame):
    def __init__(self, parent, app, theme: dict | None = None):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.theme = theme or {}
        self.gm = GroupManager(app)

        # State
        self.selected_group_id: str | None = None
        self.selected_channel_id: str | None = None
        self._poll_job = None

        # Left: search + groups list + actions
        left = ctk.CTkFrame(self, fg_color=self.theme.get("sidebar_bg", "#2a2a3a"), width=300)
        left.pack(side="left", fill="y")
        self.left_panel = left

        # Search / join entry
        sframe = ctk.CTkFrame(left, fg_color="transparent")
        sframe.pack(fill="x", padx=8, pady=(8, 4))
        self.search = ctk.CTkEntry(sframe, placeholder_text="Search groups or paste invite code",
                                   fg_color=self.theme.get("input_bg", "#2e2e3f"),
                                   text_color=self.theme.get("input_text", "white"))
        self.search.pack(side="left", expand=True, fill="x")
        ctk.CTkButton(sframe, text="Go", width=50, fg_color=self.theme.get("sidebar_button", "#4a90e2"),
                      hover_color=self.theme.get("sidebar_button_hover", "#357ABD"),
                      command=self._search_or_join).pack(side="left", padx=(6, 0))

        # Actions
        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=4)
        ctk.CTkButton(actions, text="New Group", command=self._create_group,
                      fg_color=self.theme.get("sidebar_button", "#4a90e2"),
                      hover_color=self.theme.get("sidebar_button_hover", "#357ABD")).pack(fill="x", pady=4)
        ctk.CTkButton(actions, text="Discover", command=self._discover_public_modal,
                      fg_color=self.theme.get("sidebar_button", "#4a90e2"),
                      hover_color=self.theme.get("sidebar_button_hover", "#357ABD")).pack(fill="x", pady=4)
        ctk.CTkButton(actions, text="Leave Group", command=self._leave_group,
                      fg_color=self.theme.get("cancel_button", "#9a9a9a"),
                      hover_color=self.theme.get("cancel_button_hover", "#7a7a7a")).pack(fill="x", pady=(4, 8))

        # Groups list
        self.groups_list = ctk.CTkScrollableFrame(left, fg_color=self.theme.get("sidebar_bg", "#2a2a3a"))
        self.groups_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Right: channels (left) + messages (right)
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)
        self.right_panel = right

        # Top bar
        top = ctk.CTkFrame(right, fg_color=self.theme.get("pub_frame_bg", "#2e2e3f"))
        top.pack(fill="x", padx=10, pady=10)
        self.group_title = ctk.CTkLabel(top, text="", anchor="w", justify="left",
                                        text_color=self.theme.get("pub_text", "white"))
        self.group_title.pack(side="left", padx=10, pady=8)
        # Add a quick back-to-DMs button when the main sidebar is hidden in groups mode
        try:
            ctk.CTkButton(top, text="DMs", width=60,
                          command=lambda: getattr(self.app, 'show_direct_messages', lambda: None)(),
                          fg_color=self.theme.get("sidebar_button", "#4a90e2"),
                          hover_color=self.theme.get("sidebar_button_hover", "#357ABD")).pack(side="right", padx=6)
        except Exception:
            pass
        ctk.CTkButton(top, text="Settings", command=self._open_group_settings,
                      fg_color=self.theme.get("button_send", "#4a90e2"),
                      hover_color=self.theme.get("button_send_hover", "#357ABD")).pack(side="right", padx=6)
        ctk.CTkButton(top, text="New Channel", command=self._create_channel,
                      fg_color=self.theme.get("button_send", "#4a90e2"),
                      hover_color=self.theme.get("button_send_hover", "#357ABD")).pack(side="right", padx=6)

        # Body split: channels list (left) and messages (right)
        body = ctk.CTkFrame(right, fg_color="transparent")
        body.pack(fill="both", expand=True)

        self.channels_list = ctk.CTkScrollableFrame(body, fg_color=self.theme.get("background", "#2e2e3f"), width=220)
        self.channels_list.pack(side="left", fill="y", padx=(10, 6), pady=(0, 10))

        center = ctk.CTkFrame(body, fg_color="transparent")
        center.pack(side="left", fill="both", expand=True)

        self.messages = ctk.CTkScrollableFrame(center, fg_color=self.theme.get("background", "#2e2e3f"), corner_radius=10)
        self.messages.pack(fill="both", expand=True, padx=10, pady=10)

        input_frame = ctk.CTkFrame(center, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.input = ctk.CTkEntry(input_frame, placeholder_text="Message #channel",
                                  fg_color=self.theme.get("input_bg", "#2e2e3f"),
                                  text_color=self.theme.get("input_text", "white"))
        self.input.pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(input_frame, text="Send", command=self._send,
                      fg_color=self.theme.get("button_send", "#4a90e2"),
                      hover_color=self.theme.get("button_send_hover", "#357ABD")).pack(side="left")

        # Populate
        self.refresh_groups()

    def set_sidebar_visible(self, visible: bool):
        """Show or hide the built-in left sidebar of this panel.
        Useful when the app's main sidebar is used for groups navigation.
        """
        try:
            if visible:
                if not self.left_panel.winfo_ismapped():
                    self.left_panel.pack(side="left", fill="y")
            else:
                if self.left_panel.winfo_ismapped():
                    self.left_panel.pack_forget()
        except Exception:
            pass

    def refresh_theme(self, theme: dict):
        self.theme = theme or {}
        # Basic recolor
        try:
            self.configure(fg_color="transparent")
        except Exception:
            pass

    # ----- Actions -----
    def _search_or_join(self):
        term = (self.search.get() or "").strip()
        if not term:
            return
        # Try join by invite if looks like a compact code
        if len(term) >= 6 and "://" not in term:
            try:
                res = self.gm.join_group_via_invite(term)
                st = res.get("status")
                if st == "joined":
                    self.app.notifier.show("Joined group", type_="success")
                elif st == "pending":
                    self.app.notifier.show("Join request sent (pending)", type_="info")
                else:
                    self.app.notifier.show(str(res), type_="info")
                self.refresh_groups()
                return
            except Exception:
                # fall through to local filter
                pass
        # Local filter
        self._filter_groups(term)

    def _create_group(self):
        name = simpledialog.askstring("Create Group", "Group name:", parent=self)
        if not name:
            return
        try:
            res = self.gm.create_group(name, is_public=False)
            self.app.notifier.show(f"Group '{name}' created", type_="success")
            self.refresh_groups(select_id=res.get("id"))
        except Exception as e:
            self.app.notifier.show(f"Create failed: {e}", type_="error")

    def _join_by_invite(self):
        code = simpledialog.askstring("Join Group", "Paste invite code:", parent=self)
        if not code:
            return
        try:
            res = self.gm.join_group_via_invite(code)
            st = res.get("status")
            if st == "joined":
                self.app.notifier.show("Joined group", type_="success")
            elif st == "pending":
                self.app.notifier.show("Join request sent (pending)", type_="info")
            else:
                self.app.notifier.show(str(res), type_="info")
            self.refresh_groups()
        except Exception as e:
            self.app.notifier.show(f"Join failed: {e}", type_="error")

    def _discover_public_modal(self):
        try:
            res = self.gm.client.discover_public()
            items = res.get("groups", [])
        except Exception as e:
            self.app.notifier.show(f"Discover failed: {e}", type_="error")
            return
        win = Toplevel(self)
        win.title("Discover Public Groups")
        win.geometry("420x480")
        win.transient(self)
        win.grab_set()

        top = ctk.CTkFrame(win, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=10)
        q = ctk.CTkEntry(top, placeholder_text="Search public groups")
        q.pack(side="left", expand=True, fill="x")
        def do_search():
            try:
                r = self.gm.client.discover_public(query=(q.get() or None))
                self._render_discover_list(list_frame, r.get("groups", []))
            except Exception:
                pass
        ctk.CTkButton(top, text="Search", command=do_search).pack(side="left", padx=6)

        list_frame = ctk.CTkScrollableFrame(win, fg_color=self.theme.get("background", "#2e2e3f"))
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._render_discover_list(list_frame, items)

    def _render_discover_list(self, parent, items: list[dict]):
        for w in parent.winfo_children():
            w.destroy()
        for g in items:
            row = ctk.CTkFrame(parent, fg_color=self.theme.get("input_bg", "#2e2e3f"))
            row.pack(fill="x", padx=6, pady=4)
            name = ctk.CTkLabel(row, text=g.get("name", "?"), font=("Segoe UI", 12, "bold"))
            name.pack(side="left", padx=8, pady=6)
            ctk.CTkButton(row, text="Join", width=80,
                          command=lambda inv=g.get("invite_code"), gid=g.get("id"): self._join_discovered(inv, gid)).pack(side="right", padx=6)

    def _join_discovered(self, invite_code: str | None, group_id: str | None):
        if not invite_code:
            return
        try:
            self.gm.join_group_via_invite(invite_code)
            self.app.notifier.show("Joined group", type_="success")
            self.refresh_groups(select_id=group_id)
        except Exception as e:
            self.app.notifier.show(f"Join failed: {e}", type_="error")

    def _create_channel(self):
        if not self.selected_group_id:
            return
        name = simpledialog.askstring("New Channel", "Channel name:", parent=self)
        if not name:
            return
        try:
            res = self.gm.create_channel(self.selected_group_id, name)
            self._load_channels(self.selected_group_id, select_id=res.get("channel_id"))
        except Exception as e:
            self.app.notifier.show(f"Create channel failed: {e}", type_="error")

    def _send(self):
        txt = (self.input.get() or "").strip()
        if not txt or not self.selected_group_id or not self.selected_channel_id:
            return
        try:
            self.gm.send_text(self.selected_group_id, self.selected_channel_id, txt)
            self._append_message("You", txt)
            self.input.delete(0, tk.END)
        except Exception as e:
            # Attempt key-version recovery on 409 errors
            msg = str(e)
            if "409" in msg or "Key version" in msg:
                try:
                    info = self.gm.client.get_member_keys(self.selected_group_id)
                    kv = int(info.get("key_version", 1))
                    my = next((m for m in info.get("members", []) if m.get("user_id") == self.app.my_pub_hex), None)
                    if my and my.get("encrypted_group_key"):
                        from utils.group_crypto import decrypt_group_key_for_me
                        key = decrypt_group_key_for_me(my["encrypted_group_key"], self.app.private_key)
                        store_my_group_key(self.app.pin, self.selected_group_id, key, kv)
                        # Retry once
                        self.gm.send_text(self.selected_group_id, self.selected_channel_id, txt)
                        self._append_message("You", txt)
                        self.input.delete(0, tk.END)
                        self.app.notifier.show("Recovered new group key", type_="success")
                        return
                except Exception:
                    pass
            self.app.notifier.show(f"Send failed: {e}", type_="error")

    # ----- Lists -----
    def refresh_groups(self, select_id: str | None = None):
        for w in self.groups_list.winfo_children():
            w.destroy()
        try:
            data = self.gm.list_groups()
            groups = data.get("groups", [])
        except Exception:
            groups = []
        for g in groups:
            row = ctk.CTkFrame(self.groups_list, fg_color=self.theme.get("bubble_other", "#2a2a3a"))
            row.pack(fill="x", padx=4, pady=4)
            name = ctk.CTkLabel(row, text=g.get("name"), font=("Segoe UI", 12, "bold"))
            name.pack(side="left", padx=8, pady=6)
            tag_txt = "Public" if g.get("is_public") else "Private"
            tag = ctk.CTkLabel(row, text=tag_txt, fg_color="#3b3b52", corner_radius=8, width=60)
            tag.pack(side="left", padx=6)
            ctk.CTkButton(row, text="Open", width=70,
                          command=lambda gid=g.get("id"), n=g.get("name"): self._select_group(gid, n)).pack(side="right", padx=6)
        if select_id:
            # Find group by id and select
            for g in groups:
                if g.get("id") == select_id:
                    self._select_group(g.get("id"), g.get("name"))
                    break

    def _select_group(self, group_id: str, group_name: str):
        self.selected_group_id = group_id
        self.group_title.configure(text=f"{group_name}")
        self._load_channels(group_id)
        # stop any previous polling
        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None

    def _load_channels(self, group_id: str, select_id: str | None = None):
        for w in self.channels_list.winfo_children():
            w.destroy()
        try:
            data = self.gm.client.list_channels(group_id)
            chans = data.get("channels", [])
        except Exception:
            chans = []
        for ch in chans:
            btn = ctk.CTkButton(self.channels_list, text=f"# {ch.get('name')}",
                                command=lambda cid=ch.get("id"), name=ch.get("name"): self._select_channel(cid, name),
                                fg_color=self.theme.get("input_bg", "#2e2e3f"),
                                hover_color=self.theme.get("bubble_you", "#7289da"))
            btn.pack(fill="x", padx=4, pady=4)
        if select_id:
            for ch in chans:
                if ch.get("id") == select_id:
                    self._select_channel(ch.get("id"), ch.get("name"))
                    break

    def _select_channel(self, channel_id: str, channel_name: str):
        self.selected_channel_id = channel_id
        # Load recent messages for the channel
        for w in self.messages.winfo_children():
            w.destroy()
        try:
            msgs = self.gm.fetch_messages(self.selected_group_id, self.selected_channel_id, since=0)
        except Exception:
            msgs = []
        for m in msgs:
            self._append_message(m.get("sender_id"), m.get("text"))
        # start polling for new messages
        self._schedule_poll()

    def _append_message(self, sender: str, text: str):
        # Simple message card; use app.create_message_bubble if desired later
        bubble = ctk.CTkFrame(self.messages, fg_color=self.theme.get("bubble_other", "#2a2a3a"), corner_radius=10)
        bubble.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(bubble, text=sender, font=("Segoe UI", 11, "bold"),
                     text_color=self.theme.get("sidebar_text", "white")).pack(anchor="w", padx=8, pady=(6, 0))
        ctk.CTkLabel(bubble, text=text, font=("Segoe UI", 12),
                     text_color=self.theme.get("sidebar_text", "white"), wraplength=800, justify="left").pack(anchor="w", padx=8, pady=(0, 8))

    # ----- Helpers -----
    def _schedule_poll(self):
        if not self.selected_group_id or not self.selected_channel_id:
            return
        # poll new messages every 2 seconds
        def _tick():
            try:
                msgs = self.gm.fetch_messages(self.selected_group_id, self.selected_channel_id, since=0)
                # naive: clear and redraw for now; can diff later
                for w in self.messages.winfo_children():
                    w.destroy()
                for m in msgs:
                    self._append_message(m.get("sender_id"), m.get("text"))
            except Exception:
                pass
            self._poll_job = self.after(2000, _tick)
        self._poll_job = self.after(2000, _tick)

    # Ban now handled inside GroupSettingsDialog

    def _leave_group(self):
        if not self.selected_group_id:
            return
        try:
            self.gm.client.leave_group(self.selected_group_id)
            self.app.notifier.show("Left group (members should rekey)", type_="info")
            self.selected_group_id = None
            self.selected_channel_id = None
            self.refresh_groups()
            for w in self.channels_list.winfo_children():
                w.destroy()
            for w in self.messages.winfo_children():
                w.destroy()
        except Exception as e:
            self.app.notifier.show(f"Leave failed: {e}", type_="error")
