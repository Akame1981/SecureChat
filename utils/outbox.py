"""Offline outbox storage.
            if ok:
                sent_any = True
                # Do not re-save or re-display; already handled optimistically on send.
fresh on each attempt to avoid stale cryptographic material.
"""
from __future__ import annotations

import os
import stat
import threading
import time
from typing import List, Dict

from utils.chat_storage import encrypt_chat, decrypt_chat, save_message
from utils.network import send_message

# Outbox file lives alongside other data artifacts
try:
    from utils.chat_storage import DATA_DIR  # reuse path logic
except Exception:
    DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data"))

OUTBOX_FILE = os.path.join(DATA_DIR, "outbox.bin")
_lock = threading.RLock()


def _atomic_write(path: str, data: bytes):
    tmp = f"{path}.tmp"
    with open(tmp, "wb") as f:
        f.write(data)
        try:
            f.flush()
        except Exception:
            pass
        try:
            if hasattr(os, "fsync"):
                os.fsync(f.fileno())
        except Exception:
            pass
    os.replace(tmp, path)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def load_outbox(pin: str) -> List[Dict]:
    """Decrypt and return list of queued messages or []."""
    with _lock:
        if not os.path.exists(OUTBOX_FILE):
            return []
        try:
            with open(OUTBOX_FILE, "rb") as f:
                data = f.read()
            items = decrypt_chat(data, pin)
            return items if isinstance(items, list) else []
        except Exception as e:
            print(f"[outbox] failed to load: {e}")
            return []


def _save_outbox(items: List[Dict], pin: str):
    with _lock:
        try:
            enc = encrypt_chat(items, pin)
            _atomic_write(OUTBOX_FILE, enc)
        except Exception as e:
            print(f"[outbox] failed to save: {e}")


def append_outbox_message(to_pub: str, text: str, pin: str, timestamp: float | None = None):
    if not to_pub or not text:
        return
    if timestamp is None:
        timestamp = time.time()
    items = load_outbox(pin)
    items.append({
        "to": to_pub,
        "text": text,
        "timestamp": timestamp,
        "attempts": 0,
    })
    _save_outbox(items, pin)


def has_outbox(pin: str) -> bool:
    return bool(load_outbox(pin))


def flush_outbox(app, max_batch: int = 10):
    """Attempt to send queued messages.

    On success: remove from outbox, persist chat history, update UI/cache.
    On failure: increment attempts and keep. We stop early if network still
    appears down (first failure) to avoid tight loops.
    """
    pin = getattr(app, "pin", None)
    if not pin:
        return
    with _lock:
        items = load_outbox(pin)
        if not items:
            return

        remaining: List[Dict] = []
        sent_any = False
        for entry in items[:max_batch]:
            to_pub = entry.get("to")
            text = entry.get("text")
            ts = entry.get("timestamp", time.time())
            attempts = entry.get("attempts", 0)

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
                # Persist into normal chat history with original timestamp
                try:
                    save_message(to_pub, "You", text, pin, timestamp=ts)
                except Exception as e:
                    print(f"[outbox] failed to save delivered message to chat: {e}")
                # Update ChatManager cache + UI if active conversation
                try:
                    if hasattr(app, "chat_manager") and app.chat_manager:
                        app.chat_manager._append_cache(to_pub, {"sender": "You", "text": text, "timestamp": ts})
                    if getattr(app, "recipient_pub_hex", None) == to_pub:
                        app.after(0, app.display_message, app.my_pub_hex, text, ts)
                except Exception:
                    pass
            else:
                # Keep for retry
                entry["attempts"] = attempts + 1
                remaining.append(entry)
                # If first failure this batch (still offline) stop early
                break

        # Append any not processed entries beyond the batch
        if len(items) > max_batch:
            remaining.extend(items[max_batch:])

        _save_outbox(remaining, pin)

        if sent_any:
            try:
                app.notifier.show("Outbox flushed", type_="success")
            except Exception:
                pass
