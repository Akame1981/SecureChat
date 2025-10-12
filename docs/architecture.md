# Whispr Architecture & Deep Dive

This document provides an in‑depth technical overview of Whispr's client, relay server, cryptographic design, data model, extensibility points, and threa---
## 6. Data Files & Persis---

## 7. WebRTC Voice Calls

### Architecture
- **Signaling**: Server-mediated SDP/ICE exchange via `/signal` WebSocket  
- **Media**: Direct P2P audio streams using STUN (stun.l.google.com:19302)
- **Invitation**: E2EE call invites sent through normal chat channel
- **Platform Support**: Linux (PulseAudio/ALSA), Windows, macOS

### Audio Pipeline
1. **Capture**: PulseAudio → ALSA → sounddevice fallback chain
2. **Transport**: aiortc WebRTC implementation
3. **Playback**: Platform-specific audio output device selection

### Call Flow
1. **Initiate**: Caller creates offer → sends encrypted invite via chat
2. **Accept**: Recipient joins call room → answers with SDP
3. **Connect**: ICE candidates exchanged → P2P audio established  
4. **Terminate**: Either party can hangup → other notified via signaling

---

## 8. Identicons

Deterministic circular identicons are generated from SHA256(public_key). A fixed logical grid (default 6×6 mirrored) ensures the same pattern at any requested pixel size (scaled with Lanczos) preventing "zoomed mismatch".

| File | Encryption | Salt Source | Contents |
|------|------------|-------------|----------|
| `data/keypair.bin` | SecretBox (PIN-derived) | Persistent scrypt salt | Private key, signing key, username |
| `data/recipients.json` | SecretBox (PIN-derived) | Fresh per encrypt | { name: pub_hex } |
| `data/whispr_messages.db` | SQLCipher | PIN-derived key | All chat history, groups, members |
| `data/attachments/<hash>.bin` | SecretBox (PIN-derived) | Fresh per encrypt | Encrypted file attachments |
| `analytics_events.log` | Plaintext line JSON | n/a | Events when Redis absent |

### SQLCipher Database Schema

**Direct Messages**: `messages` table with sender, recipient, ciphertext, timestamps
**Groups**: `groups`, `group_members`, `group_channels`, `group_messages` tables  
**Attachments**: File hash references with metadata in message records

Each file encrypts independently; compromise of one ciphertext doesn't leak others (aside from shared PIN factoring risk).tions.

> Version: 2025-10-12 – Matches current `main` branch state.

---
## 1. High-Level System Model

Whispr is a **hybrid E2EE communication platform** combining pull-based relay with real-time WebSocket push and WebRTC signaling. The server acts as a message queue, group coordination hub, and signaling relay while maintaining zero-knowledge of plaintext content.

