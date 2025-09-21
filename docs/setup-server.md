# SecureChat Server Setup Guide

This guide will help you set up your own **SecureChat** server using **FastAPI**.  

> Note: The GUI client connects by default to the official public server. You only need this if you want to host your own server.

---

## 1. Clone the Repository

```bash
git clone https://github.com/Akame1981/SecureChat.git
cd SecureChat
```
## 2. Create a Python Virtual Environment
```bash
python -m venv venv
```
## 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## 4. Redis (Optional)

Redis is used for ephemeral message storage. If you don’t install Redis, the server will automatically fallback to in-memory storage.  

- **Install Redis**: [https://redis.io/download](https://redis.io/download)  
- **Start the Redis server locally**:

```bash
redis-server
```
If Redis is running, SecureChat will store messages in Redis with a short TTL (ephemeral).

If Redis is not available, messages will be stored in-memory, which works but will be lost if the server restarts (and in my opinion its less secure).

## 5. Generate SSL Certificates (Recommended)

- **Using SSL ensures your server communicates securely over HTTPS.**

Generate a self-signed certificate:


```bash
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
    -keyout key.pem -out cert.pem \
    -subj "/C=%Country%/ST=%State%/L=%whatever this is%/O=%name%/CN= %IP%" \
    -addext "subjectAltName=IP: %IP%"
```

change :
    -%country% - with 2 letter representation of your Contry Code : (eg. for bulgaria - BG)

    -%State% - State name

    -%whatever this is% - IDK what is it i just put random shit

    -%name% - Name of the app/certificate (put whatever you want)
    
    -%IP% - put external ip address (have to port forward it ofc)


- **This will generate two files.**
    key.pem → Private key (keep secret)

    cert.pem → Public certificate

    put cert.pem inside utils folder.


## 6. Running server
```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --ssl-keyfile key.pem --ssl-certfile cert.pem
```

The server will be available at https://YOUR_SERVER_IP:8000

Without SSL (for local testing):

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

## 7. Systemd Service (Linux) 

- **Create a service file /etc/systemd/system/securechat.service:**
```bash
[Unit]
Description=SecureChat FastAPI server
After=network.target

[Service]
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/SecureChat
ExecStart=/home/YOUR_USERNAME/SecureChat/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8000 --ssl-keyfile /home/YOUR_USERNAME/SecureChat/server-key.pem --ssl-certfile /home/YOUR_USERNAME/SecureChat/server-cert.pem
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start :

```bash
sudo systemctl daemon-reload
sudo systemctl enable securechat
sudo systemctl start securechat
sudo systemctl status securechat
```



## Developed by Oktay Mehmed (Akame1981)