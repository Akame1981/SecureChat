import base64
import threading
import time
import asyncio
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from nacl.public import PrivateKey
from nacl.signing import VerifyKey
from pydantic import BaseModel

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()  # ✅ create app first

# Then add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins for WS connections
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# Active WebSocket connections: recipient_key -> set[WebSocket]
active_ws = {}
active_ws_lock = threading.Lock()

# Attempt to import analytics event collector to feed live stats
try:
    from server_utils.analytics_backend.services.event_collector import register_message, register_attachment  # type: ignore
    ANALYTICS_ENABLED = True
except Exception:
    ANALYTICS_ENABLED = False
    def register_message(*args, **kwargs):  # fallback no-op
        return None
    def register_attachment(*args, **kwargs):  # fallback no-op
        return None

if not REDIS_AVAILABLE:
    messages_store = {}
    rate_limit_store = {}
    store_lock = threading.Lock()

MAX_MESSAGES_PER_RECIPIENT = 20
MAX_MESSAGES_PER_SECOND = 10
MESSAGE_TTL = 60  # seconds for ephemeral messages

server_private = PrivateKey.generate()
server_public = server_private.public_key

class Message(BaseModel):
    to: str
    from_: str
    enc_pub: str
    message: str
    signature: str
    timestamp: Optional[float] = None  # client timestamp

class AttachmentUpload(BaseModel):
    to: str
    from_: str
    enc_pub: str
    blob: str  # sealed box ciphertext (base64)
    signature: str  # signature over raw blob bytes
    name: str
    size: int
    sha256: str  # hex sha256 of ciphertext or original (we choose ciphertext)

