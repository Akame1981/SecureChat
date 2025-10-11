import mimetypes
import os

def is_text_file(filename, blob=None):
    """Return True if the file is a text file (by extension or content)."""
    # Check by extension
    text_exts = {'.txt', '.md', '.py', '.js', '.json', '.csv', '.xml', '.html', '.css', '.yaml', '.yml', '.ini', '.log', '.sh', '.bat', '.c', '.cpp', '.h', '.hpp', '.java', '.rb', '.go', '.rs', '.php', '.pl', '.swift', '.ts', '.tsx', '.jsx', '.toml', '.conf', '.cfg', '.rst', '.tex'}
    ext = os.path.splitext(filename)[1].lower()
    if ext in text_exts:
        return True
    # Fallback: use mimetypes
    mt, _ = mimetypes.guess_type(filename)
    if mt and mt.startswith('text/'):
        return True
    # Optionally, check content if provided
    if blob is not None:
        try:
            if isinstance(blob, bytes):
                sample = blob[:512]
                # If it decodes as utf-8, likely text
                sample.decode('utf-8')
                return True
        except Exception:
            return False
    return False
