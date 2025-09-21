import json
import os

# -------------------------
# --- Data folder setup ---
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")
CHATS_DIR = os.path.join(DATA_DIR, "chats")
os.makedirs(CHATS_DIR, exist_ok=True)

# -------------------------
# --- Chat storage ---
# -------------------------
def get_chat_file(pub_hex: str):
    """Get path to the chat file for a recipient by their public key."""
    filename = f"{pub_hex}.json"
    return os.path.join(CHATS_DIR, filename)

def save_message(pub_hex: str, sender: str, text: str):
    """Save a single message to the recipient's chat file."""
    chat_file = get_chat_file(pub_hex)
    if os.path.exists(chat_file):
        with open(chat_file, "r", encoding="utf-8") as f:
            messages = json.load(f)
    else:
        messages = []

    messages.append({"sender": sender, "text": text})
    
    # keep last N messages only
    MAX_MESSAGES = 100
    messages = messages[-MAX_MESSAGES:]

    with open(chat_file, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=4)

def load_messages(pub_hex: str):
    """Load chat history for a recipient."""
    chat_file = get_chat_file(pub_hex)
    if os.path.exists(chat_file):
        with open(chat_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []
