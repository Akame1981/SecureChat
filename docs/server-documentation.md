# Whispr Server Documentation

Comprehensive guide to the Whispr FastAPI server: message relay, group chat backend, WebRTC signaling, real-time WebSocket push, analytics integration, and deployment.

## Table of Contents

1. [Overview](#overview)
2. [Server Architecture](#server-architecture)
3. [Core Message Relay](#core-message-relay)
4. [Group Chat Backend](#group-chat-backend)
5. [WebRTC Signaling](#webrtc-signaling)
6. [Real-time WebSocket Push](#real-time-websocket-push)
7. [Analytics Integration](#analytics-integration)
8. [API Reference](#api-reference)
9. [Data Storage](#data-storage)
10. [Security Model](#security-model)
11. [Performance & Scaling](#performance--scaling)
12. [Deployment Guide](#deployment-guide)
13. [Troubleshooting](#troubleshooting)
14. [Configuration](#configuration)

---

## Overview

The Whispr server is a **multi-layered FastAPI application** that provides secure communication infrastructure without ever seeing plaintext content. It combines multiple backends to support different communication modes while maintaining end-to-end encryption.

**Core Principles:**
- **Zero-knowledge**: Server never sees plaintext messages or private keys
- **Modular**: Message relay, groups, signaling, and analytics are separate subsystems
- **Scalable**: Redis backing with in-memory fallback for development
- **Secure**: Signature verification, rate limiting, and optional analytics

**Server Components:**
- **Message Relay**: E2EE direct message queuing and delivery
- **Groups Backend**: Multi-channel group chat with member management  
- **WebRTC Signaling**: Voice call coordination via WebSocket
- **Real-time Push**: WebSocket notifications for instant delivery
- **Analytics**: Optional usage tracking and administration interface

---

## Server Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    Whispr Server (FastAPI)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Message    │  │    Groups    │  │  Analytics   │       │
│  │    Relay     │  │   Backend    │  │  (Optional)  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                           │                                 │
│              ┌────────────▼────────────┐                    │
│              │     Storage Layer       │                    │
│              │  Redis + SQLite + Files │                    │
│              └─────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
     │   Direct     │ │    Group     │ │   Voice      │
     │  Messages    │ │    Chats     │ │   Calls      │
     │              │ │              │ │              │
     │ HTTP + WS    │ │ REST API     │ │ WebRTC + WS  │
     └──────────────┘ └──────────────┘ └──────────────┘
```

### Component Responsibilities

| Component | Purpose | Technology | Storage |
|-----------|---------|------------|---------|
| **Message Relay** | Direct E2EE message queue | FastAPI + Redis/Memory | Ephemeral queues |
| **Groups Backend** | Multi-channel group chat | FastAPI + SQLAlchemy | SQLite database |
| **WebRTC Signaling** | Voice call coordination | WebSocket | In-memory rooms |
| **WebSocket Push** | Real-time notifications | WebSocket | Active connections |
| **Analytics** | Usage tracking & admin | FastAPI + JWT | SQLite database |

---

## Core Message Relay

### Responsibilities

| Function | Implementation | Details |
|----------|---------------|---------|
| **Signature Verification** | Ed25519 detached signatures | Rejects tampered messages (400) |
| **Rate Limiting** | Per-sender sliding window | 10 msgs/sec default (429 if exceeded) |
| **Message Queuing** | Redis lists or in-memory | Ephemeral storage with TTL |
| **Real-time Push** | WebSocket broadcast | Instant delivery to connected clients |
| **Inbox Management** | Atomic fetch-and-delete | Prevents message duplication |

### Message Flow
1. **Client sends** encrypted message via `POST /send`
2. **Server verifies** Ed25519 signature
3. **Rate limiting** checked against sender's history
4. **Message queued** in recipient's inbox
5. **WebSocket push** to connected recipient (if online)
6. **Client polls** or receives via WebSocket
7. **Inbox cleared** after successful delivery

### Direct Messaging Endpoints

#### `POST /send`
Send encrypted message to recipient.

**Request:**
```json
{
  "to": "<recipient_encryption_public_key_hex>",
  "from_": "<sender_signing_key_hex>", 
  "enc_pub": "<sender_encryption_public_key_hex>",
  "message": "<base64_encrypted_message>",
  "signature": "<base64_signature>",
  "timestamp": 1633024800.123
}
```

**Response:**
```json
{ "status": "ok" }
```

#### `GET /inbox/{recipient_key}?since={timestamp}`
Fetch and clear messages for recipient.

**Response:**
```json
{
  "messages": [
    {
      "from": "<sender_signing_key_hex>",
      "enc_pub": "<sender_encryption_key_hex>", 
      "message": "<base64_encrypted_message>",
      "signature": "<base64_signature>",
      "timestamp": 1633024800.123
    }
  ]
}
```

#### `WebSocket /ws/{recipient_key}`
Real-time message push for instant delivery.

**Message Format:** Same as inbox fetch response, pushed immediately when messages arrive.

---

## Group Chat Backend

### Architecture
The groups backend provides **multi-channel group communication** with end-to-end encrypted content and server-side member management.

**Key Features:**
- **Multi-channel groups** (like Discord servers)
- **Role-based permissions** (owner/admin/member)
- **Invite code system** for controlled membership
- **Group key rotation** for security
- **Attachment support** for file sharing

### Group Structure
```text
Group
├── Metadata (name, visibility, invite codes)
├── Members (roles, encrypted group keys) 
└── Channels
    ├── #general (default text channel)
    ├── #announcements (admin-only)
    └── #media (file sharing)
```

### Group Management Endpoints

#### `POST /groups/create`
Create a new group with default channel.

**Request:**
```json
{
  "name": "My Team",
  "is_public": false,
  "owner_id": "<creator_public_key_hex>"
}
```

**Response:**
```json
{
  "id": "<group_uuid>",
  "invite_code": "<random_invite_code>"
}
```

#### `POST /groups/join`
Join group via invite code.

**Request:**
```json
{
  "user_id": "<joiner_public_key_hex>",
  "invite_code": "<invite_code>"
}
```

#### `GET /groups/list?user_id={public_key}`
List groups for a user.

**Response:**
```json
{
  "groups": [
    {
      "id": "<group_uuid>",
      "name": "My Team", 
      "is_public": false,
      "owner_id": "<owner_public_key>",
      "key_version": 1
    }
  ]
}
```

### Channel Management

#### `POST /groups/channels/create`
Create new channel in group (owner/admin only).

**Request:**
```json
{
  "group_id": "<group_uuid>",
  "name": "announcements",
  "type": "text"
}
```

#### `GET /groups/channels/list?group_id={uuid}`
List channels in group.

### Group Messaging

#### `POST /groups/messages/send`
Send encrypted message to group channel.

**Request:**
```json
{
  "group_id": "<group_uuid>",
  "channel_id": "<channel_uuid>",
  "sender_id": "<sender_public_key>",
  "ciphertext": "<base64_group_encrypted_content>",
  "nonce": "<base64_encryption_nonce>", 
  "key_version": 1,
  "timestamp": 1633024800.123,
  "attachment_meta": "<optional_json_metadata>"
}
```

#### `POST /groups/messages/fetch`
Retrieve channel message history.

**Request:**
```json
{
  "group_id": "<group_uuid>",
  "channel_id": "<channel_uuid>",
  "since": 1633024800.0,
  "limit": 50
}
```

### Member Management

#### `POST /groups/members/approve`
Approve pending member (admin/owner only).

#### `POST /groups/members/keys/update`
Update encrypted group key for member.

#### `GET /groups/members/keys?group_id={uuid}`
Get encrypted group keys for all members.

---

## WebRTC Signaling

### Purpose
Provides **server-mediated signaling** for WebRTC voice calls while maintaining end-to-end encryption for call setup.

### Architecture
- **Call Rooms**: Temporary coordination spaces per `call_id`
- **SDP Exchange**: Offer/answer relay between call participants
- **ICE Coordination**: STUN candidate relay for NAT traversal
- **E2EE Invites**: Call invitations sent via normal chat encryption

### Signaling Flow
1. **Caller** generates unique `call_id`
2. **Encrypted invite** sent via normal chat to recipient
3. **Both parties** connect to `/signal` WebSocket
4. **Join room** using `call_id` for coordination
5. **SDP exchange** (offer/answer) relayed through server
6. **ICE candidates** shared for NAT traversal
7. **Direct P2P** audio connection established
8. **Room cleanup** when call ends

### WebRTC Endpoints

#### `WebSocket /signal`
Real-time signaling for voice calls.

**Message Types:**
```json
// Join call room
{
  "type": "join",
  "call_id": "<unique_call_uuid>"
}

// Relay signaling data  
{
  "type": "signal", 
  "call_id": "<call_uuid>",
  "payload": {
    "sdp": "<session_description>",
    "type": "offer|answer"
  }
}

// Leave call
{
  "type": "leave",
  "call_id": "<call_uuid>"
}
```

**Server Responses:**
```json
// Peer joined room
{ "type": "peer-join" }

// Peer left room  
{ "type": "peer-leave" }

// Relayed signaling
{
  "type": "signal",
  "payload": "<relayed_data>"
}
```

---

## Real-time WebSocket Push

### Purpose
Provides **instant message delivery** without polling delays, significantly improving user experience and reducing server load.

### Features
- **Per-recipient connections** identified by public key
- **Automatic fallback** to HTTP polling if WebSocket fails
- **Message integrity** maintained via signature verification
- **Connection management** with automatic cleanup

### WebSocket Management

#### Connection Establishment
```text
Client → GET /ws/{recipient_public_key} 
Server → WebSocket Upgrade
Client → Connection maintained for real-time push
```

#### Message Broadcasting
When a message is sent via `POST /send`:
1. **Message stored** in recipient inbox
2. **WebSocket broadcast** to recipient (if connected)
3. **Sender notification** (if sender has active WebSocket)
4. **Fallback** to polling if WebSocket unavailable

#### Connection Lifecycle
- **Auto-reconnect** on connection drops
- **Graceful degradation** to HTTP polling
- **Resource cleanup** when clients disconnect
- **Multiple connections** supported per recipient
---

## Analytics Integration

### Overview
Optional **usage tracking and administration** system that provides insights into server usage while respecting privacy boundaries.

### Components
- **Event Collection**: Message counts, group activity, user statistics
- **Admin Dashboard**: Web interface for server management
- **Group Management**: Administrative group operations
- **Privacy Respect**: No access to plaintext content

### Analytics Architecture
```text
┌─────────────────┐    Events    ┌─────────────────┐
│  Main Server    │ ──────────► │  Analytics      │
│  (Port 8000)    │              │  Backend        │
└─────────────────┘              │  (Port 8001)    │
                                 └─────────────────┘
                                          │
                                          ▼
                                 ┌─────────────────┐
                                 │  Web Dashboard  │
                                 │  (Frontend)     │
                                 └─────────────────┘
```

### Analytics Endpoints

#### `GET /api/stats/overview`
Server usage statistics.

**Response:**
```json
{
  "total_messages": 1250,
  "active_users": 45,
  "groups_count": 12,
  "avg_messages_per_day": 187
}
```

#### `GET /api/groups/public/list`
Public groups directory.

#### `DELETE /api/groups/delete?group_id={uuid}`
Administrative group deletion.

### Event Collection
When analytics are enabled, the server collects:
- **Message counts** (no content)
- **Group creation/deletion** events
- **User activity** patterns (no identity)
- **Server performance** metrics

### Privacy Protection
- **No plaintext access** - only metadata collected
- **Anonymous metrics** - no personal information stored
- **Optional system** - can be completely disabled
- **Local storage** - data stays on your server

---

## API Reference

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| **200** | Success | Normal operation |
| **400** | Bad Request | Invalid signature, malformed payload |
| **403** | Forbidden | Insufficient group permissions |
| **404** | Not Found | Group/channel/user not found |
| **409** | Conflict | Group key version mismatch |
| **429** | Rate Limited | Too many messages from sender |
| **500** | Server Error | Internal server failure |

### Error Response Format
```json
{
  "detail": "Invalid signature",
  "error_code": "SIGNATURE_INVALID",
  "timestamp": 1633024800.123
}
```

### Authentication
- **Direct Messages**: Public key cryptography (no auth needed)
- **Groups**: User ID parameter based on public key
- **Analytics**: JWT token for admin operations
- **WebRTC**: Room-based temporary access

---

## Data Storage

### Storage Architecture

| Data Type | Storage | Encryption | Retention |
|-----------|---------|------------|-----------|
| **Direct Messages** | Redis/Memory | Client-side E2EE | TTL-based expiry |
| **Group Data** | SQLite | Server stores ciphertext only | Persistent |
| **WebRTC Rooms** | Memory | E2EE signaling | Session-based |
| **Analytics** | SQLite | Aggregated metrics only | Configurable |

### Direct Message Storage

**Redis Implementation:**
```text
Key: inbox:<recipient_public_key>
Type: List
TTL: 60 seconds (configurable)
Max Size: 20 messages (configurable)
```

**Memory Fallback:**
```python
messages_store = {
    "recipient_key": [
        {
            "from": "sender_key",
            "message": "encrypted_content", 
            "timestamp": 1633024800.123
        }
    ]
}
```

### Group Storage Schema

**Groups Table:**
```sql
CREATE TABLE groups (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    invite_code TEXT UNIQUE,
    key_version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Channels Table:**
```sql
CREATE TABLE channels (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT DEFAULT 'text',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
);
```

**Group Messages Table:**
```sql
CREATE TABLE group_messages (
    id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    sender_id TEXT NOT NULL,
    ciphertext TEXT NOT NULL,
    nonce TEXT NOT NULL,
    key_version INTEGER DEFAULT 1,
    timestamp REAL DEFAULT (julianday('now')),
    attachment_meta TEXT,
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
    FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
);
```

---

## Security Model

### Cryptographic Guarantees

| Aspect | Implementation | Security Level |
|--------|---------------|----------------|
| **Message Confidentiality** | Client-side NaCl SealedBox | ✅ Strong |
| **Message Authenticity** | Ed25519 detached signatures | ✅ Strong |  
| **Group Key Distribution** | E2EE per-member encryption | ✅ Strong |
| **Call Setup Privacy** | E2EE call invitations | ✅ Strong |
| **Server Zero-Knowledge** | No plaintext access | ✅ Enforced |

### Attack Resistance

| Attack Vector | Mitigation | Status |
|---------------|------------|--------|
| **Message Tampering** | Signature verification | ✅ Protected |
| **Replay Attacks** | Timestamp validation + inbox flush | ⚠️ Partial |
| **DoS/Flooding** | Rate limiting per sender | ⚠️ Basic |
| **Group Key Compromise** | Key rotation capability | ✅ Recoverable |
| **Server Compromise** | Zero-knowledge architecture | ✅ Content protected |
| **Network Eavesdropping** | TLS + E2EE | ✅ Protected |

### Metadata Exposure

**What Server Sees:**
- Sender and recipient public keys
- Message timing and frequency  
- Group membership relationships
- Call coordination metadata

**What Server Cannot See:**
- Message plaintext content
- Private keys or PINs
- File attachment contents
- Voice call audio data

### Security Best Practices

**For Operators:**
- Use TLS certificates in production
- Keep Redis/SQLite access restricted
- Monitor for unusual traffic patterns
- Regularly update dependencies
- Configure proper firewall rules

**For Users:**
- Verify public keys through secondary channels
- Use strong PINs for client-side encryption
- Keep clients updated for security patches
- Report suspicious server behavior

---

## Performance & Scaling

### Current Performance Characteristics

| Metric | Performance | Notes |
|--------|-------------|--------|
| **Message Throughput** | ~1000 msg/sec | Limited by signature verification |
| **WebSocket Connections** | ~10,000 concurrent | Memory-bound on single instance |
| **Group Message Latency** | <100ms | SQLite + key lookup |
| **Call Setup Time** | 2-5 seconds | WebRTC negotiation dependent |
| **Memory Usage** | ~50MB baseline | Plus Redis/SQLite overhead |

### Scaling Strategies

**Horizontal Scaling:**
- **Load balancer** for multiple server instances
- **Redis cluster** for distributed message queues
- **Database sharding** for large group installations
- **CDN** for analytics frontend assets

**Vertical Scaling:**
- **CPU**: Signature verification is CPU-intensive
- **Memory**: WebSocket connections and message queues
- **Storage**: Group databases and analytics data
- **Network**: Bandwidth for file attachments

### Performance Optimization

**Message Relay:**
```python
# Rate limiting optimization
MAX_MESSAGES_PER_SECOND = 20  # Increase for high-traffic servers
MESSAGE_TTL_SECONDS = 30      # Reduce for faster cleanup

# Queue size optimization  
MAX_MESSAGES_PER_RECIPIENT = 50  # Increase for offline users
```

**Groups Backend:**
```python
# Query optimization
- Index on (group_id, channel_id, timestamp) for message fetching
- Connection pooling for SQLite
- Prepared statements for frequent queries
```

**WebSocket Management:**
```python
# Connection limits
MAX_WEBSOCKET_CONNECTIONS = 10000
HEARTBEAT_INTERVAL = 30  # Keep-alive frequency
```

---

## Deployment Guide

### Basic Deployment

**1. Install Dependencies:**
```bash
pip install -r requirements.txt
```

**2. Setup Redis (Recommended):**
```bash
# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis-server

# macOS  
brew install redis
brew services start redis
```

**3. Run Server:**
```bash
# Development
uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# Production
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 4
```

### Production Deployment

**Docker Compose Example:**
```yaml
version: '3.8'
services:
  whispr-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
    depends_on:
      - whispr-server
    restart: unless-stopped
```

**NGINX Configuration:**
```nginx
upstream whispr {
    server whispr-server:8000;
}

server {
    listen 443 ssl http2;
    server_name whispr.example.com;
    
    ssl_certificate /etc/ssl/whispr.crt;
    ssl_certificate_key /etc/ssl/whispr.key;
    
    location / {
        proxy_pass http://whispr;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /ws/ {
        proxy_pass http://whispr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
    
    location /signal {
        proxy_pass http://whispr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

### Analytics Setup (Optional)

**1. Run Analytics Backend:**
```bash
uvicorn server_utils.analytics_backend.main:app --port 8001
```

**2. Build Frontend:**
```bash
cd server_utils/analytics_frontend
npm install
npm run build
```

**3. Serve Frontend:**
```bash
# Development
npm run dev

# Production (served by nginx)
cp -r .next/static /var/www/html/
```

---

## Troubleshooting

### Common Issues

**"Redis not available" Warning**
```
⚠ Redis installed but not running. Using in-memory fallback.
```
**Solutions:**
- Start Redis: `sudo systemctl start redis-server`
- Check Redis config: `redis-cli ping`
- For development: ignore warning (in-memory works fine)

**"Groups backend disabled" Error**
```
⚠ Groups backend disabled: ModuleNotFoundError
```
**Solutions:**
- Install SQLAlchemy: `pip install sqlalchemy`
- Check file permissions on `data/` directory
- Verify Python path includes `server_utils/`

**WebSocket Connection Failures**
```
[ws] error: Handshake status 403
```
**Solutions:**
- Check CORS configuration in FastAPI
- Verify WebSocket endpoint is accessible
- Test with simple WebSocket client first
- Check firewall rules for WebSocket traffic

**High CPU Usage**
```
Server consuming 100% CPU during message sends
```
**Solutions:**
- Ed25519 verification is CPU-intensive with many messages
- Consider increasing `MAX_MESSAGES_PER_SECOND` if legitimate traffic
- Monitor for DoS attacks via rate limiting logs
- Scale horizontally with load balancer

**Group Messages Not Syncing**
```
Group members not receiving messages
```
**Solutions:**
- Check group key distribution status
- Verify all members have correct `key_version`
- Test with direct messages to isolate issue
- Check SQLite database permissions and space

### Monitoring

**Health Check Endpoint:**
```bash
curl https://your-server.com/public-key
# Should return server public key and analytics status
```

**Redis Monitoring:**
```bash
redis-cli info memory
redis-cli client list
redis-cli monitor  # Live command monitoring
```

**Database Monitoring:**
```bash
sqlite3 data/server_groups.db ".tables"
sqlite3 data/server_groups.db "SELECT COUNT(*) FROM groups;"
```

**Log Analysis:**
```bash
# Check for errors
grep ERROR server.log

# Monitor rate limiting
grep "Rate limit" server.log

# WebSocket connections
grep "WebSocket" server.log
```

---

## Configuration

### Environment Variables

```bash
# Server Configuration
WHISPR_HOST=0.0.0.0
WHISPR_PORT=8000
WHISPR_WORKERS=4

# Redis Configuration  
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_password

# Security
WHISPR_CORS_ORIGINS=https://your-frontend.com
WHISPR_MAX_MESSAGE_SIZE=1048576  # 1MB

# Analytics
ANALYTICS_ENABLED=true
ANALYTICS_JWT_SECRET=your_secret_key
ANALYTICS_DB_PATH=data/analytics.db

# Rate Limiting
MAX_MESSAGES_PER_SECOND=10
MAX_MESSAGES_PER_RECIPIENT=20
MESSAGE_TTL_SECONDS=60
```

### Configuration Files

**server_utils/config/settings.json:**
```json
{
  "max_messages_per_recipient": 20,
  "max_messages_per_second": 10, 
  "message_ttl_seconds": 60,
  "analytics_enabled": true,
  "cors_origins": ["*"],
  "max_file_size": 10485760
}
```

### Production Tuning

**For High Traffic:**
```python
MAX_MESSAGES_PER_SECOND = 100
MAX_MESSAGES_PER_RECIPIENT = 100
MESSAGE_TTL_SECONDS = 30
```

**For Large Groups:**
```python
GROUP_MESSAGE_LIMIT = 1000
GROUP_MEMBER_LIMIT = 500
CHANNEL_LIMIT_PER_GROUP = 50
```

**For Voice Calls:**
```python
MAX_CONCURRENT_CALLS = 1000
CALL_ROOM_TIMEOUT = 3600  # 1 hour max call duration
STUN_SERVERS = [
    "stun:stun.l.google.com:19302",
    "stun:stun1.l.google.com:19302"
]
```

---

*For client documentation, see [client-usage.md](client-usage.md)*
*For server setup guide, see [setup-server.md](setup-server.md)*


