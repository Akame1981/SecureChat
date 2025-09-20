import os
import base64
import ctypes
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.secret import SecretBox
from nacl.exceptions import CryptoError
from nacl.utils import random
from nacl.pwhash import scrypt, SCRYPT_OPSLIMIT_INTERACTIVE, SCRYPT_MEMLIMIT_INTERACTIVE
import stat
import hashlib

KEY_FILE = "keypair.bin"
MIN_PIN_LENGTH = 6  # Enforce minimum PIN length


# -------------------------
# --- Key derivation -------
# -------------------------
def derive_key(pin: str, salt: bytes) -> bytes:
    """Derive a 32-byte key from PIN using scrypt with a salt."""
    if len(pin) < MIN_PIN_LENGTH:
        raise ValueError(f"PIN too short. Must be at least {MIN_PIN_LENGTH} characters.")

    pin_bytes = pin.encode()  # encode as bytes
    key = scrypt.kdf(
        SecretBox.KEY_SIZE,
        pin_bytes,
        salt,
        opslimit=SCRYPT_OPSLIMIT_INTERACTIVE,
        memlimit=SCRYPT_MEMLIMIT_INTERACTIVE
    )
    
    # Attempt to zero the bytearray copy (best-effort)
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
def save_key(private_key: PrivateKey, pin: str):
    """Encrypt and save the private key to disk securely."""
    salt = random(scrypt.SALTBYTES)
    key = derive_key(pin, salt)
    box = SecretBox(key)
    
    # Encrypted data includes authentication
    encrypted = box.encrypt(private_key.encode())
    
    # Include a version byte for future-proofing
    version = b'\x01'
    with open(KEY_FILE, "wb") as f:
        f.write(version + salt + encrypted)
    
    # Secure file permissions: owner read/write only
    os.chmod(KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
    zero_bytes(key)


def load_key(pin: str) -> PrivateKey:
    """Load and decrypt the private key from disk."""
    if not os.path.exists(KEY_FILE):
        raise FileNotFoundError("Key file not found.")
    
    with open(KEY_FILE, "rb") as f:
        data = f.read()
    
    # Versioning for future changes
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
        return PrivateKey(decrypted)
    except CryptoError:
        zero_bytes(key)
        raise ValueError("Incorrect PIN or corrupted key file!")


# -------------------------
# --- Encryption / Decryption ---
# -------------------------
def encrypt_message(text: str, recipient_hex: str) -> str:
    """Encrypt a message using recipient's public key with forward secrecy."""
    if not text:
        raise ValueError("Cannot encrypt empty message")
    
    recipient = PublicKey(bytes.fromhex(recipient_hex))
    box = SealedBox(recipient)
    encrypted = box.encrypt(text.encode())
    
    return base64.b64encode(encrypted).decode()


def decrypt_message(enc_b64: str, private_key: PrivateKey) -> str:
    """Decrypt a message using your private key."""
    enc = base64.b64decode(enc_b64)
    box = SealedBox(private_key)
    
    try:
        return box.decrypt(enc).decode()
    except CryptoError:
        raise ValueError("Decryption failed. Data may be corrupted or key incorrect.")


# -------------------------
# --- Optional: PIN Strength Check ---
# -------------------------
def is_strong_pin(pin: str) -> bool:
    """Simple check for PIN strength."""
    if len(pin) < MIN_PIN_LENGTH:
        return False
    if pin.isdigit():
        return len(pin) >= 8  # Require longer numeric PINs
    return True
