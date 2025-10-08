import json
import os
import stat
import sys
from time import time
import shutil
import threading

from nacl.secret import SecretBox
from nacl.utils import random
import msgpack

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
SEGMENT_SIZE = 300  # messages per segment before rolling

# Per-chat locks to avoid race conditions when appending simultaneously
_chat_locks = {}
_locks_lock = threading.Lock()

def _get_lock(pub_hex: str):
    with _locks_lock:
        lock = _chat_locks.get(pub_hex)
        if not lock:
            lock = threading.Lock()
            _chat_locks[pub_hex] = lock
        return lock

# -------------------------
# Encrypt/Decrypt helpers
# -------------------------
def get_chat_file(pub_hex: str) -> str:
    return os.path.join(CHATS_DIR, f"{pub_hex}.bin")

def get_chat_dir(pub_hex: str) -> str:
    return os.path.join(CHATS_DIR, pub_hex)

def _segment_path(pub_hex: str, index: int) -> str:
    return os.path.join(get_chat_dir(pub_hex), f"s{index:03d}.bin")

def is_segmented(pub_hex: str) -> bool:
    return os.path.isdir(get_chat_dir(pub_hex))

def _list_segment_indices(pub_hex: str) -> list:
    d = get_chat_dir(pub_hex)
    if not os.path.isdir(d):
        return []
    indices = []
    for name in os.listdir(d):
        if name.startswith('s') and name.endswith('.bin') and len(name) == 8:  # s000.bin
            try:
                indices.append(int(name[1:4]))
            except ValueError:
                pass
    return sorted(indices)

def _write_segment(pub_hex: str, index: int, messages: list, pin: str):
    path = _segment_path(pub_hex, index)
    encrypted = encrypt_chat(messages, pin)
    _atomic_write(path, encrypted)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass

def encrypt_chat(data: list, pin: str) -> bytes:
    """Serialize (msgpack) + encrypt chat list. Prepend salt and a format marker byte.

    Format: [1-byte format marker][32-byte salt][SecretBox(payload)]
    Markers:
      0x01 = msgpack
      0x00 = legacy (no marker, JSON) -> we keep support in decrypt_chat
    """
    salt = random(SALT_SIZE)
    master_key = derive_master_key(pin, salt)
    try:
        box = SecretBox(bytes(master_key[:32]))
        packed = msgpack.packb(data, use_bin_type=True)
        encrypted = box.encrypt(packed)
        return b"\x01" + salt + encrypted
    finally:
        zero_bytes(master_key)

