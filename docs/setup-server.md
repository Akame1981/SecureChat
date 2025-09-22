# SecureChat Server Setup Guide

This guide will help you deploy your own **SecureChat** server using **FastAPI**.  
The SecureChat client connects to the official public server by default, but you can host your own for full control and privacy.

---

## 1. Clone the Repository

```sh
git clone https://github.com/Akame1981/SecureChat.git
cd SecureChat
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

> If Redis is running, SecureChat will use it automatically.  
> If not, the server prints a warning and uses in-memory fallback.

---

## 5. (Recommended) Generate SSL Certificates

**SSL is strongly recommended for secure HTTPS communication.**

Generate a self-signed certificate (replace placeholders as needed):

```sh
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
    -keyout key.pem -out cert.pem \
    -subj "/C=BG/ST=Sofia/L=Sofia/O=SecureChat/CN=YOUR_IP" \
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

Create `/etc/systemd/system/securechat.service`:

```ini
[Unit]
Description=SecureChat FastAPI server
After=network.target

[Service]
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/SecureChat
ExecStart=/home/YOUR_USERNAME/SecureChat/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000 --ssl-keyfile /home/YOUR_USERNAME/SecureChat/key.pem --ssl-certfile /home/YOUR_USERNAME/SecureChat/cert.pem
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```sh
sudo systemctl daemon-reload
sudo systemctl enable securechat
sudo systemctl start securechat
sudo systemctl status securechat
```

---

## Notes & Tips

- **Firewall:** Open port 8000 (or your chosen port) for incoming connections.
- **Port Forwarding:** If hosting behind a router, forward the server port to your local machine.
- **Security:** Always use SSL in production. Keep your private key (`key.pem`) safe.
- **Redis:** For best security and reliability, use Redis for message storage.

---

## Developed by Oktay Mehmed (Akame1981)

For API details, see [docs/server-documentation.md](server-documentation.md).
For client setup, see [docs/client-usage.md](client-usage.md).