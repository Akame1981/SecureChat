# 🕵️ Whispr

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-green.svg)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Redis Optional](https://img.shields.io/badge/Cache-Redis%20(Optional)-d82c20.svg)](https://redis.io/)
![State](https://img.shields.io/badge/State-Alpha-orange.svg)

**Whispr** is a lightweight end‑to‑end encrypted (E2EE) chat client & minimal message relay service. The server never sees plaintext. Keys never leave the client. Messages are ephemeral by design.

> Not security-audited. Do not rely on Whispr for high‑risk environments yet.

---

## 🚨 Important Notice

For detailed instructions on **setting up the server**, including HTTPS, self-signed certificates, and systemd setup, please refer to the [Whispr Documentation](docs/setup-server.md).

> **Never share your PIN or private key.**  
> The server cannot decrypt your messages, but your device security is your responsibility.

---

## ✨ Feature Highlights

| Category | Current | Notes |
|----------|---------|-------|
| Encryption | NaCl `SealedBox` + `Ed25519` signatures | Per‑message authenticity & confidentiality |
| Key Storage | Local (`SecretBox` + Scrypt KDF) | PIN protected (blacklist + heuristics) |
| Transport | FastAPI relay + optional WebSocket push | In‑memory or Redis queues; optional real‑time push via WebSocket |
| Ephemerality | Last N msgs (default 20) | Cleared on fetch / TTL 60s (Redis) |
| GUI Client | Tkinter + themes | Light/Dark/Custom |
| Rate Limiting | 10 msgs/sec | Abuse prevention |
| Analytics | Optional backend + dashboard | Auto-disable if absent |
| Packaging | PyInstaller aware | Manual build notes |
| Planned | Offline/groups/calls | See roadmap (file sharing and WebSocket push implemented) |

Additional conveniences:

- Username embedding in encrypted key file (`keypair.bin`).
- Recipient public key list stored locally (`recipients.json`).
- Theming via JSON with dynamic reload.
- Optional local analytics file fallback (`analytics_events.log`) when Redis absent.

---

## ⚡ Quick Start (Client Only)

```bash
git clone https://github.com/Akame1981/Whispr.git
cd Whispr
python -m venv venv
./venv/Scripts/activate   # Windows
# source venv/bin/activate # macOS/Linux
pip install -r requirements.txt
python gui.py
```

On first launch you will be asked to set a PIN (used to encrypt your private keys). A keypair is generated automatically.

> By default the client points to the public demo server over HTTPS. Run your own server for full control.

---

## 🧪 Running Your Own Server (Basic)

```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Then in the GUI Settings, switch to Custom Server and set `http://127.0.0.1:8000` (or your LAN IP). If you want TLS locally, place a certificate in `utils/cert.pem` and enable certificate use in settings.

### Optional: Redis for Ephemeral Scaling

When Redis is available (`localhost:6379`) the server:

- Uses Redis lists per recipient (`inbox:<pub>`) with TTL.
- Tracks rate limiting via sorted sets.
- Aggregates lightweight daily/hourly analytics counters.

If Redis is absent the server falls back to an in‑memory dictionary (per‑process) and a line‑delimited JSON analytics log.

---

## � Optional Analytics Stack

The project ships an experimental analytics backend and dashboard (Next.js + Tailwind) for real‑time message metrics (counts, bytes, users).

Spin it up (requires Docker):

```bash
docker compose -f docker-compose.analytics.yml up --build
```

Services:

- Backend: FastAPI microservice (port 8001)
- Frontend: Next.js dashboard (port 3001)

Environment variables for the backend live in `server_utils/analytics_backend/.env` (create if missing). If the analytics collector is unreachable the main server continues normally.

---

## 🧱 Architecture Overview

```text
[User Input]
   │
   ▼
 GUI (Tkinter) ──► Local Key Mgmt (SecretBox + scrypt PIN KDF)
   │                       │
   │ (encrypt + sign)      │ (keypair.bin encrypted)
   ▼                       │
 Message Envelope (SealedBox ciphertext + Ed25519 signature)
   │
   ▼ HTTPS POST /send
 FastAPI Relay ──┬─► (Redis / in‑memory queue; max N msgs; TTL)
                 └─► (Optional analytics counters)
   │
   ▼
 Recipient fetches /inbox/<pub> → decrypts locally → local (encrypted) history
```

Key points:

- Server is intentionally dumb: store, rate limit, expire. No decryption possible.
- No multi-device sync yet; keypair is local to one machine.
- Inbox fetch clears messages (pull‑and‑delete retrieval semantics).
- Optionally a `since` timestamp can be supplied to filter messages.

### Message Flow (Simplified)

1. Plaintext → SealedBox(public_recipient)
2. Base64(ciphertext) signed via Ed25519
3. Payload: `{to, from_, enc_pub, message, signature, timestamp}`
4. Server validates signature against `from_` then enqueues.
5. Recipient fetches & decrypts with private key.

---

## ⚡ Real-time push (WebSockets)

WebSocket support has been added to provide low‑latency, server‑pushed delivery of incoming messages. The server exposes two compatible endpoints:

- Path form: `/ws/{recipient_pubhex}`
- Query form: `/ws?recipient={recipient_pubhex}`

Notes:

- The client will attempt to start a WebSocket background thread if the `websocket-client` package is available. If not installed, the client falls back to periodic polling.
- TLS is supported via `wss://` when you configure the client to use an `https://` server URL and provide a pinned certificate (`utils/cert.pem`) in settings.
- The client reduces polling frequency automatically when a WebSocket connection is active.
- WebSocket push sends the same envelope structure as the `/inbox` payload (fields: `from`, `enc_pub`, `message`, `signature`, `timestamp`). The client verifies signatures and decrypts messages locally before displaying or storing them.

Server-side behavior:

- When a message is accepted by `POST /send` the server will attempt to push the stored envelope to any active WebSocket connections for the recipient. Failures are ignored (best‑effort delivery).
- The WebSocket endpoints accept simple pings from clients but are primarily used for server→client push. Disconnects and handshake failures are handled gracefully.

## 📎 File sharing (Attachments)

Attachments (file sharing) are implemented end‑to‑end encrypted and ephemeral. Key points:

- Client behavior:
  - GUI supports sending attachments via the Attach button and optional drag & drop. Attachments are encrypted client‑side and the GUI stores a local, encrypted copy in `data/attachments` (see `utils/attachments.py`).
  - When sending, the client uploads the sealed ciphertext and metadata to the server using `POST /upload` and stores a placeholder message locally that points to the attachment (name, size, `att_id`).
  - Downloading an attachment is done via `GET /download/{att_id}?recipient={your_pubhex}`; the client will request the ciphertext from the server, verify the recipient, then decrypt locally using the owner's PIN‑derived key.

- Server behavior / API:
  - `POST /upload` accepts an attachment envelope containing `{to, from_, enc_pub, blob, signature, name, size, sha256}` where `blob` is the base64 sealed ciphertext and `sha256` is a hex digest used as the attachment id (`att_id`).
  - The server verifies the signature over the blob, enforces a size guard (default 10 MB), stores the ciphertext in an in‑memory attachment store (or Redis when configured), and returns `{"att_id": "<sha256>", "status": "ok"}`.
  - `GET /download/{att_id}?recipient=<pubhex>` returns `{"att_id","blob","name","size","from","to"}` if the recipient matches and the attachment has not expired.
  - Attachments are ephemeral and subject to the same TTL used for messages (default 60s) unless you configure a longer retention on the server side.

- Security model:
  - Attachments are sealed/encrypted by the sender using the recipient's public key (SealedBox) and signed by the sender. The server only stores ciphertext, size and metadata and cannot decrypt attachment contents.
  - Attachment files stored on the client are encrypted with a key derived from the user's PIN (see `utils/attachments.py`) so local copies remain protected.

- Analytics & limits:
  - Attachment uploads are accounted for by the analytics collector (if enabled). The server records attachment counts and average sizes for reporting.
  - The server rejects attachments larger than the configured limit (10 MB by default) and will return a `413 Attachment too large` response.

Developer notes:

- Attachment ids are deterministic SHA256 hex of the ciphertext. Sending the same file twice will reuse the same `att_id` on the server and client local store.
- The client includes a placeholder message in chat history pointing to the attachment (`[Attachment] filename (size)`); selecting the placeholder starts a download + decrypt flow.


## ⚙️ Configuration & Files

| File / Path | Purpose |
|-------------|---------|
| `data/keypair.bin` | Encrypted key + signing key + username blob (versioned format) |
| `data/recipients.json` | Stored recipient public keys (may be encrypted by PIN) |
| `config/settings.json` | Client runtime settings (server selection, theme) |
| `config/themes.json` | Theme registry (colors, etc.) |
| `config/weak_pins.json` | Blacklist of weak PINs (override internal copy) |
| `utils/cert.pem` | Pinned server certificate (if using self‑signed) |
| `analytics_events.log` | Fallback analytics event log (only when Redis absent) |

`settings.json` keys (example):

```jsonc
{
  "server_type": "public",          // or "custom"
  "custom_url": "http://127.0.0.1:8000",
  "use_cert": true,
  "cert_path": "utils/cert.pem",
  "theme_name": "Dark"              // optional active theme
}
```

---

## 🔐 Security Model (Summary)

- E2E: Only sender & recipient have necessary key material.
- Public keys are safe to share; private keys never leave local disk.
- PIN protects key file using Scrypt → 64‑byte master key → split into encryption & HMAC keys.
- Integrity: HMAC-SHA256 over encrypted blob; signature verification for messages.
- Server stores: ciphertext, signature, `from`, `enc_pub`, timestamp. No plaintext, no key derivation info.
- Metadata leakage: Server still sees sender & recipient public keys and rough timing. Traffic analysis is in scope.
- Threats NOT mitigated (yet): MITM without pinned cert, compromised endpoint malware, replay detection, forward secrecy (static keypairs), multi-device conflict resolution.

> This project has **not** undergone formal cryptographic review. Use at your own risk.

---

## 🛠 Tech Stack

Backend: FastAPI, optional Redis
Client: Tkinter (`customtkinter`), Pillow, QR Code
Crypto: PyNaCl (SealedBox, SecretBox, SigningKey), Scrypt KDF
Extras: Requests, SQLAlchemy (future use), JWT (analytics auth), Passlib
Analytics Frontend: Next.js, React, Recharts, Tailwind

---

## 🧩 Selected Code Internals

| Module | Responsibility |
|--------|----------------|
| `server.py` | Relay endpoints: `/send`, `/inbox/{pub}`, `/public-key` |
| `utils/crypto.py` | Key generation, storage, PIN strength, encrypt/decrypt, signing |
| `utils/network.py` | Client HTTP send & inbox polling |
| `gui/` | Tkinter UI components, theming, dialogs |
| `server_utils/analytics_*` | Optional metrics collection & dashboard |

---

## 🖥️ GUI Basics

- Unlock screen appears if a key file exists.
- New install → Set PIN → Keys generated → Welcome view.
- Sidebar manages recipients; settings dialog manages server/theme/pin.
- Copy your public key to share. Paste others' public keys to add them.

---

## 🧪 Development Workflow

```bash
git clone https://github.com/Akame1981/Whispr.git
cd Whispr
python -m venv venv
./venv/Scripts/activate  # Windows
pip install -r requirements.txt
uvicorn server:app --port 8000 --reload  # in one terminal
python gui.py                            # in another
```

Run analytics stack (optional):
```bash
docker compose -f docker-compose.analytics.yml up --build
```

Frontend dashboard manual dev:
```bash
cd server_utils/analytics_frontend
npm install
npm run dev
```

### Linting / Formatting (suggested)
Add tools (not bundled by default):
```bash
pip install ruff black mypy
```

---

## � Packaging (PyInstaller Example)

_Experimental guidance:_
```bash
pip install pyinstaller
pyinstaller --onefile --name Whispr gui.py
```
Ensure runtime resources (themes, settings, weak PIN list) are copied or embedded. The helper `get_resource_path` in `utils/crypto.py` supports PyInstaller’s `_MEIPASS` layout.

---

## 🧷 Limitations & Future Hardening

- No forward secrecy (static long-lived keypairs)
- No perfect metadata obfuscation (timing & key correlation remain)
- No multi-device sync / conflict resolution
- No message retraction or edit support
- Replay protection minimal (timestamp presence only)
- Limited unit tests (community contribution welcome)

---

## 📸 Screenshots

Coming soon (themes, recipient panel, PIN dialog, analytics dashboard).

---

## ❓ FAQ

**Can the server read my messages?**  
No, ciphertext only. Integrity is signature-verified.

**What if I forget my PIN?**  
Keys are unrecoverable. There is no backdoor.

**Multiple devices?**  
Not yet. Export/import planned.

**Why Redis?**  
Provides multi-process safe queues, TTL expiration, distributed rate limiting, and shared analytics counters.

## ⚡ Real-time push (WebSockets)

WebSocket support has been added to provide low‑latency, server‑pushed delivery of incoming messages. The server exposes two compatible endpoints:

- Path form: `/ws/{recipient_pubhex}`
- Query form: `/ws?recipient={recipient_pubhex}`

Notes:

- The client will attempt to start a WebSocket background thread if the `websocket-client` package is available. If not installed, the client falls back to periodic polling.
- TLS is supported via `wss://` when you configure the client to use an `https://` server URL and provide a pinned certificate (`utils/cert.pem`) in settings.
- The client reduces polling frequency automatically when a WebSocket connection is active.
- WebSocket push sends the same envelope structure as the `/inbox` payload (fields: `from`, `enc_pub`, `message`, `signature`, `timestamp`). The client verifies signatures and decrypts messages locally before displaying or storing them.

Server-side behavior:

- When a message is accepted by `POST /send` the server will attempt to push the stored envelope to any active WebSocket connections for the recipient. Failures are ignored (best‑effort delivery).
- The WebSocket endpoints accept simple pings from clients but are primarily used for server→client push. Disconnects and handshake failures are handled gracefully.
## 📎 File sharing (Attachments)

Attachments (file sharing) are implemented end‑to‑end encrypted and ephemeral. Key points:

- Client behavior:
  - GUI supports sending attachments via the Attach button and optional drag & drop. Attachments are encrypted client‑side and the GUI stores a local, encrypted copy in `data/attachments` (see `utils/attachments.py`).
  - When sending, the client uploads the sealed ciphertext and metadata to the server using `POST /upload` and stores a placeholder message locally that points to the attachment (name, size, `att_id`).
  - Downloading an attachment is done via `GET /download/{att_id}?recipient={your_pubhex}`; the client will request the ciphertext from the server, verify the recipient, then decrypt locally using the owner's PIN‑derived key.

- Server behavior / API:
  - `POST /upload` accepts an attachment envelope containing `{to, from_, enc_pub, blob, signature, name, size, sha256}` where `blob` is the base64 sealed ciphertext and `sha256` is a hex digest used as the attachment id (`att_id`).
  - The server verifies the signature over the blob, enforces a size guard (default 10 MB), stores the ciphertext in an in‑memory attachment store (or Redis when configured), and returns `{"att_id": "<sha256>", "status": "ok"}`.
  - `GET /download/{att_id}?recipient=<pubhex>` returns `{"att_id","blob","name","size","from","to"}` if the recipient matches and the attachment has not expired.
  - Attachments are ephemeral and subject to the same TTL used for messages (default 60s) unless you configure a longer retention on the server side.

- Security model:
  - Attachments are sealed/encrypted by the sender using the recipient's public key (SealedBox) and signed by the sender. The server only stores ciphertext, size and metadata and cannot decrypt attachment contents.
  - Attachment files stored on the client are encrypted with a key derived from the user's PIN (see `utils/attachments.py`) so local copies remain protected.

- Analytics & limits:
  - Attachment uploads are accounted for by the analytics collector (if enabled). The server records attachment counts and average sizes for reporting.
  - The server rejects attachments larger than the configured limit (10 MB by default) and will return a `413 Attachment too large` response.

Developer notes:

- Attachment ids are deterministic SHA256 hex of the ciphertext. Sending the same file twice will reuse the same `att_id` on the server and client local store.
- The client includes a placeholder message in chat history pointing to the attachment (`[Attachment] filename (size)`); selecting the placeholder starts a download + decrypt flow.


---

## 🗺️ Roadmap (High-Level)

- UI & UX polish / accessibility
- Offline message queue + retry
- Group conversations (shared symmetric group keys)
- Voice / video (WebRTC + E2EE framing)
- Multi-server selection & failover
- Mobile and multi-device sync
- Forward secrecy & key rotation
- Message deletion / editing protocol

Detailed task list below (original checklist retained).

---

## 🤝 Contributing

We welcome:
- Security reviews & responsible disclosures
- Unit tests (focus: crypto wrappers, rate limiting logic)
- GUI accessibility improvements
- Feature flags for experimental protocols

Please open an issue before large refactors. Follow conventional commits if possible.

---

## 📜 License

Licensed under **CC BY-NC 4.0**.  
✔️ Modify & share with attribution.  
❌ Commercial use prohibited without permission.  
🔗 See full text in `LICENSE.txt`.

---

## 📬 Contact

Author: **Akame1981**  
Issues / discussions via **GitHub Issues**.

---

## Detailed Roadmap Checklist

This expands on the high-level roadmap above.


### ⬜ Next Updates


- [ ] Group Chats
  - [ ] Create and manage group conversations
  - [ ] Add/remove participants securely
  - [ ] Support for group message encryption
- [ ] Voice/Video Calling
  - [ ] Secure calling between users
  - [ ] End-to-end encryption for calls
  - [ ] Call notifications
- [ ] Servers & Network
  - [ ] Add support for multiple servers
  - [ ] Server selection in settings
  - [ ] Improve server reliability and connection feedback

### 🌟 Future Vision

- [ ] Integration with mobile apps
- [ ] Multi-device sync
- [ ] Advanced chat features (reactions, message edits/deletes)

**Stay tuned!** More secure and user-friendly features are on the way. 🚀
