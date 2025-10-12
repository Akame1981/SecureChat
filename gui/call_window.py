import customtkinter as ctk

class CallWindow(ctk.CTkToplevel):
    def __init__(self, app, title="Call"):
        super().__init__(app)
        self.app = app
        self.title(title)
        self.geometry("420x360")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.video_label = ctk.CTkLabel(self, text="Video")
        self.video_label.pack(fill="both", expand=True, padx=8, pady=8)

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
