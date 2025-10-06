import customtkinter as ctk
from datetime import datetime
from utils.recipients import get_recipient_name

def create_message_bubble(parent, sender_pub, text, my_pub_hex, pin):
    """Create a styled message bubble in the parent container."""
    display_sender = "You" if sender_pub == my_pub_hex else get_recipient_name(sender_pub, pin) or sender_pub
    is_you = display_sender == "You"
    bubble_color = "#7289da" if is_you else "#2f3136"

    bubble_frame = ctk.CTkFrame(
        parent,
        fg_color=bubble_color,
        corner_radius=20
    )

    ts_str = datetime.now().strftime("%H:%M")  # You can pass timestamp if needed

    sender_label = ctk.CTkLabel(
        bubble_frame,
        text=f"{display_sender} • {ts_str}",
        text_color="white",
        font=("Roboto", 10, "bold")
    )
    sender_label.pack(anchor="w" if not is_you else "e", pady=(0,5), padx=20)

    msg_label = ctk.CTkLabel(
        bubble_frame,
        text=text,
        wraplength=400,
        justify="left" if not is_you else "right",
        text_color="white",
        font=("Roboto", 12)
    )
    msg_label.pack(anchor="w" if not is_you else "e", padx=20, pady=(0,10))

    bubble_frame.pack(anchor="w" if not is_you else "e", pady=8, padx=20, fill="x")

    # Auto-scroll
    parent._parent_canvas.update_idletasks()
    parent._parent_canvas.yview_moveto(1.0)

    return bubble_frame
