

## 🧪 Test Case

**Test Name:** Scroll Position Persist — Switching Between Chats

**Goal:**  
Verify that the chat window correctly resets or adjusts scroll position when switching between users with varying message lengths.

---

## ✅ Expected Behavior

- When switching from a long chat (scrolled down) to a shorter chat:  
  - The scroll position should reset to **bottom** (show latest messages).  
  - All messages should render immediately without requiring user scroll.
- When switching back to a longer chat:  
  - Scroll position should remain at **bottom** or restore last known position.

---

## ⚙️ Test Execution

| Step | Action | Expected | Result |
|------|---------|-----------|--------|
| 1 | Open chat with User A (long conversation) | Chat renders and scrolls to bottom | ✅ |
| 2 | Scroll to bottom manually | Last message visible | ✅ |
| 3 | Switch to chat with User B (short chat, few messages) | Scroll resets to bottom and all messages visible | ❌ Chat remains scrolled far down, messages hidden |
| 4 | Switch back to User A | Long chat reopens | ✅ Scroll remains correct |

---

## 🧩 Observations

- When switching to a chat with **fewer messages**, the previous scroll offset is **retained**, causing the new chat’s messages to appear invisible until the user manually scrolls up.
- The rendering logic assumes the previous chat’s scroll height, not recalculated per user.
- The shorter chat **does not trigger re-render** because the scroll container hasn’t changed dimensions yet when messages load.

---



## ✅ Expected Post-Fix Behavior

| Step | Expected Result | Status |
|------|------------------|--------|
| Open long chat | Scrolls to bottom | ✅ |
| Switch to short chat | Scroll resets to bottom | ✅ |
| Switch back to long chat | Scroll restores correctly | ✅ |

---

**Status:** ❌ Bug confirmed  
**Priority:** Medium (affects usability but not data integrity)  
**Fix Version Target:** v0.9.7  
**Tester:** Oktay Mehmed  
**Date:** 2025-10-13
