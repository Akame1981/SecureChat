# chat_manager.py
import threading
import time
import queue
from datetime import datetime

from utils.chat_storage import (
    load_messages,
    load_recent_messages,
    load_all_segments,
    save_message,
    is_segmented,
)
from utils.crypto import decrypt_message, verify_signature, decrypt_blob
from utils.network import fetch_messages, send_message
from utils.outbox import flush_outbox, has_outbox
from utils.recipients import get_recipient_name


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
        # Limit of newest messages to show instantly on initial selection (after segmentation). None = show all recent segments
        self.initial_message_limit = 1

        # Start background threads
        threading.Thread(target=self.fetch_loop, daemon=True).start()
        threading.Thread(target=self.send_loop, daemon=True).start()

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

    # ---------------- Cache helpers ----------------
    def get_messages(self, pub_hex: str):
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

        if is_segmented(pub_hex):
            recent = load_recent_messages(pub_hex, self.app.pin, recent_segments=2, max_messages=self.initial_message_limit)
            with self._cache_lock:
                self._chat_cache[pub_hex] = list(recent)
            threading.Thread(target=self._backfill_full_history, args=(pub_hex,), daemon=True).start()
            return recent

        msgs = load_messages(pub_hex, self.app.pin)
        with self._cache_lock:
            self._chat_cache[pub_hex] = msgs
        return msgs

    def _backfill_full_history(self, pub_hex: str):
        try:
            full = load_all_segments(pub_hex, self.app.pin)
        except Exception as e:
            print(f"[chat_manager] backfill failed for {pub_hex}: {e}")
            return
        with self._cache_lock:
            current = self._chat_cache.get(pub_hex, [])
            if len(full) > len(current):
                self._chat_cache[pub_hex] = full
        if self.app.recipient_pub_hex == pub_hex:
            try:
                self.app.after(0, self._rebuild_conversation_ui, pub_hex, full)
            except Exception:
                pass

    def _rebuild_conversation_ui(self, pub_hex: str, messages: list):
        if self.app.recipient_pub_hex != pub_hex:
            return
        try:
            for widget in self.app.messages_container.winfo_children():
                widget.destroy()
            for msg in messages:
                self.app.display_message(msg.get('sender'), msg.get('text'), timestamp=msg.get('timestamp'))
        except Exception as e:
            print(f"[chat_manager] rebuild UI failed: {e}")

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

                for msg in msgs:
                    sender_pub = msg["from_enc"]
                    encrypted_message = msg["message"]
                    signature = msg.get("signature")
                    timestamp = msg.get("timestamp", time.time())  # fallback

                    if signature and verify_signature(msg["from_sign"], encrypted_message, signature):
                        decrypted_raw = decrypt_message(encrypted_message, self.app.private_key)
                        msg_text = decrypted_raw
                        attachment_meta = None
                        if decrypted_raw.startswith("ATTACH:"):
                            import json as _json
                            try:
                                meta = _json.loads(decrypted_raw[7:])
                                if meta.get("type") == "file":
                                    attachment_meta = meta
                                    # For display, show a placeholder line; clicking could trigger save later
                                    fn = meta.get("name", "file")
                                    size = meta.get("size", 0)
                                    human = self._human_size(size)
                                    msg_text = f"[Attachment] {fn} ({human})"
                            except Exception:
                                pass

                        msg_dict = {
                            "sender": get_recipient_name(sender_pub, self.app.pin) or sender_pub,
                            "text": msg_text,
                            "timestamp": timestamp,
                        }
                        if attachment_meta:
                            msg_dict["_attachment"] = attachment_meta
                        # Save locally with timestamp (will decrypt if cache absent)
                        save_message(
                            sender_pub,
                            msg_dict["sender"],
                            msg_dict["text"],
                            self.app.pin,
                            timestamp=timestamp,
                            attachment=attachment_meta
                        )
                        # Update cache and display (only if active chat matches; display_message already filters later if added)
                        self._append_cache(sender_pub, msg_dict)
                        # Display in GUI with timestamp (only if active conversation is this sender)
                        if self.app.recipient_pub_hex == sender_pub:
                            self.app.after(0, self.app.display_message, sender_pub, msg_text, timestamp, attachment_meta)

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
                ts = time.time()

                success = send_message(
                    self.app,
                    to_pub=recipient_pub,
                    signing_pub=self.app.signing_pub_hex,
                    text=text,
                    signing_key=self.app.signing_key,
                    enc_pub=self.app.my_pub_hex
                )

                if success:
                    msg_dict = {"sender": "You", "text": text, "timestamp": ts}
                    # Save quickly (append) and update cache
                    save_message(recipient_pub, "You", text, self.app.pin, timestamp=ts)
                    self._append_cache(recipient_pub, msg_dict)
                    # Display only if user still viewing this conversation
                    if self.app.recipient_pub_hex == recipient_pub:
                        self.app.after(0, self.app.display_message, self.app.my_pub_hex, text, ts)
                else:
                    self.app.notifier.show("Failed to send message", type_="error")

            except queue.Empty:
                continue

    # ---------------- Queue message ----------------
    def send(self, text):
        if not self.app.recipient_pub_hex:
            self.app.notifier.show("Select a recipient first", type_="warning")
            return
        self.send_queue.put({"text": text, "to_pub": self.app.recipient_pub_hex})

    # ---------------- Stop ChatManager ----------------
    def stop(self):
        self.stop_event.set()
