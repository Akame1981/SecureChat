import customtkinter as ctk
from datetime import datetime
from utils.recipients import get_recipient_name

def create_message_bubble(parent, sender_pub, text, my_pub_hex, pin, app=None, timestamp=None):
    display_sender = "You" if sender_pub == my_pub_hex else get_recipient_name(sender_pub, pin) or sender_pub
    is_you = display_sender == "You"

    theme = {}
    if app and hasattr(app, "theme_colors") and hasattr(app, "current_theme"):
        theme = app.theme_colors.get(app.current_theme, {})

    bubble_you = theme.get("bubble_you", "#7289da")
    bubble_other = theme.get("bubble_other", "#2f3136")
    text_color = theme.get("text", "white")

    bubble_color = bubble_you if is_you else bubble_other

    bubble_frame = ctk.CTkFrame(
        parent,
        fg_color=bubble_color,
        corner_radius=20
    )
    bubble_frame.is_you = is_you  # store for theme updates

    # Store labels for live updates
    bubble_frame.sender_label = ctk.CTkLabel(
        bubble_frame,
        text=f"{display_sender} • {datetime.fromtimestamp(timestamp).strftime('%H:%M') if timestamp else datetime.now().strftime('%H:%M')}",
        text_color=text_color,
        font=("Roboto", 10, "bold")
    )
    bubble_frame.sender_label.pack(anchor="w" if not is_you else "e", pady=(0,5), padx=20)

    bubble_frame.msg_label = ctk.CTkLabel(
        bubble_frame,
        text=text,
        wraplength=400,
        justify="left" if not is_you else "right",
        text_color=text_color,
        font=("Roboto", 12)
    )
    bubble_frame.msg_label.pack(anchor="w" if not is_you else "e", padx=20, pady=(0,10))

    bubble_frame.pack(anchor="w" if not is_you else "e", pady=8, padx=20, fill="x")

    # Auto-scroll
    parent._parent_canvas.update_idletasks()
    parent._parent_canvas.yview_moveto(1.0)

    return bubble_frame
