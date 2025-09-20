import json
import os

# Ensure data folder exists
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")
os.makedirs(DATA_DIR, exist_ok=True)

# Path to recipients.json in data folder
RECIPIENTS_FILE = os.path.join(DATA_DIR, "recipients.json")

# Load existing recipients or start empty
if os.path.exists(RECIPIENTS_FILE):
    with open(RECIPIENTS_FILE, "r") as f:
        recipients = json.load(f)
else:
    recipients = {}

# Save recipients to JSON
def save_recipients():
    with open(RECIPIENTS_FILE, "w") as f:
        json.dump(recipients, f, indent=4)

# Add a recipient
def add_recipient(name: str, pub_key: str):
    recipients[name] = pub_key
    save_recipients()

# Delete a recipient
def delete_recipient(name: str):
    if name in recipients:
        del recipients[name]
        save_recipients()

# Get a recipient's public key
def get_recipient_key(name: str):
    return recipients.get(name)
