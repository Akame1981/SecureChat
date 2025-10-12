# Whispr User Guide

A comprehensive guide to using Whispr - your secure, end-to-end encrypted communication platform with messaging, group chats, and voice calls.

## Table of Contents

1. [What is Whispr?](#what-is-whispr)
2. [Getting Started](#getting-started)
3. [What You Can Do](#what-you-can-do)
4. [Direct Messaging](#direct-messaging)
5. [Group Chats](#group-chats)
6. [Voice Calls](#voice-calls)
7. [File Sharing](#file-sharing)
8. [Customization & Settings](#customization--settings)
9. [Security Features](#security-features)
10. [Tips & Tricks](#tips--tricks)
11. [Troubleshooting](#troubleshooting)
12. [Advanced Features](#advanced-features)

---

## What is Whispr?

Whispr is a **secure messaging app** that keeps your conversations completely private. Unlike other messaging apps, Whispr encrypts everything on your device before sending it, so even the server can't read your messages. 

**Key Benefits:**
- 🔒 **Complete Privacy**: All messages encrypted end-to-end
- 💬 **Direct Messages**: Private 1-on-1 conversations
- 👥 **Group Chats**: Create groups with multiple channels
- 📞 **Voice Calls**: High-quality audio calls
- 📁 **Secure File Sharing**: Send images and documents safely
- 🎨 **Customizable**: Multiple themes and appearance options
- 🔄 **Auto-Updates**: Stay current with the latest features
- 🌐 **Cross-Platform**: Works on Windows, macOS, and Linux

---

## Getting Started

### First Launch
1. **Run Whispr** - Launch the application
2. **Set Your PIN** - Create a secure PIN to protect your identity (this encrypts your private keys)
3. **Choose Username** - Pick a display name for yourself
4. **You're Ready!** - Your secure identity is created and stored locally

### Your Identity
- Whispr creates a unique cryptographic identity for you
- Your **Public Key** (shown in the app) is like your "address" - share this with people to receive messages
- Your **Private Key** stays on your device, encrypted with your PIN
- Nobody else (including the server) can read messages meant for you

---

## What You Can Do

### 💬 Messaging
- **Send secure messages** to anyone with Whispr
- **Real-time delivery** - messages appear instantly
- **Message history** - all conversations saved securely on your device (server doesn't save your messages after delivery)
- **Rich text support** - send formatted messages

### 👥 Group Communication  
- **Create groups** with custom names
- **Multiple channels** per group
- **Member management** - invite, approve, or remove members
- **Role-based permissions** - owners, admins, and members
- **Group security** - encrypted group keys that rotate for security

### 📞 Voice Calling
- **High-quality voice calls** using WebRTC technology
- **Direct peer-to-peer** - calls go directly between you and the other person
- **Device selection** - choose your microphone and speakers
- **Cross-platform** - call between different operating systems

### 📁 File Sharing
- **Secure file transfers** - all files encrypted before upload
- **Image previews** - see images directly in chat
- **Document support** - share any file type safely
- **Local encryption** - files stored encrypted on your device

### 🎨 Customization
- **Multiple themes** - dark mode, light mode, custom colors
- **Live theme switching** - change appearance without restarting
- **Notification settings** - control how you're alerted to new messages
- **Audio device settings** - configure microphone and speaker preferences

---

## Direct Messaging

### Starting a Conversation
1. **Get someone's public key** - they can copy it from their Whispr app and send it to you
2. **Add them as a contact**:
   - Click the **"Add Recipient"** button in the sidebar
   - Paste their public key
   - Give them a friendly name
   - Click "Add"
3. **Send your first message** - click on their name and start typing!

### Sharing Your Public Key
- Your public key is displayed at the top of the app
- Click **"Copy"** to copy it to clipboard
- Share this with anyone you want to receive messages from
- This is completely safe to share publicly

### Message Features
- **Real-time delivery** - messages appear instantly when both users are online
- **Message history** - all your conversations are saved securely
- **Timestamps** - see exactly when messages were sent
- **Encryption status** - all messages are automatically encrypted

### Starting Voice Calls
- Click the **"Call"** button next to the Copy button
- The other person will receive a call invitation in their chat
- They can accept or decline the call
- Enjoy high-quality voice conversation!

---

## Group Chats

### Creating Your First Group
1. **Switch to Groups** - click the "Groups" tab in the main interface
2. **Create Group**:
   - Click "Create Group" button
   - Enter a group name
   - Choose visibility (Public or Private)
   - Click create
3. **Invite Members**:
   - Share the invite code with people you want to join
   - They can use "Join Group" and enter the code
   - As owner, you'll need to distribute the group key to new members

### Understanding Channels
- **Groups have channels** - like different rooms for different topics
- **Default channel** - every group starts with a "general" channel
- **Create new channels** - click "New Channel" (owners/admins only)
- **Channel types**:
  - **Text** - for regular conversations
  - **Media** - for sharing files and images

### Group Roles Explained
- **Owner** (you, if you created the group):
  - Full control over the group
  - Can create/delete channels
  - Can promote members to admin
  - Can delete the entire group
  
- **Admin** (promoted by owner):
  - Can approve new members
  - Can create/delete channels
  - Can manage group settings
  
- **Member** (everyone else):
  - Can send messages in channels
  - Can share files and participate in discussions

### Managing Your Group
1. **Group Settings** - click "Settings" when viewing a group
2. **Approve Members** - if someone requests to join
3. **Create Channels** - organize conversations by topic
4. **Rotate Security Keys** - refresh group encryption (removes old members' access)
5. **Invite Management** - generate new invite codes or disable old ones

---

## Voice Calls

### Making a Call
1. **Select a contact** in direct messages
2. **Click "Call"** button in the chat interface
3. **Call window opens** with your audio settings
4. **Wait for response** - the other person receives an invitation
5. **Start talking** when they accept!

### Receiving Calls
1. **Call notification appears** when someone calls you
2. **Accept or Decline** using the popup dialog
3. **Call window opens** if you accept
4. **Adjust settings** if needed during the call

### Audio Settings
- **Microphone Selection**:
  - Choose which microphone to use
  - Test audio levels before important calls
  - Default usually works well
  
- **Speaker Selection**:
  - Pick your audio output device
  - Use headphones for better quality
  - Avoid feedback by not using speakers + mic simultaneously

### Call Quality Tips
- **Good internet connection** improves call quality
- **Close other apps** that use lots of bandwidth
- **Use wired headphones** for best audio experience
- **Quiet environment** helps the other person hear you clearly

---

## File Sharing

### Sending Files
1. **In any chat** - direct message or group channel
2. **Click the attachment button** (📎) next to the message input
3. **Select your files** - choose one or multiple files
4. **Files are encrypted** and sent securely
5. **Recipients see previews** for images and can download anything

### Supported File Types
- **Images** - JPEG, PNG, GIF (shown as previews in chat)
- **Documents** - PDF, Word, Excel, text files
- **Any file type** - Whispr can send anything securely
- **Size limits** - check with your server administrator for limits

### File Security
- **Automatic encryption** - all files encrypted before leaving your device
- **Secure storage** - files stored encrypted on your device
- **No server access** - the server can't see your files, only encrypted data
- **Safe sharing** - only intended recipients can decrypt and view files

### Viewing Received Files
- **Images show automatically** in the chat as thumbnails
- **Click to view full size** or save to your computer
- **Other files** show as download links
- **All files scan-safe** - encrypted files can't contain viruses until decrypted

---

## Customization & Settings

### Changing Themes
1. **Open Settings** - click the gear icon in the sidebar
2. **Appearance Tab** - select different visual themes
3. **Live Preview** - changes apply immediately
4. **Available Themes**:
   - Light mode for daytime use
   - Dark mode for low-light environments
   - Custom color schemes
   - High contrast options

### Server Configuration
- **Default Server** - works out of the box for most users
- **Custom Server** - advanced users can set up their own Whispr server
- **Connection Status** - green dot shows server connectivity
- **Certificate Pinning** - enhanced security for custom servers

### Notification Preferences
- **Desktop Notifications** - get alerts for new messages
- **Sound Alerts** - audio notifications for calls and messages
- **Do Not Disturb** - disable notifications temporarily
- **Call Alerts** - special notifications for incoming voice calls

### Privacy Settings
- **PIN Protection** - change your PIN if needed
- **Key Management** - view your public key, backup options
- **Message History** - choose how long to keep conversations
- **Auto-lock** - automatically lock the app after inactivity

---

## Security Features

### What Makes Whispr Secure

**End-to-End Encryption**
- Your messages are encrypted on your device before sending
- Only you and the intended recipient can read them
- The server only sees encrypted data, never plaintext
- Even if the server is compromised, your messages stay private

**Perfect Forward Secrecy (Groups)**
- Group keys can be rotated to invalidate old access
- If someone leaves a group, they can't read new messages
- Protects against future key compromises

**Local Security**
- All data stored encrypted on your device
- Your PIN encrypts your private keys
- Message history protected even if device is stolen
- No plaintext data touches your hard drive

### Best Security Practices

1. **Strong PIN** - use a unique, complex PIN
2. **Keep Software Updated** - Whispr auto-updates for security patches
3. **Verify Contacts** - confirm public keys through a second channel
4. **Secure Your Device** - use device encryption and screen locks
5. **Regular Key Rotation** - rotate group keys periodically
6. **Backup Considerations** - understand that losing your PIN means losing access

### Understanding Privacy
- **What Whispr Knows**: Only your public key and connection timing
- **What Whispr Doesn't Know**: Your messages, contacts, groups, or files
- **Metadata Protection**: Limited - sender/recipient relationships visible to server
- **Network Privacy**: Use VPN for additional network-level protection

---

## Tips & Tricks

### Getting the Most Out of Whispr

**Message Management**
- **Search in History** - use Ctrl+F to find old messages in long conversations
- **Quick Replies** - press Enter to send, Shift+Enter for new lines
- **Copy Messages** - right-click messages to copy text
- **Timestamps** - hover over messages to see exact send times

**Group Organization**
- **Meaningful Channel Names** - use descriptive names like "project-updates" or "random-chat"
- **Pin Important Messages** - remember important information (feature coming soon)
- **Mute Busy Groups** - reduce notifications for very active groups
- **Archive Old Groups** - leave groups you no longer need

**Call Quality Optimization**
- **Test Audio First** - use the audio settings to test before important calls
- **Stable Internet** - calls work best with consistent connection
- **Quiet Space** - background noise affects call quality for everyone
- **Backup Communication** - have a text chat open during calls for troubleshooting

**Security Best Practices**
- **Verify New Contacts** - confirm public keys through a second communication method
- **Regular Updates** - keep Whispr updated for the latest security improvements
- **Strong PINs** - use unique PINs not used anywhere else
- **Device Security** - keep your computer secure with screen locks and encryption

### Keyboard Shortcuts
- **Ctrl+N** - Add new recipient
- **Ctrl+G** - Switch to groups view
- **Ctrl+D** - Switch to direct messages
- **Enter** - Send message
- **Shift+Enter** - New line in message
- **Escape** - Close dialogs and popups

---

## Troubleshooting

### Common Issues and Solutions

**"Can't connect to server"**
- Check your internet connection
- Verify server URL in settings (default usually works)
- Try switching between WiFi and mobile data
- Contact your administrator if using a custom server

**"Messages not arriving"**
- Green dot should show server connection
- Try clicking refresh or restarting Whispr
- Check if WebSocket failed (app will show notification)
- Verify recipient's public key is correct

**"Can't join group"**
- Confirm the invite code is correct
- Ask group owner to check if group is set to require approval
- Make sure group hasn't been deleted
- Try copying the invite code again to avoid typos

**"No audio in calls"**
- Check microphone permissions in your operating system
- Try different audio devices in call settings
- Restart the call if audio stops working
- Make sure both people have working internet connections

**"Forgot my PIN"**
- Unfortunately, PINs cannot be recovered (this is by design for security)
- You'll need to create a new identity (new public key)
- Inform your contacts of your new public key
- Previous message history will be lost

**"App running slowly"**
- Close other applications that use lots of memory
- Restart Whispr occasionally to clear caches
- Check available disk space on your computer
- Consider moving to a computer with more resources for very large groups

### Getting Help
- Check this documentation first
- Look for error messages or notifications in the app
- Try restarting Whispr to resolve temporary issues
- Report bugs on the GitHub repository with details about what happened

---

## Advanced Features

### For Power Users

**Custom Servers**
- Set up your own Whispr server for complete control
- Configure custom certificate pinning for enhanced security
- Manage server resources and user limits
- See `setup-server.md` for detailed instructions

**Backup and Recovery**
- Export your public key for sharing
- Understand that private keys are not exportable (by design)
- Plan for device migration by informing contacts of key changes
- Keep secure records of important group invite codes

**Network Configuration**
- Use VPN for additional privacy protection
- Configure firewall rules for Whispr traffic
- Understand how WebRTC works for call troubleshooting
- Monitor network usage during calls and file transfers

**Development and Customization**
- Create custom themes by editing JSON files
- Understand the plugin architecture (coming soon)
- Contribute to open source development
- Report security issues responsibly

### Integration Ideas
- **Business Use**: Create groups for teams and projects
- **Family Communication**: Private family groups with photo sharing
- **Study Groups**: Academic collaboration with file sharing
- **Community Organization**: Event planning and coordination
- **International Communication**: Secure communication across borders

---

*For technical documentation and server setup, see the other guides in the `docs/` folder.*
