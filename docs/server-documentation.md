# SecureChat Server Documentation

This document describes the SecureChat server codebase and its API.

---

## Overview

The SecureChat server is built with FastAPI and provides endpoints for sending and receiving encrypted messages.  
It supports Redis for persistent, ephemeral message storage and rate limiting, with an in-memory fallback if Redis is unavailable.

---

## Main Components

- **server.py**: Main FastAPI application. Handles message send/receive, rate limiting, and signature verification.
- **Redis (optional)**: Used for scalable, ephemeral message storage and rate limiting.
- **Ephemeral In-Memory Store**: Used if Redis is not available.

---

## Key Features

- **Ephemeral Messaging**:  
  - Messages are stored temporarily (default: 5 seconds) and deleted after retrieval.
  - Only the last N messages per recipient are kept (default: 5).

- **Rate Limiting**:  
  - Limits senders to 10 messages per second.

- **Signature Verification**:  
  - All messages must be signed with the sender's Ed25519 signing key.
  - The server verifies the signature before accepting a message.

- **Public Key Endpoint**:  
  - The server exposes its public key for clients.

---

## API Endpoints

### `POST /send`

Send an encrypted message to a recipient.

**Request Body:**
```json
{
  "to": "<recipient encryption public key hex>",
  "from_": "<sender signing key hex>",
  "enc_pub": "<sender encryption public key hex>",
  "message": "<encrypted message (base64)>",
  "signature": "<signature of encrypted message (base64)>"
}
```

**Response:**
```json
{ "status": "ok" }
```

**Errors:**
- `400 Invalid signature`
- `429 Rate limit exceeded`

---

### `GET /inbox/{recipient_key}`

Fetch and delete all messages for a recipient.

**Response:**
```json
{
  "messages": [
    {
      "from": "<sender signing key hex>",
      "enc_pub": "<sender encryption public key hex>",
      "message": "<encrypted message (base64)>",
      "signature": "<signature (base64)>"
    }
  ]
}
```

---

### `GET /public-key`

Get the server's encryption public key.

**Response:**
```json
{ "public_key": "<server public key hex>" }
```

---

## Security Notes

- The server does not store any private keys.
- Messages are **never stored in plain text**; they are always encrypted.
- Messages are only stored temporarily and are deleted after retrieval.
- All messages must be signed and are verified before acceptance.
- Rate limiting prevents abuse.


---

## Running the Server

**With Redis:**
1. Start Redis on localhost:6379.
2. Run:
   ```sh
   uvicorn server:app --host 0.0.0.0 --port 8000
   ```

**Without Redis:**
- The server will use in-memory storage and print a warning.

---

## File Reference

- [`server.py`](../server.py): FastAPI server logic.

---

## Example Usage

- Send a message:  
  Use the `/send` endpoint with a properly signed and encrypted payload.
- Fetch messages:  
  Use the `/inbox/{recipient_key}` endpoint to retrieve and delete messages.

---

For client documentation, see [docs/client-usage.md](client-usage.md).

For server setup, see [docs/setup-server.md](setup-server.md).