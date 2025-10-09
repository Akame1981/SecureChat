"""WebSocket client for real-time push of incoming messages.

Falls back silently if connection cannot be established. Integrates with
existing ChatManager workflow by saving, caching and displaying messages
exactly like the polling fetch loop would.
"""
from __future__ import annotations

import json
import threading
import time
import ssl
import traceback
import urllib.parse

try:
    import websocket  # type: ignore
except ImportError:  # graceful fallback
    websocket = None  # type: ignore

from utils.crypto import decrypt_message, verify_signature
from utils.chat_storage import save_message
from utils.recipients import get_recipient_name, ensure_recipient_exists


def _candidate_ws_urls(http_url: str, recipient_key: str):
    if http_url.startswith("https://"):
        base = "wss://" + http_url[len("https://"):]
    elif http_url.startswith("http://"):
        base = "ws://" + http_url[len("http://"):]
    else:
        base = "ws://" + http_url
    base = base.rstrip('/')
    q = urllib.parse.quote(recipient_key, safe="")
    return [
        f"{base}/ws/{q}",              # path form
        f"{base}/ws?recipient={q}",    # query form
    ]


def start_ws_client(app):
    if websocket is None:
        print("[ws] websocket-client not installed; skipping real-time push")
        return

    def on_open(ws):  # noqa: ANN001
        app.ws_connected = True
        try:
            app.notifier.show("Real-time connected", type_="success")
        except Exception:
            pass
        # Optionally send a hello/ping
        try:
            ws.send("ping")
        except Exception:
            pass

    def on_close(ws, status, msg):  # noqa: ANN001
        app.ws_connected = False
        try:
            app.notifier.show("Real-time disconnected", type_="warning")
        except Exception:
            pass

    def on_error(ws, err):  # noqa: ANN001
        app.ws_connected = False
        try:
            msg = str(err)
            print(f"[ws] error: {msg}")
            # Detect repeated client-side handshake failures (likely server missing WS support or proxy blocking)
            if any(code in msg for code in ["Handshake status 403", "Handshake status 404", "Handshake status 400"]):
                app.__dict__.setdefault('_ws_handshake_failures', 0)
                app._ws_handshake_failures += 1  # type: ignore[attr-defined]
                if app._ws_handshake_failures >= 3 and not getattr(app, '_ws_permanently_disabled', False):  # type: ignore[attr-defined]
                    app._ws_permanently_disabled = True  # type: ignore[attr-defined]
                    try:
                        app.notifier.show("Real-time disabled (server rejected WebSocket)", type_="warning")
                    except Exception:
                        pass
        except Exception:
            pass

    def on_message(ws, message):  # noqa: ANN001
        try:
            data = json.loads(message)
            # Fields mirror inbox payload: from, enc_pub, message, signature, timestamp
            sender_sign = data.get("from")
            sender_enc = data.get("enc_pub")
            enc_b64 = data.get("message")
            signature = data.get("signature")
            ts = data.get("timestamp", time.time())

            if not (sender_sign and sender_enc and enc_b64):
                return
            if signature and not verify_signature(sender_sign, enc_b64, signature):
                return
            try:
                plaintext = decrypt_message(enc_b64, app.private_key)
            except Exception:
                return

            # Ensure chat exists for unknown sender
            name = get_recipient_name(sender_enc, app.pin)
            if not name:
                try:
                    name = ensure_recipient_exists(sender_enc, app.pin)
                    if hasattr(app, 'sidebar') and hasattr(app.sidebar, 'update_list'):
                        try:
                            app.after(0, app.sidebar.update_list)
                        except Exception:
                            pass
                except Exception:
                    name = sender_enc
            save_message(sender_enc, name, plaintext, app.pin, timestamp=ts)
            if hasattr(app, 'chat_manager'):
                try:
                    app.chat_manager._append_cache(sender_enc, {"sender": name, "text": plaintext, "timestamp": ts})
                except Exception:
                    pass
            if app.recipient_pub_hex == sender_enc:
                try:
                    app.after(0, app.display_message, sender_enc, plaintext, ts)
                except Exception:
                    pass
        except Exception:
            traceback.print_exc()

    def run():
        urls = _candidate_ws_urls(app.SERVER_URL, app.my_pub_hex)
        idx = 0
        sslopt = {}
        if app.SERVER_CERT:
            sslopt = {"cert_reqs": ssl.CERT_REQUIRED, "ca_certs": app.SERVER_CERT}
        else:
            # In dev you might skip verification
            sslopt = {"cert_reqs": ssl.CERT_NONE}
        backoff = 1
        while not app.stop_event.is_set():
            if getattr(app, '_ws_permanently_disabled', False):
                # Abort loop entirely; polling continues elsewhere.
                return
            try:
                app.ws_connected = False
                url = urls[idx % len(urls)]
                idx += 1  # next attempt will try alternate form if this fails
                ws_app = websocket.WebSocketApp(
                    url,
                    on_open=on_open,
                    on_close=on_close,
                    on_error=on_error,
                    on_message=on_message,
                )
                ws_app.run_forever(sslopt=sslopt, ping_interval=30, ping_timeout=10)
            except Exception as e:  # connection or run_forever crash
                print(f"[ws] run_forever exception: {e}")
            if app.stop_event.is_set():
                break
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)

    threading.Thread(target=run, daemon=True).start()
