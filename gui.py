# --- Standard library ---
import os
import sys
import time
import json
import threading
from datetime import datetime
import tkinter as tk
from tkinter import simpledialog, Toplevel

# --- Third-party ---
import requests
import customtkinter as ctk

# --- GUI modules ---
from gui.pin_dialog import PinDialog
from gui.settings.window import SettingsWindow
from gui.tooltip import ToolTip
from gui.widgets.notification import Notification, NotificationManager
from gui.widgets.sidebar import Sidebar
from gui.layout import WhisprUILayout
from gui.message_styling import create_message_bubble
from gui.message_styling import recolor_message_bubble
from gui.profile_window import open_profile
from gui.theme_manager import ThemeManager
from gui.locked_screen import show_locked_screen

# --- Utils modules ---
from utils.chat_storage import load_messages, save_message
from utils.attachment_envelope import parse_attachment_envelope
from utils.crypto import (
    KEY_FILE,
    PrivateKey,
    SigningKey,
    decrypt_message,
    encrypt_message,
    load_key,
    save_key,
    sign_message,
    verify_signature,
)
from utils.network import fetch_messages, send_message
from utils.ws_client import start_ws_client
from utils.recipients import add_recipient, get_recipient_key, get_recipient_name, load_recipients
from utils.chat_manager import ChatManager
from utils.server_check import run_server_check_in_thread
from utils.auto_updater import run_auto_update_check_in_thread, apply_pending_update, get_pending_update
from utils.message_handler import handle_send
from utils.key_manager import init_keypair
from utils.app_settings import load_app_settings
from utils.path_utils import get_resource_path



CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "config/settings.json"))

