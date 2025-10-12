import asyncio
import json
import ssl
import threading
import uuid
from dataclasses import dataclass
from typing import Optional, Callable

import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.rtcconfiguration import RTCConfiguration, RTCIceServer
from aiortc.contrib.media import MediaPlayer

from utils.rtc_media import AudioPlayer, TkVideoRenderer, MicrophoneSDTrack
from utils.crypto import encrypt_message, decrypt_message


@dataclass
class CallState:
    call_id: str
    pc: RTCPeerConnection
    remote_video_label: any
    on_close: Optional[Callable[[], None]] = None


class RTCManager:
    def __init__(self, app):
        self.app = app
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._ws = None
        self._ws_lock = threading.Lock()
        self.current_call = None  # type: Optional[CallState]
        self._remote_pub_hex = None  # type: Optional[str]
        self._sent_leave = False
        # Selected devices (None = default)
        self._mic_device = None
        self._speaker_device = None
        self._camera_device = None

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _notify(self, msg: str, type_: str = "info"):
        try:
            if hasattr(self.app, 'after') and hasattr(self.app, 'notifier'):
                self.app.after(0, self.app.notifier.show, msg, type_)
            elif hasattr(self.app, 'notifier'):
                # Best effort without after
                self.app.notifier.show(msg, type_)
        except Exception:
            pass

    # ---- Device selection API ----
    def set_mic_device(self, device):
        self._mic_device = device

    def set_speaker_device(self, device):
        self._speaker_device = device

    def set_camera_device(self, path: str | None):
        self._camera_device = path

    def _server_ws_url(self) -> str:
        base = self.app.SERVER_URL.rstrip('/')
        if base.startswith('https://'):
            return 'wss://' + base[len('https://'):] + '/signal'
        if base.startswith('http://'):
            return 'ws://' + base[len('http://'):] + '/signal'
        return 'ws://' + base + '/signal'

    def _ssl_context(self):
        if self.app.SERVER_CERT:
            ctx = ssl.create_default_context(cafile=self.app.SERVER_CERT)
        else:
            ctx = ssl._create_unverified_context()
        return ctx

    def _ensure_ws(self):
        async def _connect():
            if self._ws is not None and not self._ws.closed:
                return self._ws
            self._ws = await websockets.connect(self._server_ws_url(), ssl=self._ssl_context())
            return self._ws
        return asyncio.run_coroutine_threadsafe(_connect(), self._loop).result()

    async def _ensure_ws_async(self):
        if self._ws is not None and not self._ws.closed:
            return self._ws
        self._ws = await websockets.connect(self._server_ws_url(), ssl=self._ssl_context())
        return self._ws

    def _ws_send(self, payload: dict):
        async def _send():
            ws = await self._ensure_ws_async()
            await ws.send(json.dumps(payload))
            return ws
        return asyncio.run_coroutine_threadsafe(_send(), self._loop).result()

    def _ws_send_nowait(self, payload: dict):
        async def _send():
            ws = await self._ensure_ws_async()
            await ws.send(json.dumps(payload))
        # Fire-and-forget; don't block the caller/UI thread
        try:
            asyncio.run_coroutine_threadsafe(_send(), self._loop)
        except Exception:
            pass

    def start_call(self, remote_pub_hex: str, remote_video_label) -> str:
        call_id = str(uuid.uuid4())
        config = RTCConfiguration(iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])])
        pc = RTCPeerConnection(configuration=config)
        self._remote_pub_hex = remote_pub_hex

        # Local media (microphone + optional camera)
        # Local microphone capture (try PulseAudio, then ALSA)
        mic_added = False
        try:
            player = MediaPlayer('default', format='pulse')  # Linux PulseAudio
            if player.audio:
                pc.addTrack(player.audio)
                mic_added = True
        except Exception:
            mic_added = False
        if not mic_added:
            try:
                player = MediaPlayer('default', format='alsa')  # ALSA fallback
                if player.audio:
                    pc.addTrack(player.audio)
                    mic_added = True
            except Exception:
                mic_added = False
        if not mic_added:
            try:
                mic = MicrophoneSDTrack(on_warning=lambda m: self._notify(m, "warning"), device=self._mic_device)
                pc.addTrack(mic)  # Fallback mic via sounddevice
                mic_added = True
            except Exception:
                mic_added = False
        if not mic_added:
            self._notify("Microphone not available. The other side may not hear you.", "warning")
        # Try attach default camera on Linux (/dev/video0)
        try:
            cam_path = self._camera_device or '/dev/video0'
            cam = MediaPlayer(cam_path, format='v4l2')
            if cam.video:
                pc.addTrack(cam.video)
        except Exception:
            pass

        # On track received
        @pc.on('track')
        def on_track(track):
            if track.kind == 'audio':
                try:
                    player = AudioPlayer(on_warning=lambda m: self._notify(m, "warning"), device=self._speaker_device)
                    player.start(self._loop, track)
                except Exception:
                    pass
            elif track.kind == 'video':
                try:
                    renderer = TkVideoRenderer(remote_video_label)
                    renderer.start(self._loop, track)
                except Exception:
                    pass

        # Offer/Signaling
        async def _do_offer():
            await pc.setLocalDescription(await pc.createOffer())
            # Wait for ICE gathering complete to include candidates in SDP
            for _ in range(100):
                if pc.iceGatheringState == 'complete':
                    break
                await asyncio.sleep(0.05)
            # Join room
            ws = await self._ensure_ws_async()
            await ws.send(json.dumps({"type": "join", "call_id": call_id}))
            # Send SDP
            payload = {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
            enc = encrypt_message(json.dumps(payload), remote_pub_hex)
            await ws.send(json.dumps({"type": "signal", "call_id": call_id, "payload": {"enc": enc}}))

        # Schedule offer task without blocking the UI
        try:
            asyncio.run_coroutine_threadsafe(_do_offer(), self._loop)
        except Exception:
            pass

        self.current_call = CallState(call_id=call_id, pc=pc, remote_video_label=remote_video_label)
        # Spawn listener
        self._spawn_listener(call_id, pc)

        # Notify callee via encrypted chat message so the invite is end-to-end
        try:
            # Reuse chat plane. This will show as text; could be improved with system styling.
            invite_text = f"CALL:{json.dumps({'call_id': call_id})}"
            if hasattr(self.app, 'chat_manager') and self.app.recipient_pub_hex == remote_pub_hex:
                self.app.chat_manager.send(invite_text)
        except Exception:
            pass
        return call_id

    def _spawn_listener(self, call_id: str, pc: RTCPeerConnection):
        async def _listen():
            ws = await self._ensure_ws_async()
            # Ensure joined
            await ws.send(json.dumps({"type": "join", "call_id": call_id}))
            try:
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                    except Exception:
                        continue
                    if data.get('type') == 'signal':
                        payload = data.get('payload') or {}
                        # Decrypt payload if encrypted
                        if 'enc' in payload:
                            try:
                                decoded = decrypt_message(payload['enc'], self.app.private_key)
                                payload = json.loads(decoded)
                            except Exception:
                                continue
                        if 'sdp' in payload and 'type' in payload:
                            desc = RTCSessionDescription(sdp=payload['sdp'], type=payload['type'])
                            if desc.type == 'offer':
                                await pc.setRemoteDescription(desc)
                                await pc.setLocalDescription(await pc.createAnswer())
                                resp = {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
                                enc = encrypt_message(json.dumps(resp), self._remote_pub_hex) if self._remote_pub_hex else json.dumps(resp)
                                await ws.send(json.dumps({"type": "signal", "call_id": call_id, "payload": {"enc": enc}}))
                            else:  # answer
                                await pc.setRemoteDescription(desc)
                        elif 'candidate' in payload:
                            # aiortc manages ICE via SDP; optional for Trickle ICE. Skipped for simplicity.
                            pass
                    elif data.get('type') == 'peer-join':
                        # Re-send our offer/answer when a new peer joins late
                        try:
                            if pc.localDescription:
                                payload = {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
                                enc = encrypt_message(json.dumps(payload), self._remote_pub_hex) if self._remote_pub_hex else json.dumps(payload)
                                await ws.send(json.dumps({"type": "signal", "call_id": call_id, "payload": {"enc": enc}}))
                        except Exception:
                            pass
                    elif data.get('type') == 'peer-leave':
                        # Remote left: gracefully close our PC, but do not send 'leave' back
                        try:
                            await pc.close()
                        except Exception:
                            pass
                        # Notify UI (non-blocking)
                        try:
                            if hasattr(self.app, 'notifier'):
                                self.app.after(0, self.app.notifier.show, "Peer left the call", "info")
                        except Exception:
                            pass
                        # Clear current call state
                        self.current_call = None
                        break
            except Exception:
                pass

        try:
            asyncio.run_coroutine_threadsafe(_listen(), self._loop)
        except Exception:
            pass

    def answer_call(self, call_id: str, remote_video_label, remote_pub_hex: str):
        # Prepare new RTCPeerConnection to answer
        config = RTCConfiguration(iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])])
        pc = RTCPeerConnection(configuration=config)
        self._remote_pub_hex = remote_pub_hex
        # Local microphone capture (PulseAudio then ALSA)
        mic_added = False
        try:
            player = MediaPlayer('default', format='pulse')
            if player.audio:
                pc.addTrack(player.audio)
                mic_added = True
        except Exception:
            mic_added = False
        if not mic_added:
            try:
                player = MediaPlayer('default', format='alsa')
                if player.audio:
                    pc.addTrack(player.audio)
                    mic_added = True
            except Exception:
                mic_added = False
        if not mic_added:
            try:
                mic = MicrophoneSDTrack(on_warning=lambda m: self._notify(m, "warning"), device=self._mic_device)
                pc.addTrack(mic)
                mic_added = True
            except Exception:
                mic_added = False
        if not mic_added:
            self._notify("Microphone not available. The other side may not hear you.", "warning")
        try:
            cam_path = self._camera_device or '/dev/video0'
            cam = MediaPlayer(cam_path, format='v4l2')
            if cam.video:
                pc.addTrack(cam.video)
        except Exception:
            pass

        @pc.on('track')
        def on_track(track):
            if track.kind == 'audio':
                try:
                    player = AudioPlayer(on_warning=lambda m: self._notify(m, "warning"), device=self._speaker_device)
                    player.start(self._loop, track)
                except Exception:
                    pass
            elif track.kind == 'video':
                try:
                    renderer = TkVideoRenderer(remote_video_label)
                    renderer.start(self._loop, track)
                except Exception:
                    pass

        # Join and listen for offer, then answer when received.
        self.current_call = CallState(call_id=call_id, pc=pc, remote_video_label=remote_video_label)
        self._spawn_listener(call_id, pc)
        # Ensure we are joined to the room so we can receive signals
        # Join room without blocking
        self._ws_send_nowait({"type": "join", "call_id": call_id})

    def hangup(self):
        st = self.current_call
        if not st:
            return
        async def _close():
            try:
                await st.pc.close()
            except Exception:
                pass
            try:
                if not self._sent_leave:
                    self._sent_leave = True
                    ws = await self._ensure_ws_async()
                    await ws.send(json.dumps({"type": "leave", "call_id": st.call_id}))
            except Exception:
                pass
        # Close without blocking UI
        try:
            asyncio.run_coroutine_threadsafe(_close(), self._loop)
        except Exception:
            pass
        if st.on_close:
            try:
                st.on_close()
            except Exception:
                pass
        self.current_call = None
