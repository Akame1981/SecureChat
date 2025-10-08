# chat_manager.py
import threading
import time
import queue
from datetime import datetime

from utils.chat_storage import (
    load_messages,
    save_message,
)
from utils.crypto import decrypt_message, verify_signature
from utils.network import fetch_messages, send_message
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

    # ---------------- Cache helpers ----------------
    def get_messages(self, pub_hex: str):
        """Return cached messages, performing fast recent load first for large chats.

        Strategy:
        - If already cached: return immediately.
        - If already cached: return immediately.
        - Otherwise: load full messages from storage and cache them.
        """
        if not pub_hex:
            return []
        with self._cache_lock:
            if pub_hex in self._chat_cache:
                return self._chat_cache[pub_hex]
        # Full load
        msgs = load_messages(pub_hex, self.app.pin)
        with self._cache_lock:
            self._chat_cache[pub_hex] = msgs
        return msgs

    def _backfill_full_history(self, pub_hex: str):
        """Load entire history (segmented) and merge with cache if user still active.

        Avoid duplicating messages by comparing lengths (segments are appended only).
        """
        # Segmented backfill logic removed: storage currently provides full loads via load_messages.
        return

    def _rebuild_conversation_ui(self, pub_hex: str, messages: list):
        # This function was part of segmented backfill flow and is no-op with current storage API.
        return

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
                        decrypted = decrypt_message(encrypted_message, self.app.private_key)

                        # Build message dict once
                        msg_dict = {
                            "sender": get_recipient_name(sender_pub, self.app.pin) or sender_pub,
                            "text": decrypted,
                            "timestamp": timestamp
                        }
                        # Save locally with timestamp (will decrypt if cache absent)
                        save_message(
                            sender_pub,
                            msg_dict["sender"],
                            msg_dict["text"],
                            self.app.pin,
                            timestamp=timestamp
                        )
                        # Update cache and display (only if active chat matches; display_message already filters later if added)
                        self._append_cache(sender_pub, msg_dict)
                        # Display in GUI with timestamp (only if active conversation is this sender)
                        if self.app.recipient_pub_hex == sender_pub:
                            self.app.after(0, self.app.display_message, sender_pub, decrypted, timestamp)

                        self.last_fetch_ts = max(self.last_fetch_ts, timestamp)

            except Exception as e:
                print("Fetch Error:", e)

            time.sleep(1 if msgs else 2)

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
