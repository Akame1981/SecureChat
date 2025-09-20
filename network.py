import requests
from crypto import encrypt_message, decrypt_message, sign_message

SERVER_URL = "http://127.0.0.1:8000"

def send_message(to_pub: str, from_pub: str, text: str, signing_key):
    try:
        encrypted_b64 = encrypt_message(text, to_pub)
        signature_b64 = sign_message(encrypted_b64, signing_key)  # <-- OK
        payload = {
            "to": to_pub,
            "from_": from_pub,
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
    try:
        r = requests.get(f"{SERVER_URL}/inbox/{my_pub_hex}")
        if r.ok:
            inbox = r.json().get("messages", [])
            decrypted_msgs = []
            for msg in inbox:
                decrypted = decrypt_message(msg["message"], private_key)
                decrypted_msgs.append({
                    "from": msg["from"],
                    "message": decrypted
                })
            return decrypted_msgs
    except Exception as e:
        print("Fetch Error:", e)
    return []
