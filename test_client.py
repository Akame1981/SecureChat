import os
import json
import requests
from nacl.public import PrivateKey, SealedBox, PublicKey
import base64
import threading
import time
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox, Toplevel
from nacl.secret import SecretBox
from nacl.utils import random
from nacl.exceptions import CryptoError
import hashlib



SERVER_URL = "http://127.0.0.1:8000"
KEY_FILE = "keypair.bin"
RECIPIENTS_FILE = "recipients.json"

# --- Persistent keypair ---
# --- Helper functions ---
def derive_key(pin: str) -> bytes:
    """Derive a 32-byte key from the pincode using SHA-256"""
    return hashlib.sha256(pin.encode()).digest()

def save_key(private_key: PrivateKey, pin: str):
    key = derive_key(pin)
    box = SecretBox(key)
    encrypted = box.encrypt(private_key.encode())
    with open(KEY_FILE, "wb") as f:
        f.write(encrypted)

def load_key(pin: str) -> PrivateKey:
    key = derive_key(pin)
    box = SecretBox(key)
    with open(KEY_FILE, "rb") as f:
        encrypted = f.read()
    try:
        decrypted = box.decrypt(encrypted)
        return PrivateKey(decrypted)
    except CryptoError:
        raise ValueError("Incorrect pincode or corrupted key file!")

def load_keypair_gui():
    """GUI version: ask for pincode via Tkinter simpledialog"""
    global private_key, public_key, my_pub_hex
    if os.path.exists(KEY_FILE):
        pin = simpledialog.askstring("Unlock Keypair", "Enter your pincode:", show="*")
        if pin is None:
            root.destroy()
            return
        try:
            private_key = load_key(pin)
        except ValueError:
            messagebox.showerror("Error", "Incorrect pincode or corrupted key file!")
            root.destroy()
            return
    else:
        pin = simpledialog.askstring("Set Pincode", "Set a new pincode for your keypair:", show="*")
        if pin is None:
            root.destroy()
            return
        private_key = PrivateKey.generate()
        save_key(private_key, pin)
        messagebox.showinfo("Keypair Created", "New keypair generated and encrypted with your pincode!")

    public_key = private_key.public_key
    my_pub_hex = public_key.encode().hex()



load_keypair_gui()


# --- Load recipients ---
if os.path.exists(RECIPIENTS_FILE):
    with open(RECIPIENTS_FILE, "r") as f:
        recipients = json.load(f)
else:
    recipients = {}

def save_recipients():
    with open(RECIPIENTS_FILE, "w") as f:
        json.dump(recipients, f, indent=4)

recipient_pub_hex = None


# --- GUI ---
root = tk.Tk()
root.title("🔒 Secure Chat")
root.geometry("600x600")
root.configure(bg="#1e1e2f")  

# --- Public key frame ---
pub_frame = tk.Frame(root, bg="#2e2e3f", pady=5)
pub_frame.pack(fill=tk.X)
pub_label = tk.Label(pub_frame, text=f"My Public Key: {my_pub_hex}", fg="white", bg="#2e2e3f", wraplength=550, justify="left")
pub_label.pack(side=tk.LEFT, padx=10)

def copy_pub_key():
    root.clipboard_clear()
    root.clipboard_append(my_pub_hex)
    messagebox.showinfo("Copied", "Public key copied to clipboard!")

copy_button = tk.Button(pub_frame, text="Copy", command=copy_pub_key, bg="#4a4a6a", fg="white", relief="flat", padx=10)
copy_button.pack(side=tk.RIGHT, padx=10)

