# SecureChat Client Documentation

This document describes the structure and usage of the SecureChat client codebase.

---

## Overview

The SecureChat client is a Tkinter-based GUI application for end-to-end encrypted messaging.  
It uses PyNaCl for cryptography and communicates with a FastAPI server.

---

## Main Components

- **gui.py**: Main entry point. Initializes the GUI, handles key management, message sending/receiving, and recipient selection.
- **gui/pin_dialog.py**: PIN entry dialog for unlocking or creating keypairs.
- **gui/settings.py**: Settings window for key management, server configuration, and recipient management.
- **gui/tooltip.py**: Tooltip widget for displaying full public keys.
- **gui/widgets/notification.py**: Notification system for user feedback.
- **gui/widgets/sidebar.py**: Sidebar for recipient selection and management.

---

## Key Features

- **Key Management**:  
  - Keys are generated and encrypted with a user PIN.
  - PIN strength is validated using a blacklist and complexity rules.
  - Keys are stored in `data/keypair.bin`.

- **Recipient Management**:  
  - Recipients are stored in `data/recipients.json`.
  - Add, edit, and delete recipients via the sidebar or settings.

- **Message Encryption**:  
  - Messages are encrypted using SealedBox (public key encryption).
  - Each message is signed with Ed25519 for authenticity.

- **Local Chat Storage**:  
  - Chat history is encrypted and stored per recipient in `data/chats/{recipient_pub}.bin`.

- **Server Communication**:  
  - Messages are sent and fetched via HTTP requests to the FastAPI server.
  - Supports both public and custom server URLs with optional SSL certificates.

- **Notifications**:  
  - User actions and errors are shown as pop-up notifications.

---

## How It Works

1. **Startup**:  
   - Prompts for PIN to unlock or create a keypair.
   - Loads saved recipients and settings.

2. **Sending Messages**:  
   - Select a recipient.
   - Type a message and press Send.
   - Message is encrypted, signed, and sent to the server.

3. **Receiving Messages**:  
   - Periodically fetches messages from the server.
   - Decrypts and verifies each message.
   - Displays messages in the chat window and saves them locally.

4. **Settings**:  
   - Change PIN, generate new keypair, manage recipients, and configure server.

---

## File Reference

- [`gui.py`](../gui.py): Main application logic.
- [`gui/pin_dialog.py`](../gui/pin_dialog.py): PIN dialog.
- [`gui/settings.py`](../gui/settings.py): Settings window.
- [`gui/tooltip.py`](../gui/tooltip.py): Tooltip widget.
- [`gui/widgets/notification.py`](../gui/widgets/notification.py): Notification system.
- [`gui/widgets/sidebar.py`](../gui/widgets/sidebar.py): Sidebar for recipients.
- [`utils/crypto.py`](../utils/crypto.py): Cryptographic operations.
- [`utils/chat_storage.py`](../utils/chat_storage.py): Local chat storage.
- [`utils/network.py`](../utils/network.py): Server communication.
- [`utils/recipients.py`](../utils/recipients.py): Recipient management.

---

## Security Notes

- Private keys are encrypted with a strong PIN.
- Messages are end-to-end encrypted and signed.
- Chat history is encrypted locally.
- Server only stores ephemeral messages.

---

## Running the Client

```sh
python gui.py
```

---

For server setup, see [docs/setup-server.md](setup-server.md).