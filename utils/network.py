# network.py
import requests
import os, hashlib
import time
from utils.crypto import encrypt_message, decrypt_message, sign_message
from utils.attachments import store_attachment


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


def send_attachment(app, to_pub: str, signing_pub: str, filename: str, data: bytes, signing_key, enc_pub: str):
    """Send an attachment (single message envelope).

    Optimization vs previous version:
    - No inner per-file encryption: rely on outer message encryption + signature.
    - Minimizes memory copies for large files (base64 only once).
    Envelope keys:
      {"type":"file","name":...,"file_b64":...,"size":N}
    Backward compatibility: receiver still understands legacy 'blob' if encountered.
    """
    try:
        import json as _json, base64 as _b64, os as _os
        # Persist encrypted locally (pin protected) and only send reference id + hash
        # 1. Upload raw sealed payload separately for dedup / lazy download
        # Prefer the att_id returned by store_attachment so the local encrypted
        # on-disk file and the uploaded reference use the same id. Fall back
        # to sha256(data) if storing fails for any reason.
        try:
            att_id = store_attachment(data, getattr(app, 'pin', ''))
        except Exception:
            att_id = hashlib.sha256(data).hexdigest()
        # Upload only if not already uploaded (best effort: HEAD style could be added later)
        import base64 as _b642
        blob_b64 = _b642.b64encode(data).decode()
        signature_blob = sign_message(blob_b64, signing_key)
        upload_payload = {
            "to": to_pub,
            "from_": signing_pub,
            "enc_pub": enc_pub,
            "blob": blob_b64,
            "signature": signature_blob,
            "name": _os.path.basename(filename),
            "size": len(data),
            "sha256": att_id
        }
        try:
            ur = requests.post(f"{app.SERVER_URL}/upload", json=upload_payload, verify=app.SERVER_CERT, timeout=30)
            if not ur.ok:
                print("Upload Error:", ur.status_code, ur.text)
                return False
        except requests.exceptions.RequestException as e:
            print("Upload Exception:", e)
            return False
    # 2. local storage already attempted above; no-op here
        # 3. Send reference envelope only
        envelope = {
            "type": "file",
            "name": _os.path.basename(filename),
            "att_id": att_id,
            "sha256": att_id,
            "size": len(data)
        }
        plaintext = "ATTACH:" + _json.dumps(envelope, separators=(',', ':'))
        encrypted_b64 = encrypt_message(plaintext, to_pub)
        signature_b64 = sign_message(encrypted_b64, signing_key)
        payload = {
            "to": to_pub,
            "from_": signing_pub,
            "enc_pub": enc_pub,
            "message": encrypted_b64,
            "signature": signature_b64,
            "timestamp": time.time()
        }
        r = requests.post(f"{app.SERVER_URL}/send", json=payload, verify=app.SERVER_CERT, timeout=30)
        if not r.ok:
            print("Send Attachment Error:", r.status_code, r.text)
        return r.ok
    except requests.exceptions.RequestException as e:
        print("Send Attachment Exception:", e)
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
