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
| Planned | Offline/groups/calls | Calls beta (WebRTC audio), file sharing and WebSocket push implemented |

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

> By default the client points to the public server over HTTPS. Run your own server for full control.



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



## 🔐 Security Model (Summary)

- E2E: Only sender & recipient have necessary key material.
- Public keys are safe to share; private keys never leave local disk.
- PIN protects key file using Scrypt → 64‑byte master key → split into encryption & HMAC keys.
- Integrity: HMAC-SHA256 over encrypted blob; signature verification for messages.
- Server stores: ciphertext, signature, `from`, `enc_pub`, timestamp. No plaintext, no key derivation info.
- Metadata leakage: Server still sees sender & recipient public keys and rough timing. Traffic analysis is in scope.
- Threats NOT mitigated (yet): MITM without pinned cert, compromised endpoint malware, replay detection, forward secrecy (static keypairs), multi-device conflict resolution.

> This project has **not** undergone formal cryptographic review.

---

## 🛠 Tech Stack

Backend: FastAPI, optional Redis
Client: Tkinter (`customtkinter`), Pillow, QR Code
Crypto: PyNaCl (SealedBox, SecretBox, SigningKey), Scrypt KDF
Extras: Requests, SQLAlchemy (future use), JWT (analytics auth), Passlib
Analytics Frontend: Next.js, React, Recharts, Tailwind

---




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
### WebRTC Calling (beta)

- Server exposes a simple signaling WebSocket at `/signal` used only to relay SDP/ICE between peers; payloads are E2E-encrypted with the recipient's public key.
- Client adds a Call button in the chat header. Click to start an audio-only call. The callee receives an in-app invite dialog.
- Media: aiortc + PulseAudio (Linux). Video rendering is basic and optional. Dependencies: `aiortc`, `av`, `sounddevice`, `numpy`.

If you run into PortAudio/PulseAudio install issues on Linux, install system packages first:

```bash
sudo apt-get install -y libportaudio2 libavdevice-dev libavfilter-dev libopus-dev libvpx-dev
```

Then reinstall Python deps:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

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

## 🧷 Limitations & Future Hardening



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



**Stay tuned!** More secure and user-friendly features are on the way. 🚀
