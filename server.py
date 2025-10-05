import base64
import threading
import time

from fastapi import FastAPI, HTTPException
from nacl.public import PrivateKey
from nacl.signing import VerifyKey
from pydantic import BaseModel


# -------------------------
# Try Redis connection
# -------------------------
try:
    import redis
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        REDIS_AVAILABLE = True
        print("✅ Connected to Redis")
    except redis.exceptions.ConnectionError:
        REDIS_AVAILABLE = False
        print("⚠ Redis installed but not running. Using in-memory fallback.")
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠ Redis not installed. Using in-memory fallback.")

# -------------------------
# App and storage
# -------------------------
app = FastAPI()

if not REDIS_AVAILABLE:
    messages_store = {}
    rate_limit_store = {}
    store_lock = threading.Lock()

MAX_MESSAGES_PER_RECIPIENT = 5
MAX_MESSAGES_PER_SECOND = 10
MESSAGE_TTL = 5  # seconds for ephemeral messages

server_private = PrivateKey.generate()
server_public = server_private.public_key

class Message(BaseModel):
    to: str          # recipient encryption public key (hex)
    from_: str       # sender signing key (hex) for verification
    enc_pub: str     # sender encryption public key (hex) for display
    message: str     # encrypted message (base64)
    signature: str   # signature of encrypted message (base64)


# -------------------------
# Helper: verify signature
# -------------------------
def verify_signature(sender_hex, message_b64, signature_b64):
    try:
        sender_verify_key = VerifyKey(bytes.fromhex(sender_hex))
        sender_verify_key.verify(base64.b64decode(message_b64), base64.b64decode(signature_b64))
        return True
    except Exception:
        return False

# -------------------------
# Send message
# -------------------------
@app.post("/send")
def send_message(msg: Message):
    # Verify signature with signing key
    if not verify_signature(msg.from_, msg.message, msg.signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    now = time.time()

    # Prepare message object for storage
    stored_msg = {
        "from": msg.from_,      
        "enc_pub": msg.enc_pub, 
        "message": msg.message,
        "signature": msg.signature
    }

    if REDIS_AVAILABLE:
        # Rate limiting per sender
        key = f"rate:{msg.from_}"
        r.zremrangebyscore(key, 0, now - 1)
        if r.zcard(key) >= MAX_MESSAGES_PER_SECOND:
            raise HTTPException(status_code=429, detail="Rate limit exceeded: max 10 messages/sec")
        r.zadd(key, {str(now): now})
        r.expire(key, 2)

        # Store message in recipient inbox
        inbox_key = f"inbox:{msg.to}"
        encoded = base64.b64encode(
            f"{msg.from_}:{msg.enc_pub}:{msg.message}:{msg.signature}".encode()
        ).decode()
        r.rpush(inbox_key, encoded)
        r.ltrim(inbox_key, -MAX_MESSAGES_PER_RECIPIENT, -1)
        r.expire(inbox_key, MESSAGE_TTL)

    else:
        # In-memory fallback
        with store_lock:
            # Rate limiting
            timestamps = rate_limit_store.get(msg.from_, [])
            timestamps = [t for t in timestamps if now - t < 1.0]
            if len(timestamps) >= MAX_MESSAGES_PER_SECOND:
                raise HTTPException(status_code=429, detail="Rate limit exceeded: max 10 messages/sec")
            timestamps.append(now)
            rate_limit_store[msg.from_] = timestamps

            # Store message
            if msg.to not in messages_store:
                messages_store[msg.to] = []
            messages_store[msg.to].append(stored_msg)
            # Keep last N messages
            messages_store[msg.to] = messages_store[msg.to][-MAX_MESSAGES_PER_RECIPIENT:]

    return {"status": "ok"}


# -------------------------
# Fetch inbox
# -------------------------
@app.get("/inbox/{recipient_key}")
def get_inbox(recipient_key: str):
    if REDIS_AVAILABLE:
        inbox_key = f"inbox:{recipient_key}"
        encoded_msgs = r.lrange(inbox_key, 0, -1)
        r.delete(inbox_key)

        msgs = []
        for em in encoded_msgs:
            decoded = base64.b64decode(em).decode()
            sender, enc_pub, message, signature = decoded.split(":", 3)
            msgs.append({
                "from": sender,      # signing key
                "enc_pub": enc_pub,  # encryption key for GUI
                "message": message,
                "signature": signature
            })
    else:
        with store_lock:
            msgs = messages_store.get(recipient_key, [])
            messages_store[recipient_key] = []

    return {"messages": msgs}

# -------------------------
# Server public key
# -------------------------
@app.get("/public-key")
def get_server_public_key():
    return {"public_key": server_public.encode().hex()}

# -------------------------
# Whispr server implementation
# -------------------------
