import customtkinter as ctk

class CallInviteWindow(ctk.CTkToplevel):
    def __init__(self, app, from_name: str, call_id: str, from_pub: str):
        super().__init__(app)
        self.app = app
        self.call_id = call_id
        self.from_pub = from_pub
        self.title("Incoming call")
        self.geometry("320x160")
        self.protocol("WM_DELETE_WINDOW", self._decline)

        label = ctk.CTkLabel(self, text=f"Call from {from_name}")
        label.pack(pady=16)

        btns = ctk.CTkFrame(self)
        btns.pack(fill="x", padx=12, pady=12)

        accept = ctk.CTkButton(btns, text="Accept", fg_color="#5cb85c", command=self._accept)
        accept.pack(side="left", expand=True, fill="x", padx=6)

        decline = ctk.CTkButton(btns, text="Decline", fg_color="#d9534f", command=self._decline)
        decline.pack(side="left", expand=True, fill="x", padx=6)

    def _accept(self):
        try:
            from gui.call_window import CallWindow
            from utils.rtc_manager import RTCManager
            if not hasattr(self.app, 'rtc'):
                self.app.rtc = RTCManager(self.app)
            cw = CallWindow(self.app, title="In call")
            self.app.rtc.answer_call(self.call_id, cw.video_label, self.from_pub)
        except Exception as e:
            print("accept call error", e)
            try:
                self.app.notifier.show("Failed to accept call", type_="error")
            except Exception:
                pass
        finally:
            self.destroy()

    def _decline(self):
        try:
            # Optionally send a decline signal via chat
            pass
        except Exception:
            pass
        self.destroy()
