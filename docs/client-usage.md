# Whispr Client Documentation

Comprehensive guide to the Whispr end‑to‑end encrypted client: architecture, runtime flow, configuration, theming, key handling, and troubleshooting.

## Table of Contents

1. [Overview](#overview)
2. [Main Components](#main-components)
3. [Key Features](#key-features)
4. [How It Works (Lifecycle)](#how-it-works-lifecycle)
5. [Message Lifecycle Deep Dive](#message-lifecycle-deep-dive)
6. [Configuration & Files](#configuration--files)
7. [Theming System](#theming-system)
8. [Identicons](#identicons)
9. [Security Model (Client Perspective)](#security-model-client-perspective)
10. [Advanced Usage](#advanced-usage)
11. [Troubleshooting](#troubleshooting)
12. [Performance Tips](#performance-tips)
13. [Extending the Client](#extending-the-client)
14. [References](#references)

---

## Overview

The Whispr client is a `customtkinter` (Tkinter-based) desktop application for **end‑to‑end encrypted (E2EE)** messaging. It uses **PyNaCl** primitives (SealedBox + Ed25519) and communicates with a minimal **FastAPI** relay server that never sees plaintext.

Goals:

- Minimal metadata exposure (only sender & recipient pubkeys + timing)  
- Simplicity & auditability over feature bloat  
- Quick theming & local-only key custody

Non‑Goals (current phase): multi‑device sync, forward secrecy ratchet, group chats.

---

## Main Components

| File / Module | Responsibility |
|---------------|----------------|
| `gui.py` | App bootstrap, layout creation, theming integration, message display |
| `gui/layout.py` | Constructs main UI frames (sidebar + chat area) |
| `gui/widgets/sidebar.py` | Recipient list, add dialog, identicon avatars, settings entry |
| `gui/widgets/notification.py` | Toast notification manager |
| `gui/pin_dialog.py` | Secure PIN capture (unlock / create) |
| `gui/settings/*` | Settings window tabs (appearance, keys, server, recipients) |
| `gui/theme_manager.py` | Theme loading, listener broadcast for live updates |
| `gui/identicon.py` | Deterministic avatar generation |
| `utils/crypto.py` | Keypair management, encrypt/decrypt, sign/verify, PIN logic |
| `utils/chat_storage.py` | Encrypted per‑recipient message history persistence |
| `utils/recipients.py` | Encrypted recipient list storage |
| `utils/network.py` | HTTP send & inbox fetch wrappers |
| `utils/chat_manager.py` | Background fetch loop & dispatch |

---

## Key Features

| Area | Feature | Notes |
|------|---------|-------|
| Identity | Ed25519 + Curve25519 keypairs | Generated locally, never sent to server |
| Encryption | NaCl SealedBox | Anonymous sender encryption (no DH state) |
| Authenticity | Detached Ed25519 signature | Signature over raw ciphertext bytes |
| Key Protection | Scrypt + SecretBox + HMAC | PIN derives master key; integrity tag prevents tampering |
| Storage | Encrypted local chat logs | Each file salted independently |
| Recipients | Named directory with encrypted mapping | Prevents casual enumeration |
| Theming | JSON-driven & hot-swappable | Immediate repaint via listeners |
| Identicons | Fixed-grid deterministic | Same pattern across sizes |
| Notifications | In-app ephemeral toasts | Non-blocking user feedback |

---

## How It Works (Lifecycle)

1. Launch → `WhisprApp` loads settings + ThemeManager.
2. PIN dialog: unlock existing keypair or create new one; keypair stored encrypted.
3. Layout builds sidebar + chat area; theme applied immediately.
4. Background fetch thread polls inbox (interval) and processes messages.
5. User selects recipient → local encrypted history decrypted & displayed.
6. Send message → encrypt + sign → POST `/send`.
7. Fetch loop pulls messages → verify → decrypt → display → persist.

---

## Message Lifecycle Deep Dive

| Stage | Component | Action | Output |
|-------|-----------|--------|--------|
| 1 | User input | Types message | Plaintext str |
| 2 | `encrypt_message` | SealedBox(recipient_pub) | Ciphertext (bytes) → base64 |
| 3 | `sign_message` | Ed25519(signing_key) | Signature (base64) |
| 4 | `ChatManager.send` | Build JSON payload | `{to, from_, enc_pub, message, signature, timestamp}` |
| 5 | Server `/send` | Verify signature, enqueue | Ephemeral queue item |
| 6 | Fetch loop | GET `/inbox/<pub>` | List of message dicts |
| 7 | Verify / decrypt | Ed25519 verify + SealedBox decrypt | Plaintext |
| 8 | Bubble + persist | UI bubble + `save_message()` | Updated encrypted history |

---

## Configuration & Files

| Path | Purpose | Encrypted |
|------|---------|-----------|
| `data/keypair.bin` | Private + signing key + username blob | Yes |
| `data/recipients.json` | Name → public key mapping | Yes |
| `data/chats/<pub>.bin` | Chat history array for that recipient | Yes |
| `config/settings.json` | Server URL, theme name, flags | No |
| `config/themes.json` | Theme definitions | No |

See `architecture.md` for binary layout details.

---

## Theming System

1. Themes loaded from JSON at startup.
2. Changing theme triggers `ThemeManager.apply()`.
3. Registered listeners recolor without restart.

Add theme example snippet (`config/themes.json`):

```jsonc
"SolarizedDark": {
  "mode": "Dark",
  "background": "#002b36",
  "sidebar_bg": "#073642",
  "sidebar_text": "#fdf6e3",
  "bubble_you": "#268bd2",
  "bubble_other": "#073642",
  "text": "#eee8d5"
}
```

---

## Identicons

Fixed 6×6 mirrored grid rendered at base resolution → masked circle → scaled to requested size, ensuring consistent pattern across sidebar (small) and profile window (large).

---

## Security Model (Client Perspective)

| Aspect | Current State | Notes |
|--------|---------------|-------|
| Confidentiality | Strong (SealedBox) | Lacks forward secrecy |
| Authenticity | Ed25519 signatures | Over ciphertext only |
| Key at rest | Scrypt + SecretBox + HMAC | No PBKDF attempt counter |
| Local logs | SecretBox per file | Independent salts |
| Replay defense | Weak | Inbox purge reduces window |
| FS / PCS | Absent | Planned ratchet upgrade |

---

## Advanced Usage

### Custom Server

1. Run `uvicorn server:app --port 8000`.
2. In Settings → set custom URL `http://127.0.0.1:8000`.

### Self-Signed Cert Pinning

Place cert at `utils/cert.pem` and enable in settings for HTTPS validation.

### Multiple Profiles

Launch from separate working directories so each has its own `data/`.

### Reset Identity

Delete `data/keypair.bin` (irreversible) → relaunch → set new PIN (new keys & public key fingerprint changes).

---

## Troubleshooting

| Issue | Explanation | Mitigation |
|-------|-------------|------------|
| Mixed theme colors at startup | Theme not applied early (legacy) | Update (ThemeManager auto-applies) |
| No incoming messages | Poll loop failing or wrong recipient key | Check server status; re-add recipient |
| Invalid signature (400) | Corrupted payload / wrong signing key | Regenerate keypair |
| Decryption failed | Incorrect private key | Ensure correct `keypair.bin` |
| High CPU on unlock | Scrypt cost factor | Accept (security) or test with alternative env |
| UI lag with huge histories | Large widget render cost | Implement paging (future) |

---

## Performance Tips

- Keep chat histories moderate until pagination is implemented.
- Run on Python ≥3.11 for interpreter optimizations.
- Avoid sending very large blobs (no chunking yet).

---

## Extending the Client

| Goal | Where to Hook |
|------|---------------|
| Add new theme-reactive widget | `theme_manager.register_listener` |
| Change storage format | Wrap & replace `chat_storage.save_message/load_messages` |
| Swap crypto primitives | Adjust functions in `utils/crypto.py` preserving interfaces |
| Add message filters | Intercept in `ChatManager.fetch_loop` before display |

---

## References

- [Architecture Deep Dive](architecture.md)
- [Server Documentation](server-documentation.md)
- [Server Setup Guide](docs/setup-server.md)
- PyNaCl Docs: <https://pynacl.readthedocs.io/>

---

For server setup details see `setup-server.md`.
