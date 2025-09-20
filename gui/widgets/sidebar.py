import customtkinter as ctk
from recipients import recipients, get_recipient_key

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, select_callback, add_callback):
        super().__init__(parent, width=200, corner_radius=0)
        self.select_callback = select_callback
        self.add_callback = add_callback
        self.pack(side="left", fill="y")
        
        ctk.CTkLabel(self, text="Recipients", font=("Segoe UI", 14, "bold")).pack(pady=10)
        self.recipient_listbox = ctk.CTkScrollableFrame(self, width=180)
        self.recipient_listbox.pack(fill="y", expand=True, padx=10, pady=(0,10))
        self.update_list()
        
        ctk.CTkButton(self, text="+ Add Recipient", command=self.add_callback, fg_color="#4a90e2").pack(pady=10, padx=10)
    
    def update_list(self, selected_pub=None):
        for widget in self.recipient_listbox.winfo_children():
            widget.destroy()
        for name, key in recipients.items():
            is_selected = (key == selected_pub)
            btn = ctk.CTkButton(
                self.recipient_listbox,
                text=name,
                fg_color="#4a90e2" if is_selected else "#3e3e50",
                hover_color="#4a4a6a",
                command=lambda n=name: self.select_callback(n)
            )
            btn.pack(fill="x", pady=2, padx=5)
