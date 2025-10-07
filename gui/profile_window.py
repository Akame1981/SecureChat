import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import qrcode
import io
import webbrowser
from datetime import datetime


from gui.identicon import generate_identicon

def short_fingerprint(key, chars=8):
    """Return a short fingerprint for easier display."""
    return key[:chars] + "..." + key[-chars:]

def open_profile(
    parent, 
    public_key, 
    signing_key, 
    copy_pub_callback, 
    messages_sent=0, 
    messages_received=0, 
    last_login=None,
    username="Anonymous"
):
    """Open a modern profile window with QR code, identicon, analytics, and share options."""

    profile_win = ctk.CTkToplevel(parent)
    profile_win.title("Your Profile")
    profile_win.geometry("400x650")
    profile_win.minsize(360, 600)
    profile_win.configure(fg_color="#181926")

    # --- Scrollable main frame ---
    scroll_frame = ctk.CTkScrollableFrame(profile_win, fg_color="#181926", corner_radius=0)
    scroll_frame.pack(fill="both", expand=True)

    # --- Header Frame ---
    header = ctk.CTkFrame(scroll_frame, fg_color="#23243a", corner_radius=0)
    header.pack(fill="x", pady=(0, 0), padx=0)

    # --- Identicon avatar ---
    avatar_img = generate_identicon(public_key, size=96)
    avatar_tk = ImageTk.PhotoImage(avatar_img)
    avatar_label = tk.Label(header, image=avatar_tk, bg="#23243a", bd=0)
    avatar_label.image = avatar_tk
    avatar_label.pack(pady=(24, 8))

    # --- Username ---
    ctk.CTkLabel(
        header,
        text=username,
        font=("Segoe UI", 18, "bold"),
        text_color="#4a90e2",
        fg_color="transparent"
    ).pack(pady=(0, 2))

    # --- Fingerprint ---
    ctk.CTkLabel(
        header,
        text=f"ID: {short_fingerprint(public_key, 10)}",
        font=("Segoe UI", 12, "bold"),
        text_color="#b2b8d6",
        fg_color="transparent"
    ).pack(pady=(0, 10))

    # --- Copy Public Key button ---
    ctk.CTkButton(
        header, text="Copy Public Key", command=copy_pub_callback,
        fg_color="#4a90e2", hover_color="#357ABD", width=180, height=36, corner_radius=16
    ).pack(pady=(0, 18))

    # --- Last Login (optional) ---
    if last_login:
        last_login_str = last_login if isinstance(last_login, str) else last_login.strftime("%Y-%m-%d %H:%M:%S")
        ctk.CTkLabel(
            header,
            text=f"Last Login: {last_login_str}",
            font=("Segoe UI", 12),
            text_color="#b2b8d6",
            fg_color="transparent"
        ).pack(pady=(0, 10))

    # --- Keys Frame ---
    keys_frame = ctk.CTkFrame(scroll_frame, fg_color="#23243a", corner_radius=16)
    keys_frame.pack(pady=(18, 0), padx=24, fill="x")

    ctk.CTkLabel(keys_frame, text="Public Key", font=("Segoe UI", 12, "bold"), text_color="#b2b8d6").pack(anchor="w", padx=10, pady=(10, 0))
    pub_entry = ctk.CTkEntry(keys_frame, width=340)
    pub_entry.insert(0, public_key)
    pub_entry.configure(state="readonly")
    pub_entry.pack(padx=10, pady=(0, 8), fill="x")

    ctk.CTkLabel(keys_frame, text="Signing Key", font=("Segoe UI", 12, "bold"), text_color="#b2b8d6").pack(anchor="w", padx=10, pady=(0, 0))
    sign_entry = ctk.CTkEntry(keys_frame, width=340)
    sign_entry.insert(0, signing_key)
    sign_entry.configure(state="readonly")
    sign_entry.pack(padx=10, pady=(0, 10), fill="x")

    # --- QR Code Frame ---
    qr_frame = ctk.CTkFrame(scroll_frame, fg_color="#23243a", corner_radius=16)
    qr_frame.pack(pady=(18, 0), padx=24, fill="x")

    ctk.CTkLabel(qr_frame, text="Scan to Add", font=("Segoe UI", 13, "bold"), text_color="#4a90e2").pack(pady=(10, 0))

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=4
    )
    qr.add_data(public_key)
    qr.make(fit=True)
    pil_img = qr.make_image(fill_color="#4a90e2", back_color="white").convert("RGB")

    qr_img_tk = ImageTk.PhotoImage(pil_img)
    qr_label = tk.Label(qr_frame, bg="#23243a", image=qr_img_tk)
    qr_label.image = qr_img_tk
    qr_label.pack(pady=10)

    # --- Export / Share buttons frame ---
    btn_frame = ctk.CTkFrame(qr_frame, fg_color="transparent")
    btn_frame.pack(pady=(0, 10))

    def save_qr():
        filename = f"{short_fingerprint(public_key, 6)}_qr.png"
        pil_img.save(filename)
        profile_win.clipboard_clear()
        profile_win.clipboard_append(filename)
        profile_win.update()
        ctk.CTkLabel(qr_frame, text=f"QR saved as {filename}", text_color="#4a90e2").pack(pady=2)

    ctk.CTkButton(btn_frame, text="Save QR", command=save_qr, width=100, fg_color="#4a90e2").pack(side="left", padx=5)

    def copy_qr(event=None):
        output = io.BytesIO()
        pil_img.save(output, format="PNG")
        profile_win.clipboard_clear()
        profile_win.clipboard_append(output.getvalue())
        profile_win.update()
        ctk.CTkLabel(qr_frame, text="QR code copied to clipboard", text_color="#4a90e2").pack(pady=2)

    qr_label.bind("<Button-1>", copy_qr)

    def share_email():
        subject = "My Public Key"
        body = f"Here is my public key:\n\n{public_key}"
        webbrowser.open(f"mailto:?subject={subject}&body={body}")

    ctk.CTkButton(btn_frame, text="Share via Email", command=share_email, width=120, fg_color="#4a90e2").pack(side="left", padx=5)

    # --- Footer ---
    ctk.CTkLabel(
        scroll_frame,
        text="Tip: Click the QR code to copy it.\nShare your public key to receive messages.",
        font=("Segoe UI", 10),
        text_color="#b2b8d6",
        fg_color="transparent"
    ).pack(pady=(10, 8))




