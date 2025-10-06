# network.py
import requests
import time
from utils.crypto import encrypt_message, decrypt_message, sign_message


def send_message(app, to_pub: str, signing_pub: str, text: str, signing_key, enc_pub: str):
    """
    Send a message to the server asynchronously.
    - to_pub: recipient's encryption public key (hex)
    - signing_pub: your signing public key (hex)
    - text: plaintext message
    - signing_key: your SigningKey object
    - enc_pub: your encryption public key (hex) for display
    """
    try:
        encrypted_b64 = encrypt_message(text, to_pub)
        signature_b64 = sign_message(encrypted_b64, signing_key)

        payload = {
            "to": to_pub,
            "from_": signing_pub,
            "enc_pub": enc_pub,
            "message": encrypted_b64,
            "signature": signature_b64,
            "timestamp": time.time()  # include client timestamp
        }

        r = requests.post(f"{app.SERVER_URL}/send", json=payload, verify=app.SERVER_CERT, timeout=5)
        if not r.ok:
            print("Send Error:", r.status_code, r.text)
        return r.ok
    except requests.exceptions.RequestException as e:
        print("Send Exception:", e)
        return False


def fetch_messages(app, my_pub_hex: str, private_key, since: float = 0):
    """
    Fetch messages addressed to your encryption public key.
    - Supports fetching messages sent since a given timestamp.
    - Returns a list of messages with: from_sign, from_enc, message, signature, timestamp
    """
    try:
        params = {"since": since} if since else {}
        r = requests.get(f"{app.SERVER_URL}/inbox/{my_pub_hex}", params=params, verify=app.SERVER_CERT, timeout=5)
        if r.ok:
            inbox = r.json().get("messages", [])
            msgs = []
            for msg in inbox:
                msgs.append({
                    "from_sign": msg["from"],
                    "from_enc": msg["enc_pub"],
                    "message": msg["message"],
                    "signature": msg.get("signature"),
                    "timestamp": msg.get("timestamp", time.time())
                })
            return msgs
        else:
            print("Fetch Error:", r.status_code, r.text)
    except requests.exceptions.RequestException as e:
        print("Fetch Exception:", e)

    return []
