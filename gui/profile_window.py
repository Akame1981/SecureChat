import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import qrcode
import io

def open_profile(parent, public_key, signing_key, copy_pub_callback):
    """Open a popup showing user profile information with QR code for public key at natural size."""
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

    # Generate QR code for the public key
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,  
        border=2,
    )
    qr.add_data(public_key)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

   
    qr_img_tk = ImageTk.PhotoImage(img)

    # Display QR code
    qr_label = tk.Label(profile_win, image=qr_img_tk, bg="#1e1e2f")
    qr_label.image = qr_img_tk 
    qr_label.pack(pady=10)
