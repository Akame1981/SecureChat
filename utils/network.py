import requests
from utils.crypto import encrypt_message, decrypt_message, sign_message

USE_PUBLIC_SERVER = True  # Set False for localhost

if USE_PUBLIC_SERVER:
    SERVER_URL = "http://34.61.34.132:8000" # That is the official public server. Use it or your own.
else:
    SERVER_URL = "http://127.0.0.1:8000"


def send_message(to_pub: str, from_sign_pub: str, text: str, signing_key):
    """
    Send a message to the server.
    - to_pub: recipient's encryption public key (hex)
    - from_sign_pub: your signing public key (hex)
    - text: plaintext message
    - signing_key: your SigningKey object
    """
    try:
        encrypted_b64 = encrypt_message(text, to_pub)
        signature_b64 = sign_message(encrypted_b64, signing_key)

        payload = {
            "to": to_pub,
            "from_": from_sign_pub,  
            "message": encrypted_b64,
            "signature": signature_b64
        }

        r = requests.post(f"{SERVER_URL}/send", json=payload)
        if not r.ok:
            print("Send Error:", r.status_code, r.text)
        return r.ok
    except Exception as e:
        print("Send Exception:", e)
        return False



def fetch_messages(my_pub_hex: str, private_key):
    """
    Fetch messages addressed to your encryption public key (my_pub_hex)
    """
    try:
        r = requests.get(f"{SERVER_URL}/inbox/{my_pub_hex}")
        if r.ok:
            inbox = r.json().get("messages", [])
            msgs = []
            for msg in inbox:
                msgs.append({
                    "from": msg["from"],       
                    "message": msg["message"],
                    "signature": msg.get("signature")
                })
            return msgs
    except Exception as e:
        print("Fetch Error:", e)
    return []
