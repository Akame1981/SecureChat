import customtkinter as ctk
import tkinter as tk
from tkinter import simpledialog

from utils.group_manager import GroupManager


class GroupsPanel(ctk.CTkFrame):
    def __init__(self, parent, app, theme: dict | None = None):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self.theme = theme or {}
        self.gm = GroupManager(app)

        # Left: groups list + actions
        left = ctk.CTkFrame(self, fg_color=self.theme.get("sidebar_bg", "#2a2a3a"), width=280)
        left.pack(side="left", fill="y")

        # Actions
        actions = ctk.CTkFrame(left, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=8)
        ctk.CTkButton(actions, text="New Group", command=self._create_group,
                      fg_color=self.theme.get("sidebar_button", "#4a90e2"),
                      hover_color=self.theme.get("sidebar_button_hover", "#357ABD")).pack(fill="x", pady=4)
        ctk.CTkButton(actions, text="Join by Invite", command=self._join_by_invite,
                      fg_color=self.theme.get("sidebar_button", "#4a90e2"),
                      hover_color=self.theme.get("sidebar_button_hover", "#357ABD")).pack(fill="x", pady=4)
        ctk.CTkButton(actions, text="Discover Public", command=self._discover_public,
                      fg_color=self.theme.get("sidebar_button", "#4a90e2"),
                      hover_color=self.theme.get("sidebar_button_hover", "#357ABD")).pack(fill="x", pady=4)

        # Groups list
        self.groups_list = ctk.CTkScrollableFrame(left, fg_color=self.theme.get("sidebar_bg", "#2a2a3a"))
        self.groups_list.pack(fill="both", expand=True, padx=8, pady=8)

        # Right: channels and messages
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True)

        # Top: group name + channel actions
        top = ctk.CTkFrame(right, fg_color=self.theme.get("pub_frame_bg", "#2e2e3f"))
        top.pack(fill="x", padx=10, pady=10)
        self.group_title = ctk.CTkLabel(top, text="", anchor="w", justify="left",
                                        text_color=self.theme.get("pub_text", "white"))
        self.group_title.pack(side="left", padx=10, pady=8)
        ctk.CTkButton(top, text="New Channel", command=self._create_channel,
                      fg_color=self.theme.get("button_send", "#4a90e2"),
                      hover_color=self.theme.get("button_send_hover", "#357ABD")).pack(side="right", padx=8)

        # Channels list
        self.channels_list = ctk.CTkScrollableFrame(right, fg_color=self.theme.get("background", "#2e2e3f"),
                                                    height=120, corner_radius=8)
        self.channels_list.pack(fill="x", padx=10, pady=(0, 10))

        # Messages area (reuses app display but isolated here)
        self.messages = ctk.CTkScrollableFrame(right, fg_color=self.theme.get("background", "#2e2e3f"), corner_radius=10)
        self.messages.pack(fill="both", expand=True, padx=10, pady=10)

        # Input area
        input_frame = ctk.CTkFrame(right, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.input = ctk.CTkEntry(input_frame, placeholder_text="Message #channel",
                                  fg_color=self.theme.get("input_bg", "#2e2e3f"),
                                  text_color=self.theme.get("input_text", "white"))
        self.input.pack(side="left", expand=True, fill="x", padx=(0, 6))
        ctk.CTkButton(input_frame, text="Send", command=self._send,
                      fg_color=self.theme.get("button_send", "#4a90e2"),
                      hover_color=self.theme.get("button_send_hover", "#357ABD")).pack(side="left")

        # Selection state
        self.selected_group_id: str | None = None
        self.selected_channel_id: str | None = None

        self.refresh_groups()

    def refresh_theme(self, theme: dict):
        self.theme = theme or {}
        # Basic recolor
        try:
            self.configure(fg_color="transparent")
        except Exception:
            pass

    # ----- Actions -----
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

    def _discover_public(self):
        try:
            res = self.gm.client.discover_public()
            items = res.get("groups", [])
            if not items:
                self.app.notifier.show("No public groups found", type_="info")
                return
            # Simple chooser: show first few and let user pick by index
            names = [f"{i+1}. {g.get('name')} ({g.get('id')[:6]})" for i, g in enumerate(items)]
            choice = simpledialog.askstring("Discover", "Pick number to join:\n" + "\n".join(names[:10]), parent=self)
            if not choice:
                return
            try:
                idx = int(choice) - 1
            except Exception:
                return
            if 0 <= idx < len(items):
                inv = items[idx].get("invite_code")
                if inv:
                    self.gm.join_group_via_invite(inv)
                    self.app.notifier.show("Joined group", type_="success")
                    self.refresh_groups(select_id=items[idx].get("id"))
        except Exception as e:
            self.app.notifier.show(f"Discover failed: {e}", type_="error")

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
            btn = ctk.CTkButton(self.groups_list, text=g.get("name"),
                                command=lambda gid=g.get("id"), name=g.get("name"): self._select_group(gid, name),
                                fg_color=self.theme.get("bubble_other", "#2a2a3a"),
                                hover_color=self.theme.get("bubble_you", "#7289da"))
            btn.pack(fill="x", padx=4, pady=4)
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
            btn.pack(side="left", padx=4, pady=4)
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

    def _append_message(self, sender: str, text: str):
        # Simple message card; use app.create_message_bubble if desired later
        bubble = ctk.CTkFrame(self.messages, fg_color=self.theme.get("bubble_other", "#2a2a3a"), corner_radius=10)
        bubble.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(bubble, text=sender, font=("Segoe UI", 11, "bold"),
                     text_color=self.theme.get("sidebar_text", "white")).pack(anchor="w", padx=8, pady=(6, 0))
        ctk.CTkLabel(bubble, text=text, font=("Segoe UI", 12),
                     text_color=self.theme.get("sidebar_text", "white"), wraplength=800, justify="left").pack(anchor="w", padx=8, pady=(0, 8))
