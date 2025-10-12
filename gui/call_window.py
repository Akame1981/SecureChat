import customtkinter as ctk
from utils.rtc_media import (
    list_audio_input_devices,
    list_audio_output_devices,
    list_video_devices,
    get_audio_debug_info,
)

class CallWindow(ctk.CTkToplevel):
    def __init__(self, app, title="Call"):
        super().__init__(app)
        self.app = app
        self.title(title)
        self.geometry("420x360")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.video_label = ctk.CTkLabel(self, text="Video")
        self.video_label.pack(fill="both", expand=True, padx=8, pady=8)

        # Device selectors
        sel_frame = ctk.CTkFrame(self)
        sel_frame.pack(fill="x", padx=8, pady=(0,8))
        try:
            ctk.CTkLabel(sel_frame, text="Mic:").pack(side="left", padx=(6,4))
            mic_vals = [label for _, label in list_audio_input_devices()]
            self._mic_choice = ctk.CTkComboBox(sel_frame, values=mic_vals, width=180)
            self._mic_choice.set(mic_vals[0] if mic_vals else "default")
            self._mic_choice.pack(side="left", padx=(0,8))
        except Exception:
            self._mic_choice = None
        try:
            ctk.CTkLabel(sel_frame, text="Speaker:").pack(side="left", padx=(6,4))
            spk_vals = [label for _, label in list_audio_output_devices()]
            self._spk_choice = ctk.CTkComboBox(sel_frame, values=spk_vals, width=180)
            self._spk_choice.set(spk_vals[0] if spk_vals else "default")
            self._spk_choice.pack(side="left", padx=(0,8))
        except Exception:
            self._spk_choice = None
        try:
            ctk.CTkLabel(sel_frame, text="Camera:").pack(side="left", padx=(6,4))
            cams = list_video_devices() or ["/dev/video0", "none"]
            self._cam_choice = ctk.CTkComboBox(sel_frame, values=cams, width=160)
            self._cam_choice.set(cams[0] if cams else "/dev/video0")
            self._cam_choice.pack(side="left", padx=(0,8))
        except Exception:
            self._cam_choice = None

        def _refresh_devices():
            try:
                # Re-query devices and repopulate combos
                if self._mic_choice:
                    mic_vals = [label for _, label in list_audio_input_devices()]
                    self._mic_choice.configure(values=mic_vals)
                    if mic_vals:
                        self._mic_choice.set(mic_vals[0])
                if self._spk_choice:
                    spk_vals = [label for _, label in list_audio_output_devices()]
                    self._spk_choice.configure(values=spk_vals)
                    if spk_vals:
                        self._spk_choice.set(spk_vals[0])
                if self._cam_choice:
                    cams = list_video_devices() or ["/dev/video0", "none"]
                    self._cam_choice.configure(values=cams)
                    if cams:
                        self._cam_choice.set(cams[0])
                try:
                    if hasattr(self.app, 'notifier'):
                        self.app.notifier.show('Devices refreshed', type_='info')
                except Exception:
                    pass
            except Exception:
                pass

        def _apply_devices():
            try:
                if hasattr(self.app, 'rtc'):
                    # Mic
                    if self._mic_choice:
                        sel = self._mic_choice.get()
                        dev = None
                        try:
                            # Extract leading index before ':' if present
                            idx = int(sel.split(':',1)[0].strip())
                            dev = idx
                        except Exception:
                            dev = None if sel == 'default' or sel.startswith('env: ') else sel
                        self.app.rtc.set_mic_device(dev)
                    # Speaker
                    if self._spk_choice:
                        sel = self._spk_choice.get()
                        dev = None
                        try:
                            idx = int(sel.split(':',1)[0].strip())
                            dev = idx
                        except Exception:
                            dev = None if sel == 'default' or sel.startswith('env: ') else sel
                        self.app.rtc.set_speaker_device(dev)
                    # Camera
                    if self._cam_choice:
                        cam = self._cam_choice.get()
                        if cam and cam != 'none':
                            self.app.rtc.set_camera_device(cam)
                        else:
                            self.app.rtc.set_camera_device(None)
                    try:
                        if hasattr(self.app, 'notifier'):
                            self.app.notifier.show('Devices applied. New selections take effect for new media or next call.', type_='info')
                    except Exception:
                        pass
            except Exception:
                pass

        try:
            ctk.CTkButton(sel_frame, text="Apply", command=_apply_devices).pack(side="right", padx=6)
        except Exception:
            pass
        try:
            ctk.CTkButton(sel_frame, text="Refresh", command=_refresh_devices).pack(side="right", padx=6)
        except Exception:
            pass
        
        def _show_audio_debug():
            try:
                info = get_audio_debug_info()
            except Exception as e:
                info = f"Error: {e}"
            # Show in a simple modal window
            win = ctk.CTkToplevel(self)
            win.title("Audio debug")
            win.geometry("560x360")
            txt = ctk.CTkTextbox(win, wrap="word")
            txt.pack(fill="both", expand=True, padx=8, pady=8)
            try:
                txt.insert("1.0", info)
            except Exception:
                pass
            try:
                txt.configure(state="disabled")
            except Exception:
                pass
        try:
            ctk.CTkButton(sel_frame, text="Audio debug", command=_show_audio_debug).pack(side="right", padx=6)
        except Exception:
            pass

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=8, pady=8)

        self.hang_btn = ctk.CTkButton(btn_frame, text="Hang up", fg_color="#d9534f", command=self._on_hang)
        self.hang_btn.pack(side="right", padx=6)

    def _on_hang(self):
        try:
            self.app.rtc.hangup()
        except Exception:
            pass
        self.destroy()

    def _on_close(self):
        self._on_hang()
