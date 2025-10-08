import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image, ImageEnhance
import os
from tkinter import messagebox
from utils.crypto import is_strong_pin, load_key

class PinDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="Enter PIN", new_pin=False):
        super().__init__(parent)
        self.parent = parent
        self.new_pin = new_pin
        self.pin = None
        self.username = None

        # Resolve theme values from parent/app if available
        app_obj = getattr(parent, "app", parent)
        theme = {}
        if hasattr(app_obj, "theme_manager"):
            tm = app_obj.theme_manager
            theme = tm.theme_colors.get(tm.current_theme, {})
        # keep theme on the instance for later use (update_strength)
        self._theme = theme

        # --- Window Setup ---
        self.title(title)
        self.geometry("380x340" if new_pin else "380x200")
        self.resizable(False, False)
        win_bg = theme.get("background", "#1f1f2e")
        self.configure(fg_color=win_bg)
        self.grab_set()

        # Title
        title_color = theme.get("text", "white")
        # placeholder color may be used by small informational text below
        placeholder_color = theme.get("placeholder_text", "gray70")
        self.label = ctk.CTkLabel(self, text=title, font=("Segoe UI", 16, "bold"),
                                  text_color=title_color)
        self.label.pack(pady=(20, 0))

        # Small informational text to remind users why the PIN matters
        info_color = theme.get("muted_text", placeholder_color)
        self.info_label = ctk.CTkLabel(
            self,
            text="Your PIN protects your encryption key. Keep it secure.",
            font=("Segoe UI", 10),
            text_color=info_color,
            wraplength=320,
            justify="center"
        )
        self.info_label.pack(pady=(0, 10), padx=20)

        # Resolve entry colors (used for username and PIN fields)
        entry_bg = theme.get("input_bg", "#2a2a3f")
        entry_text = theme.get("input_text", "white")
        placeholder_color = theme.get("placeholder_text", "gray70")

        # Username entry (optional)
        if self.new_pin:
            self.username_entry = ctk.CTkEntry(
                self, placeholder_text="Username (default: Anonymous)",
                height=40, corner_radius=12, fg_color=entry_bg, text_color=entry_text,
                placeholder_text_color=placeholder_color
            )
            self.username_entry.pack(pady=5, padx=30, fill="x")
        else:
            self.username_entry = None

        # PIN entry placed in a horizontal container so we can attach
        # a small image 'continue' button to its right for existing-PIN flows.
        entry_container = ctk.CTkFrame(self, fg_color="transparent")
        entry_container.pack(pady=5, padx=30, fill="x")

        self.entry = ctk.CTkEntry(
            entry_container, show="*", placeholder_text="Enter PIN",
            height=40, corner_radius=12, fg_color=entry_bg, text_color=entry_text,
            placeholder_text_color=placeholder_color
        )
        self.entry.pack(side="left", expand=True, fill="x")
        self.entry.focus()

        # For existing-account dialogs (not creating a new one) add an image
        # button to the right of the entry that acts like the OK button.
        if not self.new_pin:
            try:
                cont_path = "gui/src/images/continue_btn.png"
                if not os.path.exists(cont_path):
                    # fallback to send button if continue icon missing
                    cont_path = "gui/src/images/send_btn.png"
                cont_img = Image.open(cont_path).resize((36, 36), Image.Resampling.LANCZOS)
                cont_icon = CTkImage(light_image=cont_img, dark_image=cont_img, size=(36, 36))

                self.cont_btn = ctk.CTkLabel(entry_container, image=cont_icon, text="", fg_color="transparent")
                self.cont_btn.image = cont_icon
                self.cont_btn.pack(side="right", padx=(6,0), pady=2)

                # Hover effect (darker icon)
                enhancer = ImageEnhance.Brightness(cont_img)
                dark_img = enhancer.enhance(0.75)
                dark_icon = CTkImage(light_image=dark_img, dark_image=dark_img, size=(36,36))
                self.cont_btn.hover_image = dark_icon

                def on_enter(e):
                    try:
                        self.cont_btn.configure(image=self.cont_btn.hover_image)
                    except Exception:
                        pass

                def on_leave(e):
                    try:
                        self.cont_btn.configure(image=self.cont_btn.image)
                    except Exception:
                        pass

                self.cont_btn.bind("<Button-1>", lambda e: self.on_ok())
                self.cont_btn.bind("<Enter>", on_enter)
                self.cont_btn.bind("<Leave>", on_leave)
            except Exception:
                # If anything fails while loading the image, fall back to a normal button
                self.cont_btn = ctk.CTkButton(entry_container, text="OK", width=60, command=self.on_ok)
                self.cont_btn.pack(side="right", padx=(6,0), pady=2)

        # Inline error label for invalid PIN feedback (shows under the entry)
        # Only show this for existing-PIN dialogs (not during new account creation)
        if not self.new_pin:
            self.error_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 10), text_color="#e74c3c")
            self.error_label.pack(pady=(6, 0))
            # Clear error while the user edits the PIN
            self.entry.bind("<KeyRelease>", lambda e: self.error_label.configure(text=""))
        else:
            self.error_label = None

        # Confirm PIN + strength bar (new PIN)
        if self.new_pin:
            self.entry.bind("<KeyRelease>", self.update_strength)

            self.confirm_entry = ctk.CTkEntry(
                self, show="*", placeholder_text="Confirm PIN",
                height=40, corner_radius=12, fg_color=entry_bg, text_color=entry_text,
                placeholder_text_color=placeholder_color
            )
            self.confirm_entry.pack(pady=5, padx=30, fill="x")

            # Strength text above the bar
            self.strength_label = ctk.CTkLabel(
                self, text="", font=("Segoe UI", 12, "bold"),
                text_color=entry_text
            )
            self.strength_label.pack(pady=(10, 2))

            # Small strength bar
            self.strength_frame = ctk.CTkFrame(self, fg_color=entry_bg, corner_radius=8, height=8)
            self.strength_frame.pack(padx=30, fill="x")
            self.strength_frame.pack_propagate(False)

            # Inner colored bar
            # initial bar color uses server_offline as a red fallback
            bar_color = theme.get("server_offline", "#e74c3c")
            self.strength_bar = ctk.CTkFrame(self.strength_frame, width=0, fg_color=bar_color, corner_radius=8)
            self.strength_bar.place(relheight=1, x=0, y=0)
            # Create button for the new account flow
            create_color = theme.get("button_send", "#4a90e2")
            create_hover = theme.get("button_send_hover", "#357ABD")
            self.create_btn = ctk.CTkButton(
                self, text="Create", width=140, height=40, corner_radius=12,
                fg_color=create_color, hover_color=create_hover, command=self.on_ok
            )
            self.create_btn.pack(pady=(12, 8))
        else:
            self.confirm_entry = None
            self.strength_bar = None
            self.strength_label = None

        # Keep return/escape bindings. Note: for new account creation the
        # dialog doesn't show the image continue button (per requirement).
        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.on_cancel())

    # --- Animate strength bar smoothly 0-100% ---
    def animate_bar(self, target_width, color, text):
        # Smooth time-based animation.
        # Use a frame interval around 16ms (~60fps). Some systems can handle 8ms
        # (~125fps) but 16ms is a good default for smooth visuals.
        if not hasattr(self, "strength_bar") or not self.strength_bar:
            return

        # Cancel any previously scheduled animation
        try:
            if getattr(self, "_anim_id", None):
                self.after_cancel(self._anim_id)
        except Exception:
            pass

        start_width = self.strength_bar.winfo_width() or 0
        end_width = int(target_width)
        delta = end_width - start_width

        # Animation parameters
        frame_ms = 16  # target ~60fps; set to 8 for even higher fps if desired
        duration_ms = 180  # total duration of the animation in ms
        steps = max(1, int(duration_ms / frame_ms))

        self._animating = True
        self._anim_step = 0

        def step_animation():
            i = self._anim_step
            t = i / steps
            # ease-out cubic for a smooth finish
            ease = 1 - (1 - t) ** 3
            cur = start_width + delta * ease
            try:
                self.strength_bar.configure(width=int(cur), fg_color=color)
                if getattr(self, "strength_label", None):
                    self.strength_label.configure(text=text, text_color=color)
            except Exception:
                # widget may have been destroyed
                self._animating = False
                return

            if i >= steps:
                # finalize
                try:
                    self.strength_bar.configure(width=end_width, fg_color=color)
                    if getattr(self, "strength_label", None):
                        self.strength_label.configure(text=text, text_color=color)
                except Exception:
                    pass
                self._animating = False
                self._anim_id = None
                return

            self._anim_step += 1
            self._anim_id = self.after(frame_ms, step_animation)

        # start
        self._anim_step = 0
        step_animation()




    def update_strength(self, event=None):
        if not self.new_pin:
            return

        pin = self.entry.get().strip()
        max_width = self.strength_frame.winfo_width() or 300

        if not pin:
            weak_color = self._theme.get("strength_weak", "#e74c3c")
            self.animate_bar(0, weak_color, "")
            return
            return

        ok, reason = is_strong_pin(pin)

        if not ok:
            color = self._theme.get("strength_weak", "#e74c3c")
            width = max_width * 0.33
            text = reason  # show reason only
        elif len(pin) < 8:
            color = self._theme.get("strength_medium", "#f1c40f")
            width = max_width * 0.66
            text = "Medium"
        else:
            color = self._theme.get("strength_strong", "#2ecc71")
            width = max_width
            text = "Strong"

        self.animate_bar(width, color, text)


    # --- OK ---
    def on_ok(self):
        pin = self.entry.get().strip()
        if not pin:
            # For new account creation, show a modal warning. For existing-PIN
            # flows, show the inline error label.
            if self.new_pin:
                messagebox.showwarning("Warning", "PIN cannot be empty!")
            else:
                if self.error_label:
                    self.error_label.configure(text="PIN cannot be empty!")
            return

        if not self.new_pin:
            # Validate PIN by attempting to load keys. If load_key raises,
            # show an inline error and keep the dialog open.
            try:
                load_key(pin)
            except FileNotFoundError:
                self.error_label.configure(text="Key file not found. Create or import a keypair.")
                return
            except ValueError:
                self.error_label.configure(text="Incorrect PIN or corrupted key file!")
                return

        if self.new_pin:
            confirm_pin = self.confirm_entry.get().strip()
            if pin != confirm_pin:
                messagebox.showwarning("Mismatch", "PINs do not match!")
                return

            ok, reason = is_strong_pin(pin)
            if not ok:
                messagebox.showwarning("Weak PIN", f"PIN rejected: {reason}")
                return

            username = self.username_entry.get().strip() if self.username_entry else ""
            if not username:
                username = "Anonymous"
            self.username = username

        self.pin = pin
        self.destroy()

    # --- Cancel ---
    def on_cancel(self):
        self.pin = None
        self.username = None
        self.destroy()
