

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


📄 Whispr Message Delivery When Recipient is Disconnected (v2)

## 🧾 Summary

**Feature:** Offline / Disconnected Message Delivery — Duplicate Send Bug  
**Status:** ❌ Not Fixed (Messages Delivered Twice)  
**Test Date:** 2025-10-13  
**Tester:** Oktay Mehmed  
**Build:** v0.9.8-pre (Offline Message Fix #2)

---

## 🎯 Objective

To verify that messages sent while a recipient’s client is disconnected are delivered **exactly once** and to document the **duplicate delivery issue** introduced in Fix #2.

---

## 🧪 Test Steps and Observations

| Step | Action | Expected Result | Actual Result | Status |
|------|---------|----------------|---------------|--------|
| 1 | Start the **Whispr server**. Launch **User 1** and **User 2** apps. | Both connected successfully. | ✅ Works. | ✅ |
| 2 | **Close User 2’s app** completely (socket disconnected). | User 2 does not receive live messages. | ✅ Works. | ✅ |
| 3 | **User 1** sends 10 messages to User 2 while User 2 is disconnected. | Messages should be queued on server for delivery. | ⚠️ Messages appear sent locally. | ⚠️ |
| 4 | **Reopen User 2’s app** (reconnect). | Server delivers **each message once**, in correct order. | ❌ Each message is delivered **twice**; duplicates appear in chat. | ❌ |
| 5 | **Check message order and status**. | Messages appear in order without duplicates. | ❌ Order correct, but duplicates present. | ❌ |
| 6 | **Restart apps and server** | Messages should persist and **not duplicate** on reconnect. | ❌ Messages remain duplicated. | ❌ |

---

## 🧩 Findings

### ✅ Working
- Messages queued on server are now delivered after recipient reconnects.  
- Message order is correct.  
- Real-time messaging still works when both users connected.  

### ❌ Broken
- Each queued message is delivered **twice** to recipient.  
- Sender’s UI does not indicate duplication risk.  
- Duplication persists even after app/server restart.  

---

## 🧠 Suggested Fixes

| Issue | Suggested Solution |
|--------|------------------|
| Duplicate delivery | Ensure server marks messages as **delivered** once sent to recipient. Use `delivered` flag or unique message IDs to prevent replay. |
| No sender feedback | Show message status (“Pending”, “Delivered”) and prevent resending already delivered messages. |
| Queue replay logic | Review message queue processing — do not resend messages that have already been sent on reconnect. |

---



## 🚀 Conclusion

Fix #2 resolves message delivery after disconnect, but introduces **duplicate messages**, which is critical for user experience and data integrity.  
**Priority:** 🔴 High — duplication must be fixed before production release.

---

**Document Version:** 1.0  
**Date:** 2025-10-13  
**Author:** QA – Whispr Message Reliability (Oktay Mehmed)