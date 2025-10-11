import customtkinter as ctk
import tkinter as tk
from tkinter import simpledialog, Toplevel
from datetime import datetime
from gui.widgets.group_settings import GroupSettingsDialog
from gui.widgets.channel_settings import ChannelSettingsDialog
from gui.widgets.discover_dialog import DiscoverDialog
from gui.identicon import generate_identicon
import threading
from utils.recipients import get_recipient_name
from tkinter import messagebox
import os
from tkinter import filedialog
from gui.tooltip import ToolTip
from PIL import Image, ImageEnhance

from utils.group_manager import GroupManager
from utils.db import store_my_group_key, load_my_group_key


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
        # Track last seen timestamp per (group_id, channel_id) for incremental polling
        self._last_ts = {}
        # Channel button widgets for highlighting
        self.channel_buttons = {}
        # Placeholder for empty-state label in messages area
        self._empty_messages_label = None
        # Groups list widgets and avatar cache for sidebar-like styling
        self.group_item_widgets = {}
        self.group_avatar_cache = {}
        # Polling guard
        self._polling = False

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
        self.send_btn = ctk.CTkButton(input_frame, text="Send", command=self._send,
                                      fg_color=self.theme.get("button_send", "#4a90e2"),
                                      hover_color=self.theme.get("button_send_hover", "#357ABD"))
        self.send_btn.pack(side="left")
        # Attachment button for groups (mirrors DM flow)
        try:
            from PIL import Image, ImageEnhance
            attach_path = "gui/src/images/attach_btn.png"
            if attach_path and os.path.exists(attach_path):
                a_img = Image.open(attach_path).resize((28,28), Image.Resampling.LANCZOS)
            else:
                a_img = ImageEnhance.Brightness(Image.new('RGBA', (28,28), (120,120,120))).enhance(0.5)
            attach_icon = ctk.CTkImage(light_image=a_img, dark_image=a_img, size=(28,28))
            attach_btn = ctk.CTkLabel(input_frame, image=attach_icon, text="", fg_color="transparent")
            attach_btn.image = attach_icon
            attach_btn.pack(side="left", padx=(6,4))

            def _do_attach_group(_=None):
                if not self.selected_group_id or not self.selected_channel_id:
                    try:
                        self.app.notifier.show("Select a channel first", type_="warning")
                    except Exception:
                        pass
                    return
                paths = tk.filedialog.askopenfilenames(title="Select files to send to group")
                for p in paths:
                    if not p:
                        continue
                    try:
                        sz = os.path.getsize(p)
                        max_size = 10 * 1024 * 1024  # 10MB guard for groups
                        if sz > max_size:
                            try:
                                self.app.notifier.show(f"Skip {os.path.basename(p)} (>10MB)", type_="warning")
                            except Exception:
                                pass
                            continue
                        with open(p, 'rb') as f:
                            data = f.read()
                        # Show placeholder immediately
                        human = self.gm.app.chat_manager._human_size(len(data)) if hasattr(self.gm.app, 'chat_manager') else f"{len(data)} bytes"
                        placeholder = f"[Attachment] {os.path.basename(p)} ({human})"
                        ts = __import__('time').time()
                        # Create deterministic id for placeholder
                        import hashlib
                        att_id = hashlib.sha256(data).hexdigest()
                        meta = {"name": os.path.basename(p), "size": len(data), "att_id": att_id, "type": "file"}
                        # Save locally in attachment store
                        try:
                            from utils.attachments import store_attachment
                            store_attachment(data, getattr(self.app, 'pin', ''))
                        except Exception:
                            pass
                        # Append placeholder message UI (include group context so save action knows where to download)
                        meta['group_id'] = self.selected_group_id
                        self._append_message("You", placeholder, ts, attachment_meta=meta)

                        # Background upload and send
                        def _bg():
                            try:
                                # Upload raw encrypted blob to groups backend; GroupClient will compute id
                                uploaded = self.gm.client.upload_attachment(self.selected_group_id, data)
                                aid = uploaded.get('id') if isinstance(uploaded, dict) else None
                                if not aid:
                                    try:
                                        self.app.notifier.show(f"Upload failed for {os.path.basename(p)}", type_="error")
                                    except Exception:
                                        pass
                                    return
                                # Send group message with attachment metadata (the message text can be empty or a caption)
                                from utils.group_crypto import encrypt_text_with_group_key
                                # Load my stored group key
                                from utils.db import load_my_group_key
                                loaded = load_my_group_key(self.app.pin, self.selected_group_id)
                                if not loaded:
                                    try:
                                        self.app.notifier.show("No group key available", type_="error")
                                    except Exception:
                                        pass
                                    return
                                key, kv = loaded
                                # Build envelope as in recipient flow: ATTACH:{{json}}
                                import json as _json
                                envelope = {"type": "file", "name": os.path.basename(p), "att_id": aid, "size": len(data)}
                                plaintext = "ATTACH:" + _json.dumps(envelope, separators=(',', ':'))
                                ct_b64, nonce_b64 = encrypt_text_with_group_key(plaintext, key)
                                # Send via group manager client
                                self.gm.client.send_message(self.selected_group_id, self.selected_channel_id, ct_b64, nonce_b64, kv, timestamp=ts)
                            except Exception as e:
                                try:
                                    self.app.notifier.show(f"Attachment send failed: {e}", type_="error")
                                except Exception:
                                    pass

                        threading.Thread(target=_bg, daemon=True).start()
                    except Exception as e:
                        print('Group attach error', e)
                        try:
                            self.app.notifier.show('Attachment error', type_='error')
                        except Exception:
                            pass

            attach_btn.bind('<Button-1>', _do_attach_group)
            ToolTip(attach_btn, 'Send attachment to channel')
        except Exception:
            pass
        # Disable send until a channel is selected
        try:
            self.send_btn.configure(state="disabled")
        except Exception:
            pass
        # Enter key sends message
        try:
            self.input.bind("<Return>", lambda e: self._send())
        except Exception:
            pass

        # Populate
        self.refresh_groups()

    def _filter_groups(self, term: str):
        """Filter groups by name locally and re-render the list with sidebar-like styling without blocking UI."""
        term_lower = (term or "").lower()

        def work():
            try:
                data = self.gm.list_groups()
                return data.get("groups", [])
            except Exception:
                return []

        def done(groups):
            filtered = [g for g in (groups or []) if term_lower in (g.get("name", "").lower())]
            self._render_group_list(self.groups_list, filtered)

        self._run_bg(work, done)

    def _render_group_list(self, parent, groups: list[dict]):
        # Clear old
        for w in parent.winfo_children():
            w.destroy()
        self.group_item_widgets.clear()
        # Colors
        sel_bg = self.theme.get("bubble_you", "#7289da")
        item_bg = self.theme.get("bubble_other", "#2a2a3a")
        text_color = self.theme.get("sidebar_text", "white")
        avatar_bg = self.theme.get("sidebar_button", "#4a90e2")

        if not groups:
            ctk.CTkLabel(parent, text="No groups",
                         text_color=text_color).pack(pady=8)
            return

        for g in groups:
            gid = g.get("id")
            gname = g.get("name")
            is_sel = (gid == self.selected_group_id)
            row = ctk.CTkFrame(parent,
                               fg_color=sel_bg if is_sel else item_bg,
                               corner_radius=12, height=40)
            row.pack(fill="x", padx=6, pady=4)
            self.group_item_widgets[gid] = row

            # Avatar identicon
            avatar_label = None
            ident_size = 28
            try:
                if gid not in self.group_avatar_cache:
                    pil_img = generate_identicon(gid or gname or "?", size=ident_size)
                    ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(ident_size, ident_size))
                    self.group_avatar_cache[gid] = ctk_img
                ctk_img = self.group_avatar_cache[gid]
                avatar_label = ctk.CTkLabel(row, image=ctk_img, text="",
                                            width=ident_size, height=ident_size)
                avatar_label.image = ctk_img
            except Exception:
                avatar_label = ctk.CTkLabel(
                    row, text=(gname or "?")[0].upper(), width=28, height=28,
                    fg_color=avatar_bg, text_color=text_color, corner_radius=14
                )
            avatar_label.pack(side="left", padx=8, pady=4)

            # Name label
            label = ctk.CTkLabel(row, text=gname, font=("Segoe UI", 12, "bold"),
                                 text_color=text_color)
            label.pack(side="left", padx=6)

            # Visibility tag (Public/Private)
            tag_txt = "Public" if g.get("is_public") else "Private"
            tag = ctk.CTkLabel(row, text=tag_txt, fg_color="#3b3b52", corner_radius=8)
            tag.pack(side="right", padx=8, pady=6)

            # Click bindings for the whole row
            row.bind("<Button-1>", lambda e, gid=gid, n=gname: self._select_group(gid, n))
            avatar_label.bind("<Button-1>", lambda e, gid=gid, n=gname: self._select_group(gid, n))
            label.bind("<Button-1>", lambda e, gid=gid, n=gname: self._select_group(gid, n))

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
        def on_join(group_id: str | None):
            try:
                self.refresh_groups(select_id=group_id)
            except Exception:
                pass
        try:
            DiscoverDialog(self, self.app, self.gm, self.theme, on_join=on_join)
        except Exception as e:
            try:
                self.app.notifier.show(f"Discover failed: {e}", type_="error")
            except Exception:
                pass

    def _open_group_settings(self):
        # Open the dedicated Group Settings dialog for the selected group
        if not self.selected_group_id:
            return
        try:
            GroupSettingsDialog(self, self.app, self.gm, self.selected_group_id, self.theme)
        except Exception as e:
            try:
                self.app.notifier.show(f"Failed to open settings: {e}", type_="error")
            except Exception:
                pass

    # discover list rendering moved to DiscoverDialog

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
        # show loading
        for w in self.groups_list.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.groups_list, text="Loading…",
                     text_color=self.theme.get("sidebar_text", "white")).pack(pady=8)

        def work():
            try:
                return self.gm.list_groups()
            except Exception:
                return {"groups": []}

        def done(res):
            groups = res.get("groups", []) if isinstance(res, dict) else []
            self._render_group_list(self.groups_list, groups)
            if select_id:
                for g in groups:
                    if g.get("id") == select_id:
                        self._select_group(g.get("id"), g.get("name"))
                        break

        self._run_bg(work, done)

    def _select_group(self, group_id: str, group_name: str):
        self.selected_group_id = group_id
        # Highlight selected group in the left list
        self._highlight_group_item(group_id)
        self.group_title.configure(text=f"{group_name}")
        self._load_channels(group_id)
        # stop any previous polling
        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None

    def _highlight_group_item(self, group_id: str):
        sel_bg = self.theme.get("bubble_you", "#7289da")
        item_bg = self.theme.get("bubble_other", "#2a2a3a")
        try:
            for gid, row in self.group_item_widgets.items():
                row.configure(fg_color=sel_bg if gid == group_id else item_bg)
        except Exception:
            pass

    def _load_channels(self, group_id: str, select_id: str | None = None):
        for w in self.channels_list.winfo_children():
            w.destroy()
        self.channel_buttons.clear()
        ctk.CTkLabel(self.channels_list, text="Loading channels…",
                     text_color=self.theme.get("sidebar_text", "white")).pack(pady=6)

        def work():
            try:
                return self.gm.client.list_channels(group_id)
            except Exception:
                return {"channels": []}

        def done(data):
            for w in self.channels_list.winfo_children():
                w.destroy()
            chans = data.get("channels", []) if isinstance(data, dict) else []
            if not chans:
                ctk.CTkLabel(self.channels_list, text="No channels",
                             text_color=self.theme.get("sidebar_text", "white")).pack(pady=6)
                return
            for ch in chans:
                cid = ch.get("id")
                cname = ch.get("name")
                btn = ctk.CTkButton(self.channels_list, text=f"# {cname}",
                                    command=lambda cid=cid, name=cname: self._select_channel(cid, name),
                                    fg_color=self.theme.get("input_bg", "#2e2e3f"),
                                    hover_color=self.theme.get("bubble_you", "#7289da"))
                btn.pack(fill="x", padx=4, pady=4)
                # Bind right-click for context menu
                try:
                    btn.bind("<Button-3>", lambda e, cid=cid, cname=cname, b=btn: self._open_channel_menu(e, cid, cname, b))
                except Exception:
                    pass
                self.channel_buttons[cid] = btn
            if select_id:
                for ch in chans:
                    if ch.get("id") == select_id:
                        self._select_channel(ch.get("id"), ch.get("name"))
                        break
            elif chans:
                self._select_channel(chans[0].get("id"), chans[0].get("name"))

        self._run_bg(work, done)

    def _select_channel(self, channel_id: str, channel_name: str):
        self.selected_channel_id = channel_id
        # Enable send button and set placeholder
        try:
            self.send_btn.configure(state="normal")
            self.input.configure(placeholder_text=f"Message #{channel_name}")
        except Exception:
            pass
        # Highlight selected channel button
        self._highlight_channel_btn(channel_id)
        # Load recent messages for the channel in background
        for w in self.messages.winfo_children():
            w.destroy()
        self._show_empty_messages("Loading messages…")

        def work():
            try:
                return self.gm.fetch_messages(self.selected_group_id, self.selected_channel_id, since=0)
            except Exception:
                return []

        def done(msgs):
            for w in self.messages.winfo_children():
                w.destroy()
            msgs = msgs or []
            if not msgs:
                self._show_empty_messages("No messages yet")
            else:
                self._clear_empty_messages()
                last_ts = 0.0
                for m in msgs:
                    # Attach group_id into attachment_meta so message renderer can use groups download endpoint
                    att = m.get("attachment_meta")
                    # If no attachment_meta but text is an ATTACH envelope, parse it so UI shows a nice placeholder
                    txt = m.get("text")
                    if not att and isinstance(txt, str) and txt.startswith("ATTACH:"):
                        try:
                            from utils.attachment_envelope import parse_attachment_envelope
                            placeholder, parsed = parse_attachment_envelope(txt)
                            if parsed:
                                att = parsed
                                # replace text with placeholder for display
                                m["text"] = placeholder or m.get("text")
                        except Exception:
                            att = None
                    if isinstance(att, dict):
                        try:
                            att = dict(att)
                            att["group_id"] = self.selected_group_id
                        except Exception:
                            pass
                    self._append_message(m.get("sender_id"), m.get("text"), m.get("timestamp"), attachment_meta=att)
                    try:
                        last_ts = max(last_ts, float(m.get("timestamp") or 0))
                    except Exception:
                        pass
                self._last_ts[(self.selected_group_id, self.selected_channel_id)] = last_ts
            self._schedule_poll()

        self._run_bg(work, done)

    def _append_message(self, sender: str, text: str, ts: float | None = None, attachment_meta: dict | None = None):
        try:
            # Normalize text: if this is an attachment message, prefer a friendly filename placeholder
            display_text = text
            # If attachment_meta omitted but text contains ATTACH: envelope, try to parse it
            if not attachment_meta and isinstance(text, str) and text.startswith("ATTACH:"):
                try:
                    from utils.attachment_envelope import parse_attachment_envelope
                    placeholder, parsed = parse_attachment_envelope(text)
                    if parsed:
                        attachment_meta = parsed
                        display_text = placeholder or display_text
                except Exception:
                    pass

            # If we have attachment_meta with a name, show that instead of raw ATTACH JSON
            if attachment_meta and isinstance(attachment_meta, dict):
                try:
                    name = attachment_meta.get('name')
                    size = int(attachment_meta.get('size') or 0)
                    if name and (not display_text or display_text.startswith('ATTACH:')):
                        # human-readable size
                        def _human_size(n: int) -> str:
                            units = ["B", "KB", "MB", "GB", "TB"]
                            f = float(n)
                            for u in units:
                                if f < 1024 or u == units[-1]:
                                    return f"{f:.1f} {u}"
                                f /= 1024
                            return f"{n} B"
                        display_text = f"[Attachment] {name} ({_human_size(size)})"
                except Exception:
                    pass

            # Use central styling logic so attachments render inline where supported
            from gui.message_styling import create_message_bubble
            bubble = create_message_bubble(self.messages, sender, display_text, self.app.my_pub_hex, self.app.pin, app=self.app, timestamp=ts, attachment_meta=attachment_meta)
            # If this message has an attachment, add an explicit right-click 'Download Attachment' entry
            try:
                if attachment_meta and isinstance(attachment_meta, dict) and attachment_meta.get('type', 'file') == 'file':
                    def _download_attachment(ev=None):
                        try:
                            raw = None
                            att_id = attachment_meta.get('att_id')
                            if att_id:
                                try:
                                    from utils.attachments import load_attachment, AttachmentNotFound
                                    raw = load_attachment(att_id, self.app.pin)
                                except AttachmentNotFound:
                                    # Try to stream from groups attachments endpoint
                                    try:
                                        import requests
                                        g_id = attachment_meta.get('group_id') or self.selected_group_id
                                        r = requests.get(f"{self.app.SERVER_URL}/groups/attachments/{att_id}", params={"group_id": g_id, "user_id": self.app.my_pub_hex}, verify=getattr(self.app, 'SERVER_CERT', None), timeout=60)
                                        if r.ok:
                                            raw = r.content
                                        else:
                                            try:
                                                messagebox.showerror("Attachment", f"Download failed: {r.status_code}")
                                            except Exception:
                                                pass
                                            return
                                    except Exception as de:
                                        try:
                                            messagebox.showerror("Attachment", f"Download error: {de}")
                                        except Exception:
                                            pass
                                        return
                            else:
                                try:
                                    messagebox.showerror("Attachment", "Missing attachment id")
                                except Exception:
                                    pass
                                return
                            # Prompt save
                            default_name = attachment_meta.get('name', 'file')
                            path = filedialog.asksaveasfilename(defaultextension='', initialfile=default_name)
                            if path and raw is not None:
                                with open(path, 'wb') as f:
                                    f.write(raw)
                                try:
                                    self.app.notifier.show(f"Saved {default_name}")
                                except Exception:
                                    pass
                        except Exception as e:
                            print('Attachment download failed', e)
                            try:
                                messagebox.showerror('Attachment', 'Failed to download attachment')
                            except Exception:
                                pass

                    # Add context menu and bind
                    try:
                        menu = tk.Menu(bubble, tearoff=0)
                        menu.add_command(label='Download Attachment', command=_download_attachment)
                        def _popup(ev):
                            try:
                                menu.tk_popup(ev.x_root, ev.y_root)
                            finally:
                                menu.grab_release()
                        # Bind right click on the bubble frame and its message label if present
                        try:
                            bubble.bind('<Button-3>', _popup)
                        except Exception:
                            pass
                        try:
                            bubble.msg_label.bind('<Button-3>', _popup)
                        except Exception:
                            pass
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            # Fallback to simple rendering
            bubble = ctk.CTkFrame(self.messages, fg_color=self.theme.get("bubble_other", "#2a2a3a"), corner_radius=10)
            bubble.pack(fill="x", padx=8, pady=4)
            stamp = ""
            try:
                if ts:
                    stamp = datetime.fromtimestamp(float(ts)).strftime("%H:%M")
            except Exception:
                stamp = ""
            display = self._resolve_sender_display(sender)
            header = f"{display}  {stamp}" if stamp else display
            ctk.CTkLabel(bubble, text=header, font=("Segoe UI", 11, "bold"),
                         text_color=self.theme.get("sidebar_text", "white")).pack(anchor="w", padx=8, pady=(6, 0))
            ctk.CTkLabel(bubble, text=text, font=("Segoe UI", 12),
                         text_color=self.theme.get("sidebar_text", "white"), wraplength=800, justify="left").pack(anchor="w", padx=8, pady=(0, 8))

    def _open_channel_menu(self, event, channel_id: str, channel_name: str, btn_widget):
        try:
            # Determine my role to enable/disable destructive items
            my_role = None
            try:
                info = self.gm.client.get_my_role(self.selected_group_id)
                my_role = (info or {}).get("role")
            except Exception:
                my_role = None
            is_admin = my_role in ("owner", "admin")

            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Open", command=lambda: self._select_channel(channel_id, channel_name))
            menu.add_command(label="Rename…", command=lambda: self._rename_channel_prompt(channel_id, channel_name), state=("normal" if is_admin else "disabled"))
            menu.add_command(label="Delete…", command=lambda: self._delete_channel_confirm(channel_id, channel_name), state=("normal" if is_admin else "disabled"))
            menu.add_separator()
            menu.add_command(label="Channel Settings", command=lambda: self._open_channel_settings(channel_id, channel_name))
            # Show at mouse position
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
        except Exception as e:
            try:
                self.app.notifier.show(f"Menu error: {e}", type_="error")
            except Exception:
                pass

    def _rename_channel_prompt(self, channel_id: str, old_name: str):
        try:
            new_name = simpledialog.askstring("Rename Channel", f"Rename '{old_name}' to:", parent=self)
            if not new_name:
                return
            self.gm.client.rename_channel(channel_id, new_name)
            # Refresh channels
            if self.selected_group_id:
                self._load_channels(self.selected_group_id)
            self.app.notifier.show("Channel renamed", type_="success")
        except Exception as e:
            try:
                self.app.notifier.show(f"Rename failed: {e}", type_="error")
            except Exception:
                pass

    def _delete_channel_confirm(self, channel_id: str, cname: str):
        try:
            # Proper confirm modal
            ok = messagebox.askyesno("Delete Channel", f"Are you sure you want to delete '#{cname}'? This cannot be undone.")
            if not ok:
                return
            self.gm.client.delete_channel(channel_id)
            # If we deleted the selected channel, clear selection
            if self.selected_channel_id == channel_id:
                self.selected_channel_id = None
                for w in self.messages.winfo_children():
                    w.destroy()
            # Refresh
            if self.selected_group_id:
                self._load_channels(self.selected_group_id)
            self.app.notifier.show("Channel deleted", type_="success")
        except Exception as e:
            try:
                self.app.notifier.show(f"Delete failed: {e}", type_="error")
            except Exception:
                pass

    def _open_channel_settings(self, channel_id: str, channel_name: str):
        try:
            ChannelSettingsDialog(self, self.app, self.gm, channel_id, channel_name, self.theme)
        except Exception as e:
            try:
                self.app.notifier.show(f"Failed to open channel settings: {e}", type_="error")
            except Exception:
                pass

    def _resolve_sender_display(self, sender_id: str | None) -> str:
        try:
            if not sender_id:
                return "?"
            # Map my own key to my username (from PIN dialog), fallback to "You"
            if hasattr(self.app, 'my_pub_hex') and sender_id == getattr(self.app, 'my_pub_hex', ''):
                uname = getattr(self.app, 'username', None)
                return uname or "You"
            if sender_id == "You":
                uname = getattr(self.app, 'username', None)
                return uname or "You"
            # Resolve from local recipients
            name = None
            try:
                name = get_recipient_name(sender_id, getattr(self.app, 'pin', ''))
            except Exception:
                name = None
            if name:
                return name
            # Fallback: short key
            sid = str(sender_id)
            return f"{sid[:8]}…" if len(sid) > 9 else sid
        except Exception:
            return str(sender_id) if sender_id else "?"

    # ----- Helpers -----
    def _schedule_poll(self):
        if not self.selected_group_id or not self.selected_channel_id:
            return
        # poll new messages every 2 seconds
        def _tick():
            if self._polling:
                self._poll_job = self.after(2000, _tick)
                return
            self._polling = True
            key = (self.selected_group_id, self.selected_channel_id)
            since = self._last_ts.get(key, 0) or 0

            def work():
                try:
                    return self.gm.fetch_messages(self.selected_group_id, self.selected_channel_id, since=since)
                except Exception:
                    return []

            def done(msgs):
                try:
                    if msgs:
                        self._clear_empty_messages()
                        for m in msgs:
                            att = m.get("attachment_meta")
                            if isinstance(att, dict):
                                try:
                                    att = dict(att)
                                    att["group_id"] = self.selected_group_id
                                except Exception:
                                    pass
                            self._append_message(m.get("sender_id"), m.get("text"), m.get("timestamp"), attachment_meta=att)
                            try:
                                tval = float(m.get("timestamp") or 0)
                                self._last_ts[key] = max(self._last_ts.get(key, 0) or 0, tval)
                            except Exception:
                                pass
                finally:
                    self._polling = False
                    self._poll_job = self.after(2000, _tick)

            self._run_bg(work, done)

        self._poll_job = self.after(2000, _tick)

    def _run_bg(self, func, callback):
        """Run blocking work in a daemon thread and call callback(result) on UI thread."""
        def runner():
            try:
                res = func()
            except Exception as e:
                res = e
            self.after(0, lambda: callback(res) if callable(callback) else None)
        t = threading.Thread(target=runner, daemon=True)
        t.start()

    def _highlight_channel_btn(self, channel_id: str):
        try:
            for cid, btn in self.channel_buttons.items():
                if cid == channel_id:
                    btn.configure(fg_color=self.theme.get("bubble_you", "#7289da"))
                else:
                    btn.configure(fg_color=self.theme.get("input_bg", "#2e2e3f"))
        except Exception:
            pass

    def _show_empty_messages(self, text: str):
        self._clear_empty_messages()
        try:
            self._empty_messages_label = ctk.CTkLabel(self.messages, text=text,
                                                     text_color=self.theme.get("sidebar_text", "white"))
            self._empty_messages_label.pack(pady=10)
        except Exception:
            pass

    def _clear_empty_messages(self):
        try:
            if self._empty_messages_label is not None:
                self._empty_messages_label.destroy()
                self._empty_messages_label = None
        except Exception:
            pass



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
