from time import time
from typing import Optional

from utils.db import insert_message, query_messages


def save_message(pub_hex: str, sender: str, text: str, pin: str, timestamp: float | None = None, attachment: dict | None = None):
    """Save a message directly into the encrypted SQLCipher database."""
    if timestamp is None:
        timestamp = time()
    insert_message(pin, pub_hex, sender, text, float(timestamp), attachment)


def load_messages(pub_hex: str, pin: str, limit: int | None = None, order_asc: bool = True) -> list:
    """Load messages from SQLCipher database.

    - order_asc=True: ascending (oldest->newest)
    - order_asc=False: descending (newest->oldest)
    Optional limit constrains row count.
    """
    return query_messages(pin, pub_hex, limit=limit, order_asc=order_asc)
