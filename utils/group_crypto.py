import base64
import os
from dataclasses import dataclass
from typing import Tuple

from nacl.public import PublicKey, SealedBox
from nacl.bindings import (
    crypto_aead_chacha20poly1305_ietf_encrypt,
    crypto_aead_chacha20poly1305_ietf_decrypt,
    crypto_aead_chacha20poly1305_ietf_NPUBBYTES,
)
from nacl.utils import random as nacl_random


GROUP_KEY_SIZE = 32  # 256-bit symmetric key


def generate_group_key() -> bytes:
    return os.urandom(GROUP_KEY_SIZE)


def encrypt_group_key_for_member(group_key: bytes, member_pub_hex: str) -> str:
    pk = PublicKey(bytes.fromhex(member_pub_hex))
    sealed = SealedBox(pk).encrypt(group_key)
    return base64.b64encode(sealed).decode()


def decrypt_group_key_for_me(encrypted_b64: str, my_private_key) -> bytes:
    from nacl.public import SealedBox
    ct = base64.b64decode(encrypted_b64)
    return SealedBox(my_private_key).decrypt(ct)


def encrypt_text_with_group_key(plaintext: str, key: bytes) -> Tuple[str, str]:
    if not isinstance(key, (bytes, bytearray)) or len(key) != GROUP_KEY_SIZE:
        raise ValueError("Invalid group key length")
    nonce = nacl_random(crypto_aead_chacha20poly1305_ietf_NPUBBYTES)
    # No associated data for now
    ct = crypto_aead_chacha20poly1305_ietf_encrypt(plaintext.encode(), b"", nonce, key)
    return base64.b64encode(ct).decode(), base64.b64encode(nonce).decode()


def decrypt_text_with_group_key(ciphertext_b64: str, nonce_b64: str, key: bytes) -> str:
    if not isinstance(key, (bytes, bytearray)) or len(key) != GROUP_KEY_SIZE:
        raise ValueError("Invalid group key length")
    nonce = base64.b64decode(nonce_b64)
    ct = base64.b64decode(ciphertext_b64)
    pt = crypto_aead_chacha20poly1305_ietf_decrypt(ct, b"", nonce, key)
    return pt.decode()
