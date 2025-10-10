import os
import sys
import json
from typing import Optional

# Prefer sqlcipher3 (sqlcipher3-wheels). Fallbacks are best-effort for dev.
try:
    import sqlcipher3 as sqlcipher
except Exception:
    try:
        import pysqlcipher3 as sqlcipher  # type: ignore
    except Exception:
        import sqlite3 as sqlcipher  # type: ignore

import base64

from nacl.utils import random as nacl_random
from nacl.secret import SecretBox

from utils.path_utils import get_resource_path
from utils.crypto import derive_master_key, zero_bytes
import tempfile
import shutil

# Detect whether the imported DB module is a real SQLCipher binding or the
# stdlib sqlite3 fallback. When using stdlib sqlite3 we provide an
# application-level encrypted file wrapper so the on-disk DB (and schema)
# aren't visible in plaintext.
IS_SQLCIPHER = getattr(sqlcipher, '__name__', '') != 'sqlite3'

# File header magic for application-level encrypted DB files
APP_DB_MAGIC = b'WHISPRDBv1'


def _is_app_encrypted_file(path: str) -> bool:
    try:
        with open(path, 'rb') as f:
            hdr = f.read(len(APP_DB_MAGIC))
            return hdr == APP_DB_MAGIC
    except Exception:
        return False


def _decrypt_db_file_to_temp(pin: str, temp_path: str) -> None:
    """Decrypt DB_PATH (app-encrypted) into plaintext at temp_path.

    Raises ValueError if DB_PATH is not app-encrypted. Raises other exceptions
    on decryption errors (bad PIN / corrupted data).
    """
    if not os.path.exists(DB_PATH):
        return
    if not _is_app_encrypted_file(DB_PATH):
        raise ValueError("DB file is not application-encrypted")
    with open(DB_PATH, 'rb') as f:
        data = f.read()[len(APP_DB_MAGIC):]
    ct = base64.b64decode(data)
    box = _enc_box_from_pin(pin)
    pt = box.decrypt(ct)
    with open(temp_path, 'wb') as f:
        f.write(pt)


def _encrypt_temp_db_to_file(pin: str, temp_path: str) -> None:
    """Encrypt the plaintext DB at temp_path and atomically write to DB_PATH."""
    with open(temp_path, 'rb') as f:
        pt = f.read()
    box = _enc_box_from_pin(pin)
    # Use a fresh random nonce for each encryption to avoid deterministic output
    nonce = nacl_random(SecretBox.NONCE_SIZE)
    ct = box.encrypt(pt, nonce)
    b64 = base64.b64encode(ct)
    dirpath = os.path.dirname(DB_PATH)
    fd, tmp_out = tempfile.mkstemp(dir=dirpath)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(APP_DB_MAGIC + b64)
        try:
            os.replace(tmp_out, DB_PATH)
        except Exception:
            os.rename(tmp_out, DB_PATH)
    finally:
        if os.path.exists(tmp_out):
            try:
                os.remove(tmp_out)
            except Exception:
                pass


if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, "../data"))
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "whispr_messages.db")
DB_SALT_PATH = os.path.join(DATA_DIR, "db_salt.bin")

SALT_SIZE = 32


def _ensure_db_salt() -> bytes:
    if os.path.exists(DB_SALT_PATH):
        with open(DB_SALT_PATH, 'rb') as f:
            return f.read()
    salt = nacl_random(SALT_SIZE)
    with open(DB_SALT_PATH, 'wb') as f:
        f.write(salt)
    try:
        os.chmod(DB_SALT_PATH, 0o600)
    except Exception:
        pass
    return salt


def _key_from_pin(pin: str) -> bytes:
    salt = _ensure_db_salt()
    key = derive_master_key(pin, salt)
    # Use first 32 bytes as raw key for SQLCipher (avoids double KDF when using x'..')
    key_bytes = bytes(key[:32])
    zero_bytes(key)
    return key_bytes


def _enc_box_from_pin(pin: str) -> SecretBox:
    """Derive a SecretBox (symmetric) from the user's PIN and the DB salt.

    Returns a SecretBox instance. This function attempts to zero sensitive
    intermediate buffers as soon as possible.
    """
    # derive_master_key returns a mutable bytearray
    master_key = derive_master_key(pin, _ensure_db_salt())
    try:
        enc_key = bytes(master_key[:32])
        box = SecretBox(enc_key)
        return box
    finally:
        # Zero sensitive material we created
        try:
            zero_bytes(master_key)
        except Exception:
            pass
        try:
            zero_bytes(enc_key)
        except Exception:
            pass


