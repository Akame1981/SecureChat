"""
Process worker utilities for CPU-bound crypto operations.

Designed to be importable on Windows (spawn) without side effects.
"""
from typing import Optional, Tuple

from nacl.public import PrivateKey, SealedBox
from nacl.signing import VerifyKey
import base64


def verify_and_decrypt(enc_b64: str, priv_bytes: bytes, from_sign_hex: Optional[str], signature_b64: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Verify signature (if provided) and decrypt ciphertext.

    Returns (ok, plaintext or None). Any failure results in (False, None).
    """
    try:
        # Verify signature if available
        if from_sign_hex and signature_b64:
            try:
                verify_key = VerifyKey(bytes.fromhex(from_sign_hex))
                verify_key.verify(base64.b64decode(enc_b64), base64.b64decode(signature_b64))
            except Exception:
                return False, None

        # Decrypt
        try:
            box = SealedBox(PrivateKey(priv_bytes))
            pt = box.decrypt(base64.b64decode(enc_b64)).decode()
        except Exception:
            return False, None
        return True, pt
    except Exception:
        return False, None
