import tkinter as tk
import customtkinter as ctk


class CTkConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="Confirm", message="Are you sure?"):
        super().__init__(parent)
        self.title(title)
        self.geometry("350x150")
        self.configure(bg="#1e1e2f")
        self.transient(parent)
        # Try grabbing input for modal behavior. On some Linux WMs this can
        # fail with "grab failed: window not viewable" if the parent isn't
        # currently mapped. Try once and schedule a retry if needed.
        try:
            try:
                self.grab_set()
            except Exception:
                try:
                    if getattr(parent, "winfo_viewable", None) and not parent.winfo_viewable():
                        def _retry():
                            try:
                                if getattr(self, "winfo_exists", None) and self.winfo_exists():
                                    self.grab_set()
                            except Exception:
                                pass
                        try:
                            self.after(150, _retry)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        self.resizable(False, False)

        self.result = False
        ctk.CTkLabel(self, text=message, font=("Roboto", 14), text_color="white", wraplength=300).pack(pady=(30, 10), padx=10)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="Yes", command=self.yes, fg_color="#4a90e2").pack(side="left", padx=5, expand=True, fill="x")
        ctk.CTkButton(btn_frame, text="No", command=self.no, fg_color="#d9534f").pack(side="left", padx=5, expand=True, fill="x")

        self.bind("<Return>", lambda e: self.yes())
        self.bind("<Escape>", lambda e: self.no())

        self.wait_window()

    def yes(self):
        self.result = True
        self.destroy()

    def no(self):
        self.result = False
        self.destroy()


class CTkDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="Input", label="Enter value:", show=None, initial_value=""):
        super().__init__(parent)
        self.title(title)
        self.geometry("350x150")
        self.configure(bg="#1e1e2f")
        self.transient(parent)
        try:
            try:
                self.grab_set()
            except Exception:
                try:
                    if getattr(parent, "winfo_viewable", None) and not parent.winfo_viewable():
                        def _retry():
                            try:
                                if getattr(self, "winfo_exists", None) and self.winfo_exists():
                                    self.grab_set()
                            except Exception:
                                pass
                        try:
                            self.after(150, _retry)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
        self.resizable(False, False)

        self.result = None

        ctk.CTkLabel(self, text=label, font=("Roboto", 14), text_color="white").pack(pady=(20, 5))
        self.entry_var = tk.StringVar(value=initial_value)
        self.entry = ctk.CTkEntry(self, textvariable=self.entry_var, show=show, width=250)
        self.entry.pack(pady=5)
        self.entry.focus()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        ctk.CTkButton(btn_frame, text="OK", command=self.ok, fg_color="#4a90e2").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Cancel", command=self.cancel, fg_color="#d9534f").pack(side="left", padx=5)

        self.bind("<Return>", lambda e: self.ok())
        self.bind("<Escape>", lambda e: self.cancel())

        self.wait_window()

    def ok(self):
        self.result = self.entry_var.get()
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()
