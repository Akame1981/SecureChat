

**Feature:** Message Delivery When Recipient Is Disconnected  
**Status:** ❌ Not Working (Messages Lost if Recipient Reconnects Later)  
**Test Date:** 2025-10-13  
**Tester:** Oktay Mehmed  

---

## 🎯 Objective

To verify that messages sent while the recipient’s **client is closed or disconnected** are stored and delivered automatically once they reconnect.

---

## 🧪 Test Steps and Observations

| Step | Action | Expected Result | Actual Result | Status |
|------|---------|----------------|----------------|--------|
| 1 | Start the **Whispr server**. Launch **User 1** and **User 2** apps. | Both connect successfully and can exchange messages. | ✅ Works normally. | ✅ |
| 2 | **Close User 2’s app** completely (socket disconnected). | User 2 no longer receives live messages. | ✅ Works. | ✅ |
| 3 | **User 1** sends 10 messages to User 2 while User 2’s app is closed. | Messages should be stored by the server for later delivery. | ⚠️ Messages appear sent (locally displayed). | ⚠️ |
| 4 | **Reopen User 2’s app** (reconnects to server). | Server should deliver the 10 messages in the correct order. | ❌ User 2 sees an empty chat — no messages received. | ❌ |
| 5 | **Restart both apps and server.** | Messages should appear once both reconnect. | ❌ Still missing — not stored on server or re-synced. | ❌ |

---

## 🧩 Findings

### ✅ Working
- Real-time delivery when both users are connected.  
- Client UI shows “sent” messages immediately (optimistic send).  

### ❌ Broken
- No persistence for messages when the recipient is disconnected.  
- Server doesn’t queue unsent messages.  
- Sender’s UI shows “sent” even if server never delivered.  
- On reconnect, recipient fetches no missed messages.  

---

## 🧠 Suggested Fixes

| Issue                       | Suggested Solution                                                                                         |
| --------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Missing message persistence | Store all outgoing messages in the database with a `delivered=false` flag until acknowledged by recipient. |
| No delivery acknowledgment  | Add per-message receipt confirmation (e.g., `DELIVERED` event).                                            |
| No sync on reconnect        | When user connects, server should send all undelivered messages.                                           |
| False “sent” state          | Mark as “pending” until confirmed delivered by server.                                                     |

---