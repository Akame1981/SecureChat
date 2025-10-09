import base64
import hashlib
import hmac
import json
import os
import stat
import sys
import tempfile

from nacl.exceptions import CryptoError
from nacl.pwhash import SCRYPT_MEMLIMIT_INTERACTIVE, SCRYPT_OPSLIMIT_INTERACTIVE, scrypt
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.secret import SecretBox
from nacl.signing import SigningKey, VerifyKey
from nacl.utils import random
try:
    from nacl.bindings import sodium_memzero
    _HAS_SODIUM_MEMZERO = True
except Exception:
    sodium_memzero = None
    _HAS_SODIUM_MEMZERO = False



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
    """Attempt to zero a mutable bytearray in-place.

    Notes:
    - Immutable `bytes` cannot be reliably zeroed in-place in Python.
    - For values we control (derived keys) we convert to `bytearray` so this
      function can zero them in-place. If an immutable `bytes` is passed we
      convert and zero the temporary copy (best-effort).
    """
    # If libsodium's sodium_memzero is available, prefer it for better guarantees.
    if _HAS_SODIUM_MEMZERO:
        try:
            # sodium_memzero accepts a writable buffer
            sodium_memzero(data)
            return
        except Exception:
            # Fall back to Python-level zeroing
            pass

    if isinstance(data, bytearray):
        for i in range(len(data)):
            data[i] = 0
        return
    if isinstance(data, memoryview):
        try:
            data.cast('B')[:] = b'\x00' * len(data)
            return
        except Exception:
            pass
    # Fallback: make a mutable copy and zero that (best-effort)
    if isinstance(data, str):
        data = bytearray(data.encode())
    elif isinstance(data, bytes):
        data = bytearray(data)
    for i in range(len(data)):
        data[i] = 0

# -------------------------
# --- Key derivation -------
# -------------------------
def derive_master_key(pin: str, salt: bytes, size: int = SecretBox.KEY_SIZE*2) -> bytearray:
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
    # Convert to mutable bytearray so callers can securely zero it later
    key_ba = bytearray(key)
    zero_bytes(pin_bytes)
    # Attempt to zero the original immutable bytes object 'key'
    try:
        zero_bytes(key)
    except Exception:
        pass
    return key_ba

# -------------------------
# --- Key saving / loading ---
# -------------------------
def save_key(private_key: PrivateKey, signing_key: SigningKey, pin: str, username: str = "Anonymous"):
    """Save keys encrypted with PIN and HMAC, plus username.

    Always generate a fresh salt on save to avoid reuse across rekey operations.
    Write is atomic (temp file + replace) to avoid half-written files.
    """
    salt = random(scrypt.SALTBYTES)

    master_key = derive_master_key(pin, salt)
    # master_key is a bytearray now
    enc_key = master_key[:32]
    hmac_key = master_key[32:]

    box = SecretBox(bytes(enc_key))
    # Store username as JSON, then keys
    username_bytes = json.dumps({"username": username}).encode()
    data = len(username_bytes).to_bytes(2, "big") + username_bytes + private_key.encode() + signing_key.encode()
    # Explicitly generate a fresh random nonce so encryption is non-deterministic
    nonce = random(SecretBox.NONCE_SIZE)
    encrypted = box.encrypt(data, nonce)
    tag = hmac.new(bytes(hmac_key), encrypted, hashlib.sha256).digest()

    # Atomic write: write to a temp file then replace
    dirpath = os.path.dirname(KEY_FILE)
    fd, tmp_path = tempfile.mkstemp(dir=dirpath)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(b'\x01' + salt + tag + encrypted)
        try:
            os.replace(tmp_path, KEY_FILE)
        except Exception:
            # Fallback to rename
            os.rename(tmp_path, KEY_FILE)
        try:
            os.chmod(KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            # os.chmod may be a no-op on Windows; ignore failures
            pass
    finally:
        # Ensure tmp file is removed if something went wrong
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    # Zero sensitive material
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
    # master_key is a bytearray
    enc_key = master_key[:32]
    hmac_key = master_key[32:]

    expected_tag = hmac.new(bytes(hmac_key), encrypted, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_tag, tag):
        zero_bytes(master_key)
        zero_bytes(enc_key)
        zero_bytes(hmac_key)
        raise ValueError("Incorrect PIN or corrupted key file!")

    # SecretBox requires an immutable 32-byte key
    box = SecretBox(bytes(enc_key))
    try:
        decrypted = box.decrypt(encrypted)  # bytes
        # Work on a mutable copy so we can zero it after parsing
        buf = bytearray(decrypted)
        try:
            username_len = int.from_bytes(buf[:2], "big")
            username_json = bytes(buf[2:2+username_len])
            username = json.loads(username_json.decode()).get("username", "Anonymous")
            priv_bytes = bytes(buf[2+username_len:2+username_len+32])
            sign_bytes = bytes(buf[2+username_len+32:])
            return PrivateKey(priv_bytes), SigningKey(sign_bytes), username
        finally:
            # Zero the mutable buffer containing plaintext
            zero_bytes(buf)
    finally:
        # Attempt to zero sensitive in-memory buffers
        try:
            zero_bytes(master_key)
            zero_bytes(enc_key)
            zero_bytes(hmac_key)
        except Exception:
            pass

# -------------------------
# --- Change PIN ----------
# -------------------------
def change_pin(old_pin: str, new_pin: str):
    priv, sign, username = load_key(old_pin)
    # Re-save with same username and a fresh salt
    save_key(priv, sign, new_pin, username)

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

# --- Binary helpers (attachments) ---
def encrypt_blob(data: bytes, recipient_hex: str) -> str:
    """Encrypt arbitrary binary data for a recipient and return base64(ciphertext).

    Uses the same SealedBox primitive as encrypt_message but accepts bytes.
    """
    recipient = PublicKey(bytes.fromhex(recipient_hex))
    sealed = SealedBox(recipient).encrypt(data)
    return base64.b64encode(sealed).decode()

def decrypt_blob(enc_b64: str, private_key: PrivateKey) -> bytes:
    """Decrypt base64(ciphertext) produced by encrypt_blob back to plaintext bytes."""
    enc = base64.b64decode(enc_b64)
    box = SealedBox(private_key)
    try:
        return box.decrypt(enc)
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
def is_strong_pin(pin: str) -> tuple[bool, str]:
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
