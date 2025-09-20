import json
import os

RECIPIENTS_FILE = "recipients.json"

if os.path.exists(RECIPIENTS_FILE):
    with open(RECIPIENTS_FILE, "r") as f:
        recipients = json.load(f)
else:
    recipients = {}

def save_recipients():
    with open(RECIPIENTS_FILE, "w") as f:
        json.dump(recipients, f, indent=4)

def add_recipient(name: str, pub_key: str):
    recipients[name] = pub_key
    save_recipients()

def delete_recipient(name: str):
    if name in recipients:
        del recipients[name]
        save_recipients()

def get_recipient_key(name: str):
    return recipients.get(name)
