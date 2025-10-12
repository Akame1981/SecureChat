import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox


class GroupSettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, app, group_manager, group_id: str, theme: dict | None = None):
        super().__init__(parent)
        self.app = app
        self.gm = group_manager
        self.gid = group_id
        self.theme = theme or {}

        self.title("Group Settings")
        self.geometry("720x540")
        self.transient(parent)
        # initialize control variables early so layout can reference them
        self.code_var = tk.StringVar(value="...")
        self.name_var = tk.StringVar(value="")
        self.is_public_var = tk.BooleanVar(value=False)
        self.appr_var = tk.StringVar(value="")
        self.chan_var = tk.StringVar(value="")
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

        # Fetch current name/code early so UI can show them immediately
        try:
            self._hydrate_public_and_name()
        except Exception:
            pass

        # Top header: big group title and invite code
        header = ctk.CTkFrame(self, fg_color=self.theme.get('pub_frame_bg', '#2e2e3f'))
        header.pack(fill='x', padx=12, pady=12)
        # Title + actions
        left_h = ctk.CTkFrame(header, fg_color='transparent')
        left_h.pack(side='left', fill='both', expand=True)
        self.title_label = ctk.CTkLabel(left_h, text=(self.name_var.get() or 'Group'), font=('Roboto', 18, 'bold'), anchor='w')
        self.title_label.pack(anchor='w')
        # small subtitle line
        self.subtitle = ctk.CTkLabel(left_h, text=f"ID: {self.gid[:12]}…", font=('Roboto', 10), text_color=self.theme.get('muted_text', '#a0a0a0'))
        self.subtitle.pack(anchor='w', pady=(4,0))

        right_h = ctk.CTkFrame(header, fg_color='transparent')
        right_h.pack(side='right')
        # code_var already initialized above
        self.code_entry = ctk.CTkEntry(right_h, textvariable=self.code_var, width=220, height=30)
        self.code_entry.pack(side='left', padx=(0,8))
        ctk.CTkButton(right_h, text='Copy', width=80, corner_radius=8, command=self._copy_code, fg_color=self.theme.get('button_send', '#4a90e2')).pack(side='left')
        ctk.CTkButton(right_h, text='Rotate', width=80, corner_radius=8, command=self._rotate_invite).pack(side='left', padx=(8,0))

        # Main body: two columns (left: controls, right: members)
        # Use a scrollable frame so long settings lists fit smaller windows while
        # keeping header/footer fixed.
        body = ctk.CTkScrollableFrame(self, fg_color='transparent')
        body.pack(fill='both', expand=True, padx=12, pady=(6,12))

        left_col = ctk.CTkFrame(body, fg_color='transparent')
        left_col.pack(side='left', fill='both', expand=True, padx=(0,8))
        right_col = ctk.CTkFrame(body, fg_color='transparent', width=320)
        right_col.pack(side='right', fill='y')

        # Controls group
        grp = ctk.CTkFrame(left_col, fg_color=self.theme.get('input_bg', '#2e2e3f'), corner_radius=8)
        grp.pack(fill='x', pady=(0,8))
        grp.pack_propagate(False)
        # Group rename row
        row = ctk.CTkFrame(grp, fg_color='transparent')
        row.pack(fill='x', padx=10, pady=10)
        ctk.CTkLabel(row, text='Group Name', font=('Roboto', 10, 'bold')).pack(anchor='w')
        self.name_var = tk.StringVar(value=self.name_var.get() if hasattr(self, 'name_var') else '')
        self.name_entry = ctk.CTkEntry(row, textvariable=self.name_var, width=360)
        self.name_entry.pack(anchor='w', pady=(6,0))

        # Public toggle and rekey
        row2 = ctk.CTkFrame(grp, fg_color='transparent')
        row2.pack(fill='x', padx=10, pady=10)
        self.is_public_var = tk.BooleanVar(value=bool(self.is_public_var.get() if hasattr(self, 'is_public_var') else False))
        ctk.CTkLabel(row2, text='Discoverable').pack(side='left')
        self.public_switch = ctk.CTkSwitch(row2, text='', variable=self.is_public_var, command=self._toggle_public)
        self.public_switch.pack(side='left', padx=12)
        ctk.CTkButton(row2, text='Force Rekey', width=120, command=self._rekey_group).pack(side='right')

        # Server distribute setting: whether server distributes member keys
        row3 = ctk.CTkFrame(grp, fg_color='transparent')
        row3.pack(fill='x', padx=10, pady=(0,10))
        self.server_dist_var = tk.BooleanVar(value=False)
        ctk.CTkLabel(row3, text='Server distributes keys').pack(side='left')
        self.server_dist_switch = ctk.CTkSwitch(row3, text='', variable=self.server_dist_var)
        self.server_dist_switch.pack(side='left', padx=(8,0))

        # Approvals
        appr_card = ctk.CTkFrame(left_col, fg_color=self.theme.get('input_bg', '#2e2e3f'), corner_radius=8)
        appr_card.pack(fill='x', pady=(0,8))
        appr_card.pack_propagate(False)
        ar = ctk.CTkFrame(appr_card, fg_color='transparent')
        ar.pack(fill='x', padx=10, pady=10)
        ctk.CTkLabel(ar, text='Approve User (paste user id)').pack(anchor='w')
        self.appr_var = tk.StringVar(value='')
        ctk.CTkEntry(ar, textvariable=self.appr_var, width=360).pack(anchor='w', pady=(6,0))
        ctk.CTkButton(ar, text='Approve', width=100, command=self._approve_member).pack(anchor='w', pady=(8,0))

        # Channels
        chan_card = ctk.CTkFrame(left_col, fg_color=self.theme.get('input_bg', '#2e2e3f'), corner_radius=8)
        chan_card.pack(fill='x', pady=(0,8))
        ch = ctk.CTkFrame(chan_card, fg_color='transparent')
        ch.pack(fill='x', padx=10, pady=10)
        ctk.CTkLabel(ch, text='New Channel').pack(anchor='w')
        self.chan_var = tk.StringVar(value='')
        ctk.CTkEntry(ch, textvariable=self.chan_var, width=300).pack(anchor='w', pady=(6,0))
        ctk.CTkButton(ch, text='Create', width=100, command=self._create_channel).pack(anchor='w', pady=(8,0))

        # Members column (right)
        ctk.CTkLabel(right_col, text='Members', font=('Roboto', 12, 'bold')).pack(anchor='w', padx=8, pady=(6,4))
        self.members_frame = ctk.CTkScrollableFrame(right_col, fg_color=self.theme.get('background', '#2e2e3f'), width=300)
        self.members_frame.pack(fill='both', expand=True, padx=8, pady=6)

        # Owner transfer / delete actions (below members)
        actions_card = ctk.CTkFrame(right_col, fg_color=self.theme.get('input_bg', '#2e2e3f'), corner_radius=8)
        actions_card.pack(fill='x', padx=8, pady=(6,8))
        ac = ctk.CTkFrame(actions_card, fg_color='transparent')
        ac.pack(fill='x', padx=8, pady=8)
        ctk.CTkLabel(ac, text='Ownership & Admin').pack(anchor='w')
        # Transfer owner dropdown
        self._transfer_var = tk.StringVar(value='')
        try:
            self._transfer_menu = ctk.CTkOptionMenu(ac, values=[], variable=self._transfer_var, width=220)
            self._transfer_menu.pack(anchor='w', pady=(6,0))
            ctk.CTkButton(ac, text='Transfer Ownership', width=180, command=self._do_transfer_owner).pack(anchor='w', pady=(8,0))
        except Exception:
            # Fallback to a simple entry if optionmenu not available
            self._transfer_entry = ctk.CTkEntry(ac, textvariable=self._transfer_var, width=220)
            self._transfer_entry.pack(anchor='w', pady=(6,0))
            ctk.CTkButton(ac, text='Transfer Ownership', width=180, command=self._do_transfer_owner).pack(anchor='w', pady=(8,0))

        # Delete group (owners/admins)
        try:
            ctk.CTkButton(ac, text='Delete Group', width=180, fg_color='#d9534f', hover_color='#c9302c', command=self._do_delete_group).pack(anchor='w', pady=(12,0))
        except Exception:
            pass

        # Footer actions
        footer = ctk.CTkFrame(self, fg_color='transparent')
        footer.pack(fill='x', padx=12, pady=8)
        ctk.CTkButton(footer, text='Save', width=120, fg_color=self.theme.get('button_send', '#4a90e2'), command=self._save_settings).pack(side='right', padx=(8,0))
        ctk.CTkButton(footer, text='Close', width=120, command=self.destroy).pack(side='right')

        # Populate members and other dynamic data
        self._load_members()

    def _rename_group(self):
        try:
            new_name = (self.name_var.get() or "").strip()
            if not new_name:
                return
            # Call server rename route
            try:
                resp = self.gm.client.rename_group(self.gid, new_name)
                if resp.get("status") == "renamed":
                    # Update UI title
                    self.title_label.configure(text=new_name)
                    self.app.notifier.show("Group renamed", type_="success")
                else:
                    self.app.notifier.show("Rename request returned unexpected response", type_="warning")
            except Exception as e:
                self.app.notifier.show(f"Rename failed: {e}", type_="error")
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
                # server_distribute may be provided in GroupInfo; if not, default False
                try:
                    self.server_dist_var.set(bool(me.get("server_distribute", False)))
                except Exception:
                    self.server_dist_var.set(False)
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

    def _save_settings(self):
        """Persist settings changed in the dialog (public flag and name if supported).

        Note: server currently exposes a public toggle endpoint. Channel/group rename
        may be implemented server-side later; for now _rename_group provides a
        UX placeholder that should be replaced with a real API call when available.
        """
        try:
            new_name = (self.name_var.get() or "").strip()
            new_public = bool(self.is_public_var.get())
            # Update public flag (server enforces permissions)
            try:
                self.gm.client.set_group_public(self.gid, new_public)
                self.app.notifier.show("Group visibility updated", type_="success")
            except Exception as e:
                # Show error but continue to attempt rename/close
                self.app.notifier.show(f"Failed to update visibility: {e}", type_="error")

            # If name changed, call the rename helper (currently a placeholder)
            try:
                # Attempt to detect current name via list_groups to avoid unnecessary calls
                cur = None
                try:
                    data = self.gm.list_groups()
                    groups = data.get("groups", [])
                    me = next((g for g in groups if g.get("id") == self.gid), None)
                    cur = me.get("name") if me else None
                except Exception:
                    cur = None
                if new_name and new_name != (cur or ""):
                    # This will show a placeholder notifier until server-side rename exists
                    self._rename_group()
            except Exception:
                pass

            # Persist server_distribute if changed (only owner/admin may change)
            try:
                # If we determined our role when loading members, only attempt update for owner/admin
                if getattr(self, '_my_role', None) in ('owner', 'admin'):
                    try:
                        # Call endpoint to set value; client method added in group_client
                        self.gm.client.set_group_server_distribute(self.gid, bool(self.server_dist_var.get()))
                        # optional notifier
                        self.app.notifier.show("Server distribution preference updated", type_="success")
                    except Exception as e:
                        # Surface actual error message to help debugging (permission, payload, server error)
                        msg = str(e)
                        try:
                            # requests exceptions often include response text; try to extract if present
                            if hasattr(e, 'response') and getattr(e, 'response') is not None:
                                try:
                                    msg = e.response.text or msg
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        self.app.notifier.show(f"Failed to update server distribution preference: {msg}", type_="warning")
                else:
                    # Not owner/admin — inform user they cannot change this setting
                    self.app.notifier.show("Only owners/admins can change server distribution", type_="warning")
            except Exception:
                pass

            # Close dialog after save
            try:
                self.destroy()
            except Exception:
                pass
        except Exception as e:
            self.app.notifier.show(f"Save failed: {e}", type_="error")

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
        # Determine my role from members list
        try:
            self._my_role = None
            my_id = getattr(self.app, 'my_pub_hex', None)
            for m in members:
                if m.get('user_id') == my_id:
                    self._my_role = m.get('role')
                    break
        except Exception:
            self._my_role = None
        for m in members:
            row = ctk.CTkFrame(self.members_frame, fg_color=self.theme.get("input_bg", "#2e2e3f"))
            row.pack(fill="x", padx=6, pady=4)
            ctk.CTkLabel(row, text=m.get("user_id", "?")[:16] + "…").pack(side="left", padx=8, pady=6)
            ctk.CTkLabel(row, text=m.get("role", "member"), fg_color="#3b3b52", corner_radius=8, width=70).pack(side="left", padx=6)
            ctk.CTkButton(row, text="Ban", width=60,
                          command=lambda uid=m.get("user_id"): self._ban_member(uid)).pack(side="right", padx=6)
        # Populate transfer dropdown values (exclude owner)
        try:
            vals = [m.get('user_id') for m in members if m.get('role') != 'owner']
            if getattr(self, '_transfer_menu', None):
                try:
                    self._transfer_menu.configure(values=vals)
                except Exception:
                    # Some CTk versions require reconstructing the menu
                    pass
            elif getattr(self, '_transfer_entry', None):
                # nothing to do; entry already editable
                pass
            # Prefill with first member if available
            if vals:
                self._transfer_var.set(vals[0])
        except Exception:
            pass

        # Enable/disable the server distribution switch based on my role
        try:
            if getattr(self, '_my_role', None) in ('owner', 'admin'):
                try:
                    self.server_dist_switch.configure(state='normal')
                except Exception:
                    pass
            else:
                try:
                    self.server_dist_switch.configure(state='disabled')
                except Exception:
                    pass
        except Exception:
            pass

    def _do_transfer_owner(self):
        new_owner = (self._transfer_var.get() or '').strip()
        if not new_owner:
            return
        try:
            # Call client transfer API
            self.gm.client.transfer_owner(self.gid, new_owner)
            self.app.notifier.show('Ownership transferred', type_='success')
            # Reload members to reflect new roles
            self._load_members()
        except Exception as e:
            self.app.notifier.show(f'Transfer failed: {e}', type_='error')

    def _do_delete_group(self):
        try:
            # Confirm
            ok = messagebox.askyesno('Delete Group', 'Are you sure you want to delete this group? This cannot be undone.')
            if not ok:
                return
            self.gm.client.delete_group(self.gid)
            self.app.notifier.show('Group deleted', type_='success')
            try:
                self.destroy()
            except Exception:
                pass
        except Exception as e:
            self.app.notifier.show(f'Delete failed: {e}', type_='error')

    def _ban_member(self, user_id: str):
        try:
            self.gm.client.ban_member(self.gid, user_id)
            self.app.notifier.show("Member removed. Rekey required.", type_="warning")
            self._load_members()
        except Exception as e:
            self.app.notifier.show(f"Ban failed: {e}", type_="error")
