import customtkinter as ctk

# Placeholder module for text-channel specific UI. For now, groups_panel will continue
# to render text messages via its existing _append_message flow. This module exists to
# keep channel-type code separate and allow future per-type customization.

def render_text_channel(parent_frame, msgs: list[dict], app, theme: dict | None = None):
    # For now do nothing; the parent (groups_panel) will render messages as before.
    return
