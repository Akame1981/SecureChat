# 🕵️ Whispr

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-green.svg)](#)

**Whispr** is a simple yet powerful end-to-end encrypted chat application built with **FastAPI**, **PyNaCl**, and **Tkinter**.  
It allows users to send encrypted messages securely between public keys, store recipients, and manage encryption keys locally.

---

## 🚨 Important Notice

For detailed instructions on **setting up the server**, including HTTPS, self-signed certificates, and systemd setup, please refer to the [Whispr Documentation](docs/setup-server.md).

> **Never share your PIN or private key.**  
> The server cannot decrypt your messages, but your device security is your responsibility.

---

## ✨ Features

- **End-to-End Encryption:** All messages are encrypted with `SealedBox` and signed using `Ed25519` for authenticity.
- **FastAPI Backend with SSL:** Secure HTTPS server for message storage and retrieval, supporting ephemeral and in-memory storage.
- **Local Key Management:** Private keys are encrypted locally with a PIN using `SecretBox`. PIN strength is enforced.
- **Recipient Management:** Add, edit, delete, and select contacts with saved public keys in `recipients.json`.
- **Tkinter GUI Client:** Modern, cross-platform chat interface with customizable themes, dark/light mode, and message history.
- **Message History:** Server stores only the last 5 messages per recipient (ephemeral by default for privacy). Local encrypted message history per contact.
- **Rate Limiting:** Prevents spam with a maximum of 10 messages per second per sender.
- **Customizable Settings:** Generate/import/export keypairs, change PIN, manage recipients, server settings, and color themes.
- **Cross-platform:** Runs on Windows, macOS, and Linux.
- **Offline Mode (Planned):** Queue messages when offline and send automatically when reconnected.
- **Group Chat, File Sharing, and Calls (Planned):** Secure group messaging, file attachments, and voice/video calls are on the roadmap.

---

## ⚡ Quick Start

1. **Clone the Repository**
    ```bash
    git clone https://github.com/Akame1981/Whispr.git
    cd Whispr
    ```

2. **Create and Activate a Virtual Environment**
    - **Windows**
      ```bash
      python -m venv venv
      venv\Scripts\activate
      ```
    - **macOS / Linux**
      ```bash
      python3 -m venv venv
      source venv/bin/activate
      ```

3. **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4. **Run the App**
    ```bash
    python gui.py
    ```

---

## 🖥️ Running the App

- The GUI is the Tkinter chat client. It will ask for a PIN to unlock or generate your private key.
- By default, it connects to the official public server. To run your own server, see [Whispr Documentation](docs/setup-server.md).

---

## 🎯 Usage

- **Send Messages:** Select a recipient and type your message to send encrypted messages.
- **Manage Recipients:** Add, delete, or choose recipients from the **Settings** menu.
- **Key Management:** Generate new keypairs or change your PIN for encryption.
- **Copy Public Key:** Share your public key so others can send you messages.

---

## 🔐 Security

- **End-to-end encryption:** All messages are encrypted on your device using [NaCl's SealedBox](https://pynacl.readthedocs.io/en/stable/public/#nacl.public.SealedBox) before being sent. Only the intended recipient can decrypt them.
- **Message signing:** Every message is signed with your Ed25519 signing key, ensuring authenticity and sender verification.
- **Private key protection:** Your private keys are never sent to the server. They are stored locally, encrypted with a strong PIN using [SecretBox](https://pynacl.readthedocs.io/en/stable/secret/).
- **PIN strength enforcement:** Weak PINs are rejected using a blacklist and complexity checks.
- **Recipient management:** Contacts and their public keys are stored locally, encrypted with your PIN.
- **Server-side privacy:**
  - The server only stores the last 5 encrypted messages per recipient (by default, can be configured).
  - Messages are deleted from the server after retrieval or after a short time (ephemeral storage).
  - The server cannot read or decrypt any messages.
  - Rate limiting is enforced to prevent spam (max 10 messages/sec per sender).
- **No plaintext history:** Message history is stored locally, encrypted per contact.
- **No key exposure:** Public keys are safe to share; private keys never leave your device.

> **Tip:** For maximum security, always use a strong PIN, keep your device secure, and run your own server if you require full control.

---

## 🛠 Tech Stack

- **Backend:** FastAPI, optional Redis for ephemeral storage
- **Client:** Tkinter (Python)
- **Encryption:** PyNaCl (`PrivateKey`, `SealedBox`, `SecretBox`, `SigningKey`)
- **Persistence:** `keypair.bin` for keys, `recipients.json` for contacts

---

## 📸 Screenshots

*Coming soon!*

---

## ❓ FAQ

**Q: Can the server read my messages?**  
A: No. All messages are end-to-end encrypted and only the intended recipient can decrypt them.

**Q: What happens if I forget my PIN?**  
A: You will not be able to access your private key or messages. There is no recovery.

**Q: Can I use Whispr on multiple devices?**  
A: Not yet, but multi-device sync is planned.

**Q: Is there a mobile app?**  
A: Not yet, but it's on the roadmap.

---

## 🗺️ Roadmap

- [ ] UI & UX Improvements
- [ ] Customization (themes, dark/light mode)
- [ ] Offline Messaging
- [ ] Group Chats
- [ ] File Sharing
- [ ] Voice/Video Calling
- [ ] Multiple server support
- [ ] Mobile app & multi-device sync

See the [full roadmap](#-whispr-roadmap---todo) below for details.

---

## 🤝 Contributing

Contributions are welcome!

- Submit issues for bugs or feature requests.
- Open pull requests with improvements or fixes.
- Please follow the [Code of Conduct](CODE_OF_CONDUCT.md) and ensure your code is well-documented.

---

## 📜 License

This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)** license.  
✔️ You may use and modify the project.  
❌ You may not sell it.  
⭐ You must give credit to the author.

---

## 📬 Contact

Developed by **Akame1981**  
💡 Share feedback, questions, or suggestions via **GitHub Issues**.

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
