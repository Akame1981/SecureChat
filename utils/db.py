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

from nacl.utils import random as nacl_random

from utils.path_utils import get_resource_path
from utils.crypto import derive_master_key, zero_bytes


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


def get_connection(pin: str):
    """Return an opened SQLCipher connection keyed with the user's PIN.

    If sqlcipher is unavailable, falls back to sqlite3 (unencrypted) so the
    app remains usable in development environments. In production, install
    sqlcipher3-wheels.
    """
    conn = sqlcipher.connect(DB_PATH)
    cur = conn.cursor()
    try:
        # If real SQLCipher, PRAGMA key will be recognized; on sqlite3 fallback, it's ignored.
        key_bytes = _key_from_pin(pin)
        hex_key = key_bytes.hex()
        # Use raw key form to avoid SQLCipher's internal KDF (we already used a strong KDF)
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
        conn.commit()
    except Exception as e:
        # If the DB is unreadable with current key (e.g., prior plaintext sqlite3 file), back it up and recreate
        try:
            import shutil
            backup = DB_PATH + ".bak"
            if os.path.exists(DB_PATH):
                shutil.move(DB_PATH, backup)
        except Exception:
            pass
        # Reconnect on a fresh database
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
        conn.commit()
    return conn


def insert_message(pin: str, pub_hex: str, sender: str, text: str, timestamp: float, attachment_meta: Optional[dict] = None):
    conn = get_connection(pin)
    try:
        cur = conn.cursor()
        att = json.dumps(attachment_meta) if attachment_meta else None
        cur.execute(
            "INSERT OR IGNORE INTO messages(pub_hex, sender, text, timestamp, attachment_meta) VALUES(?,?,?,?,?)",
            (pub_hex, sender, text, timestamp, att),
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
        for sender, text, ts, att_json in rows:
            # Defer JSON parsing to render-time to reduce CPU during bulk loads
            m = {"sender": sender, "text": text, "timestamp": ts, "_attachment_json": att_json}
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
        for sender, text, ts, att_json in rows:
            msgs.append({"sender": sender, "text": text, "timestamp": ts, "_attachment_json": att_json})
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
