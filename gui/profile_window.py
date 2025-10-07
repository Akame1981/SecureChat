import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import qrcode
import io

def open_profile(parent, public_key, signing_key, copy_pub_callback):
    """Open a popup showing user profile information with dynamically fitting QR code."""
    profile_win = tk.Toplevel(parent)
    profile_win.title("Your Profile")
    profile_win.configure(bg="#1e1e2f")

    # Title
    tk.Label(
        profile_win,
        text="🕵️ Your Profile",
        font=("Arial", 14, "bold"),
        bg="#1e1e2f",
        fg="white"
    ).pack(pady=10)

    # Public key
    tk.Label(
        profile_win,
        text=f"Public Key:\n{public_key}",
        wraplength=300,
        bg="#1e1e2f",
        fg="white"
    ).pack(pady=5)

    # Signing key
    tk.Label(
        profile_win,
        text=f"Signing Key:\n{signing_key}",
        wraplength=300,
        bg="#1e1e2f",
        fg="white"
    ).pack(pady=5)

    # Button to copy public key
    ctk.CTkButton(profile_win, text="Copy Public Key", command=copy_pub_callback).pack(pady=10)

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(public_key)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to PIL image
    pil_img = img.convert("RGB")
    qr_label = tk.Label(profile_win, bg="#1e1e2f")
    qr_label.pack(pady=10, expand=True)

    # Function to resize QR dynamically
    def resize_qr(event=None):
        # Determine the max size (fit width or height minus padding)
        max_size = min(profile_win.winfo_width()-20, profile_win.winfo_height()-150)
        if max_size <= 0:
            return
        # Resize using NEAREST to keep QR sharp
        resized_img = pil_img.resize((max_size, max_size), Image.NEAREST)
        qr_img_tk = ImageTk.PhotoImage(resized_img)
        qr_label.configure(image=qr_img_tk)
        qr_label.image = qr_img_tk

    # Bind resizing
    profile_win.bind("<Configure>", resize_qr)
    profile_win.update_idletasks()  # trigger initial resize
    resize_qr()
