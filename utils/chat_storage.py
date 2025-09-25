import json
import os
import stat
import sys

from nacl.secret import SecretBox
from nacl.utils import random

from utils.crypto import MIN_PIN_LENGTH, derive_master_key, zero_bytes


# -------------------------
# --- Base directory setup ---
# -------------------------
if getattr(sys, "frozen", False):
    # Running as PyInstaller one-file bundle
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running as a normal Python script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -------------------------
# --- Data folder setup ---
# -------------------------
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "../data"))
CHATS_DIR = os.path.join(DATA_DIR, "chats")
os.makedirs(CHATS_DIR, exist_ok=True)

SALT_SIZE = 32  # for chat encryption

# -------------------------
# --- Encrypt/Decrypt helpers ---
# -------------------------
def get_chat_file(pub_hex: str) -> str:
    return os.path.join(CHATS_DIR, f"{pub_hex}.bin")

def encrypt_chat(data: dict, pin: str) -> bytes:
    salt = random(SALT_SIZE)
    master_key = derive_master_key(pin, salt)
    box = SecretBox(master_key[:32])
    json_bytes = json.dumps(data).encode()
    encrypted = box.encrypt(json_bytes)
    zero_bytes(master_key)
    return salt + encrypted  # prepend salt

def decrypt_chat(enc_bytes: bytes, pin: str) -> dict:
    salt = enc_bytes[:SALT_SIZE]
    ciphertext = enc_bytes[SALT_SIZE:]
    master_key = derive_master_key(pin, salt)
    box = SecretBox(master_key[:32])
    try:
        decrypted = box.decrypt(ciphertext)
        return json.loads(decrypted.decode())
    finally:
        zero_bytes(master_key)









# -------------------------
# --- Public functions ---
# -------------------------
def save_message(pub_hex: str, sender: str, text: str, pin: str):
    chat_file = get_chat_file(pub_hex)
    if os.path.exists(chat_file):
        with open(chat_file, "rb") as f:
            try:
                chat_data = decrypt_chat(f.read(), pin)
            except Exception:
                chat_data = []
    else:
        chat_data = []

    chat_data.append({"sender": sender, "text": text})
    with open(chat_file, "wb") as f:
        f.write(encrypt_chat(chat_data, pin))
    os.chmod(chat_file, stat.S_IRUSR | stat.S_IWUSR)

def load_messages(pub_hex: str, pin: str) -> list:
    chat_file = get_chat_file(pub_hex)
    if not os.path.exists(chat_file):
        return []
    try:
        return decrypt_chat(open(chat_file, "rb").read(), pin)
    except Exception:
        return []  # maybe wrong pin or corrupted file
