import json
import customtkinter as ctk
import os

class AppearanceTab:
    def __init__(self, parent, app, config_path):
        self.parent = parent
        self.app = app
        self.config_path = config_path
        self.themes_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../config/themes.json"))

        # Load saved theme
        self.settings = self.load_settings()
        self.current_theme = self.settings.get("theme_name", "Dark")

        # Load all themes
        self.themes = self.load_themes()

        # --- UI ---
        ctk.CTkLabel(parent, text="Select Theme:", font=("Roboto", 14, "bold")).pack(pady=(20, 5))
        self.theme_menu = ctk.CTkOptionMenu(
            parent,
            values=list(self.themes.keys()),
            command=self.change_theme
        )
        self.theme_menu.set(self.current_theme)
        self.theme_menu.pack(pady=5)

        # Short help text
        ctk.CTkLabel(parent, text="Tip: You can preview a theme instantly. Click 'Apply & Save' to persist.", font=("Roboto", 10), text_color="#b2b8d6", fg_color="transparent").pack(pady=(6, 12))

        # Right-aligned Apply & Save button
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12)
        btn_frame.grid_columnconfigure(0, weight=1)
        self.save_button = ctk.CTkButton(btn_frame, text="Apply & Save", command=self.save_settings, width=140)
        self.save_button.grid(row=0, column=1, sticky="e", pady=12)

        # Theme editor button
        self.theme_editor_btn = ctk.CTkButton(btn_frame, text="Theme Editor", command=self.open_theme_editor, width=140, fg_color="#6c6f76")
        self.theme_editor_btn.grid(row=0, column=0, sticky="w", pady=12)

        # Apply theme immediately
        self.apply_theme()

    # -------------------- Load themes from JSON --------------------
    def load_themes(self):
        if os.path.exists(self.themes_file):
            try:
                with open(self.themes_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    # -------------------- Change theme --------------------
    def change_theme(self, theme_name):
        self.current_theme = theme_name
        self.apply_theme()

    # -------------------- Apply selected theme --------------------
    def apply_theme(self):
        # Prefer the ThemeManager if the app has one (new API)
        if hasattr(self.app, "theme_manager"):
            # Tell the theme manager to switch and apply global appearance
            self.app.theme_manager.set_theme_by_name(self.current_theme)
            # Get resolved theme values
            theme = self.app.theme_manager.theme_colors.get(self.app.theme_manager.current_theme, {})
        else:
            theme = self.themes.get(self.current_theme, {})
            if not theme:
                return

            # Apply appearance mode for older code paths
            mode = theme.get("mode", "Dark")
            ctk.set_appearance_mode(mode.lower())

        # Apply colors to main app elements (both new and legacy)
        try:
            self.app.configure(fg_color=theme.get("background", "#1e1e2f"))
        except Exception:
            pass

        if hasattr(self.app, "sidebar"):
            try:
                self.app.sidebar.configure(fg_color=theme.get("sidebar_bg", "#2a2a3a"))
            except Exception:
                pass

        # Update all existing message bubbles
        if hasattr(self.app, "messages_container"):
            tb_flag = bool(theme.get('bubble_transparent', False))
            for bubble in self.app.messages_container.winfo_children():
                try:
                    if tb_flag:
                        bubble.configure(fg_color="transparent")
                    else:
                        if hasattr(bubble, "is_you") and bubble.is_you:
                            bubble.configure(fg_color=theme.get("bubble_you", "#7289da"))
                        else:
                            bubble.configure(fg_color=theme.get("bubble_other", "#2f3136"))
                except Exception:
                    pass

        # Update message bubble widgets via app helper (uses ThemeManager when available)
        if hasattr(self.app, "update_message_bubbles_theme"):
            try:
                self.app.update_message_bubbles_theme()
            except Exception:
                pass

        # No per-theme UI toggles here; theme flags (like bubble_transparent) are read from the theme directly


    # -------------------- Settings Handling --------------------
    def load_settings(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def save_settings(self):
        self.settings["theme_name"] = self.current_theme
        with open(self.config_path, "w") as f:
            json.dump(self.settings, f, indent=4)
        # Update app-level settings and theme manager (if present)
        if hasattr(self.app, "app_settings"):
            try:
                self.app.app_settings["theme_name"] = self.current_theme
            except Exception:
                pass

        # Apply the theme and notify the user
        self.apply_theme()
        self.app.notifier.show("Theme saved!", type_="success")

    def open_theme_editor(self):
        try:
            from gui.settings.theme_editor import ThemeEditor
            def _on_save():
                # reload themes and reapply
                self.themes = self.load_themes()
                try:
                    self.theme_menu.configure(values=list(self.themes.keys()))
                    if self.current_theme in self.themes:
                        self.theme_menu.set(self.current_theme)
                except Exception:
                    pass

            ThemeEditor(self.parent, self.themes_file, on_save=_on_save, app=self.app)
        except Exception:
            pass
