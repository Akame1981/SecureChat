<div align="center">

# 🕵️ Whispr

### Modern End-to-End Encrypted Communication Platform

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-green.svg)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![WebRTC](https://img.shields.io/badge/Calls-WebRTC-00ADD8.svg)](https://webrtc.org/)
![State](https://img.shields.io/badge/State-Beta-yellow.svg)

**Whispr** is a feature-rich, end-to-end encrypted (E2EE) messaging platform with voice calls, file sharing, group chats, and real-time communication. Zero-knowledge architecture ensures the server never sees your plaintext—all encryption happens client-side.

[Quick Start](#-quick-start) • [Features](#-features) • [Documentation](docs/) • [Server Setup](docs/setup-server.md)

</div>

---

## 🚨 Security Notice

> **⚠️ Alpha/Beta Software**: Whispr has not undergone a professional security audit. While built with industry-standard cryptography (NaCl/libsodium), do not rely on it for high-risk communications.

**Security Best Practices:**
- � Never share your PIN or export your private keys
- 🔒 Use strong, unique PINs (weak PINs are actively blocked)
- 📱 Enable device encryption on your system
- 🌐 Use HTTPS in production environments
- 🔄 Keep Whispr updated (auto-update available)

---

## ✨ Features

### 🔐 **Military-Grade Encryption**
- **End-to-End Encryption**: NaCl `SealedBox` (Curve25519-XSalsa20-Poly1305)
- **Message Signing**: Ed25519 signatures for authenticity verification
- **Zero-Knowledge Server**: Server cannot decrypt messages or access keys
- **PIN-Protected Keys**: Scrypt KDF + SecretBox for local key encryption
- **Encrypted Database**: SQLCipher for local message history (AES-256)
- **Ephemeral Messages**: Configurable retention (default: last 20 messages)

### 💬 **Messaging & Communication**
- **Real-Time Messaging**: WebSocket push for instant delivery
- **Direct Messages**: Private 1-on-1 encrypted conversations
- **Group Chats**: 
  - Public/Private groups with invite codes
  - Multiple channels per group
  - Group key rotation and member management
  - End-to-end encrypted group messages
- **Voice Calls**: WebRTC-powered audio calls
- **Outbox Queue**: Automatic retry for failed messages
- **Message History**: Persistent encrypted local storage

### 📎 **File & Media Sharing**
- **Secure Attachments**: Encrypted file transfers (images, documents, etc.)
- **Large Text Support**: Auto-conversion to `.txt` attachments (>100KB)
- **Local Encryption**: Attachments encrypted at rest with PIN-derived keys
- **Inline Previews**: View text files and images directly in chat

### 🎨 **Modern User Interface**
- **CustomTkinter GUI**: Clean, modern interface with smooth animations
- **Theme System**: 
  - Light/Dark modes built-in
  - Custom themes via JSON
  - Dynamic theme switching without restart
  - Per-element color customization
- **Identicons**: Visual user identification with unique generated avatars
- **Rich Message Bubbles**: Styled messages with sender identification
- **Smart Notifications**: Desktop notifications with sound
- **Tooltips & UI Polish**: User-friendly with helpful hints

### 🔧 **Advanced Features**
- **Auto-Update System**: 
  - GitHub-based update checking
  - One-click updates with version tracking
  - Update rollback capability
- **Server Discovery**: Automatic server health checking
- **Settings Management**:
  - Public/custom server selection
  - Certificate management (self-signed support)
  - Audio device configuration
  - Theme preferences
- **Analytics Dashboard** (Optional):
  - Real-time usage statistics
  - Message volume tracking
  - Redis-backed or file-based fallback
- **Multi-Platform**: Windows, macOS, Linux support
- **PyInstaller Ready**: Standalone executable builds

### 🌐 **Server Features**
- **FastAPI Backend**: High-performance async server
- **Redis Support**: Optional Redis for scalability (in-memory fallback)
- **Rate Limiting**: 10 msg/sec per user (configurable)
- **Message TTL**: Automatic expiration (60s on Redis)
- **WebSocket Push**: Real-time message delivery
- **Groups Backend**: Full group/channel management API
- **CORS Enabled**: Web client compatible
- **Docker Support**: `docker-compose.yml` for analytics stack

---

## ⚡ Quick Start

### Client Installation

```bash
# Clone the repository
git clone https://github.com/Akame1981/Whispr.git
cd Whispr

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Launch Whispr
python gui.py
```

**First Launch:**
1. Set a secure PIN (8+ characters, complexity enforced)
2. Your keypair is automatically generated and encrypted
3. Set your username
4. Start chatting!

> 💡 **Tip**: The client defaults to the public server. For privacy, [run your own server](docs/setup-server.md).

### Server Deployment

```bash
# Install server dependencies
pip install -r requirements.txt

# Optional: Start Redis for production
redis-server

# Run the server
uvicorn server:app --host 0.0.0.0 --port 8000

# With HTTPS (recommended)
uvicorn server:app --host 0.0.0.0 --port 8000 \
  --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

📖 **Full server setup guide**: [docs/setup-server.md](docs/setup-server.md)

---

## 🏗️ Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Whispr Client (GUI)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Messages   │  │  Voice Calls │  │    Groups    │     │
│  │  (E2EE Chat) │  │   (WebRTC)   │  │  (Channels)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                           │                                 │
│              ┌────────────▼────────────┐                    │
│              │   Crypto Layer (NaCl)   │                    │
│              │  • SealedBox Encryption │                    │
│              │  • Ed25519 Signatures   │                    │
│              │  • PIN-Protected Keys   │                    │
│              └────────────┬────────────┘                    │
│                           │                                 │
│              ┌────────────▼────────────┐                    │
│              │   SQLCipher Database    │                    │
│              │  (Encrypted Messages)   │                    │
│              └─────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
                            │
                   HTTPS/WebSocket
                            │
┌─────────────────────────────────────────────────────────────┐
│                   Whispr Server (FastAPI)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Message    │  │    Groups    │  │  Analytics   │     │
│  │    Relay     │  │   Backend    │  │  (Optional)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                           │                                 │
│              ┌────────────▼────────────┐                    │
│              │   Redis (Optional) or   │                    │
│              │   In-Memory Queue       │                    │
│              └─────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

### Message Flow

1. **Encryption**: User types message → encrypted with recipient's public key (NaCl SealedBox)
2. **Signing**: Ciphertext signed with sender's Ed25519 private key
3. **Transmission**: Envelope sent to server via HTTPS POST `/send`
4. **Storage**: Server validates signature, stores in queue (ephemeral, TTL-based)
5. **Delivery**: Recipient polls/receives via WebSocket → validates signature → decrypts
6. **Persistence**: Decrypted message saved to local SQLCipher database

**Key Principle**: Server sees only encrypted blobs and metadata—zero plaintext access.

---

## 📁 Project Structure

```
Whispr/
├── gui.py                    # Main GUI application
├── server.py                 # FastAPI message relay server
├── requirements.txt          # Python dependencies
├── config/
│   ├── settings.json         # Server/theme configuration
│   ├── themes.json           # UI theme definitions
│   └── weak_pins.json        # Blacklisted weak PINs
├── data/
│   ├── whispr_messages.db    # SQLCipher encrypted database
│   ├── keypair.bin           # Encrypted user keypair
│   ├── recipients.json       # Public key registry
│   └── attachments/          # Encrypted file storage
├── gui/
│   ├── call_invite.py        # Incoming call dialog
│   ├── call_window.py        # Voice call interface
│   ├── theme_manager.py      # Theme system
│   ├── locked_screen.py      # PIN entry screen
│   ├── settings/             # Settings panels
│   └── widgets/              # Custom UI components
│       ├── sidebar.py
│       ├── notification.py
│       ├── groups_panel.py
│       └── ...
├── utils/
│   ├── crypto.py             # NaCl encryption primitives
│   ├── db.py                 # SQLCipher database wrapper
│   ├── chat_manager.py       # Message orchestration
│   ├── group_manager.py      # Group chat logic
│   ├── rtc_manager.py        # WebRTC call management
│   ├── auto_updater.py       # GitHub auto-update
│   ├── ws_client.py          # WebSocket client
│   └── attachments.py        # File encryption/storage
├── server_utils/
│   ├── groups_backend/       # Group chat API
│   ├── analytics_backend/    # Analytics service
│   └── analytics_frontend/   # Analytics dashboard
└── docs/
    ├── setup-server.md       # Server deployment guide
    ├── architecture.md       # Technical deep-dive
    └── client-usage.md       # User manual
```

---

## 🔑 Cryptography Details

### Encryption Schemes

| Component              | Algorithm                                    | Purpose                                |
| ---------------------- | -------------------------------------------- | -------------------------------------- |
| **Message Encryption** | `crypto_box_seal` (X25519-XSalsa20-Poly1305) | E2EE message confidentiality           |
| **Message Signing**    | Ed25519                                      | Message authenticity & non-repudiation |
| **Key Derivation**     | Scrypt (N=2^20, r=8, p=1)                    | PIN → encryption key                   |
| **Key Storage**        | NaCl SecretBox                               | Encrypt private keys at rest           |
| **Database**           | SQLCipher (AES-256)                          | Encrypted message history              |
| **Group Keys**         | Symmetric AES-256 (via NaCl)                 | Group message encryption               |

### Key Management

- **Keypair Generation**: Ed25519 signing key + X25519 encryption key
- **Storage**: Encrypted in `keypair.bin` using PIN-derived key
- **PIN Protection**: 
  - Minimum 8 characters
  - Blacklist of common weak PINs
  - Scrypt makes brute-force computationally expensive
- **No Cloud Storage**: Keys never leave your device

---

## 🎯 Roadmap

### ✅ Completed
- [x] End-to-end encrypted messaging
- [x] Voice calls (WebRTC)
- [x] File attachments
- [x] Group chats with channels
- [x] WebSocket real-time push
- [x] Auto-update system
- [x] SQLCipher database
- [x] Theme system
- [x] Analytics dashboard

### 🚧 In Progress
- [ ] Video calls
- [ ] Multi-device sync
- [ ] Mobile clients (iOS/Android)
- [ ] Message reactions
- [ ] Typing indicators

### 📋 Planned
- [ ] Offline message queue
- [ ] Message search
- [ ] Profile pictures
- [ ] Voice messages
- [ ] Screen sharing
- [ ] Plugin system









---


### Project Architecture

**Key Modules**:
- `utils/crypto.py`: NaCl wrapper, key management
- `utils/db.py`: SQLCipher database with encryption
- `utils/chat_manager.py`: Message orchestration & caching
- `utils/rtc_manager.py`: WebRTC signaling & media
- `utils/group_manager.py`: Group chat logic
- `gui/`: All UI components (CustomTkinter)

**Design Patterns**:
- **Singleton**: `ChatManager`, `RTCManager`
- **Observer**: WebSocket message notifications
- **Factory**: Message bubble creation
- **Strategy**: Encryption algorithm selection




---


### WebRTC Setup (Linux)

If you encounter PortAudio/PulseAudio issues:

```bash
sudo apt-get install -y libportaudio2 libavdevice-dev \
  libavfilter-dev libopus-dev libvpx-dev
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 📊 Performance & Scaling

### Client Performance
- **Startup Time**: ~2-3 seconds
- **Message Encryption**: <10ms per message
- **Database Query**: <50ms for 1000 messages
- **Memory Usage**: ~50-100 MB

### Server Scaling
- **Without Redis**: ~100 concurrent users
- **With Redis**: ~10,000+ concurrent users
- **Message Throughput**: ~1,000 msg/sec (single instance)
- **Horizontal Scaling**: Load balance multiple servers with shared Redis

---

## ❓ FAQ

**Q: Is it safe?**  
A: Built on well-regarded NaCl cryptography, but **not professionally audited**. Avoid high-risk scenarios.

**Q: Can the server read my messages?**  
A: No. The server stores only encrypted ciphertext. Decryption keys never leave the client.

**Q: Can I recover a lost PIN?**  
A: No. Lost PIN = lost keys. Backup `keypair.bin` in a secure location. Use in-app settings

**Q: What if I don't trust the default server?**  
A: Run your own! The server is easy to deploy (FastAPI + optional Redis).

**Q: How can I verify my friend's public key?**  
A: Currently manual. QR code fingerprint verification planned for future updates.

**Q: Does it work offline?**  
A: Partially. You can view chat history offline, but sending/receiving requires server connection.




---

## 📜 License

**Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**

✅ **You CAN**:
- Use Whispr personally
- Modify and adapt the code
- Share with others (with attribution)
- Deploy your own servers

❌ **You CANNOT**:
- Use for commercial purposes
- Sell Whispr or derivatives
- Remove copyright notices

📄 Full License: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)

---

## 🤝 Contributing

We welcome contributions! Here's how:

### Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`
3. **Commit** changes: `git commit -m 'Add voice effects'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. **Open** a Pull Request with detailed description

### Contribution Guidelines

- ✅ Follow PEP 8 Python style guide
- ✅ Add docstrings to new functions
- ✅ Test cryptographic changes thoroughly
- ✅ Update documentation for new features
- ✅ Maintain backward compatibility when possible
- ❌ Don't weaken security or encryption
- ❌ Don't introduce proprietary dependencies

### Code Review Standards

All PRs require:
- Descriptive commit messages
- Code passes basic security review
- No obvious bugs or crashes
- Documentation updates if needed
- Tests documented in [docs/tests](docs/Tests)

### Areas We Need Help

- 🧪 Unit tests for crypto modules
- 📱 Mobile client development
- 🎨 UI/UX improvements
- 🌍 Internationalization (i18n)
- 📖 Documentation improvements
- 🔒 Security auditing

---

## 🙏 Acknowledgments

This project wouldn't be possible without:

- **[PyNaCl](https://pynacl.readthedocs.io/)** - Python bindings for libsodium/NaCl
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern async web framework
- **[CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)** - Modern Tkinter UI
- **[aiortc](https://github.com/aiortc/aiortc)** - WebRTC for Python
- **[SQLCipher](https://www.zetetic.net/sqlcipher/)** - Encrypted SQLite
- **[Redis](https://redis.io/)** - In-memory data store

Special thanks to the cryptography and privacy communities for inspiration.

---

## 📞 Support & Community

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/Akame1981/Whispr/issues)
- 📖 **Documentation**: [docs/](docs/)
- 🔒 **Security Issues**: Report privately to repository owner



---

<div align="center">

**Made with 🤍 for privacy & open communication**

*Whispr: Speak freely, stay encrypted.*

[⬆ Back to Top](#-whispr)

</div>


---

## 🛠 Tech Stack

Backend: FastAPI, optional Redis
Client: Tkinter (`customtkinter`), Pillow, QR Code
Crypto: PyNaCl (SealedBox, SecretBox, SigningKey), Scrypt KDF
Extras: Requests, SQLAlchemy (future use), JWT (analytics auth), Passlib
Analytics Frontend: Next.js, React, Recharts, Tailwind

---


## 📸 Screenshots

Coming soon (themes, recipient panel, PIN dialog, analytics dashboard).

---








---

## 📬 Contact

Author: **Akame1981**  
Issues / discussions via **GitHub Issues**.

---


**Stay tuned!** More secure and user-friendly features are on the way. 🚀
