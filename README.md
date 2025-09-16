# 🔒 SecureChat

**SecureChat** is a simple yet powerful end-to-end encrypted chat application built with **FastAPI**, **PyNaCl**, and **Tkinter**.  
It allows users to send encrypted messages securely between public keys, store recipients, and manage encryption keys locally.

---

## Features

- **End-to-End Encryption**: Messages are encrypted using public/private key cryptography with `PyNaCl`.
- **FastAPI Backend**: Handles message storage and retrieval.
- **Local Key Management**: Users set a PIN to encrypt their private key on disk.
- **Persistent Recipients**: Add, choose, and manage contacts with saved public keys.
- **GUI Interface**: Intuitive Tkinter-based chat client.
- **Message History**: Stores the last 5 messages per recipient on the server.
- **Customizable Settings**:
  - Generate a new keypair
  - Change your PIN
  - Copy your public key to share
- **Cross-platform**: Works on Windows, macOS, and Linux with Python.

---

## 🚀 Installation

1. **Clone the repository**




- **git clone** https://github.com/Akame1981/SecureChat.git

- **cd SecureChat**

2. Create and activate a Python virtual environment:


    python -m venv venv


# Windows
venv\Scripts\activate


# macOS/Linux
source venv/bin/activate




# Install dependencies:


pip install -r requirements.txt


# Running the App
Start the FastAPI server

uvicorn main:app --reload

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
