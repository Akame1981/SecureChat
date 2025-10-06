# chat_manager.py
import threading
import time
from datetime import datetime
import queue

from utils.chat_storage import load_messages, save_message
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

        # Start background threads
        threading.Thread(target=self.fetch_loop, daemon=True).start()
        threading.Thread(target=self.send_loop, daemon=True).start()

    # ---------------- Fetching messages ----------------
    def fetch_loop(self):
        """
        Continuously fetch new messages from the server in the background.
        Uses adaptive sleep to reduce unnecessary polling.
        """
        while not self.stop_event.is_set():
            try:
                # Fetch messages since last timestamp
                msgs = fetch_messages(self.app, self.app.my_pub_hex, self.app.private_key, since=self.last_fetch_ts)

                for msg in msgs:
                    sender_pub = msg["from_enc"]
                    encrypted_message = msg["message"]
                    signature = msg.get("signature")
                    timestamp = msg.get("timestamp", time.time())

                    if signature and verify_signature(msg["from_sign"], encrypted_message, signature):
                        decrypted = decrypt_message(encrypted_message, self.app.private_key)

                        # Display in GUI
                        self.app.after(0, self.app.display_message, sender_pub, decrypted)

                        # Save locally
                        save_message(
                            sender_pub,
                            get_recipient_name(sender_pub, self.app.pin) or sender_pub,
                            decrypted,
                            self.app.pin
                        )

                        # Update last fetch timestamp
                        self.last_fetch_ts = max(self.last_fetch_ts, timestamp)

            except Exception as e:
                print("Fetch Error:", e)

            # Adaptive sleep: slower if no messages
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

                success = send_message(
                    self.app,
                    to_pub=recipient_pub,
                    signing_pub=self.app.signing_pub_hex,
                    text=text,
                    signing_key=self.app.signing_key,
                    enc_pub=self.app.my_pub_hex
                )

                if success:
                    # Display locally
                    self.app.after(0, self.app.display_message, self.app.my_pub_hex, text)
                    save_message(recipient_pub, "You", text, self.app.pin)
                else:
                    self.app.notifier.show("Failed to send message", type_="error")

            except queue.Empty:
                continue

    def send(self, text):
        """
        Queue a message to be sent to the currently selected recipient.
        """
        if not self.app.recipient_pub_hex:
            self.app.notifier.show("Select a recipient first", type_="warning")
            return

        self.send_queue.put({"text": text, "to_pub": self.app.recipient_pub_hex})

    # ---------------- Stop ChatManager ----------------
    def stop(self):
        self.stop_event.set()
