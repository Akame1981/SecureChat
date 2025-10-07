import base64
import hashlib
import hmac
import json
import os
import stat
import sys

from nacl.exceptions import CryptoError
from nacl.pwhash import SCRYPT_MEMLIMIT_INTERACTIVE, SCRYPT_OPSLIMIT_INTERACTIVE, scrypt
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.secret import SecretBox
from nacl.signing import SigningKey, VerifyKey
from nacl.utils import random


import os
import sys



def get_resource_path(relative_path):
    """Return absolute path to resource, works for dev and PyInstaller."""
    if getattr(sys, "_MEIPASS", False):
        # PyInstaller onefile mode
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)
# -------------------------
# --- Base directory setup ---
# -------------------------
if getattr(sys, "frozen", False):
    # Running as PyInstaller one-file bundle
    BASE_DIR = os.path.dirname(sys.executable)  # folder where the EXE is located
else:
    # Running as a normal Python script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# -------------------------
# --- Data folder setup ---
# -------------------------
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "../data"))
os.makedirs(DATA_DIR, exist_ok=True)

KEY_FILE = os.path.join(DATA_DIR, "keypair.bin")
MIN_PIN_LENGTH = 6

# -------------------------
# --- Config folder setup ---
# -------------------------
# Dev / user config folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.abspath(os.path.join(BASE_DIR, "../config"))
os.makedirs(CONFIG_DIR, exist_ok=True)

# Path for the weak PINs
dev_file = os.path.join(CONFIG_DIR, "weak_pins.json")
internal_file = get_resource_path("_internal/config/weak-pins.json")

# Use dev file if exists, otherwise fallback to internal bundled file
WEAK_PIN_FILE = dev_file if os.path.exists(dev_file) else internal_file
# -----------------
# --------
# --- Memory hygiene -------
# -------------------------
def zero_bytes(data):
    if isinstance(data, str):
        data = bytearray(data.encode())
    elif isinstance(data, bytes):
        data = bytearray(data)
    for i in range(len(data)):
        data[i] = 0

# -------------------------
# --- Key derivation -------
# -------------------------
def derive_master_key(pin: str, salt: bytes, size: int = SecretBox.KEY_SIZE*2) -> bytes:
    if len(pin) < MIN_PIN_LENGTH:
        raise ValueError(f"PIN too short. Must be at least {MIN_PIN_LENGTH} characters.")
    pin_bytes = pin.encode()
    key = scrypt.kdf(
        size,
        pin_bytes,
        salt,
        opslimit=SCRYPT_OPSLIMIT_INTERACTIVE,
        memlimit=SCRYPT_MEMLIMIT_INTERACTIVE
    )
    zero_bytes(pin_bytes)
    return key

# -------------------------
# --- Key saving / loading ---
# -------------------------
def save_key(private_key: PrivateKey, signing_key: SigningKey, pin: str, username: str = "Anonymous"):
    """Save keys encrypted with PIN and HMAC, plus username."""
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            version = f.read(1)
            if version != b'\x01':
                raise ValueError("Unsupported key file version")
            salt = f.read(scrypt.SALTBYTES)
    else:
        salt = random(scrypt.SALTBYTES)

    master_key = derive_master_key(pin, salt)
    enc_key = master_key[:32]
    hmac_key = master_key[32:]

    box = SecretBox(enc_key)
    # Store username as JSON, then keys
    username_bytes = json.dumps({"username": username}).encode()
    data = len(username_bytes).to_bytes(2, "big") + username_bytes + private_key.encode() + signing_key.encode()
    encrypted = box.encrypt(data)
    tag = hmac.new(hmac_key, encrypted, hashlib.sha256).digest()

    with open(KEY_FILE, "wb") as f:
        f.write(b'\x01' + salt + tag + encrypted)
    os.chmod(KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)

    zero_bytes(master_key)
    zero_bytes(enc_key)
    zero_bytes(hmac_key)

