from __future__ import annotations

import asyncio
import threading

import numpy as np
import sounddevice as sd

try:
    from PIL import Image, ImageTk
except Exception:  # pillow optional for video rendering
    Image = None  # type: ignore
    ImageTk = None  # type: ignore


class AudioPlayer:
    """Consume an aiortc audio track and play via sounddevice in an asyncio task."""

    def __init__(self, sample_rate: int = 48000):
        self._sample_rate = sample_rate
        self._stream = None
        self._task = None

    async def _runner(self, track):
        # Lazy create stream with parameters from frames if available
        self._stream = sd.OutputStream(samplerate=self._sample_rate, channels=1, dtype="int16")
        self._stream.start()
        try:
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
