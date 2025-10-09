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

    # Delegate to ChatManager for optimistic UI + background send
    app.chat_manager.send(text)

    # Clear input box
    app.input_box.delete(0, "end")
