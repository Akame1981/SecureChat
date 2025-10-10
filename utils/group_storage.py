from typing import Optional, List, Dict
import time

from .db import get_connection


def upsert_group(pin: str, group: Dict):
    conn = get_connection(pin)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO groups(id, name, owner_id, is_public, invite_code, key_version, created_at)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                owner_id=excluded.owner_id,
                is_public=excluded.is_public,
                invite_code=excluded.invite_code,
                key_version=excluded.key_version,
                created_at=excluded.created_at
            ;
            """,
            (
                group.get("id"),
                group.get("name"),
                group.get("owner_id"),
                1 if group.get("is_public") else 0,
                group.get("invite_code"),
                int(group.get("key_version", 1)),
                float(group.get("created_at") or time.time()),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def upsert_member(pin: str, group_id: str, user_id: str, role: str, encrypted_group_key: Optional[str], key_version: int):
    conn = get_connection(pin)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO group_members(group_id, user_id, role, joined_at, encrypted_group_key, key_version)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(group_id, user_id) DO UPDATE SET
                role=excluded.role,
                encrypted_group_key=excluded.encrypted_group_key,
                key_version=excluded.key_version
            ;
            """,
            (group_id, user_id, role, time.time(), encrypted_group_key, int(key_version)),
        )
        conn.commit()
    finally:
        conn.close()


def upsert_channel(pin: str, channel: Dict):
    conn = get_connection(pin)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO channels(id, group_id, name, type, created_at)
            VALUES(?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                type=excluded.type
            ;
            """,
            (
                channel.get("id"),
                channel.get("group_id"),
                channel.get("name"),
                channel.get("type", "text"),
                float(channel.get("created_at") or time.time()),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def store_group_message(pin: str, msg: Dict):
    conn = get_connection(pin)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR REPLACE INTO group_messages(id, group_id, channel_id, sender_id, ciphertext, nonce, key_version, timestamp)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                msg.get("id"),
                msg.get("group_id"),
                msg.get("channel_id"),
                msg.get("sender_id"),
                msg.get("ciphertext"),
                msg.get("nonce"),
                int(msg.get("key_version", 1)),
                float(msg.get("timestamp") or time.time()),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_groups(pin: str) -> list[dict]:
    conn = get_connection(pin)
    try:
        cur = conn.cursor()
        rows = cur.execute("SELECT id, name, owner_id, is_public, invite_code, key_version, created_at FROM groups").fetchall()
        return [
            {
                "id": rid,
                "name": name,
                "owner_id": owner,
                "is_public": bool(is_pub),
                "invite_code": inv,
                "key_version": int(kv or 1),
                "created_at": ts,
            }
            for (rid, name, owner, is_pub, inv, kv, ts) in rows
        ]
    finally:
        conn.close()
