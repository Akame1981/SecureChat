import json
import os
import stat
import sys
from time import time

from nacl.secret import SecretBox
from nacl.utils import random

from utils.crypto import MIN_PIN_LENGTH, derive_master_key, zero_bytes

# -------------------------
# Base directories
# -------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "../data"))
CHATS_DIR = os.path.join(DATA_DIR, "chats")
os.makedirs(CHATS_DIR, exist_ok=True)

SALT_SIZE = 32

# -------------------------
# Encrypt/Decrypt helpers
# -------------------------
def get_chat_file(pub_hex: str) -> str:
    return os.path.join(CHATS_DIR, f"{pub_hex}.bin")

def encrypt_chat(data: list, pin: str) -> bytes:
    salt = random(SALT_SIZE)
    master_key = derive_master_key(pin, salt)
    box = SecretBox(master_key[:32])
    json_bytes = json.dumps(data).encode()
    encrypted = box.encrypt(json_bytes)
    zero_bytes(master_key)
    return salt + encrypted

def decrypt_chat(enc_bytes: bytes, pin: str) -> list:
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
# Public functions
# -------------------------
def save_message(pub_hex: str, sender: str, text: str, pin: str, timestamp: float = None):
    """
    Save a message with optional timestamp.
    """
    if timestamp is None:
        timestamp = time()

    chat_file = get_chat_file(pub_hex)
    if os.path.exists(chat_file):
        with open(chat_file, "rb") as f:
            try:
                chat_data = decrypt_chat(f.read(), pin)
            except Exception:
                chat_data = []
    else:
        chat_data = []

    chat_data.append({
        "sender": sender,
        "text": text,
        "timestamp": timestamp
    })

    with open(chat_file, "wb") as f:
        f.write(encrypt_chat(chat_data, pin))
    os.chmod(chat_file, stat.S_IRUSR | stat.S_IWUSR)

def load_messages(pub_hex: str, pin: str) -> list:
    """
    Load messages with timestamps.
    """
    chat_file = get_chat_file(pub_hex)
    if not os.path.exists(chat_file):
        return []
    try:
        return decrypt_chat(open(chat_file, "rb").read(), pin)
    except Exception:
        return []
