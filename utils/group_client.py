import requests
from typing import Optional


class GroupClient:
    def __init__(self, app):
        self.app = app

    def create_group(self, name: str, is_public: bool = False) -> dict:
        payload = {"name": name, "is_public": is_public, "owner_id": self.app.my_pub_hex}
        r = requests.post(f"{self.app.SERVER_URL}/groups/create", json=payload, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def join_group(self, invite_code: Optional[str] = None, group_id: Optional[str] = None) -> dict:
        payload = {"user_id": self.app.my_pub_hex}
        if invite_code:
            payload["invite_code"] = invite_code
        if group_id:
            payload["group_id"] = group_id
        r = requests.post(f"{self.app.SERVER_URL}/groups/join", json=payload, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def approve_member(self, group_id: str, approve_user_id: str) -> dict:
        payload = {"group_id": group_id, "approve_user_id": approve_user_id, "user_id": self.app.my_pub_hex}
        r = requests.post(f"{self.app.SERVER_URL}/groups/approve", json=payload, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def leave_group(self, group_id: str) -> dict:
        payload = {"group_id": group_id, "user_id": self.app.my_pub_hex}
        r = requests.post(f"{self.app.SERVER_URL}/groups/leave", json=payload, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def list_groups(self) -> dict:
        r = requests.get(f"{self.app.SERVER_URL}/groups/list", params={"user_id": self.app.my_pub_hex}, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def create_channel(self, group_id: str, name: str, type_: str = "text") -> dict:
        payload = {"group_id": group_id, "name": name, "type": type_}
        r = requests.post(f"{self.app.SERVER_URL}/groups/channels/create", params={"user_id": self.app.my_pub_hex}, json=payload, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def rename_channel(self, channel_id: str, name: str) -> dict:
        payload = {"channel_id": channel_id, "name": name}
        r = requests.post(f"{self.app.SERVER_URL}/groups/channels/rename", params={"user_id": self.app.my_pub_hex}, json=payload, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def delete_channel(self, channel_id: str) -> dict:
        params = {"channel_id": channel_id, "user_id": self.app.my_pub_hex}
        r = requests.post(f"{self.app.SERVER_URL}/groups/channels/delete", params=params, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def list_channels(self, group_id: str) -> dict:
        r = requests.get(f"{self.app.SERVER_URL}/groups/channels/list", params={"group_id": group_id, "user_id": self.app.my_pub_hex}, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_channel_meta(self, channel_id: str) -> dict:
        r = requests.get(f"{self.app.SERVER_URL}/groups/channels/meta", params={"channel_id": channel_id, "user_id": self.app.my_pub_hex}, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def set_channel_meta(self, channel_id: str, topic: str | None, description: str | None) -> dict:
        params = {"channel_id": channel_id, "user_id": self.app.my_pub_hex}
        r = requests.post(f"{self.app.SERVER_URL}/groups/channels/meta/set", params=params, json={"topic": topic, "description": description}, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_my_role(self, group_id: str) -> dict:
        r = requests.get(f"{self.app.SERVER_URL}/groups/channels/role", params={"group_id": group_id, "user_id": self.app.my_pub_hex}, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def send_message(self, group_id: str, channel_id: str, ciphertext_b64: str, nonce_b64: str, key_version: int, timestamp: float | None = None) -> dict:
        payload = {
            "group_id": group_id,
            "channel_id": channel_id,
            "sender_id": self.app.my_pub_hex,
            "ciphertext": ciphertext_b64,
            "nonce": nonce_b64,
            "key_version": key_version,
        }
        if timestamp is not None:
            payload["timestamp"] = timestamp
        r = requests.post(f"{self.app.SERVER_URL}/groups/messages/send", json=payload, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def fetch_messages(self, group_id: str, channel_id: str, since: float | None = None, limit: int = 200) -> dict:
        payload = {"group_id": group_id, "channel_id": channel_id, "since": since, "limit": limit}
        r = requests.post(f"{self.app.SERVER_URL}/groups/messages/fetch", params={"user_id": self.app.my_pub_hex}, json=payload, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_member_keys(self, group_id: str) -> dict:
        r = requests.get(f"{self.app.SERVER_URL}/groups/members/keys", params={"group_id": group_id}, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def update_member_key(self, group_id: str, user_id: str, encrypted_key_b64: str, key_version: int) -> dict:
        params = {"group_id": group_id, "user_id": user_id, "encrypted_key_b64": encrypted_key_b64, "key_version": key_version}
        r = requests.post(f"{self.app.SERVER_URL}/groups/members/keys/update", params=params, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def rotate_invite(self, group_id: str) -> dict:
        params = {"group_id": group_id, "user_id": self.app.my_pub_hex}
        r = requests.post(f"{self.app.SERVER_URL}/groups/invites/rotate", params=params, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def discover_public(self, query: str | None = None, limit: int = 50) -> dict:
        params = {"limit": limit}
        if query:
            params["query"] = query
        r = requests.get(f"{self.app.SERVER_URL}/groups/discover", params=params, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def ban_member(self, group_id: str, target_user_id: str) -> dict:
        params = {"group_id": group_id, "target_user_id": target_user_id, "user_id": self.app.my_pub_hex}
        r = requests.post(f"{self.app.SERVER_URL}/groups/members/ban", params=params, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def rekey(self, group_id: str) -> dict:
        params = {"group_id": group_id, "user_id": self.app.my_pub_hex}
        r = requests.post(f"{self.app.SERVER_URL}/groups/rekey", params=params, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()

    def set_group_public(self, group_id: str, is_public: bool) -> dict:
        params = {"group_id": group_id, "user_id": self.app.my_pub_hex, "is_public": is_public}
        r = requests.post(f"{self.app.SERVER_URL}/groups/public/set", params=params, verify=self.app.SERVER_CERT, timeout=10)
        r.raise_for_status()
        return r.json()