# --- Settings button ---
def open_settings():
    settings = Toplevel(root)
    settings.title("Settings")
    settings.geometry("400x300")
    settings.configure(bg="#1e1e2f")

    # Generate new key
    def new_key():
        if messagebox.askyesno("New Key", "This will generate a new keypair and replace the old one. Proceed?"):
            pin = simpledialog.askstring("Set Pincode", "Set a pincode for the new keypair:", show="*")
            if not pin:
                return
            global private_key, public_key, my_pub_hex
            private_key = PrivateKey.generate()
            save_key(private_key, pin)
            public_key = private_key.public_key
            my_pub_hex = public_key.encode().hex()
            pub_label.config(text=f"My Public Key: {my_pub_hex}")
            messagebox.showinfo("New Key", "New keypair generated and encrypted with your pincode!")


    tk.Button(settings, text="Generate New Keypair", command=new_key, bg="#4a90e2", fg="white", relief="flat", padx=10, pady=5).pack(pady=10)

    # Show current public key
    tk.Label(settings, text="Current Public Key:", bg="#1e1e2f", fg="white").pack()
    pub_display = tk.Text(settings, height=3, width=45, bg="#2e2e3f", fg="white")
    pub_display.insert(tk.END, my_pub_hex)
    pub_display.configure(state="disabled")
    pub_display.pack(pady=5)
    def change_pincode():
        old_pin = simpledialog.askstring("Current Pincode", "Enter your current pincode:", show="*")
        if not old_pin:
            return
        try:
            priv = load_key(old_pin)
        except ValueError:
            messagebox.showerror("Error", "Incorrect current pincode!")
            return
        new_pin = simpledialog.askstring("New Pincode", "Enter new pincode:", show="*")
        if not new_pin:
            return
        save_key(priv, new_pin)
        messagebox.showinfo("Pincode Changed", "Your pincode has been updated successfully!")
    tk.Button(settings, text="Change Pincode", command=change_pincode, bg="#4a90e2", fg="white", relief="flat", padx=10, pady=5).pack(pady=10)


    # Manage recipients
    def show_recipients():
        rec_window = Toplevel(settings)
        rec_window.title("Saved Recipients")
        rec_window.geometry("350x300")
        rec_window.configure(bg="#1e1e2f")

        listbox = tk.Listbox(rec_window, bg="#2e2e3f", fg="white")
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for name, key in recipients.items():
            listbox.insert(tk.END, f"{name}: {key}")

        def delete_selected():
            sel = listbox.curselection()
            if sel:
                entry = listbox.get(sel[0])
                name = entry.split(":")[0]
                if messagebox.askyesno("Delete Recipient", f"Delete {name}?"):
                    recipients.pop(name)
                    save_recipients()
                    listbox.delete(sel[0])

        tk.Button(rec_window, text="Delete Selected", command=delete_selected, bg="#d9534f", fg="white").pack(pady=5)

    tk.Button(settings, text="Manage Recipients", command=show_recipients, bg="#4a90e2", fg="white", relief="flat", padx=10, pady=5).pack(pady=10)

settings_button = tk.Button(pub_frame, text="Settings", command=open_settings, bg="#4a90e2", fg="white", relief="flat", padx=10)
settings_button.pack(side=tk.RIGHT, padx=10)

# --- Messages display ---
messages_box = scrolledtext.ScrolledText(root, width=70, height=25, state='disabled', bg="#2e2e3f", fg="white", wrap=tk.WORD, relief="flat")
messages_box.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# --- Input frame ---
input_frame = tk.Frame(root, bg="#1e1e2f")
input_frame.pack(fill=tk.X, padx=10, pady=(0,10))
input_box = tk.Entry(input_frame, width=50, bg="#3e3e50", fg="white", relief="flat", insertbackground="white")
input_box.pack(side=tk.LEFT, padx=(0,5), pady=5, ipady=5)

# --- Bind Enter key to send ---
input_box.bind("<Return>", lambda event: on_send())


# --- Recipient commands ---
def handle_commands(text):
    global recipient_pub_hex
    if text.startswith("/new"):
        add_new_recipient()
        input_box.delete(0, tk.END)
        return

    if text.startswith("/choose"):
        choose_recipient()
        input_box.delete(0, tk.END)
        return

    return False

