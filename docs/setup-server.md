# 🚀 Whispr Server Setup Guide

> **Deploy and operate your own Whispr relay server**  
> Complete guide covering local development, TLS configuration, systemd services, reverse proxy setup, security hardening, and production deployment.

---

## 📋 Quick Start

### 1️⃣ Clone the Repository

```sh
git clone https://github.com/Akame1981/Whispr.git
cd Whispr
```

### 2️⃣ Create a Python Virtual Environment

```sh
python -m venv venv
source venv/bin/activate  # On Linux/Mac
```

### 3️⃣ Install Dependencies

```sh
pip install -r requirements.txt
```

### 4️⃣ Install and Run Redis (Optional but Recommended)

> 💡 **Why Redis?** Provides secure, ephemeral message storage and rate limiting.  
> Without Redis, the server falls back to in-memory storage (data lost on restart).

**Installation:**
- 🔗 [Download Redis](https://redis.io/download)

**Start Redis:**
```sh
redis-server
```

✅ Whispr automatically detects and enables Redis mode when available.

---

## 🔐 Security Configuration

### 5️⃣ Generate SSL Certificates (Strongly Recommended)

> ⚠️ **Production Warning:** Always use SSL/TLS for secure HTTPS communication.

**Generate a self-signed certificate:**

```sh
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
    -keyout key.pem -out cert.pem \
    -subj "/C=BG/ST=Sofia/L=Sofia/O=Whispr/CN=YOUR_IP" \
    -addext "subjectAltName=IP:YOUR_IP"
```

**Certificate Parameters:**
| Parameter | Description | Example |
|-----------|-------------|---------|
| `C` | Country code | `BG` |
| `ST` | State/Province | `Sofia` |
| `L` | City | `Sofia` |
| `O` | Organization | `Whispr` |
| `CN` | Server IP/Domain | `203.0.113.1` |

**Generated Files:**
- 🔑 `key.pem` → Private key (**keep secret!**)
- 📜 `cert.pem` → Public certificate (copy to `utils/` folder)

---

## ▶️ Running the Server

### 6️⃣ Start the Server

**Production (with SSL):**
```sh
uvicorn server:app --host 0.0.0.0 --port 8000 \
    --ssl-keyfile key.pem --ssl-certfile cert.pem
```

✅ Server available at: `https://YOUR_SERVER_IP:8000`

**Development (local testing only):**
```sh
uvicorn server:app --host 0.0.0.0 --port 8000
```

⚠️ **Warning:** HTTP mode should only be used for local development.

---

## ⚙️ Production Deployment

### 7️⃣ Run as a Systemd Service (Linux)

> 🔄 **Benefit:** Automatic restart on failure and system boot.

**Create service file:** `/etc/systemd/system/whispr.service`

```ini
[Unit]
Description=Whispr FastAPI Server
After=network.target redis.service

[Service]
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/Whispr
ExecStart=/home/YOUR_USERNAME/Whispr/venv/bin/uvicorn server:app \
    --host 0.0.0.0 --port 8000 \
    --ssl-keyfile /home/YOUR_USERNAME/Whispr/key.pem \
    --ssl-certfile /home/YOUR_USERNAME/Whispr/cert.pem
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```sh
sudo systemctl daemon-reload
sudo systemctl enable whispr
sudo systemctl start whispr
sudo systemctl status whispr
```

### 8️⃣ Reverse Proxy with Nginx

> 🌐 **Best Practice:** Terminate TLS at Nginx for better performance and easier certificate management.

**Create configuration:** `/etc/nginx/sites-available/whispr.conf`

```nginx
server {
    listen 443 ssl http2;
    server_name your.domain.tld;

    # SSL Configuration
    ssl_certificate     /etc/letsencrypt/live/your.domain.tld/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your.domain.tld/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy Configuration
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your.domain.tld;
    return 301 https://$server_name$request_uri;
}
```

**Activate configuration:**
```sh
sudo ln -s /etc/nginx/sites-available/whispr.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 🎛️ Configuration

### 9️⃣ Environment Variables

> 📝 **Note:** Core settings  for `server.py` are currently in [server_utils/config/(server_utils/config/).

**Environment Variables:**

| Variable                     | Purpose                         | Default    |
| ---------------------------- | ------------------------------- | ---------- |
| `max_messages_per_recipient` | Queue length per recipient      | `20`       |
| `max_messages_per_second`    | Rate limit per sender           | `10`       |
| `message_ttl_seconds`        | Message TTL (seconds)           | `10`       |
| `attachment_max_size_bytes`  | Max size for attachment (bytes) | `10485760` |


---

## 🔒 Security Hardening

### 🛡️ Security Checklist

| Category             | Requirement                     | Implementation                      |
| -------------------- | ------------------------------- | ----------------------------------- |
| **TLS/SSL**          | ✅ Always use valid certificates | LetsEncrypt or self-signed pinned   |
| **User Permissions** | ✅ Run as non-root user          | Dedicated system user               |
| **Firewall**         | ✅ Restrict ports                | Allow only 80/443 (+ 8000 internal) |
| **Redis Security**   | ✅ Enable authentication         | `requirepass` or localhost-only     |
| **Logging**          | ✅ Minimize sensitive data       | Avoid raw request bodies            |
| **Dependencies**     | ✅ Keep updated                  | Regular `pip upgrade`               |
| **Rate Limiting**    | ✅ Tune for environment          | Adjust `MAX_MESSAGES_PER_SECOND`    |
| **Headers**          | ✅ Security headers enabled      | HSTS, X-Frame-Options, etc.         |

### 🔧 Additional Hardening Steps

**Firewall Configuration:**
```sh
# UFW example
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

**Redis Authentication:**
```sh
# Edit /etc/redis/redis.conf
requirepass YOUR_STRONG_PASSWORD
```

---

## 📊 Monitoring & Metrics

### Monitoring Options

**Redis Metrics:**
```sh
# Check memory usage
redis-cli info memory

# Monitor key counts
redis-cli dbsize
```

**Nginx Logs:**
```sh
# Access logs
tail -f /var/log/nginx/access.log

# Error logs
tail -f /var/log/nginx/error.log
```

**System Resources:**
```sh
# Check service status
sudo systemctl status whispr

# View logs
sudo journalctl -u whispr -f
```

### 📈 Optional Analytics

- 📁 **File-based:** Analytics backend for message metrics
- 🔍 **Advanced:** Integrate Prometheus/Grafana for real-time dashboards

---

## ⚡ Scaling & Performance

### Scaling Strategy

| Growth Area | 🎯 First Step | 🚀 Next Step |
|-------------|--------------|-------------|
| **Connections** | Use Uvicorn workers<br/>`--workers 4` | Load balancer + sticky hashing |
| **Queue Storage** | Single Redis instance | Redis cluster with partitioning |
| **Analytics** | File logging | Kafka/Prometheus pipeline |
| **Geographic** | Single region | Multi-region deployment |

### Performance Tips

**Uvicorn Workers:**
```sh
uvicorn server:app --host 0.0.0.0 --port 8000 \
    --workers 4 \
    --ssl-keyfile key.pem --ssl-certfile cert.pem
```

**Redis Optimization:**
```sh
# Edit /etc/redis/redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
```

---

## 💾 Backup & Maintenance

### Backup Strategy

> ℹ️ **Server Design:** Whispr is stateless - user data lives on clients, server holds only ephemeral queues.

**Optional Backups:**
- 📊 `analytics_events.log` (if using analytics)
- 🔑 Certificate files (`key.pem`, `cert.pem`)
- ⚙️ Configuration files

### 🔄 Upgrading

**Standard Upgrade Process:**

1. **Pull latest changes:**
   ```sh
   cd Whispr
   git pull origin main
   ```

2. **Review changes:**
   ```sh
   git log --oneline -10
   # Check CHANGELOG if present
   ```

3. **Update dependencies:**
   ```sh
   source venv/bin/activate
   pip install -r requirements.txt --upgrade
   ```

4. **Restart service:**
   ```sh
   sudo systemctl restart whispr
   sudo systemctl status whispr
   ```

5. **Update environment variables** (when available)

---

## 🔧 Troubleshooting

### Common Issues

| 🚨 Symptom | 🔍 Possible Cause | ✅ Resolution |
|-----------|------------------|--------------|
| **400 Invalid signature** | Client signing key mismatch | Regenerate client keypair |
| **429 Rate limit exceeded** | High throughput or attack | Increase rate limit (staging only) |
| **Empty inbox after send** | Messages already fetched | Use `since` parameter in requests |
| **Redis fallback warning** | Redis not reachable | Start Redis / check firewall rules |
| **TLS handshake errors** | Certificate mismatch | Re-issue cert with correct `subjectAltName` |
| **502 Bad Gateway** | Uvicorn not running | Check systemd status and logs |
| **Port already in use** | Another process on port 8000 | `sudo lsof -i :8000` to identify |

### 🩺 Diagnostic Commands

```sh
# Check if server is listening
sudo netstat -tlnp | grep 8000

# Test SSL certificate
openssl s_client -connect YOUR_IP:8000 -showcerts

# View recent logs
sudo journalctl -u whispr --since "10 minutes ago"

# Check Redis connection
redis-cli ping  # Should return: PONG
```

---

## 💡 Pro Tips & Best Practices

### Network Configuration
- 🔥 **Firewall:** Open port 8000 (or 443 for reverse proxy)
- 🌐 **Port Forwarding:** Forward external port to your server
- 🔒 **Security:** Always use SSL/TLS in production
- 🔑 **Key Safety:** Never commit `key.pem` to version control

### Performance & Reliability
- 📦 **Redis:** Use Redis for production deployments
- ⚡ **Workers:** Scale Uvicorn workers based on CPU cores
- 🔄 **Monitoring:** Implement health checks (`/healthz` endpoint coming soon)
- 📊 **Logs:** Rotate logs to prevent disk space issues

### Development Workflow
```sh
# Quick development server
uvicorn server:app --reload --host 127.0.0.1 --port 8000

# Production-like testing
uvicorn server:app --workers 2 --host 0.0.0.0 --port 8000
```

---

## 📚 Additional Resources

| Resource | Description |
|----------|-------------|
| 📖 [Server Documentation](server-documentation.md) | Complete API reference |
| 💻 [Client Usage Guide](client-usage.md) | Client setup instructions |
| 🏗️ [Architecture Overview](architecture.md) | System design details |
| 🐛 [GitHub Issues](https://github.com/Akame1981/Whispr/issues) | Report bugs & request features |

---

## 👨‍💻 About

**Developed by Oktay Mehmed (Akame1981)**

> 🌟 Whispr - Secure, ephemeral messaging relay server

**Support & Community:**
- 🐙 [GitHub Repository](https://github.com/Akame1981/Whispr)
- 📧 Report issues on GitHub Issues
- ⭐ Star the project if you find it useful!

---

<div align="center">

**Made with ❤️ for secure communications**

</div>
