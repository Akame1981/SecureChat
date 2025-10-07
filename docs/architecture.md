# Whispr Architecture & Deep Dive

This document provides an in‑depth technical overview of Whispr’s client, relay server, cryptographic design, data model, extensibility points, and threat considerations.

> Version: 2025-10-08 – Matches current `main` branch state.

---
## 1. High-Level System Model

Whispr is an **opportunistic, minimal E2EE pull‑relay**. The server acts only as a transient queue with rate limiting + optional analytics. All confidentiality and authenticity are end‑to‑end between clients.

```text
+-----------+        HTTPS (ciphertext + signatures)        +-----------+
|  Sender   |  -------------------------------------------> |   Relay   |
|  (GUI)    |                                               |  (FastAPI) |
+-----------+                                               +-----------+
      ^                                                           |
      | (poll /inbox)                                             v
+-----------+                                               +-----------+
| Recipient | <--------------------------------------------- |  Storage  |
|  (GUI)    |  Pull, decrypt, verify; local history          | (Redis or |
+-----------+                                                |  memory)  |
                                                             +-----------+
```

---
## 2. Cryptographic Primitives

| Purpose | Primitive | Library | Notes |
|---------|-----------|---------|-------|
| Asym. encryption | NaCl `SealedBox` | PyNaCl | Sender → recipient public key |
| Signatures | Ed25519 `SigningKey` | PyNaCl | Detached sign over ciphertext bytes |
| Symmetric key storage | NaCl `SecretBox` | PyNaCl | AES/ChaCha20 (XSalsa20-Poly1305) inside SecretBox |
| KDF | Scrypt (interactive params) | PyNaCl | Derives 64‑byte master key from PIN + salt |
| PIN integrity | HMAC-SHA256 | hashlib/hmac | Over encrypted key blob |
| Local chat & recipients encryption | SecretBox + Scrypt | PyNaCl | Separate salts per file |

### Key File Layout (`keypair.bin`)

```text
0      : 0x01 (version)
1..32  : scrypt salt (32 bytes)
33..64 : HMAC tag (SHA256 over ciphertext)
65..end: secretbox ciphertext of:
          [2 bytes username_len][username_json][32 priv_key][32 signing_key]
```

### Message Payload (client side structure before sending)

```jsonc
{
  to: <recipient_enc_pub_hex>,
  from_: <sender_signing_pub_hex>,
  enc_pub: <sender_enc_pub_hex>,
  message: <base64 sealedbox ciphertext>,
  signature: <base64 signature(bytes)>,
  timestamp: <epoch seconds>
}
```
`signature = Ed25519( raw_ciphertext_bytes )` enabling tamper detection.

---
## 3. Server Responsibility & Constraints

| Function | Enforced? | Details |
|----------|-----------|---------|
| Store ciphertext temporarily | Yes | Redis list or in‑memory list per recipient |
| Enforce per-sender rate limit | Yes | Redis ZSET or in‑memory timestamps |
| Verify signature | Yes | Rejects invalid messages (400) |
| Provide forward secrecy | No | Static long‑lived keypairs (future: X3DH / Double Ratchet) |
| Metadata protection | Minimal | Relay sees sender/recipient public keys + timing |
| Replay protection | Partial | Inbox clear on fetch; no global nonce store |

Redis inbox key: `inbox:<recipientPub>`, trimmed to last `MAX_MESSAGES_PER_RECIPIENT` and TTL `MESSAGE_TTL`.

Analytics counters are opportunistic; if disabled they do not affect delivery.

---
## 4. Client Architecture

`gui.py` orchestrates subsystems:

| Component | File | Responsibility |
|-----------|------|---------------|
| Theme system | `gui/theme_manager.py` | Loads JSON themes, broadcasts live changes |
| Sidebar / Recipients | `gui/widgets/sidebar.py` | Recipient list, add dialog, identicon avatars |
| Notifications | `gui/widgets/notification.py` | Ephemeral toast popups |
| Message styling | `gui/message_styling.py` | Bubble creation, alignment, color mapping |
| Key mgmt / PIN | `utils/crypto.py` + dialogs | Generation, encryption, signing |
| Local storage | `utils/chat_storage.py` | Encrypted per‑recipient history |
| Recipients store | `utils/recipients.py` | Encrypted map name→pubkey |
| Networking | `utils/network.py` | Send, poll inbox loop |
| Chat manager | `utils/chat_manager.py` | Background fetch thread + dispatch |

### Live Theme Propagation Flow

`AppearanceTab.change_theme` → `ThemeManager.set_theme_by_name` → `ThemeManager.apply()` → listeners (`WhisprApp._on_theme_changed`, `Sidebar.refresh_theme`, `layout.refresh_theme`, etc.) recolor widgets in place.