class WhisprApp(ctk.CTk):

    def update_recipient_list(self):
        """Refresh the sidebar recipient buttons."""
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.update_list(selected_pub=self.recipient_pub_hex)
    
    def update_message_bubbles_theme(self):
        if not hasattr(self, "messages_container") or not hasattr(self, "theme_manager"):
            return
        # Ask ThemeManager for the full theme dict and use the message_styling recolor helper
        theme = self.theme_manager.theme_colors.get(self.theme_manager.current_theme, {})
        for bubble in self.messages_container.winfo_children():
            try:
                # Use recolor helper when available for consistent behavior
                recolor_message_bubble(bubble, theme)
            except Exception:
                # Fallback to minimal updates
                try:
                    bubble.configure(fg_color=theme.get('bubble_you' if getattr(bubble, 'is_you', False) else 'bubble_other'))
                except Exception:
                    pass


    def __init__(self):
        super().__init__()
        # Load settings and theme manager
        self.app_settings = load_app_settings()
        self.SERVER_URL = self.app_settings.get("server_url")
        self.SERVER_CERT = self.app_settings.get("server_cert")

        self.theme_manager = ThemeManager()
        # If config provided a theme name, apply it
        cfg_theme = self.app_settings.get("theme_name")
        if cfg_theme:
            self.theme_manager.set_theme_by_name(cfg_theme)

        # Force a full appearance mode + color theme apply right away to avoid
        # any brief mix of default/system + custom colors before widgets mount.
        try:
            self.theme_manager.apply()
        except Exception:
            pass

        # Register a listener so future theme changes apply live
        try:
            self.theme_manager.register_listener(self._on_theme_changed)
        except Exception:
            pass


        self.title("🕵️ Whispr")
        self.geometry("1000x800")

        # Apply root background color from theme immediately so window does not flash default color
        try:
            bg = self.theme_manager.theme_colors.get(self.theme_manager.current_theme, {}).get("background")
            if bg:
                self.configure(fg_color=bg)
        except Exception:
            pass


        

        self.private_key = None
        self.public_key = None
        self.my_pub_hex = None
        self.recipient_pub_hex = None
        self.username = "Anonymous"

        self.notifier = NotificationManager(self)

        # If an update was marked pending, attempt to apply it now (before
        # starting background threads). If applied, prompt the user to
        # restart so new code takes effect.
        try:
            pending_sha = get_pending_update()
            if pending_sha:
                applied = apply_pending_update()
                if applied:
                    try:
                        self.notifier.show("Update applied. Restart recommended.", type_="info")
                    except Exception:
                        pass

                    # Prompt user to restart now
                    try:
                        import tkinter as _tk
                        from tkinter import messagebox as _mb
                        restart = _mb.askyesno("Whispr Update", "An update was applied. Restart now to use the new version?")
                        if restart:
                            # Spawn new process and quit
                            import subprocess, sys, os
                            try:
                                subprocess.Popen([sys.executable] + sys.argv, cwd=os.getcwd())
                            except Exception:
                                pass
                            try:
                                self.on_close()
                            except Exception:
                                pass
                            try:
                                sys.exit(0)
                            except SystemExit:
                                raise
                    except Exception:
                        # If prompting fails, just continue; notifier already showed a notice
                        pass
        except Exception:
            pass




        # Default server values (backup if config load fails)
        if not getattr(self, "SERVER_URL", None):
            self.SERVER_URL = "https://34.61.34.132:8000"
        if not getattr(self, "SERVER_CERT", None):
            # Use packaged cert as fallback
            try:
                self.SERVER_CERT = get_resource_path("utils/cert.pem")
            except Exception:
                self.SERVER_CERT = None


    # --- Settings and theme already loaded above ---

        # Initialize keypair
        self.init_keypair()

        # If keypair failed to load (incorrect PIN or user cancelled), show a
        # locked placeholder UI so the app remains open and user can retry.
        if not getattr(self, "private_key", None):
            try:
                # Defensive: only attempt to show locked screen if the Tk root
                # still exists. In some edge cases (dialogs calling
                # sys.exit()/destroy), the Tcl interpreter may already be
                # destroyed which causes a hard crash when creating widgets.
                if getattr(self, 'winfo_exists', lambda: False)() and self.winfo_exists():
                    show_locked_screen(self)
                else:
                    # Root doesn't exist anymore; abort initialization
                    raise tk.TclError("Tk root not available")
            except tk.TclError:
                # If Tk was already destroyed, ensure we exit cleanly instead
                # of raising an uncaught exception that crashes the process.
                try:
                    self.on_close()
                except Exception:
                    pass
                try:
                    sys.exit(0)
                except SystemExit:
                    raise
            except Exception:
                # Any other error when creating the locked screen should not
                # stop the whole application startup; continue gracefully.
                pass
        else:
            self._post_key_init()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        # Optional drag & drop for attachments (requires tkinterdnd2)
        try:
            from tkinterdnd2 import DND_FILES  # type: ignore
            # Only attempt registration if the runtime actually added the
            # drag & drop methods to tkinter widgets. Custom Tk derivatives
            # like CustomTkinter may not have been patched or may not be
            # compatible with the tkdnd extension; avoid raising AttributeError.
            if hasattr(self, 'drop_target_register') and callable(getattr(self, 'drop_target_register')) and hasattr(self, 'dnd_bind') and callable(getattr(self, 'dnd_bind')):
                try:
                    self.drop_target_register(DND_FILES)
                    self.dnd_bind('<<Drop>>', self._on_file_drop)
                except Exception as e:
                    # If registration fails (native tkdnd missing or other),
                    # log once and continue without DnD support.
                    print("Drag&Drop register failed:", e)
            else:
                # Best-effort: the tkinterdnd2 package sometimes requires using
                # its Tk wrapper class or loading the native tkdnd package.
                # We try to call the module's internal loader if available,
                # but don't fail startup if it doesn't work on this platform.
                try:
                    import tkinterdnd2.TkinterDnD as _td  # type: ignore
                    try:
                        _td._require(self)
                        if hasattr(self, 'drop_target_register') and callable(getattr(self, 'drop_target_register')):
                            self.drop_target_register(DND_FILES)
                            self.dnd_bind('<<Drop>>', self._on_file_drop)
                    except Exception as e:
                        # Native support couldn't be loaded; fallback silently.
                        print("Drag&Drop: native tkdnd not available:", e)
                except Exception:
                    # No further action — DnD not available in this environment.
                    pass
        except Exception:
            # tkinterdnd2 isn't installed; that's fine — app will run without DnD.
            pass

    def _post_key_init(self):
        """Run initialization steps that require a loaded keypair."""
        self.layout = WhisprUILayout(self)
        self.layout.create_widgets()
        # Re-apply theme after widgets were created to propagate colors to all
        # newly added components (some custom widgets read global appearance
        # only at construction time).
        try:
            self.theme_manager.apply()
        except Exception:
            pass
        self.update_message_bubbles_theme()

        self.chat_manager = ChatManager(self)

        # Start fetch loop
        self.stop_event = threading.Event()
        threading.Thread(target=self.chat_manager.fetch_loop, daemon=True).start()

        # Start WebSocket client (real-time push). Runs alongside polling; polling will idle when ws_connected.
        try:
            self.ws_connected = False
            start_ws_client(self)
        except Exception as e:
            print(f"[gui] failed to start websocket client: {e}")

        run_server_check_in_thread(self, interval=1.0)
        # Start auto-update checker (runs in background). Default: check every hour.
        try:
            run_auto_update_check_in_thread(self, owner="Akame1981", repo="Whispr", branch="main", interval=3600.0)
        except Exception:
            pass

    # locked screen UI moved to gui/locked_screen.show_locked_screen

    def _try_unlock(self):
        """Prompt for PIN again and initialize the app if successful."""
        self.init_keypair()
        if getattr(self, "private_key", None):
            # Remove locked UI and continue initialization
            try:
                self.lock_frame.destroy()
            except Exception:
                pass

    def _on_theme_changed(self, theme):
        """Callback invoked by ThemeManager when theme changes; update all dynamic widget colors."""
        try:
            self.configure(fg_color=theme.get("background", "#1c1c28"))
        except Exception:
            pass

        # Sidebar
        if hasattr(self, "sidebar"):
            try:
                self.sidebar.configure(fg_color=theme.get("sidebar_bg", "#252536"))
                # force relist to recolor entries
                self.sidebar.theme = theme
                self.sidebar.update_list(selected_pub=self.recipient_pub_hex)
            except Exception:
                pass

        # Layout-level frames (pub_frame, messages container, etc.)
        if hasattr(self, 'layout') and hasattr(self.layout, 'refresh_theme'):
            try:
                self.layout.refresh_theme(theme)
            except Exception:
                pass

        # Public key frame / labels
        try:
            if hasattr(self, "pub_label") and self.pub_label.winfo_exists():
                self.pub_label.configure(text_color=theme.get("pub_text", "white"))
        except Exception:
            pass

        try:
            if hasattr(self, "copy_btn"):
                self.copy_btn.configure(fg_color=theme.get("button_send", "#5a9bf6"),
                                        hover_color=theme.get("button_send_hover", "#3d7ddb"))
        except Exception:
            pass

        # Messages container background
        if hasattr(self, "messages_container"):
            try:
                self.messages_container.configure(fg_color=theme.get("background", "#2e2e3f"))
            except Exception:
                pass

        # Input box
        if hasattr(self, "input_box"):
            try:
                self.input_box.configure(fg_color=theme.get("input_bg", "#2e2e3f"),
                                         text_color=theme.get("input_text", "white"))
            except Exception:
                pass

        # Server status dot color might depend on online/offline state; just re-run update if function exists
        if hasattr(self, "update_status_color"):
            try:
                # if we tracked online state, we could store it; for now assume offline->online refresh not critical
                pass
            except Exception:
                pass

        # Update existing message bubbles colors/text
        self.update_message_bubbles_theme()



