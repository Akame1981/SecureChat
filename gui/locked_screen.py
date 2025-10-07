import customtkinter as ctk


def show_locked_screen(app):
    """Create and show a locked screen inside the provided app instance.

    This assigns the created frame to `app.lock_frame` so callers can remove
    it later (for example after successful unlock).
    """
    lock_frame = ctk.CTkFrame(app, fg_color="#1b1b2a")
    lock_frame.pack(fill="both", expand=True, padx=20, pady=40)

    ctk.CTkLabel(lock_frame, text="Whispr is locked", font=("Segoe UI", 18, "bold"), text_color="white").pack(pady=(20,10))
    ctk.CTkLabel(lock_frame, text="Unlock your account to continue.", font=("Segoe UI", 12), text_color="gray70").pack(pady=(0,20))

    btns = ctk.CTkFrame(lock_frame, fg_color="transparent")
    btns.pack(pady=10)

    # Unlock -> call app._try_unlock (keeps unlock behavior inside app)
    ctk.CTkButton(btns, text="Unlock", fg_color="#4a90e2", command=lambda: app._try_unlock(), width=120).pack(side="left", padx=8)
    # Settings -> use app.open_settings wrapper
    ctk.CTkButton(btns, text="Settings", fg_color="#4a90e2", command=app.open_settings, width=120).pack(side="left", padx=8)
    # Quit -> close the app
    ctk.CTkButton(btns, text="Quit", fg_color="#d9534f", command=app.on_close, width=120).pack(side="left", padx=8)

    # Attach to app for removal by the caller
    try:
        app.lock_frame = lock_frame
    except Exception:
        pass

    return lock_frame
