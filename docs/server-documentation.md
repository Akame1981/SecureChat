# Whispr Server Documentation

In‑depth guide to the FastAPI relay: endpoints, ephemeral storage model, rate limiting, analytics, and security assumptions.

## Table of Contents

1. [Overview](#overview)
2. [Runtime Responsibilities](#runtime-responsibilities)
3. [Core Endpoints](#core-endpoints)
4. [Data Model](#data-model)
5. [Ephemeral Storage Implementations](#ephemeral-storage-implementations)
6. [Rate Limiting](#rate-limiting)
7. [Analytics Integration](#analytics-integration)
8. [Validation & Error Handling](#validation--error-handling)
9. [Security Notes](#security-notes)
10. [Extension Points](#extension-points)
11. [Performance Considerations](#performance-considerations)
12. [Troubleshooting](#troubleshooting)
13. [Example curl Commands](#example-curl-commands)
14. [Future Improvements](#future-improvements)

---

## Overview

Stateless (aside from ephemeral queues) relay for **ciphertext envelopes**. It never holds plaintext or private keys. Redis is optional; if absent an in‑memory fallback is used (single process scope).

Design goals:

- Minimal logic: enqueue, verify signature, rate limit, deliver & purge.
- Operate safely with or without Redis.
- Avoid user enumeration leaks (only recipient keys used as inbox identifiers).

---

## Main Components

- **server.py**: Main FastAPI application. Handles message send/receive, rate limiting, and signature verification.
- **Redis (optional)**: Used for scalable, ephemeral message storage and rate limiting.
- **Ephemeral In-Memory Store**: Used if Redis is not available.

---

## Runtime Responsibilities

| Responsibility | Implemented? | Notes |
|----------------|-------------|-------|
| Verify Ed25519 signature | Yes | Rejects invalid payload early (400) |
| Enforce per-sender rate | Yes | 10 msgs/sec (config constant) |
| Ephemeral queue store | Yes | Redis list (trim+TTL) or in-memory list |
| Timestamp attach | Partial | Accepts client timestamp or sets server time |
| Analytics counters | Optional | Redis pipeline or file log fallback |
| Public server key exposure | Yes | `/public-key` |
| Replay protection | Minimal | Inbox deletion on fetch only |

---

## Core Endpoints

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

## Data Model

Internal stored message (Python dict):

```jsonc
{
  "from": "<sender signing key hex>",
  "enc_pub": "<sender encryption public key hex>",
  "message": "<base64 sealedbox ciphertext>",
  "signature": "<base64 signature>",
  "timestamp": 1733677337.123  // float seconds
}
```

No plaintext or recipient private key material is ever present.

## Ephemeral Storage Implementations

| Mode | Structure | Trim Logic | Expiry | Concurrency |
|------|-----------|-----------|--------|-------------|
| Redis | List `inbox:<recipient>` | `LTRIM` to last N | `EXPIRE` TTL | Multi-process safe |
| Memory | Dict `messages_store[recipient]` | Slice last N | TTL implicit (cleared on fetch) | Single-process only |

## Rate Limiting

| Store | Mechanism | Window | Complexity |
|-------|-----------|--------|------------|
| Redis | Sorted set of timestamps | 1 second sliding | O(log n) ops + trim |
| Memory | List of floats pruned | 1 second sliding | O(n) prune (small n) |

`MAX_MESSAGES_PER_SECOND` constant defines threshold (default 10). Exceed → HTTP 429.

## Analytics Integration

If `server_utils.analytics_backend` imports successfully, `register_message(...)` is invoked with `size_bytes`, sender, recipient, and timestamp. When Redis absent, a lightweight append‑only log `analytics_events.log` accumulates JSON lines for later batch ingestion.

## Validation & Error Handling

| Step | Failure Action |
|------|----------------|
| Base64 decoding | 400 invalid signature (implicit) |
| Signature verify | 400 Invalid signature |
| Rate limit breach | 429 Rate limit exceeded |
| Internal exception | 500 (stack suppressed in production) |

## Security Notes

| Aspect | State | Notes |
|--------|-------|-------|
| Plaintext storage | None | Only ciphertext is persisted transiently |
| Message integrity | Enforced | Ed25519 verify before enqueue |
| Metadata leakage | Present | Sender & recipient public keys + timing |
| Key compromise risk | Low at server | No private keys handled |
| Replay mitigation | Weak | Fetch drains inbox, no nonce DB |
| DoS mitigation | Basic | Per-sender rate only |


---

## Extension Points

| Area | How to Extend |
|------|---------------|
| Storage | Replace Redis list usage with DB / MQ layer implementing same push/trim/delete semantics |
| Rate limiting | Swap per-sender logic for token bucket / leaky bucket in Redis |
| Authentication | Add optional API key header verification wrapper |
| Analytics | Implement richer event schema or export to Kafka / Prometheus |
| Protocol | Add fields (must ignore unknowns) / version envelope |

## Performance Considerations

| Factor | Impact | Tip |
|--------|--------|-----|
| Redis latency | Affects send throughput | Keep Redis local or on low‑latency network |
| Large message size | Increases base64 overhead | Enforce max size (future) |
| High concurrency | Python GIL for in-memory mode | Prefer Redis for scaling |

## Troubleshooting

| Symptom | Cause | Remedy |
|---------|-------|--------|
| 400 Invalid signature | Mismatched signing key / tampered payload | Check client signing key, resync keys |
| 429 Rate limit exceeded | Flood from sender | Backoff or raise limit constant (test only) |
| Empty inbox despite sends | Fetch raced after earlier fetch cleared queue | Use `since` param; confirm timing |
| Redis fallback warning | Redis not running | Start Redis or ignore if single-user testing |

## Example curl Commands

Send (example values):

```bash
curl -X POST http://localhost:8000/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "<recipient_pub>",
    "from_": "<sender_signing_pub>",
    "enc_pub": "<sender_enc_pub>",
    "message": "<base64_ciphertext>",
    "signature": "<base64_signature>",
    "timestamp": 1733677337.01
  }'
```

Fetch inbox:

```bash
curl http://localhost:8000/inbox/<recipient_pub>
```

Server public key:

```bash
curl http://localhost:8000/public-key
```

## Future Improvements

- WebSocket / SSE push channel
- Forward secrecy handshake introduction
- Structured analytics metrics endpoint
- Attachment size enforcement & rejection
- Enhanced replay / duplicate suppression

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

For server setup, see [docs/setup-server.md](updates/0e9b1e05f9c97128512ac8a69bd4e62c9c44fddd/docs/setup-server.md).
