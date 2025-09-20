# 🔒 SecureChat

**SecureChat** is a simple yet powerful end-to-end encrypted chat application built with **FastAPI**, **PyNaCl**, and **Tkinter**.  
It allows users to send encrypted messages securely between public keys, store recipients, and manage encryption keys locally.

---



# Features

- **End-to-End Encryption**: Messages are encrypted using `SealedBox` and signed with `Ed25519`.
- **FastAPI Backend**: Handles message storage, retrieval, and ephemeral messages.
- **Local Key Management**: Private keys are encrypted with a PIN using `SecretBox`.
- **Persistent Recipients**: Add, select, and manage contacts with saved public keys in `recipients.json`.
- **Tkinter GUI Client**: Cross-platform chat interface with message history.
- **Message History**: Server stores the last 5 messages per recipient, ephemeral messages by default. (I can make database or other type of persistent storage but LIKE THAT IS MORE PRIVATE)
- **Rate Limiting**: Prevents spam with max 10 messages/sec per sender. (Maybe still way too much for normal user but still)
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

source venv/bin/activate




3. Install dependencies:

```bash
pip install -r requirements.txt

```

# Running the App
Start the FastAPI server

uvicorn server:app --reload

- **The server will run at http://127.0.0.1:8000.**

Launch the GUI client

# python client.py

test_client.py is the Tkinter chat client. It will ask for a PIN to unlock or generate your private key.

---

## 🎯 Usage
- **Send Messages** → Select a recipient and type your message to send encrypted messages.  
- **Manage Recipients** → Add, delete, or choose recipients from the **Settings** menu.  
- **Key Management** → Generate new keypairs or change your PIN for encryption.  
- **Copy Public Key** → Share your public key so others can send you messages.  

---

## 🔐 Security
- Messages are encrypted end-to-end using **SealedBox**.  
- Private keys are encrypted locally with a **PIN-based SecretBox**.  
- The server stores **only encrypted messages**, never plaintext.  

---

## 📜 License
This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)** license.  
✔️ You may use and modify the project.  
❌ You may not sell it.  
⭐ You must give credit to the author.  

---

## 🛠 Tech Stack
- **Backend** → FastAPI  
- **Client** → Tkinter (Python)  
- **Encryption** → PyNaCl (`PrivateKey`, `SealedBox`, `SecretBox`)  
- **Persistence** → JSON files for recipients and local encrypted keys  

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
