# chat_manager.py
import threading
import time
import queue
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
import json

from utils.chat_storage import (
    load_messages,
    save_message,
)
from utils.db import query_messages_before, has_older_messages
from utils.crypto import decrypt_message, verify_signature, decrypt_blob
from utils.network import fetch_messages, send_message, send_attachment
from utils.attachment_envelope import parse_attachment_envelope
from utils.attachments import store_attachment
import json
from utils.outbox import flush_outbox, has_outbox, append_outbox_message
from utils.recipients import get_recipient_name, ensure_recipient_exists
try:
    from gui.call_invite import CallInviteWindow
except Exception:
    CallInviteWindow = None  # type: ignore


class ChatManager:
    def __init__(self, app):
        """
        ChatManager handles sending and fetching messages efficiently.
        """
        self.app = app
        self.stop_event = threading.Event()
        self.send_queue = queue.Queue()
        self.last_fetch_ts = 0  # Timestamp of last received message
        # In-memory decrypted chat cache: { pub_hex: [ {sender,text,timestamp}, ... ] }
        self._chat_cache = {}
        self._cache_lock = threading.RLock()
        # Fast-path limits for initial chat opening
        # - Only decrypt the most recent N segments to avoid heavy I/O on large chats
        # - Limit how many messages we render immediately for snappy UX
        self.recent_segments_initial = 1
        self.initial_message_limit = 100
        # Lazy-load configuration
        self.lazy_chunk = 200
        # Virtualization/trim configuration
        self.cache_soft_limit = 1000  # keep only last N messages in memory per chat
        self.ui_soft_limit = 500      # keep only last N widgets on screen
        # Track oldest timestamp per chat in cache for efficient paging
        self._oldest_ts = {}
        # Track per-chat loading state for older-message prefetch
        self._loading_older = {}

        # Start background threads
        threading.Thread(target=self.fetch_loop, daemon=True).start()
        threading.Thread(target=self.send_loop, daemon=True).start()
        # Decryption worker pool for CPU-bound tasks
        self._proc_pool = ProcessPoolExecutor(max_workers=2)
        # Threshold (bytes) above which plaintext messages are sent as .txt attachments
        self.ATTACHMENT_FALLBACK_THRESHOLD = 100 * 1024  # 100 KB

    # --------------- Utility ---------------
    @staticmethod
    def _human_size(bytes_count: int) -> str:
        try:
            units = ["B", "KB", "MB", "GB", "TB"]
            size = float(bytes_count)
            for u in units:
                if size < 1024 or u == units[-1]:
                    return f"{size:.1f} {u}"
                size /= 1024
        except Exception:
            return f"{bytes_count} B"
        return f"{bytes_count} B"

    # --------------- UI rendering helpers ---------------
    def _render_messages_batched(self, pub_hex: str, messages: list, clear_existing: bool = False, chunk_size: int = 50):
        """Render messages in small chunks using Tk's event loop to avoid blocking the UI.

        - Respects current selection; aborts if user navigates away.
        - Optionally clears existing widgets first.
        - Parses attachment envelopes on the fly without rewriting history.
        """
        app = self.app
        if app.recipient_pub_hex != pub_hex:
            return
        try:
            if clear_existing:
                for w in app.messages_container.winfo_children():
                    w.destroy()
            else:
                # Best-effort: if a 'Loading messages…' placeholder exists, clear it before rendering
                try:
                    kids = app.messages_container.winfo_children()
                    if len(kids) == 1 and hasattr(kids[0], 'cget') and 'text' in kids[0].keys():
                        if str(kids[0].cget('text')).lower().startswith('loading'):
                            kids[0].destroy()
                except Exception:
                    pass
        except Exception:
            pass

        def do_chunk(start_idx=0):
            if app.recipient_pub_hex != pub_hex or self.stop_event.is_set():
                return
            end_idx = min(start_idx + chunk_size, len(messages))
            for i in range(start_idx, end_idx):
                msg = messages[i]
                try:
                    txt = msg.get("text", "")
                    # Lazy attachment JSON parsing: parse once at render time
                    meta = msg.get("_attachment")
                    if not meta and msg.get("_attachment_json"):
                        try:
                            meta = json.loads(msg["_attachment_json"]) if msg["_attachment_json"] else None
                            if meta:
                                msg["_attachment"] = meta
                        except Exception:
                            meta = None
                    if (not meta) and isinstance(txt, str) and txt.startswith("ATTACH:"):
                        placeholder, parsed = parse_attachment_envelope(txt)
                        if placeholder and parsed:
                            txt = placeholder
                            meta = parsed
                            msg["_attachment"] = parsed
                    app.display_message(
                        msg.get("sender"),
                        txt,
                        timestamp=msg.get("timestamp"),
                        attachment_meta=meta,
                    )
                except Exception as e:
                    print(f"[chat_manager] render msg failed: {e}")

            if end_idx < len(messages):
                try:
                    app.after(1, do_chunk, end_idx)
                except Exception:
                    pass

        try:
            app.after(0, do_chunk, 0)
        except Exception:
            pass

    def show_initial_messages(self, pub_hex: str, limit: int | None = None):
        """Load initial messages off the UI thread and render them in batches.

        Uses the same fast path as get_messages(); safe to call on selection.
        """
        def _bg_load():
            try:
                msgs = self.get_messages(pub_hex, limit=limit)
            except Exception as e:
                print(f"[chat_manager] initial load failed: {e}")
                msgs = []
            # Render on UI thread in batches
            try:
                self.app.after(0, self._render_messages_batched, pub_hex, msgs, True)
            except Exception:
                pass

        threading.Thread(target=_bg_load, daemon=True).start()

    # ---------------- Cache helpers ----------------
    def get_messages(self, pub_hex: str, limit: int | None = None):
        """Return cached messages, with fast partial load for segmented chats.

        Strategy:
        - If cached: return.
        - If segmented: load only recent segments (configurable) and spawn background
          thread to backfill full history.
        - Else legacy: full load.
        """
        if not pub_hex:
            return []
        with self._cache_lock:
            if pub_hex in self._chat_cache:
                return self._chat_cache[pub_hex]

        # Try DB-backed path with limit
        try:
            # Fetch newest messages first so we can display recent chat instantly
            qlimit = limit if limit is not None else self.initial_message_limit
            msgs = load_messages(pub_hex, self.app.pin, limit=qlimit, order_asc=False)
            with self._cache_lock:
                self._chat_cache[pub_hex] = list(msgs)
                if msgs:
                    # Track the oldest timestamp in the current window for lazy paging
                    self._oldest_ts[pub_hex] = min(m.get('timestamp', 0) for m in msgs)
            # No full-history backfill; we page on demand for scalability
            return msgs
        except Exception:
            msgs = []

        # Fallback: load full history ascending if limited query failed
        msgs = load_messages(pub_hex, self.app.pin, limit=None, order_asc=True)
        with self._cache_lock:
            self._chat_cache[pub_hex] = msgs
            if msgs:
                self._oldest_ts[pub_hex] = msgs[0].get('timestamp', 0)
        return msgs

    def _backfill_full_history(self, pub_hex: str):
        # Deprecated: replaced by on-demand paging for performance
        return

    # --------------- Lazy load older messages ---------------
    def has_more_older(self, pub_hex: str) -> bool:
        with self._cache_lock:
            oldest = self._oldest_ts.get(pub_hex)
        if oldest is None:
            return False
        try:
            return has_older_messages(self.app.pin, pub_hex, float(oldest))
        except Exception:
            return False

    def load_older_messages(self, pub_hex: str, count: int = 10):
        """Fetch older messages in chunks and prepend without freezing UI.

        `count` controls how many older messages to fetch (default 10).
        """
        with self._cache_lock:
            oldest = self._oldest_ts.get(pub_hex)
            if self._loading_older.get(pub_hex):
                # Already fetching older messages for this conversation
                return
            # Mark as loading to avoid duplicate fetches
            self._loading_older[pub_hex] = True
        if oldest is None:
            # Nothing to page from; clear loading flag
            with self._cache_lock:
                self._loading_older[pub_hex] = False
            return

        def _bg_fetch():
            try:
                older = query_messages_before(self.app.pin, pub_hex, float(oldest), int(count))
            except Exception as e:
                print(f"[chat_manager] lazy load older failed: {e}")
                with self._cache_lock:
                    self._loading_older[pub_hex] = False
                return
            if not older:
                with self._cache_lock:
                    self._loading_older[pub_hex] = False
                return
            with self._cache_lock:
                current = self._chat_cache.get(pub_hex, [])
                new_list = list(older) + list(current)
                self._chat_cache[pub_hex] = new_list
                self._oldest_ts[pub_hex] = new_list[0].get('timestamp', oldest)
            # Prepend in UI
            if self.app.recipient_pub_hex == pub_hex:
                try:
                    self.app.after(0, self._prepend_messages_ui, pub_hex, older)
                except Exception:
                    pass
                # Do not trim immediately on prepend to avoid removing newly loaded items

        threading.Thread(target=_bg_fetch, daemon=True).start()

    def _prepend_messages_ui(self, pub_hex: str, messages: list):
        if self.app.recipient_pub_hex != pub_hex:
            return
        c = self.app.messages_container
        try:
            # Remember current scroll to keep visible content stable after prepending
            try:
                y = c._parent_canvas.yview()
            except Exception:
                y = None
            # Insert at top in chronological order
            for msg in messages:
                meta = msg.get('_attachment')
                if not meta and msg.get('_attachment_json'):
                    try:
                        meta = json.loads(msg.get('_attachment_json')) if msg.get('_attachment_json') else None
                        if meta:
                            msg['_attachment'] = meta
                    except Exception:
                        meta = None
                self.app.display_message(msg.get('sender'), msg.get('text'), timestamp=msg.get('timestamp'), attachment_meta=meta)
                # Reorder: move the last-added child to the top
                try:
                    w = c.winfo_children()[-1]
                    w.pack_forget()
                    w.pack(in_=c, before=c.winfo_children()[0], fill='x')
                except Exception:
                    pass
            # Restore scroll position approximately
            if y is not None:
                try:
                    c._parent_canvas.yview_moveto(y[0])
                except Exception:
                    pass
        except Exception as e:
            print(f"[chat_manager] prepend UI failed: {e}")

    def _rebuild_conversation_ui(self, pub_hex: str, messages: list):
        if self.app.recipient_pub_hex != pub_hex:
            return
        # Non-blocking batched render for full history
        self._render_messages_batched(pub_hex, messages, clear_existing=True)
        # Enforce UI soft limit by trimming oldest widgets
        try:
            c = self.app.messages_container
            children = c.winfo_children()
            extra = len(children) - self.ui_soft_limit
            if extra > 0:
                for w in children[:extra]:
                    try:
                        w.destroy()
                    except Exception:
                        pass
        except Exception:
            pass

    def _append_cache(self, pub_hex: str, message: dict):
        if not pub_hex:
            return
        with self._cache_lock:
            if pub_hex not in self._chat_cache:
                # Create list with message to keep ordering
                self._chat_cache[pub_hex] = [message]
            else:
                self._chat_cache[pub_hex].append(message)

    # ---------------- Fetching messages ----------------
    def fetch_loop(self):
        """
        Continuously fetch new messages from the server in the background.
        Uses adaptive sleep to reduce unnecessary polling.
        """
        while not self.stop_event.is_set():
            # If WebSocket is active, reduce polling frequency drastically
            if getattr(self.app, 'ws_connected', False):
                time.sleep(5)
                continue
            try:
                msgs = fetch_messages(
                    self.app,
                    self.app.my_pub_hex,
                    self.app.private_key,
                    since=self.last_fetch_ts
                )

                # Decrypt in parallel
                results = self._decrypt_messages_parallel(msgs)
                for ok, plaintext, msg in results:
                    if not ok or plaintext is None:
                        continue

                    sender_pub = msg["from_enc"]
                    timestamp = msg.get("timestamp", time.time())

                    msg_text = plaintext
                    attachment_meta = None
                    # Detect call invites
                    if plaintext.startswith("CALL:"):
                        try:
                            invite = json.loads(plaintext[5:])
                            call_id = str(invite.get('call_id'))
                            if call_id:
                                # Show incoming call dialog on UI thread
                                from_name = get_recipient_name(sender_pub, self.app.pin) or sender_pub
                                def _show_invite():
                                    try:
                                        if CallInviteWindow:
                                            CallInviteWindow(self.app, from_name, call_id, sender_pub)
                                    except Exception as _e:
                                        print("invite dialog error", _e)
                                try:
                                    self.app.after(0, _show_invite)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    if plaintext.startswith("ATTACH:"):
                        placeholder, meta = parse_attachment_envelope(plaintext)
                        if placeholder and meta:
                            msg_text = placeholder
                            attachment_meta = meta

                    # Ensure unknown senders create a chat entry
                    sender_name = get_recipient_name(sender_pub, self.app.pin)
                    if not sender_name:
                        try:
                            sender_name = ensure_recipient_exists(sender_pub, self.app.pin)
                            if hasattr(self.app, 'sidebar') and hasattr(self.app.sidebar, 'update_list'):
                                self.app.after(0, self.app.sidebar.update_list)
                        except Exception as _:
                            sender_name = sender_pub

                    msg_dict = {
                        "sender": sender_name or sender_pub,
                        "text": msg_text,
                        "timestamp": timestamp,
                    }
                    if attachment_meta:
                        msg_dict["_attachment"] = attachment_meta

                    # Save locally and update cache/UI
                    save_message(
                        sender_pub,
                        msg_dict["sender"],
                        msg_dict["text"],
                        self.app.pin,
                        timestamp=timestamp,
                        attachment=attachment_meta
                    )
                    self._append_cache(sender_pub, msg_dict)
                    with self._cache_lock:
                        msgs_cache = self._chat_cache.get(sender_pub, [])
                        if len(msgs_cache) > self.cache_soft_limit:
                            self._chat_cache[sender_pub] = msgs_cache[-self.cache_soft_limit:]
                    if self.app.recipient_pub_hex == sender_pub:
                        self.app.after(0, self._display_message_virtualized, sender_pub, msg_text, timestamp, attachment_meta)
                        # If chatting with an unknown contact, surface the inline Save Contact banner
                        try:
                            if hasattr(self.app, 'update_unknown_contact_banner'):
                                self.app.after(0, self.app.update_unknown_contact_banner)
                        except Exception:
                            pass

                    self.last_fetch_ts = max(self.last_fetch_ts, timestamp)

            except Exception as e:
                print("Fetch Error:", e)

            # Opportunistically flush any queued outbox messages every loop
            try:
                flush_outbox(self.app)
            except Exception as fe:
                print(f"[chat_manager] outbox flush error: {fe}")

            time.sleep(1 if 'msgs' in locals() and msgs else 2)

    # ---------------- Sending messages ----------------
    def send_loop(self):
        """
        Background thread to send messages from a queue asynchronously.
        """
        while not self.stop_event.is_set():
            try:
                item = self.send_queue.get(timeout=1)
                text = item["text"]
                recipient_pub = item["to_pub"]
                # Preserve the timestamp used for local render/save when available
                ts = item.get("ts", time.time())

                # Attachment fallback: if the queued item is an attachment send, handle via send_attachment
                if item.get("attachment"):
                    try:
                        fname = item.get("filename")
                        data = item.get("data")
                        ok = send_attachment(
                            self.app,
                            to_pub=recipient_pub,
                            signing_pub=self.app.signing_pub_hex,
                            filename=fname,
                            data=data,
                            signing_key=self.app.signing_key,
                            enc_pub=self.app.my_pub_hex,
                        )
                    except Exception as e:
                        print(f"[chat_manager] send_attachment exception: {e}")
                        ok = False
                    success = ok
                else:
                    success = send_message(
                        self.app,
                        to_pub=recipient_pub,
                        signing_pub=self.app.signing_pub_hex,
                        text=text,
                        signing_key=self.app.signing_key,
                        enc_pub=self.app.my_pub_hex
                    )

                # We already saved and displayed optimistically in send();
                # On failure, queue to outbox for retry.
                if not success:
                    try:
                        # For attachments we enqueue the ATTACH envelope into outbox so flush_outbox can resend properly
                        if item.get("attachment"):
                            # envelope should have been persisted locally by send(); recreate small ATTACH: envelope text
                            env = item.get("envelope")
                            if env is None:
                                # fallback: construct minimal envelope
                                env = {"type": "file", "name": item.get("filename"), "att_id": item.get("att_id"), "sha256": item.get("att_id"), "size": len(item.get("data") or b"")}
                            append_outbox_message(recipient_pub, "ATTACH:" + json.dumps(env, separators=(',', ':')), self.app.pin, timestamp=ts)
                        else:
                            append_outbox_message(recipient_pub, text, self.app.pin, timestamp=ts)
                        # Optional gentle notice; avoid blocking UX
                        try:
                            self.app.notifier.show("Offline: message queued", type_="warning")
                        except Exception:
                            pass
                    except Exception:
                        # As a last resort, keep a minimal error toast
                        try:
                            self.app.notifier.show("Failed to send message", type_="error")
                        except Exception:
                            pass

            except queue.Empty:
                continue

    # ---------------- Queue message ----------------
    def send(self, text):
        if not self.app.recipient_pub_hex:
            self.app.notifier.show("Select a recipient first", type_="warning")
            return
        text = (text or "").strip()
        if not text:
            return
        recipient_pub = self.app.recipient_pub_hex
        ts = time.time()

        # If message is extremely large, send as attachment to avoid GUI/X11 rendering crashes
        try:
            size_bytes = len(text.encode('utf-8'))
        except Exception:
            size_bytes = len(text)
        if size_bytes > getattr(self, 'ATTACHMENT_FALLBACK_THRESHOLD', 100*1024):
            # Prepare attachment data
            fname = f"message_{int(ts)}.txt"
            data = text.encode('utf-8')
            # Store local encrypted attachment for persistence
            try:
                att_id = store_attachment(data, getattr(self.app, 'pin', ''))
            except Exception:
                att_id = None

            # Save placeholder message pointing to attachment instead of full text
            placeholder = f"[File sent: {fname} ({self._human_size(size_bytes)})]"
            try:
                save_message(recipient_pub, "You", placeholder, self.app.pin, timestamp=ts, attachment={"type": "file", "name": fname, "att_id": att_id, "size": size_bytes})
            except Exception as e:
                print(f"[chat_manager] save_message (attachment) failed: {e}")
            try:
                self._append_cache(recipient_pub, {"sender": "You", "text": placeholder, "timestamp": ts, "_attachment": {"type": "file", "name": fname, "att_id": att_id, "size": size_bytes}})
            except Exception:
                pass
            if self.app.recipient_pub_hex == recipient_pub:
                try:
                    self.app.after(0, self._display_message_virtualized, self.app.my_pub_hex, placeholder, ts, {"type": "file", "name": fname, "att_id": att_id, "size": size_bytes})
                except Exception:
                    pass

            # Enqueue attachment send item for background worker
            self.send_queue.put({"attachment": True, "filename": fname, "data": data, "to_pub": recipient_pub, "ts": ts, "att_id": att_id, "envelope": {}})
            return

        # Optimistic local render and persistence
        try:
            save_message(recipient_pub, "You", text, self.app.pin, timestamp=ts)
        except Exception as e:
            print(f"[chat_manager] save_message failed: {e}")
        try:
            self._append_cache(recipient_pub, {"sender": "You", "text": text, "timestamp": ts})
        except Exception:
            pass
        if self.app.recipient_pub_hex == recipient_pub:
            try:
                self.app.after(0, self._display_message_virtualized, self.app.my_pub_hex, text, ts, None)
            except Exception:
                pass

        # Enqueue background send (non-blocking)
        self.send_queue.put({"text": text, "to_pub": recipient_pub, "ts": ts})

    # ---------------- Stop ChatManager ----------------
    def stop(self):
        self.stop_event.set()
        try:
            self._proc_pool.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass

    # ---------------- Virtualization helpers ----------------
    def _display_message_virtualized(self, sender_pub: str, text: str, ts: float, attachment_meta: dict | None):
        """Display a message with a soft cap on the number of widgets on screen."""
        try:
            self.app.display_message(sender_pub, text, ts, attachment_meta)
        except Exception:
            return
        # Trim oldest widgets if over limit
        try:
            c = self.app.messages_container
            children = c.winfo_children()
            extra = len(children) - self.ui_soft_limit
            if extra > 0:
                for w in children[:extra]:
                    try:
                        w.destroy()
                    except Exception:
                        pass
        except Exception:
            pass

    # ---------------- Parallel decrypt in fetch_loop ----------------
    def _decrypt_messages_parallel(self, items: list):
        """Decrypt and verify messages using a process pool.

        items: list of dicts with keys from_sign, message, signature, from_enc, timestamp.
        Returns list of tuples (ok, result_dict or None).
        """
        if not items:
            return []
        try:
            from utils.decrypt_worker import verify_and_decrypt
            priv_bytes = bytes(self.app.private_key.encode())
            futures = [
                self._proc_pool.submit(
                    verify_and_decrypt,
                    item.get("message"),
                    priv_bytes,
                    item.get("from_sign"),
                    item.get("signature"),
                ) for item in items
            ]
            results = []
            for idx, fut in enumerate(futures):
                ok, pt = False, None
                try:
                    ok, pt = fut.result()
                except Exception:
                    ok, pt = False, None
                it = items[idx]
                results.append((ok, pt, it))
            return results
        except Exception:
            # Fallback to sequential path
            out = []
            for it in items:
                try:
                    if it.get("signature") and not verify_signature(it.get("from_sign"), it.get("message"), it.get("signature")):
                        out.append((False, None, it))
                        continue
                    pt = decrypt_message(it.get("message"), self.app.private_key)
                    out.append((True, pt, it))
                except Exception:
                    out.append((False, None, it))
            return out
