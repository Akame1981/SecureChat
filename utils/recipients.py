import json
import os
import sys
import stat

from nacl.secret import SecretBox
from nacl.utils import random

from utils.crypto import derive_master_key, zero_bytes

# -------------------------
# --- Base & data folders ---
# -------------------------
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "../data"))
os.makedirs(DATA_DIR, exist_ok=True)

RECIPIENTS_FILE = os.path.join(DATA_DIR, "recipients.json")
SALT_SIZE = 32  # random salt for encryption

# -------------------------
# --- Encrypted helpers ---
# -------------------------
def encrypt_data(data: dict, pin: str) -> bytes:
    salt = random(SALT_SIZE)
    master_key = derive_master_key(pin, salt)
    try:
        box = SecretBox(bytes(master_key[:32]))
        json_bytes = json.dumps(data).encode()
        # Use explicit random nonce for non-deterministic encryption
        encrypted = box.encrypt(json_bytes, random(SecretBox.NONCE_SIZE))
        return salt + encrypted
    finally:
        zero_bytes(master_key)

def decrypt_data(enc_bytes: bytes, pin: str) -> dict:
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
# --- Load/save recipients ---
# -------------------------
def load_recipients(pin: str) -> dict:
    if not os.path.exists(RECIPIENTS_FILE):
        return {}
    try:
        return decrypt_data(open(RECIPIENTS_FILE, "rb").read(), pin)
    except Exception:
        return {}

def save_recipients(data: dict, pin: str):
    enc_bytes = encrypt_data(data, pin)
    with open(RECIPIENTS_FILE, "wb") as f:
        f.write(enc_bytes)
    os.chmod(RECIPIENTS_FILE, stat.S_IRUSR | stat.S_IWUSR)

# -------------------------
# --- Public API ---
# -------------------------
def add_recipient(name: str, pub_key: str, pin: str):
    recipients = load_recipients(pin)
    name = name.strip()
    pub_key = pub_key.strip().lower()

    if name in recipients:
        raise ValueError(f"A recipient with the name '{name}' already exists.")
    if pub_key in recipients.values():
        existing_name = [n for n, k in recipients.items() if k == pub_key][0]
        raise ValueError(f"This public key is already assigned to '{existing_name}'.")

    recipients[name] = pub_key
    save_recipients(recipients, pin)
    print(f"Added recipient: {name} / {pub_key}")

def delete_recipient(name: str, pin: str):
    recipients = load_recipients(pin)
    if name in recipients:
        del recipients[name]
        save_recipients(recipients, pin)

def get_recipient_key(name: str, pin: str):
    recipients = load_recipients(pin)
    key = recipients.get(name)
    return key.lower() if key else None

def get_recipient_name(pub_key: str, pin: str):
    recipients = load_recipients(pin)
    pub_key = pub_key.strip().lower()
    for name, key in recipients.items():
        if key.strip().lower() == pub_key:
            return name
    return None


def ensure_recipient_exists(pub_key: str, pin: str, preferred_name: str | None = None) -> str:
    """Ensure a recipient entry exists for the given public key.

    - If the key already exists, return its name.
    - Else, create a new recipient with a generated unique name and return it.
    Name generation: preferred_name if provided and unique; otherwise
    "Unknown-<first6>" with a numeric suffix if needed to avoid collisions.
    """
    if not pub_key:
        raise ValueError("pub_key is required")

    recipients = load_recipients(pin)
    normalized = pub_key.strip().lower()

    # If key already present, return existing name
    for name, key in recipients.items():
        if key.strip().lower() == normalized:
            return name

    # Propose a base name
    base = preferred_name.strip() if preferred_name else f"Unknown-{normalized[:6]}"
    candidate = base
    i = 1
    # Ensure uniqueness among names
    while candidate in recipients:
        i += 1
        candidate = f"{base}-{i}"

    # Add and persist
    recipients[candidate] = normalized
    save_recipients(recipients, pin)
    return candidate


def set_recipient_name_for_key(pub_key: str, new_name: str, pin: str) -> str:
    """Set/rename the recipient name for a given public key.

    Behavior:
    - If the key already exists under a name, it will be moved/renamed to new_name.
    - If the key is not present, a new entry will be added with new_name.
    - If new_name exists and is mapped to a DIFFERENT key, raises ValueError.
    Returns the final name stored (new_name).
    """
    if not pub_key or not new_name:
        raise ValueError("pub_key and new_name are required")

    recipients = load_recipients(pin)
    normalized_key = pub_key.strip().lower()
    new_name = new_name.strip()

    # If the new name exists and maps to a different key, disallow to avoid ambiguity
    if new_name in recipients and recipients[new_name].strip().lower() != normalized_key:
        raise ValueError(f"A recipient with the name '{new_name}' already exists.")

    # Find current name for this key, if any
    current_name = None
    for n, k in recipients.items():
        if k.strip().lower() == normalized_key:
            current_name = n
            break

    # If name unchanged, nothing to do
    if current_name == new_name:
        return new_name

    # Remove old mapping if present
    if current_name is not None and current_name in recipients:
        try:
            del recipients[current_name]
        except Exception:
            pass

    # Set new mapping
    recipients[new_name] = normalized_key
    save_recipients(recipients, pin)
    return new_name



