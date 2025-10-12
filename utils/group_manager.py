import time
from typing import Optional, Dict, List

from .group_client import GroupClient
from .group_crypto import (
    generate_group_key,
    encrypt_group_key_for_member,
    decrypt_group_key_for_me,
    encrypt_text_with_group_key,
    decrypt_text_with_group_key,
)
import json
from .db import store_my_group_key, load_my_group_key


class GroupManager:
    def __init__(self, app):
        self.app = app
        self.client = GroupClient(app)

    # ----- Group lifecycle -----
    def create_group(self, name: str, is_public: bool = False) -> Dict:
        res = self.client.create_group(name, is_public)
        group_id = res["id"]
        invite_code = res["invite_code"]
        # Generate initial group key and store locally (version 1)
        key = generate_group_key()
        store_my_group_key(self.app.pin, group_id, key, 1)
        # Distribute to myself via server member key update
        ek = encrypt_group_key_for_member(key, self.app.my_pub_hex)
        self.client.update_member_key(group_id, self.app.my_pub_hex, ek, 1)
        return res

    def join_group_via_invite(self, invite_code: str) -> Dict:
        res = self.client.join_group(invite_code=invite_code)
        if res.get("status") == "joined":
            gid = res.get("group_id")
            # Fetch member keys and decrypt mine
            info = self.client.get_member_keys(gid)
            kv = int(info.get("key_version", 1))
            my_entry = next((m for m in info.get("members", []) if m.get("user_id") == self.app.my_pub_hex), None)
            if my_entry and my_entry.get("encrypted_group_key"):
                key = decrypt_group_key_for_me(my_entry["encrypted_group_key"], self.app.private_key)
                store_my_group_key(self.app.pin, gid, key, kv)
        return res

    def leave_group(self, group_id: str) -> Dict:
        return self.client.leave_group(group_id)

    def list_groups(self) -> Dict:
        return self.client.list_groups()

    # ----- Channels -----
    def create_channel(self, group_id: str, name: str, type_: str = "text") -> Dict:
        return self.client.create_channel(group_id, name, type_)

    # ----- Messages -----
    def send_text(self, group_id: str, channel_id: str, plaintext: str, timestamp: Optional[float] = None) -> Dict:
        # Ensure we have a group key locally; fetch from server if missing
        loaded = load_my_group_key(self.app.pin, group_id)
        if not loaded:
            loaded = self._ensure_have_group_key(group_id)
        if not loaded:
            raise RuntimeError("No group key for this group")
        key, kv = loaded
        ct_b64, nonce_b64 = encrypt_text_with_group_key(plaintext, key)
        return self.client.send_message(group_id, channel_id, ct_b64, nonce_b64, kv, timestamp)

    def fetch_messages(self, group_id: str, channel_id: str, since: Optional[float] = None, limit: int = 200) -> List[Dict]:
        loaded = load_my_group_key(self.app.pin, group_id)
        if not loaded:
            loaded = self._ensure_have_group_key(group_id)
        if not loaded:
            # Still no key: cannot decrypt or send. Return empty list gracefully.
            return []
        key, kv = loaded
        res = self.client.fetch_messages(group_id, channel_id, since, limit)
        out = []
        for m in res.get("messages", []):
            if int(m.get("key_version", 0)) != int(kv):
                # Skip messages for old/new version until rekey handled
                continue
            try:
                pt = decrypt_text_with_group_key(m.get("ciphertext"), m.get("nonce"), key)
            except Exception:
                continue
            # Attachments: backend returns optional _attachment_json string
            att = None
            try:
                aj = m.get("_attachment_json") if isinstance(m, dict) else None
                if aj:
                    att = json.loads(aj) if isinstance(aj, str) else aj
            except Exception:
                att = None
            out.append({
                "id": m.get("id"),
                "sender_id": m.get("sender_id"),
                "text": pt,
                "timestamp": m.get("timestamp"),
                "attachment_meta": att,
            })
        return out

    # ----- Rekeying -----
    def rekey_group(self, group_id: str, member_pub_hexes: list[str]) -> int:
        """Owner/Admin rotates group key and updates encrypted keys for members.

        Returns new key_version.
        """
        # Bump version client-side by checking server-reported version
        # Ask server to bump key_version
        resp = self.client.rekey(group_id)
        new_version = int(resp.get("key_version", 1))
        key = generate_group_key()
        store_my_group_key(self.app.pin, group_id, key, new_version)
        for uid in member_pub_hexes:
            ek = encrypt_group_key_for_member(key, uid)
            self.client.update_member_key(group_id, uid, ek, new_version)
        return new_version

    # ----- Helpers -----
    def _ensure_have_group_key(self, group_id: str) -> tuple[bytes, int] | None:
        """If local key is missing, try to fetch my encrypted group key from the server and store it.

        Returns (key, key_version) if available, else None.
        """
        try:
            info = self.client.get_member_keys(group_id)
            kv = int(info.get("key_version", 1))
            my_entry = next((m for m in info.get("members", []) if m.get("user_id") == self.app.my_pub_hex), None)
            if my_entry and my_entry.get("encrypted_group_key"):
                key = decrypt_group_key_for_me(my_entry["encrypted_group_key"], self.app.private_key)
                store_my_group_key(self.app.pin, group_id, key, kv)
                return key, kv
        except Exception:
            pass
        return None

    def is_admin_or_owner(self, group_id: str) -> bool:
        try:
            info = self.client.get_my_role(group_id)
            role = (info or {}).get("role")
            return role in ("owner", "admin")
        except Exception:
            return False

    def reconcile_member_keys(self, group_id: str) -> int:
        """Owner/Admin: ensure all members have the current encrypted group key.

        Returns the number of members updated.
        """
        try:
            if not self.is_admin_or_owner(group_id):
                return 0
            loaded = load_my_group_key(self.app.pin, group_id)
            if not loaded:
                # Try to fetch my own key first
                loaded = self._ensure_have_group_key(group_id)
            if not loaded:
                return 0
            key, kv = loaded
            info = self.client.get_member_keys(group_id)
            updated = 0
            for m in (info.get("members", []) if isinstance(info, dict) else []):
                uid = m.get("user_id")
                m_kv = int(m.get("key_version", 0) or 0)
                has_key = bool(m.get("encrypted_group_key"))
                if uid and (not has_key or m_kv != int(kv)):
                    try:
                        ek = encrypt_group_key_for_member(key, uid)
                        self.client.update_member_key(group_id, uid, ek, int(kv))
                        updated += 1
                    except Exception:
                        pass
            return updated
        except Exception:
            return 0
