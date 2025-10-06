# chat_manager.py
import threading
import time
from datetime import datetime

from utils.chat_storage import load_messages, save_message
from utils.crypto import decrypt_message, verify_signature
from utils.network import fetch_messages, send_message
from utils.recipients import get_recipient_name

class ChatManager:
    def __init__(self, app):
        """
        app: The WhisprApp instance, used to access GUI, keys, pin, etc.
        """
        self.app = app
        self.stop_event = threading.Event()

        # Start fetch loop in background
        threading.Thread(target=self.fetch_loop, daemon=True).start()

    def fetch_loop(self):
        while not self.stop_event.is_set():
            msgs = fetch_messages(self.app, self.app.my_pub_hex, self.app.private_key)
            for msg in msgs:
                sender_pub = msg["from_enc"]
                encrypted_message = msg["message"]
                signature = msg.get("signature")

                if signature and verify_signature(msg["from_sign"], encrypted_message, signature):
                    decrypted = decrypt_message(encrypted_message, self.app.private_key)
                    
                    # Display in GUI
                    self.app.after(0, self.app.display_message, sender_pub, decrypted)
                    
                    # Save locally
                    save_message(sender_pub, get_recipient_name(sender_pub, self.app.pin) or sender_pub, decrypted, self.app.pin)
            time.sleep(1)

    def send(self, text):
        """
        Send a message to the currently selected recipient.
        """
        if not self.app.recipient_pub_hex:
            self.app.notifier.show("Select a recipient first", type_="warning")
            return

        if send_message(
            self.app,
            to_pub=self.app.recipient_pub_hex,
            signing_pub=self.app.signing_pub_hex,
            text=text,
            signing_key=self.app.signing_key,
            enc_pub=self.app.my_pub_hex
        ):
            # Display locally
            self.app.display_message(self.app.my_pub_hex, text)
            save_message(self.app.recipient_pub_hex, "You", text, self.app.pin)

    def stop(self):
        self.stop_event.set()
