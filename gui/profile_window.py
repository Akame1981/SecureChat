import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
import qrcode
import hashlib
import io
import webbrowser
from datetime import datetime

def generate_identicon(data, size=64, block_size=8):
    """Generate a simple identicon (square pattern) from data."""
    hash_bytes = hashlib.md5(data.encode()).digest()
    img = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(img)
    for y in range(0, size, block_size):
        for x in range(0, size, block_size):
            idx = ((y//block_size)*size//block_size + (x//block_size)) % len(hash_bytes)
            if hash_bytes[idx] % 2 == 0:
                draw.rectangle([x, y, x+block_size-1, y+block_size-1], fill="black")
    return img

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
    
    profile_win = tk.Toplevel(parent)
    profile_win.title("Your Profile")
    profile_win.configure(bg="#1e1e2f")
    profile_win.geometry("360x550")
    profile_win.minsize(320, 500)

    # --- Title ---
    tk.Label(
        profile_win,
        text="🕵️ Your Profile",
        font=("Arial", 16, "bold"),
        bg="#1e1e2f",
        fg="white"
    ).pack(pady=10)

    # --- Username ---
    tk.Label(
        profile_win,
        text=f"Username: {username}",
        font=("Arial", 13, "bold"),
        bg="#1e1e2f",
        fg="#4a90e2"
    ).pack(pady=(0, 6))

    # --- Identicon avatar ---
    avatar_img = generate_identicon(public_key, size=80)
    avatar_tk = ImageTk.PhotoImage(avatar_img)
    avatar_label = tk.Label(profile_win, image=avatar_tk, bg="#1e1e2f")
    avatar_label.image = avatar_tk
    avatar_label.pack(pady=5)

    # --- Keys ---
    tk.Label(
        profile_win,
        text=f"Public Key:\n{short_fingerprint(public_key)}",
        wraplength=320,
        bg="#1e1e2f",
        fg="white"
    ).pack(pady=2)

    tk.Label(
        profile_win,
        text=f"Signing Key:\n{short_fingerprint(signing_key)}",
        wraplength=320,
        bg="#1e1e2f",
        fg="white"
    ).pack(pady=2)

    # --- Copy Public Key button ---
    ctk.CTkButton(profile_win, text="Copy Public Key", command=copy_pub_callback).pack(pady=5)

    # --- Analytics / Stats ---
    stats_frame = ctk.CTkFrame(profile_win, fg_color="#2a2a3a", corner_radius=10)
    stats_frame.pack(pady=10, padx=10, fill="x")

    tk.Label(stats_frame, text=f"Messages Sent: {messages_sent}", bg="#2a2a3a", fg="white").pack(pady=2)
    tk.Label(stats_frame, text=f"Messages Received: {messages_received}", bg="#2a2a3a", fg="white").pack(pady=2)
    if last_login:
        last_login_str = last_login if isinstance(last_login, str) else last_login.strftime("%Y-%m-%d %H:%M:%S")
        tk.Label(stats_frame, text=f"Last Login: {last_login_str}", bg="#2a2a3a", fg="white").pack(pady=2)

    # --- QR Code ---
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2
    )
    qr.add_data(public_key)
    qr.make(fit=True)
    pil_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    qr_label = tk.Label(profile_win, bg="#1e1e2f")
    qr_label.pack(pady=10, expand=True)

    # --- Export / Share buttons frame ---
    btn_frame = ctk.CTkFrame(profile_win, fg_color="transparent")
    btn_frame.pack(pady=5)

    # Save QR button
    def save_qr():
        filename = f"{short_fingerprint(public_key, 6)}_qr.png"
        pil_img.save(filename)
        print(f"QR saved as {filename}")

    ctk.CTkButton(btn_frame, text="Save QR", command=save_qr, width=100).pack(side="left", padx=5)

    # Copy QR on click
    def copy_qr(event=None):
        profile_win.clipboard_clear()
        output = io.BytesIO()
        pil_img.save(output, format="PNG")
        profile_win.clipboard_append(output.getvalue())
        profile_win.update()
        print("QR code copied to clipboard")

    qr_label.bind("<Button-1>", copy_qr)

    # Share via email
    def share_email():
        subject = "My Public Key"
        body = f"Here is my public key:\n\n{public_key}"
        webbrowser.open(f"mailto:?subject={subject}&body={body}")

    ctk.CTkButton(btn_frame, text="Share via Email", command=share_email, width=120).pack(side="left", padx=5)

    # --- Resize QR dynamically ---
    def resize_qr(event=None):
        max_size = min(profile_win.winfo_width() - 40, profile_win.winfo_height() - 350)
        if max_size <= 0:
            return
        resized_img = pil_img.resize((max_size, max_size), Image.NEAREST)
        qr_img_tk = ImageTk.PhotoImage(resized_img)
        qr_label.configure(image=qr_img_tk)
        qr_label.image = qr_img_tk

    profile_win.bind("<Configure>", resize_qr)
    profile_win.update_idletasks()
    resize_qr()
