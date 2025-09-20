import os
import base64
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.secret import SecretBox
from nacl.exceptions import CryptoError
from nacl.utils import random
from nacl.pwhash import scrypt, SCRYPT_OPSLIMIT_INTERACTIVE, SCRYPT_MEMLIMIT_INTERACTIVE
from nacl.signing import SigningKey, VerifyKey
import hmac
import hashlib
import stat

# -------------------------
# --- Data folder setup ---
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

KEY_FILE = os.path.join(DATA_DIR, "keypair.bin")  # moved to data folder
MIN_PIN_LENGTH = 6
HMAC_KEY_SIZE = 32


# -------------------------
# --- Memory hygiene -------
# -------------------------
def zero_bytes(data):
    """Overwrite sensitive data in memory (best-effort)."""
    if isinstance(data, str):
        data = bytearray(data.encode())
    elif isinstance(data, bytes):
        data = bytearray(data)
    for i in range(len(data)):
        data[i] = 0

# -------------------------
# --- Key derivation -------
# -------------------------
def derive_master_key(pin: str, salt: bytes, size: int = SecretBox.KEY_SIZE * 2) -> bytes:
    """Derive a master key of given size (default 64 bytes) from PIN using scrypt."""
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

def save_key(private_key: PrivateKey, signing_key: SigningKey, pin: str):
    """Encrypt and save private + signing key with PIN-derived key and HMAC."""
    salt = random(scrypt.SALTBYTES)
    master_key = derive_master_key(pin, salt)  # 64 bytes

    enc_key = master_key[:32]
    hmac_key = master_key[32:]

    box = SecretBox(enc_key)

    # Combine keys
    data = private_key.encode() + signing_key.encode()
    encrypted = box.encrypt(data)

    # HMAC for integrity
    tag = hmac.new(hmac_key, encrypted, hashlib.sha256).digest()

    version = b'\x01'
    with open(KEY_FILE, "wb") as f:
        f.write(version + salt + tag + encrypted)

    os.chmod(KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
    zero_bytes(master_key)
    zero_bytes(enc_key)
    zero_bytes(hmac_key)

def load_key(pin: str):
    """Load private + signing key and verify HMAC using PIN-derived key."""
    if not os.path.exists(KEY_FILE):
        raise FileNotFoundError("Key file not found.")
    with open(KEY_FILE, "rb") as f:
        data = f.read()

    version = data[0]
    if version != 1:
        raise ValueError("Unsupported key file version")

    salt = data[1:1+scrypt.SALTBYTES]
    tag = data[1+scrypt.SALTBYTES:1+scrypt.SALTBYTES+32]
    encrypted = data[1+scrypt.SALTBYTES+32:]

    master_key = derive_master_key(pin, salt)  # same derivation (64 bytes!)
    enc_key = master_key[:32]
    hmac_key = master_key[32:]

    # Verify HMAC
    expected_tag = hmac.new(hmac_key, encrypted, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_tag, tag):
        zero_bytes(master_key)
        zero_bytes(enc_key)
        zero_bytes(hmac_key)
        raise ValueError("Key file integrity check failed!")

    box = SecretBox(enc_key)

    try:
        decrypted = box.decrypt(encrypted)
        priv_bytes = decrypted[:32]
        sign_bytes = decrypted[32:]
        return PrivateKey(priv_bytes), SigningKey(sign_bytes)
    except CryptoError:
        raise ValueError("Incorrect PIN or corrupted key file!")
    finally:
        zero_bytes(master_key)
        zero_bytes(enc_key)
        zero_bytes(hmac_key)



# -------------------------
# --- Authenticated Encryption ---
# -------------------------
def encrypt_message(text: str, recipient_hex: str) -> str:
    """Encrypt with recipient's public key and add AE with SecretBox."""
    recipient = PublicKey(bytes.fromhex(recipient_hex))
    sealed = SealedBox(recipient).encrypt(text.encode())
    return base64.b64encode(sealed).decode()

def decrypt_message(enc_b64: str, private_key: PrivateKey) -> str:
    """Decrypt message using recipient's private key."""
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
def is_strong_pin(pin: str) -> bool:
    if len(pin) < MIN_PIN_LENGTH:
        return False
    if pin.isdigit():
        return len(pin) >= 10  # numeric-only stronger
    return True
