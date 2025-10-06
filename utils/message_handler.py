from utils.chat_storage import save_message
from utils.network import send_message
from time import time

def handle_send(app):
    """
    Handles sending a message from the input box.
    'app' is the WhisprApp instance.
    """
    text = app.input_box.get().strip()
    if not text:
        return

    # Handle special commands
    if text.startswith("/new"):
        app.add_new_recipient()
        app.input_box.delete(0, "end")
        return
    if text.startswith("/choose"):
        app.choose_recipient()
        app.input_box.delete(0, "end")
        return

    # No recipient selected
    if not app.recipient_pub_hex:
        app.notifier.show("Select a recipient first", type_="warning")
        return

    # Send the message
    if send_message(
        app,
        to_pub=app.recipient_pub_hex,
        signing_pub=app.signing_pub_hex,
        text=text,
        signing_key=app.signing_key,
        enc_pub=app.my_pub_hex
    ):
        # Display the message locally
        app.display_message(app.my_pub_hex, text)

        # Save message locally
        save_message(app.recipient_pub_hex, "You", text, app.pin, timestamp=time())

    # Clear input box
    app.input_box.delete(0, "end")
