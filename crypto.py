import os
import base64
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.secret import SecretBox
from nacl.exceptions import CryptoError
from nacl.utils import random
from nacl.pwhash import scrypt, SCRYPT_OPSLIMIT_INTERACTIVE, SCRYPT_MEMLIMIT_INTERACTIVE
from nacl.signing import SigningKey, VerifyKey
import stat

KEY_FILE = "keypair.bin"
MIN_PIN_LENGTH = 6  # Enforce minimum PIN length

# -------------------------
# --- Key derivation -------
# -------------------------
def derive_key(pin: str, salt: bytes) -> bytes:
    """Derive a 32-byte key from PIN using scrypt with a salt."""
    if len(pin) < MIN_PIN_LENGTH:
        raise ValueError(f"PIN too short. Must be at least {MIN_PIN_LENGTH} characters.")
    pin_bytes = pin.encode()
    key = scrypt.kdf(
        SecretBox.KEY_SIZE,
        pin_bytes,
        salt,
        opslimit=SCRYPT_OPSLIMIT_INTERACTIVE,
        memlimit=SCRYPT_MEMLIMIT_INTERACTIVE
    )
    zero_bytes(bytearray(pin_bytes))
    return key

def zero_bytes(data):
    """Overwrite sensitive data in memory (best-effort in Python)."""
    if isinstance(data, str):
        data = bytearray(data.encode())
    elif isinstance(data, bytes):
        data = bytearray(data)
    for i in range(len(data)):
        data[i] = 0

# -------------------------
# --- Persistent keypair ---
# -------------------------
def save_key(private_key: PrivateKey, signing_key: SigningKey, pin: str):
    """Encrypt and save private and signing key to disk securely."""
    salt = random(scrypt.SALTBYTES)
    key = derive_key(pin, salt)
    box = SecretBox(key)

    # Store both encryption key and signing seed
    data_to_store = private_key.encode() + signing_key.encode()
    encrypted = box.encrypt(data_to_store)

    version = b'\x01'
    with open(KEY_FILE, "wb") as f:
        f.write(version + salt + encrypted)

    os.chmod(KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
    zero_bytes(key)

def load_key(pin: str):
    """Load private and signing key from disk."""
    if not os.path.exists(KEY_FILE):
        raise FileNotFoundError("Key file not found.")
    with open(KEY_FILE, "rb") as f:
        data = f.read()

    version = data[0]
    if version != 1:
        raise ValueError("Unsupported key file version")

    salt = data[1:1 + scrypt.SALTBYTES]
    encrypted = data[1 + scrypt.SALTBYTES:]

    key = derive_key(pin, salt)
    box = SecretBox(key)

    try:
        decrypted = box.decrypt(encrypted)
        zero_bytes(key)
        priv_bytes = decrypted[:32]
        sign_bytes = decrypted[32:]
        return PrivateKey(priv_bytes), SigningKey(sign_bytes)
    except CryptoError:
        zero_bytes(key)
        raise ValueError("Incorrect PIN or corrupted key file!")

# -------------------------
# --- Encryption / Decryption ---
# -------------------------
def encrypt_message(text: str, recipient_hex: str) -> str:
    recipient = PublicKey(bytes.fromhex(recipient_hex))
    box = SealedBox(recipient)
    encrypted = box.encrypt(text.encode())
    return base64.b64encode(encrypted).decode()

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
    """
    Sign a base64-encoded encrypted message using your signing key.
    Returns base64 signature.
    """
    signature = signing_key.sign(base64.b64decode(message_b64))
    return base64.b64encode(signature.signature).decode()


def verify_signature(sender_pub_hex: str, message_b64: str, signature_b64: str) -> bool:
    """
    Verify a signed message with the sender's public key (Ed25519).
    """
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
        return len(pin) >= 8
    return True
