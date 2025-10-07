# Whispr Server Setup Guide

Deploy and operate your own **Whispr** relay. Covers local development, TLS, systemd service, reverse proxy, security hardening, scaling considerations, and maintenance.

---

## 1. Clone the Repository

```sh
git clone https://github.com/Akame1981/Whispr.git
cd Whispr
```

---

## 2. Create a Python Virtual Environment

```sh
python -m venv venv
```

---

## 3. Install Dependencies

```sh
pip install -r requirements.txt
```

---

## 4. (Optional) Install and Run Redis

**Redis** is recommended for secure, ephemeral message storage and rate limiting.  
If Redis is not available, the server will use in-memory storage (messages lost on restart).

- **Install Redis:**  
  [Download Redis](https://redis.io/download)

- **Start Redis locally:**

```sh
redis-server
```

> If Redis is running, Whispr auto‑enables Redis mode. Otherwise it falls back to in‑memory (single process).

---

## 5. (Recommended) Generate SSL Certificates

**SSL is strongly recommended for secure HTTPS communication.**

Generate a self-signed certificate (replace placeholders as needed):

```sh
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
    -keyout key.pem -out cert.pem \
    -subj "/C=BG/ST=Sofia/L=Sofia/O=Whispr/CN=YOUR_IP" \
    -addext "subjectAltName=IP:YOUR_IP"
```

- `C`: Country code (e.g., BG for Bulgaria)
- `ST`: State or province
- `L`: City
- `O`: Organization/app name
- `CN`: Your server's external IP address

**Result:**

- `key.pem` → Private key (keep secret)
- `cert.pem` → Public certificate (copy to `utils/` folder)

---

## 6. Run the Server

**With SSL:**

```sh
uvicorn server:app --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem
```
 
Server will be available at:  
`https://YOUR_SERVER_IP:8000`

**Without SSL (local testing only):**

```sh
uvicorn server:app --host 0.0.0.0 --port 8000
```

---

## 7. (Optional) Run as a Systemd Service (Linux)

Create `/etc/systemd/system/whispr.service`:

```ini
[Unit]
Description=Whispr FastAPI server
After=network.target

[Service]
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/Whispr
ExecStart=/home/YOUR_USERNAME/Whispr/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000 --ssl-keyfile /home/YOUR_USERNAME/Whispr/key.pem --ssl-certfile /home/YOUR_USERNAME/Whispr/cert.pem
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```sh
sudo systemctl daemon-reload
sudo systemctl enable whispr
sudo systemctl start whispr
sudo systemctl status whispr
```

---

## 8. Reverse Proxy (Nginx Example)

Terminate TLS at Nginx and forward to local Uvicorn (no SSL options needed in uvicorn command).

`/etc/nginx/sites-available/whispr.conf`:

```nginx
server {
  listen 443 ssl http2;
  server_name your.domain.tld;

  ssl_certificate     /etc/letsencrypt/live/your.domain.tld/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/your.domain.tld/privkey.pem;

  add_header Strict-Transport-Security "max-age=63072000" always;
  add_header X-Content-Type-Options nosniff;
  add_header X-Frame-Options DENY;

  location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto https;
  }
}
```

Symlink + reload:

```bash
sudo ln -s /etc/nginx/sites-available/whispr.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 9. Environment Variables / Configuration

Currently core server settings are constants in `server.py` (e.g. `MAX_MESSAGES_PER_RECIPIENT`, `MAX_MESSAGES_PER_SECOND`, `MESSAGE_TTL`). To externalize:

1. Add `os.getenv("WHISPR_MAX_MSGS", 20)` style lookups.
2. Document them here.

Recommended env var plan (future):

| Variable | Purpose | Default |
|----------|---------|---------|
| WHISPR_MAX_MSGS | Queue length per recipient | 20 |
| WHISPR_MSG_TTL | Seconds before expiration | 60 |
| WHISPR_RATE_PER_SEC | Rate limit per sender | 10 |
| WHISPR_ANALYTICS_DISABLE | Force disable analytics import | unset |

## 10. Security Hardening Checklist

| Item | Action |
|------|--------|
| TLS | Always use valid cert (LetsEncrypt / self-signed pinned) |
| System user | Run under dedicated non-root user |
| Firewall | Allow only 80/443 (and 8000 if internal) |
| Redis auth | Enable `requirepass` or bind to localhost only |
| Logging | Avoid writing raw request bodies (they are ciphertext but still limit logs) |
| Updates | Keep Python & dependencies patched |
| Rate limits | Tune `MAX_MESSAGES_PER_SECOND` for environment |

## 11. Monitoring & Metrics

Basic options:

- Redis key counts / memory usage: `redis-cli info memory`.
- Request counts: front Nginx access logs or add simple middleware.
- Analytics backend (optional) for higher-level message metrics.

## 12. Scaling Considerations

| Growth Area | First Step | Next Step |
|-------------|-----------|-----------|
| Connections | Use Uvicorn workers (e.g. `--workers 4`) | Add load balancer + sticky hashing on recipient key |
| Queue storage | Redis instance | Redis cluster / partition by recipient hash |
| Analytics volume | File log | Dedicated metrics pipeline (Kafka/Prometheus) |

## 13. Backup & Restore

Only user state is on clients. Server holds ephemeral queues, so no critical data persistence required. Optional: backup `analytics_events.log` if you rely on it for historical metrics.

## 14. Upgrading

1. `git pull` latest.
2. Review CHANGELOG (if present) for breaking constants.
3. Restart systemd service.
4. (If env var approach implemented) update `.env` or systemd unit `Environment=` lines.

## 15. Troubleshooting

| Symptom | Possible Cause | Resolution |
|---------|----------------|-----------|
| 400 Invalid signature | Client signing key mismatch | Regenerate client keys |
| 429 Rate limit exceeded quickly | Legit high throughput | Raise temp in staging only |
| Empty inbox after send | Client fetched earlier (queue drained) | Use `since` param; monitor poll interval |
| Redis fallback warning | Redis not reachable | Start service / check firewall |
| TLS handshake errors | Wrong cert path / mismatch SAN | Re-issue cert with correct `subjectAltName` |

## 16. Notes & Tips

- **Firewall:** Open port 8000 (or 443 if reverse proxy) for incoming connections.
- **Port Forwarding:** If hosting behind a router, forward the published port to your server.
- **Security:** Always use SSL in production. Keep your private key (`key.pem`) safe.
- **Redis:** For best security and reliability, use Redis for message storage.
- **Observability:** Add a simple `/healthz` endpoint (future) for uptime monitoring.

---

## Developed by Oktay Mehmed (Akame1981)

For API details, see [docs/server-documentation.md](server-documentation.md).  
For client setup, see [docs/client-usage.md](client-usage.md).
