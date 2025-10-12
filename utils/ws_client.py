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
# Lazy import in handler to avoid hard dependency if GUI components change


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
            # If this is an ATTACH: envelope, parse it so we save/display a
            # friendly placeholder and attachment metadata (same behavior as
            # the polling/fetch path). Otherwise save the raw plaintext.
            attachment_meta = None
            save_text = plaintext
            try:
                if isinstance(plaintext, str) and plaintext.startswith('ATTACH:'):
                    from utils.attachment_envelope import parse_attachment_envelope
                    placeholder, meta = parse_attachment_envelope(plaintext)
                    if placeholder and meta:
                        save_text = placeholder
                        attachment_meta = meta
            except Exception:
                # Parsing failed; fall back to raw plaintext
                attachment_meta = None

            # Determine which conversation this message belongs to. If server
            # included a 'to' field and it matches our own pub, treat this as
            # an incoming message for that conversation. If the message was
            # sent by us (we are the sender) the server will include 'to'
            # so we save under that conversation to persist the sender's copy.
            conv_pub = sender_enc
            try:
                if isinstance(data, dict) and data.get('to'):
                    # If the 'to' field equals our public key, conv_pub should be sender_enc
                    # otherwise the message should be saved under the 'to' pub_hex so the sender
                    # can see their own sent message in that conversation.
                    to_field = data.get('to')
                    if to_field and to_field != app.my_pub_hex:
                        conv_pub = to_field
                    else:
                        conv_pub = sender_enc
            except Exception:
                conv_pub = sender_enc

            save_message(conv_pub, name, save_text, app.pin, timestamp=ts, attachment=attachment_meta)
            # If this is a call invite, surface a dialog
            if isinstance(plaintext, str) and plaintext.startswith("CALL:"):
                import json as _json
                try:
                    inv = _json.loads(plaintext[5:])
                    cid = str(inv.get('call_id'))
                    if cid:
                        def _open_invite():
                            try:
                                from gui.call_invite import CallInviteWindow
                                CallInviteWindow(app, name or sender_enc, cid, sender_enc)
                            except Exception as _e:
                                print("invite dialog error", _e)
                        try:
                            app.after(0, _open_invite)
                        except Exception:
                            pass
                except Exception:
                    pass
            if hasattr(app, 'chat_manager'):
                try:
                    app.chat_manager._append_cache(sender_enc, {"sender": name, "text": save_text, "timestamp": ts, "_attachment": attachment_meta})
                except Exception:
                    pass
            if app.recipient_pub_hex == sender_enc:
                try:
                    # Ensure attachment_meta is forwarded to the UI so the
                    # message bubble can render attachments immediately.
                    app.after(0, app.display_message, sender_enc, save_text, ts, attachment_meta)
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
