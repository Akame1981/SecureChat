import os
import base64
import ctypes
from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.secret import SecretBox
from nacl.exceptions import CryptoError
from nacl.utils import random
from nacl.pwhash import scrypt, SCRYPT_OPSLIMIT_INTERACTIVE, SCRYPT_MEMLIMIT_INTERACTIVE
import stat

KEY_FILE = "keypair.bin"


# -------------------------
# --- Key derivation -------
# -------------------------
def derive_key(pin: str, salt: bytes) -> bytes:
    """Derive a 32-byte key from PIN using scrypt with a salt."""
    key = scrypt.kdf(
        SecretBox.KEY_SIZE,
        pin.encode(),
        salt,
        opslimit=SCRYPT_OPSLIMIT_INTERACTIVE,
        memlimit=SCRYPT_MEMLIMIT_INTERACTIVE
    )
    zero_bytes(pin)
    return key


def zero_bytes(data):
    """Overwrite sensitive data in memory."""
    if isinstance(data, str):
        data = bytearray(data.encode())
    elif isinstance(data, bytes):
        data = bytearray(data)
    # Overwrite each byte
    for i in range(len(data)):
        data[i] = 0



# -------------------------
# --- Persistent keypair ---
# -------------------------
def save_key(private_key: PrivateKey, pin: str):
    """Encrypt and save the private key to disk."""
    salt = random(scrypt.SALTBYTES)
    key = derive_key(pin, salt)
    box = SecretBox(key)
    encrypted = box.encrypt(private_key.encode())
    with open(KEY_FILE, "wb") as f:
        f.write(salt + encrypted)
    os.chmod(KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)  # Owner read/write only
    zero_bytes(key)


def load_key(pin: str) -> PrivateKey:
    """Load and decrypt the private key from disk."""
    if not os.path.exists(KEY_FILE):
        raise FileNotFoundError("Key file not found.")
    with open(KEY_FILE, "rb") as f:
        data = f.read()
    salt = data[:scrypt.SALTBYTES]
    encrypted = data[scrypt.SALTBYTES:]
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
    """Encrypt a message using recipient's public key."""
    recipient = PublicKey(bytes.fromhex(recipient_hex))
    box = SealedBox(recipient)
    encrypted = box.encrypt(text.encode())
    return base64.b64encode(encrypted).decode()


def decrypt_message(enc_b64: str, private_key: PrivateKey) -> str:
    """Decrypt a message using your private key."""
    enc = base64.b64decode(enc_b64)
    box = SealedBox(private_key)
    return box.decrypt(enc).decode()