def get_connection(pin: str):
    """Return an opened connection keyed with the user's PIN.

    Uses SQLCipher when available. Otherwise decrypts the application-encrypted
    DB file into a temp plaintext DB and returns a wrapper that will
    re-encrypt the temp DB back to disk when closed.
    """
    # SQLCipher available: use DB-level encryption
    if IS_SQLCIPHER:
        conn = sqlcipher.connect(DB_PATH)
        cur = conn.cursor()
        try:
            key_bytes = _key_from_pin(pin)
            hex_key = key_bytes.hex()
            cur.execute(f"PRAGMA key = x'{hex_key}';")
        except Exception:
            pass

        # Pragmas for performance
        try:
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=NORMAL;")
            cur.execute("PRAGMA temp_store=MEMORY;")
            cur.execute("PRAGMA cache_size=-20000;")  # ~20MB page cache
        except Exception:
            pass

        # Initialize schema; handle cases where an old plaintext sqlite DB exists
        try:
            cur.execute("PRAGMA user_version;")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pub_hex TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    text TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    attachment_meta TEXT NULL
                );
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_pub_ts ON messages(pub_hex, timestamp);")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_unique ON messages(pub_hex, timestamp, sender, text);")
            # Groups schema (client-side local cache + keys)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS groups (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    is_public INTEGER DEFAULT 0,
                    invite_code TEXT,
                    key_version INTEGER DEFAULT 1,
                    created_at REAL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS group_members (
                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT DEFAULT 'member',
                    joined_at REAL,
                    encrypted_group_key TEXT,
                    key_version INTEGER DEFAULT 1,
                    PRIMARY KEY (group_id, user_id)
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS channels (
                    id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    type TEXT DEFAULT 'text',
                    created_at REAL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS group_messages (
                    id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    ciphertext TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    key_version INTEGER DEFAULT 1,
                    timestamp REAL
                );
                """
            )
            # Local secure store of my group keys (encrypted with PIN-derived SecretBox)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS my_group_keys (
                    group_id TEXT PRIMARY KEY,
                    key_version INTEGER NOT NULL,
                    enc_blob TEXT NOT NULL
                );
                """
            )
            conn.commit()
        except Exception:
            # If the DB is unreadable with current key, back it up and recreate
            try:
                backup = DB_PATH + ".bak"
                if os.path.exists(DB_PATH):
                    shutil.move(DB_PATH, backup)
            except Exception:
                pass
            conn.close()
            conn = sqlcipher.connect(DB_PATH)
            cur = conn.cursor()
            try:
                key_bytes = _key_from_pin(pin)
                hex_key = key_bytes.hex()
                cur.execute(f"PRAGMA key = x'{hex_key}';")
            except Exception:
                pass
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pub_hex TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    text TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    attachment_meta TEXT NULL
                );
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_pub_ts ON messages(pub_hex, timestamp);")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_unique ON messages(pub_hex, timestamp, sender, text);")
            # Groups schema
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS groups (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    is_public INTEGER DEFAULT 0,
                    invite_code TEXT,
                    key_version INTEGER DEFAULT 1,
                    created_at REAL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS group_members (
                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT DEFAULT 'member',
                    joined_at REAL,
                    encrypted_group_key TEXT,
                    key_version INTEGER DEFAULT 1,
                    PRIMARY KEY (group_id, user_id)
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS channels (
                    id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    type TEXT DEFAULT 'text',
                    created_at REAL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS group_messages (
                    id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    ciphertext TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    key_version INTEGER DEFAULT 1,
                    timestamp REAL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS my_group_keys (
                    group_id TEXT PRIMARY KEY,
                    key_version INTEGER NOT NULL,
                    enc_blob TEXT NOT NULL
                );
                """
            )
            conn.commit()
        return conn

    # Application-level encrypted file path: decrypt to a temp file and return a
    # wrapper that re-encrypts on close.
    dirpath = os.path.dirname(DB_PATH)
    os.makedirs(dirpath, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix='whispr_db_', dir=dirpath)
    os.close(fd)
    try:
        try:
            _decrypt_db_file_to_temp(pin, temp_path)
            need_init = not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0
        except ValueError:
            # Existing DB was plaintext or not app-encrypted: back it up
            try:
                if os.path.exists(DB_PATH):
                    shutil.move(DB_PATH, DB_PATH + '.bak')
            except Exception:
                pass
            need_init = True

        conn = sqlcipher.connect(temp_path)
        cur = conn.cursor()
        # Apply performance pragmas where supported
        try:
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=NORMAL;")
            cur.execute("PRAGMA temp_store=MEMORY;")
            cur.execute("PRAGMA cache_size=-20000;")
        except Exception:
            pass

        # Initialize schema if needed
        try:
            cur.execute("PRAGMA user_version;")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pub_hex TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    text TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    attachment_meta TEXT NULL
                );
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_pub_ts ON messages(pub_hex, timestamp);")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_unique ON messages(pub_hex, timestamp, sender, text);")
            # Groups schema
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS groups (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    is_public INTEGER DEFAULT 0,
                    invite_code TEXT,
                    key_version INTEGER DEFAULT 1,
                    created_at REAL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS group_members (
                    group_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT DEFAULT 'member',
                    joined_at REAL,
                    encrypted_group_key TEXT,
                    key_version INTEGER DEFAULT 1,
                    PRIMARY KEY (group_id, user_id)
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS channels (
                    id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    type TEXT DEFAULT 'text',
                    created_at REAL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS group_messages (
                    id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    channel_id TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    ciphertext TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    key_version INTEGER DEFAULT 1,
                    timestamp REAL
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS my_group_keys (
                    group_id TEXT PRIMARY KEY,
                    key_version INTEGER NOT NULL,
                    enc_blob TEXT NOT NULL
                );
                """
            )
            conn.commit()
        except Exception:
            # On schema init failure, clean up and re-raise
            try:
                conn.close()
            except Exception:
                pass
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            raise

    except Exception:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass
        raise

    class EncryptedConnectionWrapper:
        def __init__(self, conn, temp_path, pin):
            self._conn = conn
            self._temp_path = temp_path
            self._pin = pin

        def cursor(self):
            return self._conn.cursor()

        def commit(self):
            return self._conn.commit()

        def execute(self, *args, **kwargs):
            return self._conn.execute(*args, **kwargs)

        def executemany(self, *args, **kwargs):
            return self._conn.executemany(*args, **kwargs)

        def close(self):
            try:
                self._conn.commit()
            except Exception:
                pass
            try:
                self._conn.close()
            except Exception:
                pass
            try:
                _encrypt_temp_db_to_file(self._pin, self._temp_path)
            finally:
                try:
                    if os.path.exists(self._temp_path):
                        os.remove(self._temp_path)
                except Exception:
                    pass

        def __getattr__(self, name):
            return getattr(self._conn, name)

    return EncryptedConnectionWrapper(conn, temp_path, pin)


def insert_message(pin: str, pub_hex: str, sender: str, text: str, timestamp: float, attachment_meta: Optional[dict] = None):
    # Encrypt the message text at-rest using a symmetric key derived from the PIN.
    # This provides message-level encryption even when SQLCipher is not available.
    try:
        box = _enc_box_from_pin(pin)
        try:
            # Use explicit nonce to ensure different ciphertexts for same plaintext
            cipher = box.encrypt(text.encode(), nacl_random(SecretBox.NONCE_SIZE))
            stored_text = base64.b64encode(cipher).decode()
        except Exception:
            # If encryption fails for any reason, fall back to storing plaintext
            stored_text = text
        try:
            sender_cipher = box.encrypt(sender.encode(), nacl_random(SecretBox.NONCE_SIZE))
            stored_sender = base64.b64encode(sender_cipher).decode()
        except Exception:
            stored_sender = sender
    except Exception:
        # If deriving key fails (e.g., PIN too short), store plaintext to avoid data loss
        stored_text = text
        stored_sender = sender

    conn = get_connection(pin)
    try:
        cur = conn.cursor()
        att = json.dumps(attachment_meta) if attachment_meta else None
        cur.execute(
            "INSERT OR IGNORE INTO messages(pub_hex, sender, text, timestamp, attachment_meta) VALUES(?,?,?,?,?)",
            (pub_hex, stored_sender, stored_text, timestamp, att),
        )
        conn.commit()
    finally:
        conn.close()


def query_messages(pin: str, pub_hex: str, limit: Optional[int] = None, since_ts: Optional[float] = None, order_asc: bool = True) -> list:
    conn = get_connection(pin)
    try:
        cur = conn.cursor()
        params = [pub_hex]
        where = "WHERE pub_hex = ?"
        if since_ts is not None:
            where += " AND timestamp >= ?"
            params.append(since_ts)
        order = "ASC" if order_asc else "DESC"
        lim = f" LIMIT {int(limit)}" if limit else ""
        sql = f"SELECT sender, text, timestamp, attachment_meta FROM messages {where} ORDER BY timestamp {order}{lim}"
        rows = cur.execute(sql, params).fetchall()
        msgs = []
        # Attempt to derive box once per query to avoid repeated KDF calls
        try:
            box = _enc_box_from_pin(pin)
        except Exception:
            box = None

        for sender, text, ts, att_json in rows:
            # Try to decrypt stored text and sender; if it fails, assume plaintext
            decoded_text = text
            decoded_sender = sender
            if text is not None and box is not None:
                try:
                    # Stored format is base64(ciphertext)
                    ct = base64.b64decode(text)
                    decoded_text = box.decrypt(ct).decode()
                except Exception:
                    decoded_text = text
            if sender is not None and box is not None:
                try:
                    cs = base64.b64decode(sender)
                    decoded_sender = box.decrypt(cs).decode()
                except Exception:
                    decoded_sender = sender

            # Defer JSON parsing to render-time to reduce CPU during bulk loads
            m = {"sender": decoded_sender, "text": decoded_text, "timestamp": ts, "_attachment_json": att_json}
            msgs.append(m)
        if not order_asc:
            msgs.reverse()
        return msgs
    finally:
        conn.close()


def query_messages_before(pin: str, pub_hex: str, before_ts: float, limit: int) -> list:
    """Return up to 'limit' messages older than 'before_ts' ordered ascending."""
    conn = get_connection(pin)
    try:
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT sender, text, timestamp, attachment_meta FROM messages WHERE pub_hex = ? AND timestamp < ? ORDER BY timestamp DESC LIMIT ?",
            (pub_hex, before_ts, int(limit)),
        ).fetchall()
        msgs = []
        try:
            box = _enc_box_from_pin(pin)
        except Exception:
            box = None

        for sender, text, ts, att_json in rows:
            decoded_text = text
            decoded_sender = sender
            if text is not None and box is not None:
                try:
                    ct = base64.b64decode(text)
                    decoded_text = box.decrypt(ct).decode()
                except Exception:
                    decoded_text = text
            if sender is not None and box is not None:
                try:
                    cs = base64.b64decode(sender)
                    decoded_sender = box.decrypt(cs).decode()
                except Exception:
                    decoded_sender = sender
            msgs.append({"sender": decoded_sender, "text": decoded_text, "timestamp": ts, "_attachment_json": att_json})
        msgs.reverse()  # return ascending
        return msgs
    finally:
        conn.close()


def has_older_messages(pin: str, pub_hex: str, before_ts: float) -> bool:
    conn = get_connection(pin)
    try:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT 1 FROM messages WHERE pub_hex = ? AND timestamp < ? LIMIT 1",
            (pub_hex, before_ts),
        ).fetchone()
        return bool(row)
    finally:
        conn.close()


def count_messages(pin: str, pub_hex: str) -> int:
    conn = get_connection(pin)
    try:
        cur = conn.cursor()
        row = cur.execute("SELECT COUNT(1) FROM messages WHERE pub_hex = ?", (pub_hex,)).fetchone()
        return int(row[0] if row else 0)
    finally:
        conn.close()


# ---- Group key local vault helpers ----
def store_my_group_key(pin: str, group_id: str, key_bytes: bytes, key_version: int) -> None:
    box = _enc_box_from_pin(pin)
    nonce = nacl_random(SecretBox.NONCE_SIZE)
    ct = box.encrypt(key_bytes, nonce)
    b64 = base64.b64encode(ct).decode()
    conn = get_connection(pin)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO my_group_keys(group_id, key_version, enc_blob)
            VALUES(?,?,?)
            ON CONFLICT(group_id) DO UPDATE SET key_version=excluded.key_version, enc_blob=excluded.enc_blob
            """,
            (group_id, int(key_version), b64),
        )
        conn.commit()
    finally:
        conn.close()


def load_my_group_key(pin: str, group_id: str) -> tuple[bytes, int] | None:
    conn = get_connection(pin)
    try:
        cur = conn.cursor()
        row = cur.execute("SELECT key_version, enc_blob FROM my_group_keys WHERE group_id = ?", (group_id,)).fetchone()
        if not row:
            return None
        kv, b64 = int(row[0]), row[1]
        box = _enc_box_from_pin(pin)
        pt = box.decrypt(base64.b64decode(b64))
        return pt, kv
    finally:
        conn.close()
