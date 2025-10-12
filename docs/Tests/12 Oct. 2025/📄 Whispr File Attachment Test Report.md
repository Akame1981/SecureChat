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


# 📄 Whispr File Attachment Test Report (v2)

## 🧪 Test Case

**Test Name:** File Test — Sending `.py` file between users

**Goal:**  
Verify that file attachments render and persist correctly for both sender and receiver in real-time and after reload.

---

## ✅ Expected Behavior

- Both users see the attached `.py` file rendered immediately.
- File viewer displays filename, size, and download/view buttons.
- File message persists correctly after reloading the chat.

---

## ⚙️ Test Execution (Post-Fix)

**Scenario:** User 2 sends `server.py` to User 1.

| Step                 | User 1                           | User 2                           |
| -------------------- | -------------------------------- | -------------------------------- |
| Send event           | Sometimes renders file correctly | Sometimes renders file correctly |
| Reload               | Sometimes message renders        | Sometimes message disappears     |
| Frequency of success | ~60–70% both render fine         | 30–40% one or both fail          |
|                      |                                  |                                  |

---



# 📄 Whispr File Attachment Test Report (v3)

## 🧪 Test Case

**Test Name:** File Test — Sending `.py` file between users (Post-Fix #2)

**Goal:**  
Validate that file attachments render consistently for both users in real time, after reload, and after full app restart.

---

## ✅ Expected Behavior

- Both users immediately see:
  - File name
  - File text preview viewer
- File attachment persists across reloads and restarts.

---

## ⚙️ Test Execution (After Latest Fix)

**Scenario:** User 2 sends `server.py` to User 1.

| Step                   | User 1                                           | User 2                                           |
| ---------------------- | ------------------------------------------------ | ------------------------------------------------ |
| Immediately after send | File name rendered, **text viewer not rendered** | File name rendered, **text viewer not rendered** |
| Reload chat            | Nothing changes                                  | Message disappears completely                    |
| Restart full app       | File viewer and name rendered correctly          | Only file name rendered, no text viewer          |

---

## 🧩 Updated Observations

### 🔸 Rendering Differences by State
- **Real-time:** Name visible → message partially parsed.
- **Reload:** Sender’s message missing → DB retrieval or local cache mismatch.
- **Full Restart:** Renderer works → means data exists in persistent storage, but front-end didn’t hydrate correctly on reload.

### 🔸 Attachment Viewer Issue
- Viewer appears only when the app fully resets → likely `file.content` or blob not being loaded until full hydration.  
- Name always visible → file metadata (`name`, `att_id`) is correct, but the text data or link to fetch it isn’t available immediately.

---

# 📄 Whispr File Attachment Test Report (v4)

## 🧪 Test Case

**Test Name:** File Test — Sending `.py` file between users (Post-Fix #3)

**Goal:**  
Confirm that file attachments render and persist correctly for both sender and receiver across live send, reload, and full restart.

---

## ✅ Expected Behavior

Both users should:
- Immediately see the file name and content viewer after sending.
- Have the message persist in chat history.
- Retain the same view after reload or restart.

---

## ⚙️ Test Execution (After Fix #3)

**Scenario:** User 2 sends a new `server.py` file to User 1.

| Step | User 1 (Receiver) | User 2 (Sender) |
|------|-------------------|-----------------|
| Immediately after send | ✅ File viewer renders fully (name + text content) | ⚠️ Only file name rendered, no viewer |
| After reload | ✅ Still visible and correct | ❌ Message disappears completely |
| After full app restart | ✅ Viewer and name still correct | ✅ File viewer appears correctly |

---

## 🧩 Observations

1. **Receiver side is now stable:**  
   Rendering and persistence for User 1 work perfectly.

2. **Sender side partially broken:**  
   - The message appears incomplete at send time (no viewer).
   - After reload, it vanishes → message not fetched from local DB.
   - After restart, it reappears → message exists in backend, but sender’s local message cache or DB isn’t updated properly after sending.

3. **Meaning:**  
   - Backend now correctly saves and serves file messages.  
   - **Sender’s client-side state and local message persistence remain inconsistent.**

---