# In-memory attachment store (TTL similar to messages, could be extended)
attachments_store = {}
attachments_lock = threading.Lock()


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
async def send_message(msg: Message):
    # Verify signature
    if not verify_signature(msg.from_, msg.message, msg.signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    now = time.time()
    stored_msg = {
        "from": msg.from_,
        "enc_pub": msg.enc_pub,
        "message": msg.message,
        "signature": msg.signature,
        "timestamp": msg.timestamp or now
    }

    if REDIS_AVAILABLE:
        # Rate limit per sender
        key = f"rate:{msg.from_}"
        r.zremrangebyscore(key, 0, now - 1)
        if r.zcard(key) >= MAX_MESSAGES_PER_SECOND:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        r.zadd(key, {str(now): now})
        r.expire(key, 2)

        # Store message in recipient inbox
        inbox_key = f"inbox:{msg.to}"
        encoded = base64.b64encode(str(stored_msg).encode()).decode()
        r.rpush(inbox_key, encoded)
        r.ltrim(inbox_key, -MAX_MESSAGES_PER_RECIPIENT, -1)
        r.expire(inbox_key, MESSAGE_TTL)

        # ---------- Cross-process analytics counters ----------
        try:
            # Day and hour keys in UTC
            import datetime, math, json
            dt_utc = datetime.datetime.utcfromtimestamp(now)
            day_key = dt_utc.strftime('%Y%m%d')
            hour_key = dt_utc.strftime('%Y%m%d%H')
            size_bytes = len(base64.b64decode(msg.message)) if msg.message else 0
            pipe = r.pipeline()
            pipe.incr(f'metrics:messages:count:{day_key}')
            if size_bytes:
                pipe.incrby(f'metrics:messages:bytes:{day_key}', size_bytes)
            pipe.incr(f'metrics:messages:day:{day_key}')  # duplicate daily counter (compat)
            pipe.incr(f'metrics:messages:hour:{hour_key}')
            pipe.sadd('metrics:users:all', msg.from_)
            pipe.sadd(f'metrics:users:new:{day_key}', msg.from_)
            # Active users: score = last seen timestamp
            pipe.zadd('metrics:active_users', {msg.from_: now})
            # Optional trim of old active users beyond 24h
            pipe.zremrangebyscore('metrics:active_users', 0, now - 86400)
            pipe.execute()
        except Exception:
            pass

    else:
        with store_lock:
            # Rate limit
            timestamps = rate_limit_store.get(msg.from_, [])
            timestamps = [t for t in timestamps if now - t < 1.0]
            if len(timestamps) >= MAX_MESSAGES_PER_SECOND:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            timestamps.append(now)
            rate_limit_store[msg.from_] = timestamps

            # Store message
            if msg.to not in messages_store:
                messages_store[msg.to] = []
            messages_store[msg.to].append(stored_msg)
            messages_store[msg.to] = messages_store[msg.to][-MAX_MESSAGES_PER_RECIPIENT:]

    # Feed analytics (size is base64 message length decoded approx)
    try:
        size_bytes = len(base64.b64decode(msg.message))
    except Exception:
        size_bytes = len(msg.message)
    register_message(size_bytes=size_bytes, sender=msg.from_, recipient=msg.to, ts=stored_msg["timestamp"])

    # Fallback file logging for analytics when Redis not running (consumed by analytics backend)
    if not REDIS_AVAILABLE:
        try:
            from pathlib import Path
            import json
            log_path = Path('analytics_events.log')
            event = {
                'ts': stored_msg["timestamp"],
                'size': size_bytes,
                'from': msg.from_,
                'to': msg.to
            }
            with log_path.open('a', encoding='utf-8') as f:
                f.write(json.dumps(event, separators=(',', ':')) + '\n')
        except Exception:
            pass

    # Push via WebSocket if recipient online (await directly, endpoint is async)
    try:
        with active_ws_lock:
            conns = list(active_ws.get(msg.to, []))
        if conns:
            payload = stored_msg
            for ws in conns:
                try:
                    await ws.send_json(payload)
                except Exception:
                    pass
    except Exception as e:
        print(f"WS push failed: {e}")

    return {"status": "ok", "analytics": ANALYTICS_ENABLED}


# -------------------------
# Upload attachment (metadata + sealed ciphertext)
# -------------------------
@app.post("/upload")
def upload_attachment(att: AttachmentUpload):
    # Verify signature over blob
    if not verify_signature(att.from_, att.blob, att.signature):
        raise HTTPException(status_code=400, detail="Invalid signature")
    # Basic size guard (could enforce a higher limit separately)
    if att.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Attachment too large")
    import base64, hashlib, time as _time
    try:
        blob_bytes = base64.b64decode(att.blob)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid blob base64")
    # Hash check consistency
    calc_hash = hashlib.sha256(blob_bytes).hexdigest()
    if calc_hash != att.sha256:
        raise HTTPException(status_code=400, detail="sha256 mismatch")
    now = _time.time()
    with attachments_lock:
        attachments_store[att.sha256] = {
            "from": att.from_,
            "to": att.to,
            "enc_pub": att.enc_pub,
            "blob": att.blob,
            "name": att.name,
            "size": att.size,
            "ts": now,
        }

    # Analytics: treat attachment as its own event stream
    try:
        # size already provided (ciphertext size) use att.size
        register_attachment(size_bytes=att.size, sender=att.from_, recipient=att.to, ts=now)
        if REDIS_AVAILABLE:
            import datetime as _dt
            day_key = _dt.datetime.utcfromtimestamp(now).strftime('%Y%m%d')
            hour_key = _dt.datetime.utcfromtimestamp(now).strftime('%Y%m%d%H')
            try:
                pipe = r.pipeline()
                pipe.incr(f'metrics:attachments:count:{day_key}')
                pipe.incrby(f'metrics:attachments:bytes:{day_key}', att.size)
                pipe.incr(f'metrics:attachments:hour:{hour_key}')
                pipe.execute()
            except Exception:
                pass
        else:
            # file log fallback
            try:
                from pathlib import Path
                import json as _json
                log_path = Path('analytics_events.log')
                event = {
                    'ts': now,
                    'size': att.size,
                    'from': att.from_,
                    'to': att.to,
                    'type': 'attachment'
                }
                with log_path.open('a', encoding='utf-8') as f:
                    f.write(_json.dumps(event, separators=(',', ':')) + '\n')
            except Exception:
                pass
    except Exception:
        pass
    return {"att_id": att.sha256, "status": "ok"}


# -------------------------
# Download attachment
# -------------------------
@app.get("/download/{att_id}")
def download_attachment(att_id: str, recipient: str):
    import time as _time
    with attachments_lock:
        entry = attachments_store.get(att_id)
        # Optionally purge expired
        if entry and _time.time() - entry.get("ts", 0) > MESSAGE_TTL:
            attachments_store.pop(att_id, None)
            entry = None
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")
    if entry.get("to") != recipient:
        raise HTTPException(status_code=403, detail="Not authorized for this attachment")
    # Return minimal metadata + ciphertext blob
    return {
        "att_id": att_id,
        "blob": entry["blob"],
        "name": entry["name"],
        "size": entry["size"],
        "from": entry["from"],
        "to": entry["to"],
    }


# -------------------------
# Fetch inbox with optional `since`
# -------------------------
@app.get("/inbox/{recipient_key}")
def get_inbox(recipient_key: str, since: Optional[float] = Query(0)):
    msgs = []

    if REDIS_AVAILABLE:
        inbox_key = f"inbox:{recipient_key}"
        encoded_msgs = r.lrange(inbox_key, 0, -1)
        r.delete(inbox_key)

        for em in encoded_msgs:
            decoded = eval(base64.b64decode(em).decode())
            if decoded.get("timestamp", 0) > since:
                msgs.append(decoded)
    else:
        with store_lock:
            stored = messages_store.get(recipient_key, [])
            msgs = [m for m in stored if m.get("timestamp", 0) > since]
            messages_store[recipient_key] = []

    # Return messages sorted by timestamp
    msgs.sort(key=lambda x: x.get("timestamp", 0))
    return {"messages": msgs}


# -------------------------
# Server public key
# -------------------------
@app.get("/public-key")
def get_server_public_key():
    return {"public_key": server_public.encode().hex(), "analytics": ANALYTICS_ENABLED}


# -------------------------
# WebSocket endpoint
# -------------------------
@app.websocket("/ws/{recipient_key}")
async def websocket_endpoint(websocket: WebSocket, recipient_key: str):
    await websocket.accept()
    # Register
    with active_ws_lock:
        bucket = active_ws.get(recipient_key)
        if not bucket:
            bucket = set()
            active_ws[recipient_key] = bucket
        bucket.add(websocket)
    try:
        while True:
            # We don't expect client-originated messages (could be ping). Just receive to detect disconnects.
            try:
                await websocket.receive_text()
            except Exception:
                # Could implement periodic ping; for now just continue.
                await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    finally:
        with active_ws_lock:
            bucket = active_ws.get(recipient_key, set())
            if websocket in bucket:
                bucket.remove(websocket)
            if not bucket and recipient_key in active_ws:
                active_ws.pop(recipient_key, None)


@app.websocket("/ws")
async def websocket_endpoint_query(websocket: WebSocket, recipient: str):
    """Alternate endpoint form: /ws?recipient=PUBHEX for backward / proxy compatibility."""
    await websocket.accept()
    recipient_key = recipient
    with active_ws_lock:
        bucket = active_ws.get(recipient_key)
        if not bucket:
            bucket = set()
            active_ws[recipient_key] = bucket
        bucket.add(websocket)
    try:
        while True:
            try:
                await websocket.receive_text()
            except Exception:
                await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    finally:
        with active_ws_lock:
            bucket = active_ws.get(recipient_key, set())
            if websocket in bucket:
                bucket.remove(websocket)
            if not bucket and recipient_key in active_ws:
                active_ws.pop(recipient_key, None)

