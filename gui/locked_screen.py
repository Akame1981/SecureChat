import customtkinter as ctk
import tkinter as tk


def show_locked_screen(app):
    """Create and show a modern locked screen inside the provided app instance.

    Returns the created frame and also attaches it to `app.lock_frame` so callers
    can remove it later (for example after successful unlock).
    """
    # Full-screen background frame
    lock_frame = ctk.CTkFrame(app, fg_color="#0f1720")
    lock_frame.pack(fill="both", expand=True)

    # Center container (card)
    container = ctk.CTkFrame(lock_frame, fg_color="#11121a", corner_radius=16)
    container.place(relx=0.5, rely=0.45, anchor="center", width=640, height=360)

    # Large lock icon in a circular badge
    badge = ctk.CTkFrame(container, width=96, height=96, corner_radius=48, fg_color="#1f2937")
    badge.place(relx=0.5, y=40, anchor="n")
    icon = ctk.CTkLabel(badge, text="🔒", font=("Segoe UI Emoji", 28), text_color="#7dd3fc", fg_color="transparent")
    icon.place(relx=0.5, rely=0.5, anchor="center")

    # Title & subtitle
    title = ctk.CTkLabel(container, text="Whispr is locked", font=("Segoe UI", 20, "bold"), text_color="#e6eef8")
    title.place(relx=0.5, y=150, anchor="n")
    subtitle = ctk.CTkLabel(container, text="Unlock your account to continue.", font=("Segoe UI", 12), text_color="#94a3b8")
    subtitle.place(relx=0.5, y=186, anchor="n")

    # Optional quick unlock entry (non-mandatory; app._try_unlock handles unlocking)
    pin_var = tk.StringVar()
    pin_entry = ctk.CTkEntry(container, textvariable=pin_var, placeholder_text="Enter PIN or press Unlock", width=360)
    pin_entry.place(relx=0.5, y=220, anchor="n")

    # Buttons row
    btns = ctk.CTkFrame(container, fg_color="transparent")
    btns.place(relx=0.5, y=276, anchor="n")

    # Unlock -> call app._try_unlock (keeps unlock behavior inside app)
    def _unlock_action(event=None):
        # If the app._try_unlock accepts an optional PIN value, pass it (best-effort)
        try:
            val = pin_var.get().strip()
            if val:
                try:
                    app._try_unlock(val)
                except TypeError:
                    app._try_unlock()
            else:
                app._try_unlock()
        except Exception:
            try:
                app._try_unlock()
            except Exception:
                pass

    unlock_btn = ctk.CTkButton(btns, text="Unlock", width=140, corner_radius=10, fg_color="#06b6d4", hover_color="#0891b2", command=_unlock_action)
    unlock_btn.pack(side="left", padx=10)

    # Settings -> use app.open_settings wrapper
    settings_btn = ctk.CTkButton(btns, text="Settings", width=120, corner_radius=10, fg_color="#334155", hover_color="#1f2937", command=app.open_settings)
    settings_btn.pack(side="left", padx=10)

    # Quit -> close the app (danger style)
    quit_btn = ctk.CTkButton(btns, text="Quit", width=120, corner_radius=10, fg_color="#ef4444", hover_color="#dc2626", command=app.on_close)
    quit_btn.pack(side="left", padx=10)

    # Small footer
    footer = ctk.CTkLabel(container, text="Your data is end-to-end encrypted and stored locally.", font=("Segoe UI", 10), text_color="#64748b")
    footer.place(relx=0.5, y=328, anchor="n")

    # Bind Enter key to unlock action for convenience
    try:
        lock_frame.bind_all("<Return>", _unlock_action)
    except Exception:
        pass

    # Focus the entry for quick typing
    try:
        pin_entry.focus_set()
    except Exception:
        pass

    # Attach to app for removal by the caller
    try:
        app.lock_frame = lock_frame
    except Exception:
        pass

    return lock_frame