```text
┌─────────────────────────────────────────────────────────────┐
│                     Whispr Client (GUI)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Messages   │  │  Voice Calls │  │    Groups    │       │
│  │  (E2EE Chat) │  │   (WebRTC)   │  │  (Channels)  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                           ││───────────────────┐            │
│              ┌────────────▼────────────┐ ┌──────────┐       │
│              │   Crypto Layer (NaCl)   │ │Decryption│-------│------------
│              │  • SealedBox Encryption │ └──────────┘       │           |
│              │  • Ed25519 Signatures   │                    │           |
│              │  • PIN-Protected Keys   │                    │           |
│              └────────────┬────────────┘                    │           |
│                           │                                 │           |
│              ┌────────────▼────────────┐                    │           |
│              │   SQLCipher Database    │                    │           |
│              │  (Encrypted Messages)   │                    │           |
│              └─────────────────────────┘                    │           |
└─────────────────────────────────────────────────────────────┘           |
                            │
                   HTTPS/WebSocket                               HTTPS/WebSocket
                            │                                             |
┌─────────────────────────────────────────────────────────────┐           |
│                   Whispr Server (FastAPI)                   │           |
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │           |
│  │   Message    │  │    Groups    │  │  Analytics   │       │-----------|
│  │    Relay     │  │   Backend    │  │  (Optional)  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                           │                                 │
│              ┌────────────▼────────────┐                    │
│              │   Redis (Optional) or   │                    │
│              │   In-Memory Queue       │                    │
│              └─────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

---
## 2. Communication Layers

Whispr operates on multiple communication layers:

### 2.1 Direct Messaging
- **Protocol**: Traditional E2EE point-to-point using NaCl SealedBox
- **Transport**: HTTP POST + WebSocket push notifications
- **Storage**: Server-side temporary queue, client-side encrypted SQLCipher

### 2.2 Group Messaging  
- **Protocol**: Symmetric group keys with member-specific encryption
- **Features**: Multi-channel groups, key rotation, member management
- **API**: Dedicated `/groups/*` endpoints with SQLite backend
- **Encryption**: ChaCha20-Poly1305 for group content + NaCl for key distribution

### 2.3 Voice Calls
- **Protocol**: WebRTC with server-mediated signaling
- **Transport**: Separate `/signal` WebSocket endpoint
- **Media**: Direct P2P audio streams with STUN/ICE
- **Security**: E2EE call invitations via chat layer

### 2.4 Real-time Push
- **Protocol**: WebSocket connections per client public key
- **Purpose**: Instant message delivery, reduces polling frequency
- **Fallback**: Graceful degradation to HTTP polling if WebSocket fails

---
## 3. Cryptographic Primitives

| Purpose | Primitive | Library | Notes |
|---------|-----------|---------|-------|
| Direct encryption | NaCl `SealedBox` | PyNaCl | Sender → recipient public key |
| Group encryption | ChaCha20-Poly1305 | PyNaCl SecretBox | Symmetric keys per group |
| Signatures | Ed25519 `SigningKey` | PyNaCl | Detached sign over ciphertext bytes |
| Key storage | NaCl `SecretBox` | PyNaCl | PIN-derived encryption for local storage |
| KDF | Scrypt (interactive params) | PyNaCl | Derives 64‑byte master key from PIN + salt |
| PIN integrity | HMAC-SHA256 | hashlib/hmac | Over encrypted key blob |
| Local DB encryption | SQLCipher | sqlcipher3-wheels | Full database encryption with PIN derivation |
| Group key generation | ChaCha20 key | PyNaCl | 32-byte symmetric keys for group content |

### Key File Layout (`keypair.bin`)

```text
0      : 0x01 (version)
1..32  : scrypt salt (32 bytes)
33..64 : HMAC tag (SHA256 over ciphertext)
65..end: secretbox ciphertext of:
          [2 bytes username_len][username_json][32 priv_key][32 signing_key]
```

### Direct Message Payload (client side structure before sending)

```json
{
  "to": "<recipient_enc_pub_hex>",
  "from_": "<sender_signing_pub_hex>",
  "enc_pub": "<sender_enc_pub_hex>",
  "message": "<base64 sealedbox ciphertext>",
  "signature": "<base64 signature(bytes)>",
  "timestamp": "<epoch seconds>"
}
```

### Group Message Payload (after group encryption)

```json
{
  "group_id": "<group_uuid>",
  "channel_id": "<channel_uuid>", 
  "sender_id": "<sender_enc_pub_hex>",
  "ciphertext": "<base64 group_encrypted_content>",
  "nonce": "<base64 encryption_nonce>",
  "key_version": "<int group_key_version>",
  "timestamp": "<epoch seconds>",
  "attachment_meta": "<optional json metadata>"
}
```

`signature = Ed25519( raw_ciphertext_bytes )` enabling tamper detection.

---
## 4. Server Architecture & Responsibilities

### 4.1 Core Message Relay

| Function | Enforced? | Details |
|----------|-----------|---------|
| Store ciphertext temporarily | Yes | Redis list or in‑memory list per recipient |
| Enforce per-sender rate limit | Yes | Redis ZSET or in‑memory timestamps |
| Verify signature | Yes | Rejects invalid messages (400) |
| WebSocket push notifications | Yes | Real-time delivery to connected clients |
| Provide forward secrecy | No | Static long‑lived keypairs (future: X3DH / Double Ratchet) |
| Metadata protection | Minimal | Relay sees sender/recipient public keys + timing |
| Replay protection | Partial | Inbox clear on fetch; no global nonce store |

### 4.2 Group Chat Backend

| Function | Implementation | Details |
|----------|---------------|---------|
| Group management | SQLite + SQLAlchemy | Create, join, leave groups |
| Channel management | Database relations | Multiple channels per group |
| Member permissions | Role-based (owner/admin/member) | Channel creation, member management |
| Key distribution | E2EE member-to-member | Server stores encrypted group keys per member |
| Message storage | Ciphertext only | Server never sees plaintext group content |

### 4.3 WebRTC Signaling

| Function | Implementation | Details |
|----------|---------------|---------|
| Room management | In-memory per call_id | Temporary peer connection coordination |
| SDP relay | WebSocket broadcast | Offer/answer exchange between peers |
| ICE coordination | Pass-through | STUN/TURN candidates relayed |
| Call invitations | Chat layer integration | E2EE call invites via normal messaging |

Redis inbox key: `inbox:<recipientPub>`, trimmed to last `MAX_MESSAGES_PER_RECIPIENT` and TTL `MESSAGE_TTL`.

Analytics counters are opportunistic; if disabled they do not affect delivery.

---
## 5. Client Architecture

`gui.py` orchestrates subsystems with enhanced real-time and media capabilities:

| Component | File | Responsibility |
|-----------|------|---------------|
| Main UI | `gui.py` | Application lifecycle, theme management, key loading |
| Theme system | `gui/theme_manager.py` | Loads JSON themes, broadcasts live changes |
| Direct messaging | `gui/widgets/sidebar.py` + `gui/layout.py` | Recipient list, message display |
| Group messaging | `gui/widgets/groups_panel.py` | Group/channel UI, member management |
| Voice calls | `gui/call_window.py` + `utils/rtc_manager.py` | WebRTC call interface, device selection |
| Real-time push | `utils/ws_client.py` | WebSocket client for instant delivery |
| Notifications | `gui/widgets/notification.py` | Cross-platform toast notifications |
| Message styling | `gui/message_styling.py` | Bubble creation, alignment, color mapping |
| Settings | `gui/settings/` | Appearance, server, advanced options |
| Key mgmt / PIN | `utils/crypto.py` + dialogs | Generation, encryption, signing |
| Local storage | `utils/chat_storage.py` + `utils/db.py` | SQLCipher encrypted history |
| Recipients store | `utils/recipients.py` | Encrypted map name→pubkey |
| Networking | `utils/network.py` | HTTP send, poll inbox |
| Chat manager | `utils/chat_manager.py` | Background fetch orchestration |
| Group manager | `utils/group_manager.py` | Group operations, key management |
| Auto-updater | `utils/auto_updater.py` | GitHub release checking and installation |

### Real-time Communication Flow

1. **WebSocket Connection**: Client connects to `/ws/{public_key}` on startup
2. **Message Send**: Sender posts to `/send` → Server stores + pushes to recipient WebSocket
3. **Instant Delivery**: Recipient receives via WebSocket → decrypts → displays immediately  
4. **Fallback Polling**: If WebSocket fails, `ChatManager` continues HTTP polling
5. **Call Signaling**: Separate `/signal` WebSocket for WebRTC SDP/ICE exchange

### Group Communication Flow

1. **Group Creation**: Owner generates symmetric key → encrypts for self → stores on server
2. **Member Addition**: Owner encrypts group key for new member → updates key distribution
3. **Message Send**: Encrypt with group key → post to `/groups/messages/send`
4. **Key Rotation**: Owner generates new key → re-encrypts for all current members → bumps version

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

## 9. Extensibility Points

| Area | Hook | How to Extend |
|------|------|---------------|
| Theme system | `ThemeManager.register_listener(cb)` | Recolor custom widgets on theme change |
| Real-time push | WebSocket message handlers | Add custom message types alongside chat |
| Group types | Channel type extensions | Media channels, file channels, custom protocols |
| Call integration | RTC event handlers | Video calls, screen sharing, recording |
| Analytics | `register_message` import | Replace with custom collector or message bus |
| Storage backend | Redis + SQLite abstraction | Alternative queue/DB with same semantics |
| Key file format | Version byte | Bump + append new sections (e.g., rotation metadata) |
| Message protocol | JSON payload | Add optional fields (must ignore unknown on server) |
| Attachment handling | Mime type dispatch | Custom preview/editing for file types |

---

## 10. Threat Model (Updated)

| Threat | Status | Notes / Mitigation |
|--------|--------|--------------------|
| Relay compromise | Partially mitigated | Sees metadata; cannot decrypt content; group keys distributed E2E |
| Group server compromise | Partially mitigated | Encrypted group keys per member; server sees membership |
| Passive network sniffing | Mitigated with TLS | Use cert pinning for stronger MITM resistance |
| Client device malware | Not mitigated | Key theft possible; SQLCipher provides some protection |
| PIN brute force (offline) | Partially mitigated | Scrypt KDF; need key file copy; no attempt counter |
| WebSocket MITM | Mitigated | TLS + signature verification on pushed messages |
| Call interception | Partially mitigated | WebRTC P2P + DTLS; signaling server sees metadata |
| Group key compromise | Recoverable | Key rotation support; forward secrecy within groups |
| Replay injection | Weak | Inbox flush reduces window; no explicit nonce tracking |
| Denial of service | Partial | Basic per‑sender rate limiting; group spam possible |

---

## 11. Planned Cryptographic Upgrades

1. **Video Calling**: WebRTC video track support with camera device selection
2. **Double Ratchet**: Ephemeral Diffie‑Hellman for forward/post-compromise secrecy  
3. **Multi-device Sync**: Cross-device key synchronization with device attestation
4. **Improved Metadata Protection**: Optional onion-style relay chaining
5. **Mobile Protocol**: Streamlined crypto for iOS/Android clients
6. **Plugin Security**: Sandboxed extension system for custom features

---

## 12. API Semantics Recap

### Direct Messaging
- `POST /send` – idempotency best‑effort; duplicate possible if client retries after network ambiguity
- `GET /inbox/{pub}?since=<epoch>` – destructive read (empties queue). Provide `since` to ignore older residual
- `WebSocket /ws/{pub}` – real-time push delivery; graceful fallback to polling

### Group Messaging  
- `POST /groups/create` – owner creates group + default channel + first member record
- `POST /groups/join` – join via invite code or admin approval  
- `POST /groups/messages/send` – encrypted group message with key version validation
- `POST /groups/messages/fetch` – retrieve channel history with since/limit pagination

### WebRTC Signaling
- `WebSocket /signal` – room-based SDP/ICE relay for call coordination
- Call invitation via encrypted chat messages enables E2EE call setup

### Error Surface

| Code | Cause |
|------|-------|
| 400  | Invalid signature / malformed payload |
| 403  | Insufficient group permissions |
| 404  | Group/channel not found |
| 409  | Group key version mismatch (client should fetch + retry) |
| 429  | Rate limit exceeded |
| 500  | Unexpected server error (should not leak stack in prod) |

---

## 13. Performance & Scalability Notes

| Dimension | Current | Observation |
|-----------|---------|-------------|
| Message send latency | Network + Redis O(1) + WebSocket push | Sub-second for most scenarios |
| Group message latency | Network + SQLite insert + key lookup | Scales with group size for key distribution |
| Voice call setup | WebRTC + STUN + signaling | 2-5 seconds typical connection time |
| Poll strategy | Adaptive (5s when WebSocket active) | WebSocket reduces server load significantly |
| Memory footprint | Small (bounded queues + SQLite) | Groups backend adds moderate overhead |
| CPU hot spots | Scrypt (PIN ops), group key crypto | Infrequent for PIN, scales with group activity |
| Database performance | SQLCipher + WAL mode | Good for typical chat loads; may need optimization for large groups |

---

## 14. Operational Guidelines

- Keep `MESSAGE_TTL` aligned with polling interval to balance freshness vs backlog risk
- Monitor Redis memory & key eviction policy (should not evict inbox keys prematurely)  
- Group database may need periodic cleanup of old messages/deleted groups
- WebSocket connection limits may require load balancing for high user counts
- Voice call quality depends on client network conditions; consider TURN server for NAT traversal
- SQLCipher performance benefits from adequate temp/cache directory space

---

## 15. Testing Suggestions

| Test | Purpose |
|------|---------|
| Signature tamper | Flip a bit in ciphertext → expect 400 reject |
| Rate limit | Burst > MAX_MESSAGES_PER_SECOND → 429 |
| Inbox flush | Send N msgs, fetch, second fetch empty |
| WebSocket failover | Kill WebSocket → verify polling continues |
| Group key rotation | Rotate key → verify old messages still decrypt |
| Voice call connectivity | Test across NAT/firewall scenarios |
| SQLCipher integrity | Database corruption recovery |
| Multi-device scenarios | Same PIN on different devices |

---

## 16. License & Attribution

See root `LICENSE.txt` (CC BY‑NC 4.0). Commercial usage requires permission.

---

## 17. Glossary

| Term | Definition |
|------|------------|
| E2EE | End‑to‑End Encryption |
| FS | Forward Secrecy |
| PCS | Post‑Compromise Security |
| TTL | Time To Live (expiration interval) |
| KDF | Key Derivation Function |
| WebRTC | Web Real-Time Communication |
| SDP | Session Description Protocol |
| ICE | Interactive Connectivity Establishment |
| STUN | Session Traversal Utilities for NAT |
| SQLCipher | Encrypted SQLite database |

---
Questions or proposals? Open a GitHub Issue with the label `design`.