# ---------------- Keypair ----------------
    def init_keypair(self):
        result = init_keypair(self.notifier, PinDialog, self)
        # If init_keypair returned None, it means the user cancelled or the PIN
        # was incorrect. Don't destroy the application here — just return and
        # let the caller decide how to proceed. This prevents an immediate
        # crash caused by continuing initialization after destroying the root.
        if not result:
            return

        self.private_key, self.signing_key, self.pin, self.username = result
        self.public_key = self.private_key.public_key
        self.my_pub_hex = self.public_key.encode().hex()
        self.signing_pub_hex = self.signing_key.verify_key.encode().hex()




    def select_recipient(self, name):
        # Pass self.pin to get_recipient_key
        self.recipient_pub_hex = get_recipient_key(name, self.pin)
        self.sidebar.update_list(selected_pub=self.recipient_pub_hex)
        # Update unknown-contact helper banner if available
        try:
            if hasattr(self, 'update_unknown_contact_banner'):
                self.update_unknown_contact_banner()
        except Exception:
            pass

        # Clear previous messages
        for widget in self.messages_container.winfo_children():
            widget.destroy()

        # Show a lightweight loading placeholder (will be cleared by ChatManager render)
        try:
            theme = self.theme_manager.theme_colors.get(self.theme_manager.current_theme, {}) if hasattr(self, 'theme_manager') else {}
            loading_lbl = ctk.CTkLabel(self.messages_container, text="Loading messages…",
                                       text_color=theme.get("sidebar_text", "white"))
            loading_lbl.pack(pady=8)
        except Exception:
            pass

        # Load messages non-blocking using ChatManager batched renderer.
        # Request only the latest 10 messages for faster initial load.
        if self.recipient_pub_hex:
            if hasattr(self, 'chat_manager'):
                try:
                    self.chat_manager.show_initial_messages(self.recipient_pub_hex, limit=10)
                except TypeError:
                    # Backwards compatibility: older ChatManager may not accept limit
                    self.chat_manager.show_initial_messages(self.recipient_pub_hex)
            else:
                # Fallback: synchronous (rare path if chat_manager missing)
                # Clear the placeholder before synchronous rendering
                for widget in self.messages_container.winfo_children():
                    widget.destroy()
                messages = load_messages(self.recipient_pub_hex, self.pin)
                for msg in messages:
                    txt = msg.get("text", "")
                    meta = msg.get("_attachment")
                    if not meta and msg.get("_attachment_json"):
                        try:
                            import json as _json
                            meta = _json.loads(msg.get("_attachment_json")) if msg.get("_attachment_json") else None
                        except Exception:
                            meta = None
                    if (not meta) and isinstance(txt, str) and txt.startswith("ATTACH:"):
                        placeholder, parsed = parse_attachment_envelope(txt)
                        if placeholder and parsed:
                            txt = placeholder
                            meta = parsed
                    self.display_message(
                        msg.get("sender"),
                        txt,
                        timestamp=msg.get("timestamp"),
                        attachment_meta=meta,
                    )




    # ---------------- Public key ----------------
    def copy_pub_key(self):
        self.clipboard_clear()
        self.clipboard_append(self.my_pub_hex)
        self.notifier.show("Public key copied!", type_="success")
    # ---------------- Messages ----------------

    def display_message(self, sender_pub, text, timestamp=None, attachment_meta=None):
        bubble = create_message_bubble(
            self.messages_container,
            sender_pub,
            text,
            self.my_pub_hex,
            self.pin,
            app=self,
            timestamp=timestamp,
            attachment_meta=attachment_meta
        )
        # Optional: attach a context menu to rename unknown senders quickly
        try:
            import tkinter as _tk
            from tkinter import Menu as _Menu
            from utils.recipients import get_recipient_name, set_recipient_name_for_key
            is_other = (sender_pub != self.my_pub_hex)
            if is_other:
                name = get_recipient_name(sender_pub, self.pin)
                looks_unknown = (not name) or (isinstance(name, str) and name.lower().startswith('unknown-'))
                if looks_unknown and hasattr(bubble, 'outer'):
                    m = _Menu(bubble.outer, tearoff=0)
                    def _rename():
                        from tkinter import simpledialog as _sd
                        proposed = name or f"Unknown-{sender_pub[:6]}"
                        new_name = _sd.askstring("Save Contact", "Name for this contact:", initialvalue=proposed)
                        if not new_name:
                            return
                        try:
                            set_recipient_name_for_key(sender_pub, new_name, self.pin)
                            if hasattr(self, 'sidebar') and hasattr(self.sidebar, 'update_list'):
                                self.sidebar.update_list(selected_pub=self.recipient_pub_hex)
                            if hasattr(self, 'update_unknown_contact_banner'):
                                self.update_unknown_contact_banner()
                            self.notifier.show(f"Saved {new_name}")
                        except Exception as e:
                            self.notifier.show(str(e), type_="error")
                    m.add_command(label="Save Contact…", command=_rename)
                    def _popup(evt):
                        try:
                            m.tk_popup(evt.x_root, evt.y_root)
                        except Exception:
                            pass
                    bubble.outer.bind("<Button-3>", _popup)
        except Exception:
            pass

    # -------------- Drag & Drop --------------
    def _on_file_drop(self, event):
        """Handle OS file(s) dropped onto the window (if tkinterdnd2 present)."""
        try:
            data = event.data
            if not data:
                return
            # Windows paths may be enclosed in { } when containing spaces
            import shlex, time as _time, os
            parts = []
            if '{' in data or '}' in data:
                # naive parse: split by } { patterns
                cur = ''
                brace = False
                for ch in data:
                    if ch == '{':
                        brace = True
                        cur = ''
                        continue
                    if ch == '}':
                        brace = False
                        parts.append(cur)
                        cur = ''
                        continue
                    if brace:
                        cur += ch
                if cur:
                    parts.append(cur)
            else:
                parts = data.split()
            if not parts:
                return
            from utils.network import send_attachment
            from utils.chat_storage import save_message
            if not self.recipient_pub_hex:
                try:
                    self.notifier.show("Select a recipient first", type_='warning')
                except Exception:
                    pass
                return
            import threading
            for path in parts:
                if not os.path.isfile(path):
                    continue
                try:
                    sz = os.path.getsize(path)
                    if sz > 5*1024*1024:
                        self.notifier.show(f"Skip {os.path.basename(path)} (>5MB)")
                        continue
                    with open(path,'rb') as f:
                        blob = f.read()
                    # Persist locally so optimistic UI can render the blob immediately
                    try:
                        from utils.attachments import store_attachment
                        att_id = store_attachment(blob, self.pin)
                    except Exception:
                        # Fall back to deterministic sha256 id if storing fails
                        import hashlib as _hashlib
                        att_id = _hashlib.sha256(blob).hexdigest()
                    placeholder = f"[Attachment] {os.path.basename(path)} ({self.chat_manager._human_size(len(blob))})"
                    ts = _time.time()
                    meta = {"name": os.path.basename(path), "size": len(blob), "att_id": att_id, "type": "file"}
                    save_message(self.recipient_pub_hex, 'You', placeholder, self.pin, timestamp=ts, attachment=meta)
                    self.display_message(self.my_pub_hex, placeholder, ts, attachment_meta=meta)

                    def _bg_send(p=path, data=blob):
                        ok = send_attachment(
                            self,
                            to_pub=self.recipient_pub_hex,
                            signing_pub=self.signing_pub_hex,
                            filename=os.path.basename(p),
                            data=data,
                            signing_key=self.signing_key,
                            enc_pub=self.my_pub_hex
                        )
                        if not ok:
                            try:
                                self.notifier.show(f"Failed to send {os.path.basename(p)}", type_='error')
                            except Exception:
                                pass
                    threading.Thread(target=_bg_send, daemon=True).start()
                except Exception as e:
                    print('Drop send error', e)
        except Exception as e:
            print('DragDrop handler error', e)






    def on_send(self):
        handle_send(self)



    def load_app_settings(self):
        """Load server settings and other configurations at startup."""
        # Settings are handled by utils.app_settings.load_app_settings
        # This method is retained for backward compatibility but does nothing.
        return









    # ---------------- Settings ----------------



    def open_settings(self):
        """Open settings as an in-place panel inside the main window.

        Falls back to the existing SettingsWindow Toplevel if the layout isn't ready.
        """
        try:
            from gui.settings.window import SettingsPanel
        except Exception:
            # fallback: open legacy toplevel window
            try:
                SettingsWindow(self, self)
            except Exception:
                pass
            return

        # If chat_frame or main_frame not ready, open legacy toplevel
        parent = getattr(self, 'chat_frame', getattr(self, 'main_frame', None))
        if parent is None:
            try:
                SettingsWindow(self, self)
            except Exception:
                pass
            return

        # If already open, ignore
        if hasattr(self, 'settings_panel') and getattr(self, 'settings_panel'):
            return

        # Hide primary chat widgets so settings can occupy the area
        self._settings_hidden = {}
        try:
            for name in ('pub_frame', 'messages_container', 'input_frame'):
                w = getattr(self, name, None)
                if w and hasattr(w, 'pack_forget'):
                    self._settings_hidden[name] = w
                    try:
                        w.pack_forget()
                    except Exception:
                        try:
                            w.grid_forget()
                        except Exception:
                            pass
        except Exception:
            pass

        # Create and pack panel
        try:
            self.settings_panel = SettingsPanel(parent, self)
            self.settings_panel.pack(fill='both', expand=True)
        except Exception:
            # On failure, try legacy window and restore hidden widgets
            try:
                SettingsWindow(self, self)
            except Exception:
                pass
            finally:
                try:
                    for w in getattr(self, '_settings_hidden', {}).values():
                        try:
                            w.pack(fill='x')
                        except Exception:
                            try:
                                w.grid()
                            except Exception:
                                pass
                except Exception:
                    pass

    def on_settings_panel_closed(self):
        """Restore UI after in-place settings panel is closed."""
        try:
            # clear reference
            if hasattr(self, 'settings_panel'):
                self.settings_panel = None
        except Exception:
            pass

        # restore hidden widgets in a best-effort order
        try:
            for name in ('pub_frame', 'messages_container', 'input_frame'):
                w = None
                if hasattr(self, '_settings_hidden') and name in self._settings_hidden:
                    w = self._settings_hidden.get(name)
                elif hasattr(self, name):
                    w = getattr(self, name)
                if w:
                    try:
                        w.pack(fill='x' if name != 'messages_container' else 'both', expand=(name == 'messages_container'))
                    except Exception:
                        try:
                            w.grid()
                        except Exception:
                            pass
        except Exception:
            pass


    # ---------------- Recipients ----------------
    def add_new_recipient(self):
        name = simpledialog.askstring("Name", "Recipient name:")
        if not name:
            return
        pub_hex = simpledialog.askstring("Public Key", f"Public key for {name}:")
        if not pub_hex or len(pub_hex) != 64:
            self.notifier.show("Invalid public key", type_="error")
            return
        
        try:
            add_recipient(name, pub_hex, self.pin)
        except ValueError as e:
            self.notifier.show(str(e), type_="error")
            return

        self.recipient_pub_hex = pub_hex
        self.update_recipient_list()
        self.notifier.show(f"{name} saved and selected.")





    def choose_recipient(self):
        recipients = load_recipients(self.pin)  
        if not recipients:
            self.notifier.show("Add a recipient first", type_="warning")
            return

        choose_win = Toplevel(self)
        choose_win.title("Choose Recipient")
        choose_win.geometry("300x300")
        choose_win.configure(bg="#1e1e2f")

        listbox = tk.Listbox(choose_win, bg="#2e2e3f", fg="white")
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for name in recipients:
            listbox.insert(tk.END, name)

        def select():
            sel = listbox.curselection()
            if sel:
                name = listbox.get(sel[0])
                self.recipient_pub_hex = get_recipient_key(name, self.pin)
                choose_win.destroy()

        tk.Button(choose_win, text="Select", command=select, bg="#4a90e2", fg="white").pack(pady=5)

    



    def open_profile(self):
        open_profile(self, self.my_pub_hex, self.signing_pub_hex, self.copy_pub_key, username=self.username)







    def on_close(self):
        # Stop background loops if they were started
        try:
            if hasattr(self, "stop_event") and self.stop_event:
                self.stop_event.set()
        except Exception:
            pass

        try:
            if hasattr(self, "chat_manager") and self.chat_manager:
                # ChatManager.stop sets its internal event
                self.chat_manager.stop()
        except Exception:
            pass

        # Finally destroy the window
        try:
            self.destroy()
        except Exception:
            # Last resort: quit the Tk mainloop
            try:
                self.quit()
            except Exception:
                pass



if __name__ == "__main__":
    app = WhisprApp()
    app.mainloop()
