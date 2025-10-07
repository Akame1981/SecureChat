import os
from utils.crypto import KEY_FILE, PrivateKey, SigningKey, load_key, save_key
from tkinter.simpledialog import askstring

def init_keypair(notifier, pin_dialog_cls, parent):
    """
    Initialize or load a keypair.
    Returns (private_key, signing_key, pin, username) or None if cancelled.
    """
    if os.path.exists(KEY_FILE):
        dlg = pin_dialog_cls(parent, "Enter PIN to unlock keypair")
        parent.wait_window(dlg)
        pin = dlg.pin
        if not pin:
            return None

        try:
            private_key, signing_key, username = load_key(pin)
        except ValueError:
            notifier.show("Incorrect PIN or corrupted key!", type_="error")
            return None
    else:
        dlg = pin_dialog_cls(parent, "Set a new PIN", new_pin=True)
        parent.wait_window(dlg)
        pin = dlg.pin
        if not pin:
            return None

        # Get username from dialog (default handled in dialog)
        username = getattr(dlg, "username", None)
        if not username:
            username = "Anonymous"

        private_key = PrivateKey.generate()
        signing_key = SigningKey.generate()
        save_key(private_key, signing_key, pin, username)
        notifier.show("New keypair generated!", type_="success")

    return private_key, signing_key, pin, username