def decrypt_chat(enc_bytes: bytes, pin: str) -> list:
    """Decrypt and deserialize chat data.

    Supports legacy JSON format (no leading marker, first 32 bytes are salt) and
    new format with a 1-byte marker followed by salt.
    """
    if not enc_bytes:
        return []
    # Detect marker
    first = enc_bytes[0]
    if first in (0x00, 0x7b, 0x5b):  # legacy: starts directly with salt (0x00 marker we never used) or '{' '[' if unencrypted
        # Legacy layout: [salt (32)][cipher]
        salt = enc_bytes[:SALT_SIZE]
        ciphertext = enc_bytes[SALT_SIZE:]
        master_key = derive_master_key(pin, salt)
        try:
            box = SecretBox(bytes(master_key[:32]))
            decrypted = box.decrypt(ciphertext)
            # Try JSON then msgpack (defensive)
            try:
                return json.loads(decrypted.decode())
            except Exception:
                return msgpack.unpackb(decrypted, raw=False)
        finally:
            zero_bytes(master_key)
    else:
        # New layout: [marker][salt][cipher]
        marker = first
        salt = enc_bytes[1:1 + SALT_SIZE]
        ciphertext = enc_bytes[1 + SALT_SIZE:]
        master_key = derive_master_key(pin, salt)
        try:
            box = SecretBox(bytes(master_key[:32]))
            decrypted = box.decrypt(ciphertext)
            if marker == 0x01:
                return msgpack.unpackb(decrypted, raw=False)
            # Unknown marker: fallback attempts
            try:
                return json.loads(decrypted.decode())
            except Exception:
                return msgpack.unpackb(decrypted, raw=False)
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

    lock = _get_lock(pub_hex)
    with lock:
        # Segmented path
        if is_segmented(pub_hex):
            seg_dir = get_chat_dir(pub_hex)
            os.makedirs(seg_dir, exist_ok=True)
            indices = _list_segment_indices(pub_hex)
            if not indices:
                # first segment
                _write_segment(pub_hex, 0, [{"sender": sender, "text": text, "timestamp": timestamp}], pin)
                return
            last_idx = indices[-1]
            # load last segment only
            last_path = _segment_path(pub_hex, last_idx)
            try:
                with open(last_path, 'rb') as f:
                    last_bytes = f.read()
                last_messages = decrypt_chat(last_bytes, pin)
            except Exception as e:
                print(f"[chat_storage] Failed to decrypt last segment {last_path}: {e}. Starting new segment.")
                last_messages = []
            last_messages.append({"sender": sender, "text": text, "timestamp": timestamp})
            if len(last_messages) > SEGMENT_SIZE:
                # roll to new segment with just this new message
                _write_segment(pub_hex, last_idx + 1, [{"sender": sender, "text": text, "timestamp": timestamp}], pin)
            else:
                _write_segment(pub_hex, last_idx, last_messages, pin)
            return

        # Legacy single-file path
        chat_file = get_chat_file(pub_hex)
        chat_data = []
        decrypt_failed = False
        if os.path.exists(chat_file):
            try:
                with open(chat_file, 'rb') as f:
                    existing_bytes = f.read()
                chat_data = decrypt_chat(existing_bytes, pin)
            except Exception as e:
                decrypt_failed = True
                print(f"[chat_storage] Decrypt failed for {chat_file}: {e}. Will back up and start new history.")

        if decrypt_failed:
            backup_path = chat_file + '.bak'
            try:
                if not os.path.exists(backup_path):
                    shutil.copy2(chat_file, backup_path)
                    try:
                        os.chmod(backup_path, stat.S_IRUSR | stat.S_IWUSR)
                    except Exception:
                        pass
            except Exception as e:
                print(f"[chat_storage] Failed to create backup {backup_path}: {e}")
            chat_data = [{
                'sender': 'system',
                'text': 'Previous chat history could not be decrypted and was archived as .bak.',
                'timestamp': time()
            }]

        chat_data.append({'sender': sender, 'text': text, 'timestamp': timestamp})

        # If threshold exceeded, migrate to segmented
        if len(chat_data) > SEGMENT_SIZE:
            seg_dir = get_chat_dir(pub_hex)
            try:
                os.makedirs(seg_dir, exist_ok=True)
                # split into segments of SEGMENT_SIZE
                for idx, start in enumerate(range(0, len(chat_data), SEGMENT_SIZE)):
                    part = chat_data[start:start + SEGMENT_SIZE]
                    _write_segment(pub_hex, idx, part, pin)
                # remove legacy file after migration
                try:
                    os.remove(chat_file)
                except Exception:
                    pass
                return
            except Exception as e:
                print(f"[chat_storage] Migration to segmented failed for {pub_hex}: {e}. Falling back to legacy write.")

        try:
            encrypted = encrypt_chat(chat_data, pin)
            _atomic_write(chat_file, encrypted)
            os.chmod(chat_file, stat.S_IRUSR | stat.S_IWUSR)
        except Exception as e:
            print(f"[chat_storage] Failed to write chat file {chat_file}: {e}")

def load_all_segments(pub_hex: str, pin: str) -> list:
    messages = []
    indices = _list_segment_indices(pub_hex)
    for idx in indices:
        path = _segment_path(pub_hex, idx)
        try:
            with open(path, 'rb') as f:
                data = f.read()
            seg_msgs = decrypt_chat(data, pin)
            if isinstance(seg_msgs, list):
                messages.extend(seg_msgs)
        except Exception as e:
            print(f"[chat_storage] Failed to load segment {path}: {e}")
    return messages

def load_recent_messages(pub_hex: str, pin: str, recent_segments: int = 2, max_messages: int | None = None) -> list:
    if not is_segmented(pub_hex):
        all_msgs = load_messages(pub_hex, pin)
        if max_messages:
            return all_msgs[-max_messages:]
        return all_msgs
    indices = _list_segment_indices(pub_hex)
    take = indices[-recent_segments:] if recent_segments > 0 else indices
    collected = []
    for idx in take:
        path = _segment_path(pub_hex, idx)
        try:
            with open(path, 'rb') as f:
                data = f.read()
            seg_msgs = decrypt_chat(data, pin)
            if isinstance(seg_msgs, list):
                collected.extend(seg_msgs)
        except Exception as e:
            print(f"[chat_storage] Failed to load recent segment {path}: {e}")
    if max_messages and len(collected) > max_messages:
        return collected[-max_messages:]
    return collected

def load_messages(pub_hex: str, pin: str) -> list:
    """Unified loader (legacy or segmented)."""
    if is_segmented(pub_hex):
        return load_all_segments(pub_hex, pin)
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
