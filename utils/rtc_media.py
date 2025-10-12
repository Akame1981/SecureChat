from __future__ import annotations

import asyncio
from typing import Callable, Optional, Union
from fractions import Fraction
import queue as _queue
import numpy as _np

try:
    import av  # type: ignore
except Exception:
    av = None  # type: ignore
try:
    from aiortc import MediaStreamTrack  # type: ignore
except Exception:
    MediaStreamTrack = object  # type: ignore

try:
    from PIL import Image, ImageTk
except Exception:  # pillow optional for video rendering
    Image = None  # type: ignore
    ImageTk = None  # type: ignore


class AudioPlayer:
    """Consume an aiortc audio track and play via sounddevice in an asyncio task.

    Provides optional user-facing warnings via on_warning.
    """

    def __init__(self, sample_rate: int = 48000, on_warning: Optional[Callable[[str], None]] = None, device: Optional[Union[int, str]] = None):
        self._preferred_sample_rate = sample_rate
        self._stream = None
        self._task = None
        self._on_warning = on_warning
        self._device = device

    def _warn(self, msg: str):
        try:
            if callable(self._on_warning):
                self._on_warning(msg)
        except Exception:
            pass

    async def _runner(self, track):
        # Lazy import to avoid crashing when PortAudio is missing
        try:
            import sounddevice as sd  # type: ignore
        except Exception:
            sd = None  # type: ignore

        if sd is None:
            # Notify once and consume frames to keep pipeline flowing
            self._warn("Audio output not available (PortAudio/sounddevice missing). Install libportaudio2 and pip install sounddevice.")
            try:
                while True:
                    _ = await track.recv()
            except Exception:
                pass
            return

        # Open stream lazily based on first received frame's sample rate
        try:
            first_frame = await track.recv()
        except Exception:
            return
        try:
            sr = getattr(first_frame, 'sample_rate', None) or self._preferred_sample_rate
        except Exception:
            sr = self._preferred_sample_rate
        try:
            self._stream = sd.OutputStream(device=self._device, samplerate=int(sr), channels=1, dtype="int16")
            self._stream.start()
        except Exception:
            # Provide device listing for troubleshooting
            try:
                devs = sd.query_devices()
                lines = []
                for idx, d in enumerate(devs):
                    if d.get('max_output_channels', 0) > 0:
                        lines.append(f"{idx}: {d.get('name')} (default_sr={d.get('default_samplerate')})")
                listing = "\n".join(lines) if lines else "<no output devices found>"
                target = f" (requested device: {self._device})" if self._device is not None else ""
                self._warn(f"Failed to open audio output stream{target}. Check your sound device and PortAudio install.\nOutputs:\n{listing}\nSet WHISPR_SPEAKER_DEVICE to pick a device (index or name).")
            except Exception:
                self._warn("Failed to open audio output stream. Check your default sound device and PortAudio installation.")
            # Drop frames if we cannot open the stream
            try:
                while True:
                    _ = await track.recv()
            except Exception:
                pass
            return

        # Write the first frame then continue loop
        try:
            pcm = first_frame.to_ndarray(format="s16", layout="mono")
            try:
                self._stream.write(pcm)
            except Exception:
                pass
            while True:
                frame = await track.recv()
                pcm = frame.to_ndarray(format="s16", layout="mono")
                try:
                    self._stream.write(pcm)
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            try:
                if self._stream:
                    self._stream.stop()
                    self._stream.close()
            except Exception:
                pass

    def start(self, loop: asyncio.AbstractEventLoop, track):
        self._task = loop.create_task(self._runner(track))

    def stop(self):
        try:
            if self._task:
                self._task.cancel()
        except Exception:
            pass


