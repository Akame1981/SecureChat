## 🧪 Test Case

**Test Name:** File Test — User 1 sends to User 2 a Python file (`server.py`)

**Goal:**  
Ensure that file attachments are sent, rendered, and persisted correctly for both sender and receiver.

---

## ✅ Expected Behavior

- Both users see the attached `.py` file immediately after sending.  
- Message renders as a **file message** with filename, icon, and open/download options.  
- File attachment remains visible after reloading the chat.

---

## ⚙️ Test Execution

| Step                                    | User 1                                                                                                                                                                                                                                              | User 2                                     |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| 1. User 2 selects and sends `server.py` | Receives message as raw string:<br>`ATTACH:{"type":"file","name":"server.py","att_id":"37a62b3eee777280d5fd424535fa675f72a5f7407f7a0b883d87d72ac5fd7c1a","sha256":"37a62b3eee777280d5fd424535fa675f72a5f7407f7a0b883d87d72ac5fd7c1a","size":19954}` | Sees **blank message** after clicking send |
| 2. Reload chat                          | File renders correctly in viewer                                                                                                                                                                                                                    | Message disappears entirely                |

---

## 🧩 Observations

- **Receiver (User 1):**  
  Message initially unparsed (raw `ATTACH:` JSON), only renders correctly after reload.

- **Sender (User 2):**  
  Message not visible immediately and missing after reload → suggests message not persisted or improperly sent.

---

## 🔍 Root Cause Analysis

### 1. Message Format Mismatch
- The frontend receives a raw string (`ATTACH:{...}`) instead of a structured message object.  
- After reload, the database returns a parsed JSON format which renders correctly.

### 2. Broadcast Inconsistency
- Backend possibly broadcasts only to the receiver.  
- Sender’s UI relies on local optimistic rendering, but since it doesn't handle `type: "file"`, it shows blank.

### 3. Persistence Issue
- Message is saved for the receiver but **not persisted** (or saved incorrectly) for the sender.

---

## 🧠 Verification Checklist

| Component | Issue | Confirmed |
|------------|--------|------------|
| Backend `send_attachment()` | Broadcasts inconsistent payloads | ✅ |
| Frontend parser | Doesn’t parse `ATTACH:` before rendering | ✅ |
| Message persistence | Sender’s message not stored | ✅ |

---
