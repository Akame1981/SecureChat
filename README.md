# 🕵️ Whispr

**Whispr** is a simple yet powerful end-to-end encrypted chat application built with **FastAPI**, **PyNaCl**, and **Tkinter**.  
It allows users to send encrypted messages securely between public keys, store recipients, and manage encryption keys locally.

---

## ⚠️ Important Notice

For detailed instructions on **setting up the server**, including HTTPS, self-signed certificates, and systemd setup, please refer to the [Whispr Documentation](docs/setup-server.md).  

> This ensures secure deployment and avoids accidental exposure of keys or misconfiguration.

---


# Features

- **End-to-End Encryption**: All messages are encrypted with `SealedBox` and signed using `Ed25519` for authenticity.
- **FastAPI Backend with SSL**: Secure HTTPS server for message storage and retrieval, supporting ephemeral and in-memory storage.
- **Local Key Management**: Private keys are encrypted locally with a PIN using `SecretBox`. PIN strength is enforced.
- **Recipient Management**: Add, edit, delete, and select contacts with saved public keys in `recipients.json`.
- **Tkinter GUI Client**: Modern, cross-platform chat interface with customizable themes, dark/light mode, and message history.
- **Message History**: Server stores only the last 5 messages per recipient (ephemeral by default for privacy). Local encrypted message history per contact.
- **Rate Limiting**: Prevents spam with a maximum of 10 messages per second per sender.
- **Customizable Settings**:
  - Generate or import/export keypairs
  - Change your PIN
  - Copy your public key
  - Manage recipients and server settings
  - Switch between public and custom servers
  - Choose and save color themes
- **Cross-platform**: Runs on Windows, macOS, and Linux.
- **Offline Mode (Planned)**: Queue messages when offline and send automatically when reconnected.
- **Group Chat, File Sharing, and Calls (Planned)**: Secure group messaging, file attachments, and voice/video calls are on the roadmap.

---

## 🚀 Installation

> **You can download it from [HERE](https://github.com/Akame1981/Whispr/releases/tag/v0.1) but it's still buggy.**  
> **Recommended:** Run it from Python for best results.

---

### 1. **Clone the Repository**

```bash
git clone https://github.com/Akame1981/Whispr.git
cd Whispr
```

---

### 2. **Create and Activate a Virtual Environment**

<details>
<summary><strong>Windows</strong></summary>

```bash
python -m venv venv
venv\Scripts\activate
```
</details>

<details>
<summary><strong>macOS / Linux</strong></summary>

```bash
python3 -m venv venv
source venv/bin/activate
```
</details>

---

### 3. **Install Dependencies**

```bash
pip install -r requirements.txt
```

---

# Running the App

## Launch the GUI Client

```bash
python gui.py
```

The GUI is the Tkinter chat client. It will ask for a PIN to unlock or generate your private key.

By default, it connects to the official public server. If you want to run your own server, refer to the [Whispr Documentation](docs/setup-server.md).

---

## 🎯 Usage
- **Send Messages** → Select a recipient and type your message to send encrypted messages.  
- **Manage Recipients** → Add, delete, or choose recipients from the **Settings** menu.  
- **Key Management** → Generate new keypairs or change your PIN for encryption.  
- **Copy Public Key** → Share your public key so others can send you messages.  

---

## 🔐 Security
- Messages are **end-to-end encrypted** with `SealedBox`.  
- **Message signing** ensures authenticity using `Ed25519`.  
- **Private keys** are encrypted locally with a PIN using `SecretBox`.  
- The **server only stores the last 5 encrypted messages of an user** and optionally uses ephemeral message storage with Redis or in-memory fallback.

---

## 📜 License
This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)** license.  
✔️ You may use and modify the project.  
❌ You may not sell it.  
⭐ You must give credit to the author.  

---

## 🛠 Tech Stack

- **Backend** → FastAPI, optional Redis for ephemeral storage  
- **Client** → Tkinter (Python)  
- **Encryption** → PyNaCl (`PrivateKey`, `SealedBox`, `SecretBox`, `SigningKey`)  
- **Persistence** → `keypair.bin` for keys, `recipients.json` for contacts

---

## 📸 Screenshots
SOON

---
# 🕵️ Whispr Roadmap - TODO

This is a task-oriented roadmap for **Whispr**.

---

## 🔄 In Progress
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

---

## ⬜ Next Updates
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

---
## 🌟 Future Vision
- [ ] Integration with mobile apps
- [ ] Multi-device sync
- [ ] Advanced chat features (reactions, message edits/deletes)

---

**Stay tuned!** More secure and user-friendly features are on the way. 🚀

## 🤝 Contributing
Contributions are welcome!  
- Submit issues for bugs or feature requests.  
- Open pull requests with improvements or fixes.  

---

## 📬 Contact
Developed by **Akame1981**  
💡 Share feedback, questions, or suggestions via **GitHub Issues**.