def list_audio_input_devices() -> list[tuple[Union[int, str], str]]:
    items: list[tuple[Union[int, str], str]] = [(None, "default")]  # type: ignore
    try:
        import sounddevice as sd  # type: ignore
        devs = sd.query_devices()
        for idx, d in enumerate(devs):
            if d.get('max_input_channels', 0) > 0:
                name = d.get('name') or f"Device {idx}"
                items.append((idx, f"{idx}: {name}"))
        # If we only have default, try to reinitialize PortAudio and re-scan
        if len(items) == 1:
            try:
                if hasattr(sd, "_terminate") and hasattr(sd, "_initialize"):
                    sd._terminate()
                    sd._initialize()
                    devs = sd.query_devices()
                    for idx, d in enumerate(devs):
                        if d.get('max_input_channels', 0) > 0:
                            name = d.get('name') or f"Device {idx}"
                            items.append((idx, f"{idx}: {name}"))
            except Exception:
                pass
    except Exception:
        pass
    # Include env override if present
    try:
        import os as _os
        env_dev = _os.environ.get("WHISPR_MIC_DEVICE") or _os.environ.get("WHISPR_AUDIO_INPUT_DEVICE")
        if env_dev:
            label = f"env: {env_dev}"
            items.append((env_dev, label))
    except Exception:
        pass
    return items


def list_audio_output_devices() -> list[tuple[Union[int, str], str]]:
    items: list[tuple[Union[int, str], str]] = [(None, "default")]  # type: ignore
    try:
        import sounddevice as sd  # type: ignore
        devs = sd.query_devices()
        for idx, d in enumerate(devs):
            if d.get('max_output_channels', 0) > 0:
                name = d.get('name') or f"Device {idx}"
                items.append((idx, f"{idx}: {name}"))
        # If we only have default, try to reinitialize PortAudio and re-scan
        if len(items) == 1:
            try:
                if hasattr(sd, "_terminate") and hasattr(sd, "_initialize"):
                    sd._terminate()
                    sd._initialize()
                    devs = sd.query_devices()
                    for idx, d in enumerate(devs):
                        if d.get('max_output_channels', 0) > 0:
                            name = d.get('name') or f"Device {idx}"
                            items.append((idx, f"{idx}: {name}"))
            except Exception:
                pass
    except Exception:
        pass
    # Include env override if present
    try:
        import os as _os
        env_dev = _os.environ.get("WHISPR_SPEAKER_DEVICE") or _os.environ.get("WHISPR_AUDIO_OUTPUT_DEVICE")
        if env_dev:
            label = f"env: {env_dev}"
            items.append((env_dev, label))
    except Exception:
        pass
    return items


def get_audio_debug_info() -> str:
    lines = []
    try:
        import sounddevice as sd  # type: ignore
        try:
            pa = sd.get_portaudio_version()
            lines.append(f"PortAudio: {pa}")
        except Exception:
            pass
        try:
            default = sd.default.device
            lines.append(f"Defaults (in,out): {default}")
        except Exception:
            pass
        try:
            hostapis = sd.query_hostapis()
            lines.append("Host APIs:")
            for i, h in enumerate(hostapis):
                lines.append(f"  {i}: {h.get('name')} devices={h.get('deviceCount')}")
        except Exception:
            pass
        try:
            devs = sd.query_devices()
            lines.append("Devices:")
            for idx, d in enumerate(devs):
                lines.append(f"  {idx}: {d.get('name')} in={d.get('max_input_channels')} out={d.get('max_output_channels')} sr={d.get('default_samplerate')}")
        except Exception as e:
            lines.append(f"query_devices error: {e}")
    except Exception as e:
        lines.append(f"sounddevice import error: {e}")
    return "\n".join(lines)


def list_video_devices() -> list[str]:
    # Linux: enumerate /dev/video*
    paths: list[str] = []
    try:
        import glob
        for p in glob.glob('/dev/video*'):
            paths.append(p)
    except Exception:
        pass
    return paths


class TkVideoRenderer:
    """Consume an aiortc video track and render frames into a Tkinter label."""

    def __init__(self, tk_label):
        self._tk_label = tk_label
        self._task = None

    async def _runner(self, track):
        if Image is None:
            # No rendering available
            return
        try:
            while True:
                frame = await track.recv()
                img = frame.to_ndarray(format="rgb24")
                pil = Image.fromarray(img)
                pil = pil.resize((320, 240))
                tkimg = ImageTk.PhotoImage(pil)
                def _update():
                    try:
                        self._tk_label.configure(image=tkimg)
                        self._tk_label.image = tkimg
                    except Exception:
                        pass
                try:
                    self._tk_label.after(0, _update)
                except Exception:
                    pass
        except Exception:
            pass

    def start(self, loop: asyncio.AbstractEventLoop, track):
        self._task = loop.create_task(self._runner(track))

    def stop(self):
        try:
            if self._task:
                self._task.cancel()
        except Exception:
            pass


