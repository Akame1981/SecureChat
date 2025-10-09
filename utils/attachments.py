import os, hashlib, stat
from nacl.secret import SecretBox
from nacl.utils import random
from .crypto import derive_master_key, zero_bytes

# Directory for encrypted attachment blobs
def _attachments_dir():
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/attachments'))
    os.makedirs(base, exist_ok=True)
    return base

MARKER = b"\xA1"  # simple format marker to distinguish future versions
SALT_SIZE = 32

class AttachmentNotFound(Exception):
    pass


def store_attachment(data: bytes, pin: str) -> str:
    """Encrypt and persist attachment bytes, returning deterministic id (sha256 hex).

    If a file with the same hash already exists, it is not rewritten.
    Layout: [MARKER][salt(32)][secretbox(cipher)]
    SecretBox key derived from pin+salt via existing derive_master_key.
    """
    h = hashlib.sha256(data).hexdigest()
    path = os.path.join(_attachments_dir(), f"{h}.bin")
    if os.path.exists(path):
        return h
    salt = random(SALT_SIZE)
    master = derive_master_key(pin, salt)
    try:
        box = SecretBox(bytes(master[:32]))
        # Use explicit nonce so attachments encrypted twice won't match
        enc = box.encrypt(data, random(SecretBox.NONCE_SIZE))
        blob = MARKER + salt + enc
        tmp = path + '.tmp'
        with open(tmp, 'wb') as f:
            f.write(blob)
            try: f.flush(); os.fsync(f.fileno())
            except Exception: pass
        os.replace(tmp, path)
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass
    finally:
        zero_bytes(master)
    return h


def load_attachment(att_id: str, pin: str) -> bytes:
    path = os.path.join(_attachments_dir(), f"{att_id}.bin")
    if not os.path.exists(path):
        raise AttachmentNotFound(att_id)
    with open(path, 'rb') as f:
        blob = f.read()
    if not blob or blob[0:1] != MARKER:
        raise ValueError('Invalid attachment format')
    salt = blob[1:1+SALT_SIZE]
    ciphertext = blob[1+SALT_SIZE:]
    master = derive_master_key(pin, salt)
    try:
        box = SecretBox(bytes(master[:32]))
        return box.decrypt(ciphertext)
    finally:
        zero_bytes(master)

