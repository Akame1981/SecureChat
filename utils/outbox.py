"""Offline outbox storage using SQLCipher (same DB), not files."""
from __future__ import annotations

import threading
import time
from typing import List, Dict

from utils.db import get_connection
from utils.chat_storage import save_message
from utils.network import send_message

_lock = threading.RLock()


def _ensure_outbox_schema(conn):
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                to_pub TEXT NOT NULL,
                text TEXT NOT NULL,
                timestamp REAL NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_outbox_ts ON outbox(timestamp);")
        conn.commit()
    except Exception:
        pass


def load_outbox(pin: str) -> List[Dict]:
    with _lock:
        conn = get_connection(pin)
        try:
            _ensure_outbox_schema(conn)
            cur = conn.cursor()
            rows = cur.execute("SELECT id, to_pub, text, timestamp, attempts FROM outbox ORDER BY timestamp ASC").fetchall()
            return [
                {"id": r[0], "to": r[1], "text": r[2], "timestamp": r[3], "attempts": r[4]}
                for r in rows
            ]
        finally:
            conn.close()


def append_outbox_message(to_pub: str, text: str, pin: str, timestamp: float | None = None):
    if not to_pub or not text:
        return
    if timestamp is None:
        timestamp = time.time()
    with _lock:
        conn = get_connection(pin)
        try:
            _ensure_outbox_schema(conn)
            cur = conn.cursor()
            cur.execute("INSERT INTO outbox(to_pub, text, timestamp, attempts) VALUES(?,?,?,0)", (to_pub, text, float(timestamp)))
            conn.commit()
        finally:
            conn.close()


def has_outbox(pin: str) -> bool:
    with _lock:
        conn = get_connection(pin)
        try:
            _ensure_outbox_schema(conn)
            cur = conn.cursor()
            row = cur.execute("SELECT 1 FROM outbox LIMIT 1").fetchone()
            return bool(row)
        finally:
            conn.close()


def flush_outbox(app, max_batch: int = 10):
    pin = getattr(app, "pin", None)
    if not pin:
        return
    with _lock:
        conn = get_connection(pin)
        try:
            _ensure_outbox_schema(conn)
            cur = conn.cursor()
            rows = cur.execute("SELECT id, to_pub, text, timestamp, attempts FROM outbox ORDER BY timestamp ASC LIMIT ?", (max_batch,)).fetchall()
            if not rows:
                return

            sent_any = False
            for (row_id, to_pub, text, ts, attempts) in rows:
                ok = False
                try:
                    ok = send_message(
                        app,
                        to_pub=to_pub,
                        signing_pub=app.signing_pub_hex,
                        text=text,
                        signing_key=app.signing_key,
                        enc_pub=app.my_pub_hex,
                    )
                except Exception as e:
                    print(f"[outbox] exception sending queued message: {e}")
                    ok = False

                if ok:
                    sent_any = True
                    # Remove from outbox
                    cur.execute("DELETE FROM outbox WHERE id = ?", (row_id,))
                    conn.commit()
                    # Persist into normal chat history with original timestamp
                    try:
                        save_message(to_pub, "You", text, pin, timestamp=ts)
                    except Exception as e:
                        print(f"[outbox] failed to save delivered message to chat: {e}")
                    # Update cache/UI
                    try:
                        if hasattr(app, "chat_manager") and app.chat_manager:
                            app.chat_manager._append_cache(to_pub, {"sender": "You", "text": text, "timestamp": ts})
                        if getattr(app, "recipient_pub_hex", None) == to_pub:
                            app.after(0, app.display_message, app.my_pub_hex, text, ts)
                    except Exception:
                        pass
                else:
                    # Increment attempts and stop early
                    cur.execute("UPDATE outbox SET attempts = ? WHERE id = ?", (attempts + 1, row_id))
                    conn.commit()
                    break

            if sent_any:
                try:
                    app.notifier.show("Outbox flushed", type_="success")
                except Exception:
                    pass
        finally:
            conn.close()
