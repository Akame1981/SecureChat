import os
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext, Toplevel
import threading
import time

from crypto import load_key, save_key, PrivateKey
from network import send_message, fetch_messages
from recipients import recipients, add_recipient, get_recipient_key


class SecureChatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🔒 Secure Chat")
        self.geometry("600x600")
        self.configure(bg="#1e1e2f")

        self.private_key = None
        self.public_key = None
        self.my_pub_hex = None
        self.recipient_pub_hex = None

        self.init_keypair()
        self.create_widgets()

        # Start fetch loop
        self.stop_event = threading.Event()
        threading.Thread(target=self.fetch_loop, daemon=True).start()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

# ---------------- Keypair ----------------
    def init_keypair(self):
        from crypto import SigningKey  # import here to avoid circular imports if needed

        if os.path.exists("keypair.bin"):
            dlg = PinDialog(self, "Enter PIN to unlock keypair")
            self.wait_window(dlg)
            pin = dlg.pin
            if not pin:
                self.destroy()
                return
            try:
                # load_key now returns both keys
                self.private_key, self.signing_key = load_key(pin)
            except ValueError:
                messagebox.showerror("Error", "Incorrect PIN or corrupted key!")
                self.destroy()
                return
        else:
            dlg = PinDialog(self, "Set a new PIN", new_pin=True)
            self.wait_window(dlg)
            pin = dlg.pin
            if not pin:
                self.destroy()
                return

            self.private_key = PrivateKey.generate()
            self.signing_key = SigningKey.generate()  # new signing key
            save_key(self.private_key, self.signing_key, pin)
            messagebox.showinfo("Key Created", "New keypair generated!")

        self.public_key = self.private_key.public_key
        self.my_pub_hex = self.public_key.encode().hex()
        self.signing_pub_hex = self.signing_key.verify_key.encode().hex()




    # ---------------- GUI ----------------
    def create_widgets(self):
        # Public key frame
        pub_frame = tk.Frame(self, bg="#2e2e3f", pady=5)
        pub_frame.pack(fill=tk.X)
        self.pub_label = tk.Label(pub_frame, text=f"My Public Key: {self.my_pub_hex}", fg="white", bg="#2e2e3f", wraplength=550, justify="left")
        self.pub_label.pack(side=tk.LEFT, padx=10)
        tk.Button(pub_frame, text="Copy", command=self.copy_pub_key, bg="#4a4a6a", fg="white", relief="flat", padx=10).pack(side=tk.RIGHT, padx=10)
        tk.Button(pub_frame, text="Settings", command=self.open_settings, bg="#4a90e2", fg="white", relief="flat", padx=10).pack(side=tk.RIGHT, padx=10)

        # Messages box
        self.messages_box = scrolledtext.ScrolledText(self, width=70, height=25, state='disabled', bg="#2e2e3f", fg="white", wrap=tk.WORD, relief="flat")
        self.messages_box.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.messages_box.tag_config("you", foreground="#4a90e2")
        self.messages_box.tag_config("other", foreground="#0F8100")

        # Input frame
        input_frame = tk.Frame(self, bg="#1e1e2f")
        input_frame.pack(fill=tk.X, padx=10, pady=(0,10))
        self.input_box = tk.Entry(input_frame, width=50, bg="#3e3e50", fg="white", relief="flat", insertbackground="white")
        self.input_box.pack(side=tk.LEFT, padx=(0,5), pady=5, ipady=5)
        self.input_box.bind("<Return>", lambda event: self.on_send())
        tk.Button(input_frame, text="Send", command=self.on_send, bg="#4a90e2", fg="white", relief="flat", padx=15, pady=5).pack(side=tk.LEFT, padx=(0,5))

    # ---------------- Public key ----------------
    def copy_pub_key(self):
        self.clipboard_clear()
        self.clipboard_append(self.my_pub_hex)
        messagebox.showinfo("Copied", "Public key copied!")

    # ---------------- Messages ----------------
    def display_message(self, sender, text):
        self.messages_box.configure(state='normal')
        tag = "you" if sender == "You" else "other"
        self.messages_box.insert(tk.END, f"{sender}: {text}\n", tag)
        self.messages_box.see(tk.END)
        self.messages_box.configure(state='disabled')

    def on_send(self):
        text = self.input_box.get().strip()
        if not text:
            return
        if text.startswith("/new"):
            self.add_new_recipient()
            self.input_box.delete(0, tk.END)
            return
        if text.startswith("/choose"):
            self.choose_recipient()
            self.input_box.delete(0, tk.END)
            return
        if not self.recipient_pub_hex:
            messagebox.showwarning("No recipient", "Select a recipient first (/choose)")
            return
        if send_message(self.recipient_pub_hex, self.signing_pub_hex, text, self.signing_key):
            self.display_message("You", text)





        self.input_box.delete(0, tk.END)

    def fetch_loop(self):
        while not self.stop_event.is_set():
            msgs = fetch_messages(self.my_pub_hex, self.private_key)
            for msg in msgs:
                self.display_message(msg["from"], msg["message"])
            time.sleep(1)

    # ---------------- Settings ----------------
    def open_settings(self):
        settings = Toplevel(self)
        settings.title("Settings")
        settings.geometry("400x300")
        settings.configure(bg="#1e1e2f")

        # Generate new key
        def new_key():
            if messagebox.askyesno("New Key", "Generate new keypair?"):
                pin = simpledialog.askstring("Set PIN", "Enter PIN for new keypair:", show="*")
                if not pin:
                    return
                self.private_key = PrivateKey.generate()
                self.signing_key = SigningKey.generate()  # <-- add this
                save_key(self.private_key, self.signing_key, pin)
                self.public_key = self.private_key.public_key
                self.my_pub_hex = self.public_key.encode().hex()
                self.pub_label.config(text=f"My Public Key: {self.my_pub_hex}")
                messagebox.showinfo("New Key", "New keypair generated!")


        tk.Button(settings, text="Generate New Keypair", command=new_key, bg="#4a90e2", fg="white").pack(pady=10)

        # Change PIN
        def change_pin():
            old_pin = simpledialog.askstring("Current PIN", "Enter current PIN:", show="*")
            if not old_pin:
                return
            try:
                priv = load_key(old_pin)
            except ValueError:
                messagebox.showerror("Error", "Incorrect PIN!")
                return
            new_pin = simpledialog.askstring("New PIN", "Enter new PIN:", show="*")
            if not new_pin:
                return
            save_key(priv, new_pin)
            messagebox.showinfo("Success", "PIN updated!")

        tk.Button(settings, text="Change Pincode", command=change_pin, bg="#4a90e2", fg="white").pack(pady=10)

        # Manage recipients
        def show_recipients():
            rec_window = Toplevel(settings)
            rec_window.title("Recipients")
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
                    if messagebox.askyesno("Delete", f"Delete {name}?"):
                        recipients.pop(name)
                        listbox.delete(sel[0])

            tk.Button(rec_window, text="Delete Selected", command=delete_selected, bg="#d9534f", fg="white").pack(pady=5)

        tk.Button(settings, text="Manage Recipients", command=show_recipients, bg="#4a90e2", fg="white").pack(pady=10)

    # ---------------- Recipients ----------------
    def add_new_recipient(self):
        name = simpledialog.askstring("Name", "Recipient name:")
        if not name:
            return
        pub_hex = simpledialog.askstring("Public Key", f"Public key for {name}:")
        if not pub_hex or len(pub_hex) != 64:
            messagebox.showerror("Error", "Invalid public key")
            return
        add_recipient(name, pub_hex)
        self.recipient_pub_hex = pub_hex
        messagebox.showinfo("Saved", f"{name} saved and selected.")

    def choose_recipient(self):
        if not recipients:
            messagebox.showwarning("No recipients", "Add a recipient first (/new)")
            return
        choose_win = Toplevel(self)
        choose_win.title("Choose Recipient")
        choose_win.geometry("300x300")
        choose_win.configure(bg="#1e1e2f")

        listbox = tk.Listbox(choose_win, bg="#2e2e3f", fg="white")
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for name in recipients:
            listbox.insert(tk.END, name)

        def select():
            sel = listbox.curselection()
            if sel:
                name = listbox.get(sel[0])
                self.recipient_pub_hex = get_recipient_key(name)
                messagebox.showinfo("Selected", f"{name} selected")
                choose_win.destroy()

        tk.Button(choose_win, text="Select", command=select, bg="#4a90e2", fg="white").pack(pady=5)

    # ---------------- Close ----------------

    
    def on_close(self):
        self.stop_event.set()
        self.destroy()

    # ---------------- PIN Dialog ----------------
