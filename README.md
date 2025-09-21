# 🔒 SecureChat

**SecureChat** is a simple yet powerful end-to-end encrypted chat application built with **FastAPI**, **PyNaCl**, and **Tkinter**.  
It allows users to send encrypted messages securely between public keys, store recipients, and manage encryption keys locally.

---

## ⚠️ Important Notice

For detailed instructions on **setting up the server**, including HTTPS, self-signed certificates, and systemd setup, please refer to the [SecureChat Documentation](docs/README.md).  

> This ensures secure deployment and avoids accidental exposure of keys or misconfiguration.

---


# Features

- **End-to-End Encryption**: Messages are encrypted using `SealedBox` and signed with `Ed25519`.
- **FastAPI Backend with SSL**: Handles message storage, retrieval, and ephemeral messages over HTTPS for secure transport.
- **Local Key Management**: Private keys are encrypted with a PIN using `SecretBox`.
- **Persistent Recipients**: Add, select, and manage contacts with saved public keys in `recipients.json`.
- **Tkinter GUI Client**: Cross-platform chat interface with message history.
- **Message History**: Server stores the last 5 messages per recipient, ephemeral messages by default. (Database or other persistent storage can be added, but ephemeral storage is more private.)
- **Rate Limiting**: Prevents spam with max 10 messages/sec per sender. (May be more than needed for normal users.)
- **Customizable Settings**:
  - Generate a new keypair
  - Change your PIN
  - Copy your public key
  - Manage recipients
- **Cross-platform**: Runs on Windows, macOS, and Linux.

---

## 🚀 Installation


1. **Clone the repository**

```bash
git clone https://github.com/Akame1981/SecureChat.git
```
cd SecureChat

2. Create and activate a Python virtual environment:


    python -m venv venv


Windows :
```bash
venv\Scripts\activate

```

macOS/Linux : 
```bash
source venv/bin/activate

```


3. Install dependencies:

```bash
pip install -r requirements.txt

```

# Running the App

## Launch the GUI client

```bash
 python gui.py
```
gui is the Tkinter chat client. It will ask for a PIN to unlock or generate your private key.


By default it connects to the official public server. If you wanna make your own server, refer to the [SecureChat Documentation](docs/README.md)

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

## 🤝 Contributing
Contributions are welcome!  
- Submit issues for bugs or feature requests.  
- Open pull requests with improvements or fixes.  

---

## 📬 Contact
Developed by **Akame1981**  
💡 Share feedback, questions, or suggestions via **GitHub Issues**.  
