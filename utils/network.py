import requests
from utils.crypto import encrypt_message, decrypt_message, sign_message

USE_PUBLIC_SERVER = True  # Set False for localhost / You wanna host your own server

if USE_PUBLIC_SERVER:
    SERVER_URL = "https://34.61.34.132:8000"  # Official Public Server 
    SERVER_CERT = "utils/cert.pem"     
else:
    SERVER_URL = "http://127.0.0.1:8000"
    SERVER_CERT = None  # No cert for HTTP



def send_message(to_pub: str, signing_pub: str, text: str, signing_key, enc_pub: str):
    """
    Send a message to the server.
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
            "signature": signature_b64
        }

        r = requests.post(f"{SERVER_URL}/send", json=payload, verify=SERVER_CERT)
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
        r = requests.get(f"{SERVER_URL}/inbox/{my_pub_hex}", verify=SERVER_CERT)
        if r.ok:
            inbox = r.json().get("messages", [])
            msgs = []
            for msg in inbox:
                msgs.append({
                    "from_sign": msg["from"],
                    "from_enc": msg["enc_pub"],
                    "message": msg["message"],
                    "signature": msg.get("signature")
                })
            return msgs
    except Exception as e:
        print("Fetch Error:", e)
    return []
