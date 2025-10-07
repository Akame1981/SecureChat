import os
import json
import customtkinter as ctk
from typing import Dict, Any
from utils.path_utils import get_resource_path


THEMES_REL = os.path.join("config", "themes.json")


class ThemeManager:
    def __init__(self):
        self.current_theme = "Dark"
        self.theme_colors: Dict[str, Any] = {}
        self._listeners = []  # callables receiving (theme_dict)

        self._load_themes()
        # Ensure the default (or previously selected) theme is applied immediately
        # so widgets created afterwards don't momentarily show mixed/system colors.
        try:
            self.apply()
        except Exception:
            pass

    def _load_themes(self):
        themes_file = get_resource_path(THEMES_REL)
        if os.path.exists(themes_file):
            try:
                with open(themes_file, "r", encoding="utf-8") as f:
                    self.theme_colors = json.load(f)
            except Exception:
                self.theme_colors = {}

    def set_theme_by_name(self, name: str):
        if name:
            self.current_theme = name
        self.apply()

    def register_listener(self, func):
        if callable(func) and func not in self._listeners:
            self._listeners.append(func)

    def unregister_listener(self, func):
        try:
            self._listeners.remove(func)
        except ValueError:
            pass

    def apply(self):
        theme = self.theme_colors.get(self.current_theme, {})
        mode = theme.get("mode", "Dark")
        ctk.set_appearance_mode(mode.lower())
        accent_color = theme.get("accent_color", "blue")
        try:
            ctk.set_default_color_theme(accent_color)
        except Exception:
            # Some versions expect a file path or a theme name; ignore failures
            pass
        # Notify listeners so they can update widget colors live
        for listener in list(self._listeners):
            try:
                listener(theme)
            except Exception:
                # Ignore listener failures to avoid breaking theme changes
                pass

    def get_bubble_colors(self):
        theme = self.theme_colors.get(self.current_theme, {})
        return {
            "bubble_you": theme.get("bubble_you", "#7289da"),
            "bubble_other": theme.get("bubble_other", "#2f3136"),
            "text": theme.get("text", "white"),
        }
