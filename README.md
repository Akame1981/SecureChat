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
| Transport | FastAPI relay | In‑memory or Redis queues |
| Ephemerality | Last N msgs (default 20) | Cleared on fetch / TTL 60s (Redis) |
| GUI Client | Tkinter + themes | Light/Dark/Custom |
| Rate Limiting | 10 msgs/sec | Abuse prevention |
| Analytics | Optional backend + dashboard | Auto-disable if absent |
| Packaging | PyInstaller aware | Manual build notes |
| Planned | Offline/groups/files/calls | See roadmap |

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

**Why not WebSockets?**  
Initial design favors simplicity (pull model). WebSocket push planned for lower latency and battery savings.

---

## 🗺️ Roadmap (High-Level)

- UI & UX polish / accessibility
- Offline message queue + retry
- Group conversations (shared symmetric group keys)
- File attachments (encrypted, size limits)
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

### 🔄 In Progress

- [ ] UI & UX Improvements (90% done)
  - [x] Fix existing UI bugs
  - [x] Improve overall user experience
  - [x] Smooth animations and better layout responsiveness
  - [ ] Final bug fixes and testing
- [ ] Customization (90% done)
  - [x] Add support for custom themes
  - [x] Dark/light mode improvements
  - [x] Optional user personalization (fonts, colors)
  - [ ] Final testing and minor tweaks

### ⬜ Next Updates

- [ ] Offline Messaging
  - [ ] Queue messages when offline
  - [ ] Automatically send messages once the user reconnects
  - [ ] Notifications for pending messages
- [ ] Group Chats
  - [ ] Create and manage group conversations
  - [ ] Add/remove participants securely
  - [ ] Support for group message encryption
- [ ] File Sharing
  - [ ] Secure file sending between users
  - [ ] End-to-end encryption for attachments
  - [ ] Limit file size and type for security
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