def on_send():
    text = input_box.get().strip()
    if not text:
        return
    if handle_commands(text):
        input_box.delete(0, tk.END)
        return
    if recipient_pub_hex is None:
        
        return
    send_message(text)
    input_box.delete(0, tk.END)

send_button = tk.Button(input_frame, text="Send", command=on_send, bg="#4a90e2", fg="white", relief="flat", padx=15, pady=5)
send_button.pack(side=tk.LEFT, padx=(0,5))

def choose_recipient():
    if not recipients:
        messagebox.showwarning("No Recipients", "No saved recipients. Use /new to add.")
        return
    choose_win = Toplevel(root)
    choose_win.title("Choose Recipient")
    choose_win.geometry("300x300")
    choose_win.configure(bg="#1e1e2f")

    listbox = tk.Listbox(choose_win, bg="#2e2e3f", fg="white")
    listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    for name in recipients:
        listbox.insert(tk.END, name)

    def select_recipient():
        sel = listbox.curselection()
        if sel:
            name = listbox.get(sel[0])
            global recipient_pub_hex
            recipient_pub_hex = recipients[name]
            messagebox.showinfo("Recipient Selected", f"{name} selected for chatting.")
            choose_win.destroy()

    tk.Button(choose_win, text="Select", command=select_recipient, bg="#4a90e2", fg="white").pack(pady=5)

def add_new_recipient():
    # Popup for name
    name = simpledialog.askstring("Recipient Name", "Enter a friendly name for this recipient:")
    if not name:
        return
    # Popup for public key
    pub_key = simpledialog.askstring("Recipient Public Key", f"Enter public key for {name}:")
    if not pub_key:
        return
    # Validate hex length
    try:
        bytes.fromhex(pub_key)
        if len(pub_key) != 64:
            raise ValueError
    except:
        messagebox.showerror("Invalid Key", "Public key must be 32 bytes (64 hex characters).")
        return
    # Save recipient
    recipients[name] = pub_key
    save_recipients()
    global recipient_pub_hex
    recipient_pub_hex = pub_key
    messagebox.showinfo("Recipient Added", f"{name} saved and selected for chatting.")

# --- Message functions ---
def display_message(sender, text):
    messages_box.configure(state='normal')
    if sender == "You":
        messages_box.insert(tk.END, f"{sender}: {text}\n", "you")
    else:
        messages_box.insert(tk.END, f"{sender}: {text}\n", "other")
    messages_box.see(tk.END)
    messages_box.configure(state='disabled')

messages_box.tag_config("you", foreground="#4a90e2")
messages_box.tag_config("other", foreground="#0F8100")

def send_message(text):
    try:
        recipient_public = PublicKey(bytes.fromhex(recipient_pub_hex))
        box = SealedBox(recipient_public)
        encrypted = box.encrypt(text.encode())
        encrypted_b64 = base64.b64encode(encrypted).decode()
        payload = {"to": recipient_pub_hex, "from_": my_pub_hex, "message": encrypted_b64}
        r = requests.post(f"{SERVER_URL}/send", json=payload)
        if r.ok:
            display_message("You", text)
    except Exception as e:
        messagebox.showerror("Error", str(e))

def fetch_messages():
    try:
        
        
        r = requests.get(f"{SERVER_URL}/inbox/{my_pub_hex}")
        if r.ok:
            inbox = r.json().get("messages", [])
            for msg in inbox:
                enc = base64.b64decode(msg["message"])
                box = SealedBox(private_key)
                decrypted = box.decrypt(enc).decode()
                display_message(f"{msg['from']}", decrypted)
                c_thread.execute("INSERT INTO messages (sender, recipient, message) VALUES (?, ?, ?)",
                                 (msg["from"], my_pub_hex, decrypted))
                
        
    except Exception as e:
        print("Fetch error:", e)

stop_event = threading.Event()
def fetch_loop():
    while not stop_event.is_set():
        fetch_messages()
        time.sleep(1)

threading.Thread(target=fetch_loop, daemon=True).start()

# --- Handle closing ---
def on_close():
    stop_event.set()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