def load_key(pin: str):
    """Load keys and username using PIN"""
    if not os.path.exists(KEY_FILE):
        raise FileNotFoundError("Key file not found.")

    with open(KEY_FILE, "rb") as f:
        data = f.read()

    if data[0] != 1:
        raise ValueError("Unsupported key file version")

    salt = data[1:1+scrypt.SALTBYTES]
    tag = data[1+scrypt.SALTBYTES:1+scrypt.SALTBYTES+32]
    encrypted = data[1+scrypt.SALTBYTES+32:]

    master_key = derive_master_key(pin, salt)
    enc_key = master_key[:32]
    hmac_key = master_key[32:]

    expected_tag = hmac.new(hmac_key, encrypted, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_tag, tag):
        zero_bytes(master_key)
        zero_bytes(enc_key)
        zero_bytes(hmac_key)
        raise ValueError("Incorrect PIN or corrupted key file!")

    box = SecretBox(enc_key)
    try:
        decrypted = box.decrypt(encrypted)
        username_len = int.from_bytes(decrypted[:2], "big")
        username_json = decrypted[2:2+username_len]
        username = json.loads(username_json.decode()).get("username", "Anonymous")
        priv_bytes = decrypted[2+username_len:2+username_len+32]
        sign_bytes = decrypted[2+username_len+32:]
        return PrivateKey(priv_bytes), SigningKey(sign_bytes), username
    finally:
        zero_bytes(master_key)
        zero_bytes(enc_key)
        zero_bytes(hmac_key)

# -------------------------
# --- Change PIN ----------
# -------------------------
def change_pin(old_pin: str, new_pin: str):
    priv, sign, _ = load_key(old_pin)
    save_key(priv, sign, new_pin)

# -------------------------
# --- Authenticated Encryption ---
# -------------------------
def encrypt_message(text: str, recipient_hex: str) -> str:
    recipient = PublicKey(bytes.fromhex(recipient_hex))
    sealed = SealedBox(recipient).encrypt(text.encode())
    return base64.b64encode(sealed).decode()

def decrypt_message(enc_b64: str, private_key: PrivateKey) -> str:
    enc = base64.b64decode(enc_b64)
    box = SealedBox(private_key)
    try:
        return box.decrypt(enc).decode()
    except CryptoError:
        raise ValueError("Decryption failed. Data may be corrupted or key incorrect.")

# -------------------------
# --- Signing / Verification ---
# -------------------------
def sign_message(message_b64: str, signing_key: SigningKey) -> str:
    signature = signing_key.sign(base64.b64decode(message_b64))
    return base64.b64encode(signature.signature).decode()

def verify_signature(sender_pub_hex: str, message_b64: str, signature_b64: str) -> bool:
    try:
        verify_key = VerifyKey(bytes.fromhex(sender_pub_hex))
        verify_key.verify(base64.b64decode(message_b64), base64.b64decode(signature_b64))
        return True
    except Exception:
        return False

# -------------------------
# --- PIN Strength Check ---
# -------------------------
def load_weak_pins_set() -> set:
    """Load weak pins from JSON file into a lowercase set."""
    if not os.path.exists(WEAK_PIN_FILE):
        return set()  # fallback: empty set if file missing
    try:
        with open(WEAK_PIN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return set()
        return {x.strip().lower() for x in data if isinstance(x, str) and x.strip()}
    except Exception:
        return set()


weak_set = load_weak_pins_set()
def is_strong_pin(pin: str) -> (bool, str):
    """Validate pin strength using blacklist + rules. Returns (ok, reason)."""
    pin = pin.strip()
    if len(pin) < MIN_PIN_LENGTH:
        return False, f"PIN too short (min {MIN_PIN_LENGTH})."

    
    if pin.lower() in weak_set:
        return False, "PIN is on the blacklist."

    if len(set(pin)) == 1:
        return False, "PIN cannot be a single repeated character."

    # Simple sequential patterns (digits/letters)
    digits = "0123456789"
    letters = "abcdefghijklmnopqrstuvwxyz"
    low = pin.lower()
    if low in digits or low in digits[::-1] or low in letters or low in letters[::-1]:
        return False, "PIN cannot be a simple sequence."

    # Complexity: at least two types (digit, letter, special)
    classes = sum([
        any(c.isdigit() for c in pin),
        any(c.isalpha() for c in pin),
        any(not c.isalnum() for c in pin),
    ])
    if classes < 2:
        return False, "Use at least two types: letters, numbers, symbols."

    return True, ""
