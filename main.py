from fastapi import FastAPI
from pydantic import BaseModel
from nacl.public import PrivateKey

app = FastAPI()

messages_store = {}
MAX_MESSAGES_PER_RECIPIENT = 5

server_private = PrivateKey.generate()
server_public = server_private.public_key

class Message(BaseModel):
    to: str       # recipient public key (hex)
    from_: str    # sender public key (hex)
    message: str  # encrypted message (base64 or hex)

@app.post("/send")
def send_message(msg: Message):
    if msg.to not in messages_store:
        messages_store[msg.to] = []
    messages_store[msg.to].append({
        "from": msg.from_,
        "message": msg.message
    })
    # Keep only last 5 messages per recipient
    messages_store[msg.to] = messages_store[msg.to][-MAX_MESSAGES_PER_RECIPIENT:]
    return {"status": "ok"}

@app.get("/inbox/{recipient_key}")
def get_inbox(recipient_key: str):
    msgs = messages_store.get(recipient_key, [])
    messages_store[recipient_key] = []  # delete after fetch
    return {"messages": msgs}

@app.get("/public-key")
def get_server_public_key():
    return {"public_key": server_public.encode().hex()}
