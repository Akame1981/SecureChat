import customtkinter as ctk
import tkinter as tk


class ChannelSettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, app, gm, channel_id: str, channel_name: str, theme: dict | None = None):
        super().__init__(parent)
        self.app = app
        self.gm = gm
        self.cid = channel_id
        self.cname = channel_name
        self.theme = theme or {}
        self.title(f"Channel Settings - #{channel_name}")
        self.geometry("480x420")
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
            pass

        # Permissions view (role-based info)
        role_frame = ctk.CTkFrame(self, fg_color="transparent")
        role_frame.pack(fill="x", padx=10, pady=(10, 6))
        self.role_var = tk.StringVar(value="?")
        ctk.CTkLabel(role_frame, text="Your role:").pack(side="left")
        ctk.CTkEntry(role_frame, textvariable=self.role_var, width=120).pack(side="left", padx=6)
        try:
            # Try to get role for the currently selected group (if parent has it)
            group_id = getattr(getattr(app, 'groups_panel', parent), 'selected_group_id', None)
            info = self.gm.client.get_my_role(group_id) if group_id else None
            if info and info.get("role"):
                self.role_var.set(info.get("role"))
        except Exception:
            pass

        # Topic/Description
        meta_frame = ctk.CTkFrame(self, fg_color="transparent")
        meta_frame.pack(fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(meta_frame, text="Topic").pack(anchor="w")
        self.topic_var = tk.StringVar(value="")
        ctk.CTkEntry(meta_frame, textvariable=self.topic_var, width=420).pack(fill="x", padx=0, pady=(0, 6))
        ctk.CTkLabel(meta_frame, text="Description").pack(anchor="w")
        self.desc = ctk.CTkTextbox(meta_frame, width=420, height=120)
        self.desc.pack(fill="x")

        # Notifications (client-side preference per channel)
        notif_frame = ctk.CTkFrame(self, fg_color="transparent")
        notif_frame.pack(fill="x", padx=10, pady=(10, 6))
        self.notif_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(notif_frame, text="Enable notifications for this channel", variable=self.notif_var).pack(anchor="w")

        # Buttons
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(btns, text="Save", command=self._save).pack(side="left")
        ctk.CTkButton(btns, text="Close", command=self.destroy,
                      fg_color=self.theme.get("cancel_button", "#9a9a9a"),
                      hover_color=self.theme.get("cancel_button_hover", "#7a7a7a")).pack(side="left", padx=6)

        self._hydrate()

    def _hydrate(self):
        # Load meta
        try:
            meta = self.gm.client.get_channel_meta(self.cid)
            if meta:
                self.topic_var.set(meta.get("topic") or "")
                try:
                    self.desc.delete("1.0", tk.END)
                    self.desc.insert("1.0", meta.get("description") or "")
                except Exception:
                    pass
        except Exception:
            pass
        # Load per-channel notif preference from app settings memory (no file write yet)
        try:
            key = f"notif:{self.cid}"
            current = getattr(self.app, "_channel_notifs", {}).get(key, True)
            self.notif_var.set(bool(current))
        except Exception:
            pass

    def _save(self):
        # Save meta to server
        try:
            topic = self.topic_var.get().strip() or None
            desc = self.desc.get("1.0", tk.END).strip() or None
            self.gm.client.set_channel_meta(self.cid, topic, desc)
        except Exception as e:
            try:
                self.app.notifier.show(f"Save failed: {e}", type_="error")
            except Exception:
                pass
            return
        # Save per-channel notif in-memory preference (could be persisted later)
        try:
            if not hasattr(self.app, "_channel_notifs"):
                self.app._channel_notifs = {}
            self.app._channel_notifs[f"notif:{self.cid}"] = bool(self.notif_var.get())
        except Exception:
            pass
        try:
            self.app.notifier.show("Channel settings saved", type_="success")
        except Exception:
            pass