class MicrophoneSDTrack(MediaStreamTrack):
    """Microphone capture using sounddevice, producing aiortc-compatible audio frames.

    This avoids relying on FFmpeg pulse/alsa input availability.
    """

    kind = "audio"

    def __init__(self, samplerate: int = 48000, channels: int = 1, block_ms: int = 20, on_warning: Optional[Callable[[str], None]] = None, device: Optional[Union[int, str]] = None):
        try:
            super().__init__()  # type: ignore
        except Exception:
            pass
        self._sr = int(samplerate)
        self._ch = int(max(1, channels))
        self._block = max(1, int(self._sr * block_ms / 1000))
        self._on_warning = on_warning
        self._q: _queue.Queue = _queue.Queue(maxsize=10)
        self._stream = None
        self._pts = 0
        self._time_base = Fraction(1, self._sr)
        self._started = False
        self._device: Optional[Union[int, str]] = device

        # Try to open input stream immediately; if it fails we'll try alternatives and warn with details
        try:
            import sounddevice as sd  # type: ignore
            # Allow env override for device selection
            import os as _os
            env_dev = _os.environ.get("WHISPR_MIC_DEVICE") or _os.environ.get("WHISPR_AUDIO_INPUT_DEVICE")
            if env_dev:
                try:
                    self._device = int(env_dev) if env_dev.isdigit() else env_dev
                except Exception:
                    self._device = env_dev

            # If samplerate not explicitly set, prefer default input device's default_samplerate
            try:
                di = sd.query_devices(self._device, kind='input') if self._device is not None else sd.query_devices(kind='input')
                dsr = int(di.get('default_samplerate') or 0)
                if dsr > 0:
                    self._sr = dsr
                    self._time_base = Fraction(1, self._sr)
                    self._block = max(1, int(self._sr * block_ms / 1000))
            except Exception:
                pass

            def _cb(indata, frames, time, status):  # noqa: ANN001
                try:
                    if status:
                        self._warn(f"Audio input status: {status}")
                    arr = indata
                    if self._ch > 1 and hasattr(arr, 'shape') and len(arr.shape) > 1 and arr.shape[1] > 1:
                        arr = arr[:, 0:1]
                    mono = _np.squeeze(arr).astype(_np.int16, copy=False)
                    try:
                        self._q.put_nowait(mono.copy())
                    except _queue.Full:
                        try:
                            _ = self._q.get_nowait()
                        except Exception:
                            pass
                        try:
                            self._q.put_nowait(mono.copy())
                        except Exception:
                            pass
                except Exception:
                    pass

            def _try_open(dev, sr_list, ch_list, block_opt):
                last_err = None
                for sr in sr_list:
                    for ch in ch_list:
                        try:
                            stream = sd.InputStream(device=dev, samplerate=int(sr), channels=int(ch), dtype="int16", blocksize=block_opt, callback=_cb)
                            stream.start()
                            return stream, sr, ch
                        except Exception as e:
                            last_err = e
                            continue
                if last_err:
                    raise last_err
                raise RuntimeError("No valid mic configuration found")

            # candidate devices: requested device -> default input -> all inputs by index
            dev_candidates: list = []
            try:
                if self._device is not None:
                    dev_candidates.append(self._device)
            except Exception:
                pass
            try:
                default_in = sd.default.device[0] if isinstance(sd.default.device, (list, tuple)) else None
                if default_in is not None and default_in not in dev_candidates:
                    dev_candidates.append(default_in)
            except Exception:
                pass
            try:
                for idx, d in enumerate(sd.query_devices()):
                    if d.get('max_input_channels', 0) > 0 and idx not in dev_candidates:
                        dev_candidates.append(idx)
            except Exception:
                pass

            # candidate samplerates: device default -> requested -> common 48000, 44100
            def _sr_list_for(dev):
                srs = []
                try:
                    di = sd.query_devices(dev, kind='input')
                    dsr = int(di.get('default_samplerate') or 0)
                    if dsr > 0:
                        srs.append(dsr)
                except Exception:
                    pass
                if self._sr not in srs:
                    srs.append(self._sr)
                for s in (48000, 44100):
                    if s not in srs:
                        srs.append(s)
                return srs

            # candidate channels: 1 then device max
            def _ch_list_for(dev):
                chs = [1]
                try:
                    di = sd.query_devices(dev, kind='input')
                    mx = int(di.get('max_input_channels') or 0)
                    if mx > 1:
                        chs.append(mx)
                except Exception:
                    pass
                return chs

            # Try with requested blocksize; if it fails broadly, try with automatic (None)
            stream = None
            last_exc = None
            for block_opt in (self._block, None):
                for dev in dev_candidates:
                    try:
                        s, used_sr, used_ch = _try_open(dev, _sr_list_for(dev), _ch_list_for(dev), block_opt)
                        stream = s
                        self._sr = int(used_sr)
                        self._ch = int(used_ch)
                        self._time_base = Fraction(1, self._sr)
                        self._block = int(self._sr * block_ms / 1000)
                        self._device = dev
                        break
                    except Exception as e:
                        last_exc = e
                        continue
                if stream is not None:
                    break

            if stream is None:
                raise last_exc or RuntimeError("Failed to open any input stream")

            self._stream = stream
            self._started = True
            # Inform which device config was selected
            try:
                lbl = sd.query_devices(self._device, kind='input')
                self._warn(f"Mic using: {lbl.get('name')} @ {self._sr} Hz, ch={self._ch}")
            except Exception:
                pass
        except Exception as e:
            self._started = False
            # Provide richer diagnostics with available devices and include the last error
            try:
                import sounddevice as sd  # type: ignore
                devs = sd.query_devices()
                lines = []
                for idx, d in enumerate(devs):
                    if d.get('max_input_channels', 0) > 0:
                        lines.append(f"{idx}: {d.get('name')} (default_sr={d.get('default_samplerate')})")
                listing = "\n".join(lines) if lines else "<no input devices found>"
                target = f" (requested device: {self._device})" if self._device is not None else ""
                self._warn(f"Microphone (sounddevice) not available{target}: {e}\nInputs:\n{listing}\nSet WHISPR_MIC_DEVICE to pick a device (index or name).")
            except Exception:
                self._warn(f"Microphone (sounddevice) not available: {e}")

    def _warn(self, msg: str):
        try:
            if callable(self._on_warning):
                self._on_warning(msg)
        except Exception:
            pass

    async def recv(self):  # type: ignore[override]
        # If we do not have a stream, produce silence frames to keep the pipeline alive
        if not self._started or av is None:
            await asyncio.sleep(self._block / self._sr)
            samples = _np.zeros(self._block, dtype=_np.int16)
        else:
            # Blocking get on a worker thread to avoid blocking the event loop
            try:
                samples = await asyncio.to_thread(self._q.get)
            except Exception:
                samples = _np.zeros(self._block, dtype=_np.int16)

        try:
            frame = av.AudioFrame.from_ndarray(samples, format="s16", layout="mono") if av else None
            if frame is None:
                # No av available; sleep and return a dummy by raising to end
                await asyncio.sleep(self._block / self._sr)
                raise asyncio.CancelledError
            frame.sample_rate = self._sr
            frame.pts = self._pts
            frame.time_base = self._time_base
            self._pts += int(samples.shape[0])
            return frame
        except Exception as e:
            # Keep pipeline alive even if frame conversion fails
            self._warn(f"Mic frame error: {e}")
            await asyncio.sleep(self._block / self._sr)
            # Generate silence frame if possible
            try:
                samples = _np.zeros(self._block, dtype=_np.int16)
                frame = av.AudioFrame.from_ndarray(samples, format="s16", layout="mono") if av else None
                if frame is None:
                    raise asyncio.CancelledError
                frame.sample_rate = self._sr
                frame.pts = self._pts
                frame.time_base = self._time_base
                self._pts += int(samples.shape[0])
                return frame
            except Exception:
                raise asyncio.CancelledError

    async def stop(self):  # type: ignore[override]
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
        except Exception:
            pass
