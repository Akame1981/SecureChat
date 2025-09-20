import os
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext, Toplevel
import threading
import time

from crypto import load_key, save_key, PrivateKey
from network import send_message, fetch_messages
from recipients import recipients, add_recipient, get_recipient_key
import customtkinter as ctk
from crypto import SigningKey

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # remove window decorations
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify="left", background="#2e2e3f",
                         foreground="white", relief="solid", borderwidth=1, font=("Segoe UI", 10))
        label.pack(ipadx=5, ipady=2)

    def hide_tip(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

class SecureChatApp(ctk.CTk):

    
    def __init__(self):
        super().__init__()
        self.title("🔒 Secure Chat")
        self.geometry("600x600")

        # Remove self.configure(bg=...) — CTk handles dark mode
        ctk.set_appearance_mode("dark")       # optional: ensure dark theme
        ctk.set_default_color_theme("blue")   # optional: theme color

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
        # ---------------- Main Layout ----------------
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True)

        # Sidebar (left)
        self.sidebar = ctk.CTkFrame(main_frame, width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")

        # Add sidebar content: list of recipients
        ctk.CTkLabel(self.sidebar, text="Recipients", font=("Segoe UI", 14, "bold")).pack(pady=10)
        self.recipient_listbox = ctk.CTkScrollableFrame(self.sidebar, width=180)
        self.recipient_listbox.pack(fill="y", expand=True, padx=10, pady=(0,10))

        self.update_recipient_list()

        # Button to add new recipient
        ctk.CTkButton(self.sidebar, text="+ Add Recipient", command=self.add_new_recipient, fg_color="#4a90e2").pack(pady=10, padx=10)

        # ---------------- Chat Area (right) ----------------
        chat_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        chat_frame.pack(side="right", fill="both", expand=True)


        # ---------------- Public Key Frame ----------------
        pub_frame = ctk.CTkFrame(chat_frame, fg_color="#2e2e3f", corner_radius=10)
        pub_frame.pack(fill="x", padx=10, pady=10)
        pub_frame.grid_columnconfigure(0, weight=1)
        pub_frame.grid_columnconfigure(1, weight=0)
        pub_frame.grid_columnconfigure(2, weight=0)

        # Copy and Settings buttons first
        self.copy_btn = ctk.CTkButton(pub_frame, text="Copy", command=self.copy_pub_key, fg_color="#4a4a6a")
        self.copy_btn.grid(row=0, column=1, padx=5, pady=10)

        self.settings_btn = ctk.CTkButton(pub_frame, text="Settings", command=self.open_settings, fg_color="#4a90e2")
        self.settings_btn.grid(row=0, column=2, padx=5, pady=10)

        # Then the label
        self.pub_label = ctk.CTkLabel(pub_frame, text="", justify="left", anchor="w")
        self.pub_label.grid(row=0, column=0, padx=10, pady=10, sticky="we")

        def update_pub_label(event=None):
            pub_frame.update_idletasks()
            frame_width = pub_frame.winfo_width() - self.copy_btn.winfo_width() - self.settings_btn.winfo_width() - 30
            approx_char_width = 7
            max_chars = max(10, frame_width // approx_char_width)

            truncated = self.my_pub_hex
            if len(truncated) > max_chars:
                truncated = truncated[:max_chars-3] + "..."
            
            self.pub_label.configure(text=f"My Public Key: {truncated}")

            # Add tooltip for full key
            ToolTip(self.pub_label, self.my_pub_hex)


        pub_frame.bind("<Configure>", update_pub_label)
        self.after(200, update_pub_label)  # initial update



        self.copy_btn = ctk.CTkButton(pub_frame, text="Copy", command=self.copy_pub_key, fg_color="#4a4a6a")
        self.copy_btn.grid(row=0, column=1, padx=5, pady=10)

        self.settings_btn = ctk.CTkButton(pub_frame, text="Settings", command=self.open_settings, fg_color="#4a90e2")
        self.settings_btn.grid(row=0, column=2, padx=5, pady=10)


        # Messages Box
        self.messages_box = ctk.CTkTextbox(chat_frame, corner_radius=10, fg_color="#2e2e3f", text_color="white")
        self.messages_box.pack(padx=10, pady=10, fill="both", expand=True)

        # Input Frame
        input_frame = ctk.CTkFrame(chat_frame, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=(0,10))

        self.input_box = ctk.CTkEntry(input_frame, placeholder_text="Type a message...")
        self.input_box.pack(side="left", expand=True, fill="x", padx=(0,5), pady=5)
        self.input_box.bind("<Return>", lambda event: self.on_send())

        ctk.CTkButton(input_frame, text="Send", command=self.on_send, fg_color="#4a90e2").pack(side="right", padx=(0,5), pady=5)

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


    def update_recipient_list(self):
        # Clear existing buttons
        for widget in self.recipient_listbox.winfo_children():
            widget.destroy()

        for name, key in recipients.items():
            # Highlight the selected recipient
            is_selected = (self.recipient_pub_hex == key)
            btn = ctk.CTkButton(
                self.recipient_listbox,
                text=name,
                fg_color="#4a90e2" if is_selected else "#3e3e50",  # highlight selected
                hover_color="#4a4a6a",
                command=lambda n=name: self.select_recipient(n)
            )
            btn.pack(fill="x", pady=2, padx=5)


    def select_recipient(self, name):
        self.recipient_pub_hex = get_recipient_key(name)
        self.update_recipient_list()  # refresh buttons to show highlight
        


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
                self.signing_key = SigningKey.generate()  # now works
                save_key(self.private_key, self.signing_key, pin)
                self.public_key = self.private_key.public_key
                self.my_pub_hex = self.public_key.encode().hex()
                self.pub_label.configure(text=f"My Public Key: {self.my_pub_hex}")
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
                
                choose_win.destroy()

        tk.Button(choose_win, text="Select", command=select, bg="#4a90e2", fg="white").pack(pady=5)

    # ---------------- Close ----------------

    
    def on_close(self):
        self.stop_event.set()
        self.destroy()

    # ---------------- PIN Dialog ----------------
class PinDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="Enter PIN", new_pin=False):
        super().__init__(parent)
        self.parent = parent
        self.new_pin = new_pin
        self.pin = None

        self.title(title)
        self.geometry("350x180")
        self.resizable(False, False)
        self.grab_set()  # Make modal

        # Configure frame padding
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Title label
        self.label = ctk.CTkLabel(self, text=title, font=("Segoe UI", 14, "bold"))
        self.label.pack(pady=(15, 10))

        # Entry field
        self.entry = ctk.CTkEntry(self, show="*", placeholder_text="Enter PIN")
        self.entry.pack(pady=5, padx=20, fill="x")
        self.entry.focus()

        # Buttons frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        self.ok_btn = ctk.CTkButton(btn_frame, text="OK", width=80, command=self.on_ok, fg_color="#4a90e2")
        self.ok_btn.pack(side="left", padx=10)

        self.cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", width=80, command=self.on_cancel, fg_color="#d9534f")
        self.cancel_btn.pack(side="right", padx=10)

        # Bind Enter and Escape keys
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
