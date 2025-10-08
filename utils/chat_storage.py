import json
import os
import stat
import sys
from time import time
import shutil

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
    try:
        box = SecretBox(bytes(master_key[:32]))
        json_bytes = json.dumps(data).encode()
        encrypted = box.encrypt(json_bytes)
        return salt + encrypted
    finally:
        zero_bytes(master_key)

def decrypt_chat(enc_bytes: bytes, pin: str) -> list:
    salt = enc_bytes[:SALT_SIZE]
    ciphertext = enc_bytes[SALT_SIZE:]
    master_key = derive_master_key(pin, salt)
    try:
        box = SecretBox(bytes(master_key[:32]))
        decrypted = box.decrypt(ciphertext)
        return json.loads(decrypted.decode())
    finally:
        zero_bytes(master_key)

# -------------------------
# Public functions
# -------------------------
def _atomic_write(path: str, data: bytes):
    """Write bytes atomically to path (best effort on current platform)."""
    tmp = f"{path}.tmp"
    with open(tmp, 'wb') as tf:
        tf.write(data)
        tf.flush()
        os.fsync(tf.fileno()) if hasattr(os, 'fsync') else None
    os.replace(tmp, path)


def save_message(pub_hex: str, sender: str, text: str, pin: str, timestamp: float = None):
    """Save a message with optional timestamp.

    Hardening changes:
    - Avoid silently discarding old history if decryption fails (wrong PIN / corruption).
    - Backup the original file once (.bak) if decryption fails before starting a new chain.
    - Atomic write to reduce chance of partial/corrupted files on crash.
    """
    if timestamp is None:
        timestamp = time()

    chat_file = get_chat_file(pub_hex)
    chat_data = []
    decrypt_failed = False

    if os.path.exists(chat_file):
        try:
            with open(chat_file, "rb") as f:
                existing_bytes = f.read()
            chat_data = decrypt_chat(existing_bytes, pin)
        except Exception as e:
            # Flag failure; we will archive old file and start a new log
            decrypt_failed = True
            print(f"[chat_storage] Decrypt failed for {chat_file}: {e}. Will back up and start new history.")

    if decrypt_failed:
        backup_path = chat_file + ".bak"
        try:
            if not os.path.exists(backup_path):
                shutil.copy2(chat_file, backup_path)
                try:
                    os.chmod(backup_path, stat.S_IRUSR | stat.S_IWUSR)
                except Exception:
                    pass
        except Exception as e:
            print(f"[chat_storage] Failed to create backup {backup_path}: {e}")
        # Start a fresh chain and inject a sentinel system notice
        chat_data = [{
            "sender": "system",
            "text": "Previous chat history could not be decrypted and was archived as .bak.",
            "timestamp": time()
        }]

    chat_data.append({
        "sender": sender,
        "text": text,
        "timestamp": timestamp
    })

    try:
        encrypted = encrypt_chat(chat_data, pin)
        _atomic_write(chat_file, encrypted)
        os.chmod(chat_file, stat.S_IRUSR | stat.S_IWUSR)
    except Exception as e:
        print(f"[chat_storage] Failed to write chat file {chat_file}: {e}")

def load_messages(pub_hex: str, pin: str) -> list:
    """Load messages with timestamps.

    Returns [] if file missing; logs and returns [] on decrypt failure (does NOT delete or truncate).
    """
    chat_file = get_chat_file(pub_hex)
    if not os.path.exists(chat_file):
        return []
    try:
        with open(chat_file, 'rb') as f:
            data = f.read()
        return decrypt_chat(data, pin)
    except Exception as e:
        print(f"[chat_storage] Decrypt failed for {chat_file}: {e}")
        return []
