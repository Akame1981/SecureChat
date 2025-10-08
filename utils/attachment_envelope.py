import json, re

def parse_attachment_envelope(text: str):
    """Parse an ATTACH:<json> envelope.

    Returns (placeholder_text, meta_dict) or (None, None) if not an envelope.
    Robust against minor corruption; will fall back to regex extraction.
    """
    if not text or not text.startswith("ATTACH:"):
        return None, None
    payload = text[7:]
    meta = None
    try:
        meta = json.loads(payload)
    except Exception:
        # Fallback: attempt to extract minimal fields via regex
        try:
            name_match = re.search(r'"name"\s*:\s*"([^"]+)"', payload)
            size_match = re.search(r'"size"\s*:\s*(\d+)', payload)
            att_id_match = re.search(r'"att_id"\s*:\s*"([0-9a-fA-F]{40,64})"', payload)
            if name_match and size_match:
                meta = {
                    "type": "file",
                    "name": name_match.group(1),
                    "size": int(size_match.group(1)),
                }
                if att_id_match:
                    meta["att_id"] = att_id_match.group(1)
        except Exception:
            meta = None
    if not isinstance(meta, dict) or meta.get("type") != "file":
        return None, None
    name = meta.get("name", "file")
    size = int(meta.get("size", 0))
    placeholder = f"[Attachment] {name} ({_human_size(size)})"
    return placeholder, meta


def _human_size(n: int) -> str:
    units = ["B","KB","MB","GB","TB"]
    f = float(n)
    for u in units:
        if f < 1024 or u == units[-1]:
            return f"{f:.1f} {u}"
        f /= 1024
    return f"{n} B"