class PinDialog(tk.Toplevel):
    def __init__(self, parent, title="Enter PIN", new_pin=False):
        super().__init__(parent)
        self.parent = parent
        self.new_pin = new_pin
        self.pin = None

        self.title(title)
        self.geometry("350x150")
        self.configure(bg="#1e1e2f")
        self.resizable(False, False)
        self.grab_set()  # Make modal

        tk.Label(self, text=title, bg="#1e1e2f", fg="white", font=("Arial", 12, "bold")).pack(pady=(10,5))

        self.entry = tk.Entry(self, show="*", bg="#3e3e50", fg="white", relief="flat", font=("Arial", 12))
        self.entry.pack(pady=5, padx=20, fill=tk.X)
        self.entry.focus()

        btn_frame = tk.Frame(self, bg="#1e1e2f")
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="OK", bg="#4a90e2", fg="white", relief="flat", width=10, command=self.on_ok).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", bg="#d9534f", fg="white", relief="flat", width=10, command=self.on_cancel).pack(side=tk.RIGHT, padx=5)

        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.on_cancel())

    def on_ok(self):
        pin = self.entry.get().strip()
        if not pin:
            messagebox.showwarning("Warning", "PIN cannot be empty!")
            return
        if len(pin) < 6:  # enforce minimum length
            messagebox.showwarning("Warning", "PIN too short. Must be at least 6 characters.")
            return
        self.pin = pin
        self.destroy()


    def on_cancel(self):
        self.pin = None
        self.destroy()

if __name__ == "__main__":
    app = SecureChatApp()
    app.mainloop()