---
## 5. Data Files & Persistence

| File | Encryption | Salt Source | Contents |
|------|------------|-------------|----------|
| `data/keypair.bin` | SecretBox (PIN-derived) | Persistent scrypt salt | Private key, signing key, username |
| `data/recipients.json` | SecretBox (PIN-derived) | Fresh per encrypt | { name: pub_hex } |
| `data/chats/<pub>.bin` | SecretBox (PIN-derived) | Fresh per encrypt | Array of message dicts |
| `analytics_events.log` | Plaintext line JSON | n/a | Events when Redis absent |

Each file encrypts independently; compromise of one ciphertext doesn’t leak others (aside from shared PIN factoring risk).

---

## 6. Identicons

Deterministic circular identicons are generated from SHA256(public_key). A fixed logical grid (default 6×6 mirrored) ensures the same pattern at any requested pixel size (scaled with Lanczos) preventing “zoomed mismatch”.

---

## 7. Extensibility Points

| Area | Hook | How to Extend |
|------|------|---------------|
| Theme system | `ThemeManager.register_listener(cb)` | Recolor custom widgets on theme change |
| Analytics | `register_message` import | Replace with custom collector or message bus |
| Storage backend | Redis abstraction | Swap for alternative queue with same semantics |
| Key file format | Version byte | Bump + append new sections (e.g., rotation metadata) |
| Message protocol | JSON payload | Add optional fields (must ignore unknown on server) |

---

## 8. Threat Model (Condensed)

| Threat | Status | Notes / Mitigation |
|--------|--------|--------------------|
| Relay compromise | Partially mitigated | Sees metadata; cannot decrypt content |
| Passive network sniffing | Mitigated with TLS | Use cert pinning for stronger MITM resistance |
| Client device malware | Not mitigated | Key theft possible |
| PIN brute force (offline) | Partially mitigated | Scrypt KDF; need key file copy; no attempt counter inside file |
| Replay injection | Weak | Inbox flush reduces replay window; no explicit nonce tracking |
| Forward secrecy loss | Present | Static keypairs; future ratchet needed |
| Denial of service | Partial | Basic per‑sender rate limiting only |

---

## 9. Planned Cryptographic Upgrades

1. Ephemeral Diffie‑Hellman introduction (X25519) alongside static identity keys.
2. Staged adoption of a double‑ratchet for FS and PCS (post‑compromise security).
3. Recipient capability advertisement (supported ciphers, ratchet version) via signed metadata message.
4. Optional onion-style relay chaining for metadata reduction.

---

## 10. API Semantics Recap

- `POST /send` – idempotency best‑effort; duplicate possible if client retries after network ambiguity.
- `GET /inbox/{pub}?since=<epoch>` – destructive read (empties queue). Provide `since` to ignore older residual messages if clock skew occurs.
- `GET /public-key` – server long‑term encryption public key (currently unused in baseline protocol for messages, but reserved for future handshake / server-signed metadata).

### Error Surface

| Code | Cause |
|------|-------|
| 400  | Invalid signature / malformed payload |
| 429  | Rate limit exceeded |
| 500  | Unexpected server error (should not leak stack in prod) |

---

## 11. Performance Notes

| Dimension | Current | Observation |
|-----------|---------|-------------|
| Message send latency | Network + Redis O(1) ops | Fine for low volume |
| Poll strategy | Fixed interval thread | Could move to long‑poll / WS |
| Memory footprint | Small (in‑memory queues) | Bounded by MAX & TTL |
| CPU hot spots | Scrypt (PIN ops) | Infrequent (unlock only) |

---

## 12. Operational Guidelines

- Keep `MESSAGE_TTL` aligned with polling interval to balance freshness vs backlog risk.
- Rotate server key (current ephemeral) only when protocol supports rekey notice to clients.
- Monitor Redis memory & key eviction policy (should not evict inbox keys prematurely).

---

## 13. Testing Suggestions

| Test | Purpose |
|------|---------|
| Signature tamper | Flip a bit in ciphertext → expect 400 reject |
| Rate limit | Burst > MAX_MESSAGES_PER_SECOND → 429 |
| Inbox flush | Send N msgs, fetch, second fetch empty |
| Decrypt failure | Use wrong private key → catch exception gracefully |
| Theme live switch | Ensure all widgets recolor without restart |

---

## 14. License & Attribution

See root `LICENSE.txt` (CC BY‑NC 4.0). Commercial usage requires permission.

---

## 15. Glossary

| Term | Definition |
|------|------------|
| E2EE | End‑to‑End Encryption |
| FS | Forward Secrecy |
| PCS | Post‑Compromise Security |
| TTL | Time To Live (expiration interval) |
| KDF | Key Derivation Function |

---
Questions or proposals? Open a GitHub Issue with the label `design`.
