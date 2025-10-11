import re
import customtkinter as ctk


def render_text_attachment(bubble_frame, filename, ext, content, wrap_len, side_anchor, prev_same, theme):
    """Render a filename label + CTkTextbox with simple syntax highlighting.

    Returns (textbox_widget, expand_button)
    """
    # Show filename on top
    try:
        file_label = ctk.CTkLabel(bubble_frame, text=filename, text_color=theme.get('muted_text', '#bfbfbf'), font=("Roboto", 9, "bold"))
        file_label.pack(anchor=side_anchor, padx=10, pady=(6, 0))
    except Exception:
        pass

    preview_lines = 12
    total_lines = content.count('\n') + 1
    collapsed = True
    textbox = ctk.CTkTextbox(
        bubble_frame,
        width=wrap_len,
        height=min(preview_lines * 18, 320),
        font=("Roboto Mono", 11),
        fg_color="#23272e",
        text_color="#e5e5e5",
        border_width=1,
        border_color="#444"
    )

    textbox.insert("1.0", content)

    try:
        lang = ext.lower()
        # Basic tags
        textbox.tag_config('str', foreground='#a8ff60')
        textbox.tag_config('com', foreground='#888888')
        textbox.tag_config('kw', foreground='#66b8ff')

        # simple keyword lists
        if lang in ('py', 'pyw'):
            keywords = [
                'def', 'class', 'import', 'from', 'return', 'if', 'elif', 'else', 'for', 'while', 'try', 'except', 'with', 'as', 'pass', 'break', 'continue', 'lambda', 'yield', 'True', 'False', 'None'
            ]
        elif lang in ('js', 'ts'):
            keywords = ['function', 'var', 'let', 'const', 'if', 'else', 'for', 'while', 'return', 'class', 'import', 'from', 'export', 'try', 'catch']
        else:
            keywords = []

        # mark keywords
        for kw in keywords:
            start = '1.0'
            pattern = r'\b' + re.escape(kw) + r'\b'
            while True:
                pos = textbox.search(pattern, start, stopindex='end', regexp=True)
                if not pos:
                    break
                endpos = f"{pos}+{len(kw)}c"
                try:
                    textbox.tag_add('kw', pos, endpos)
                except Exception:
                    pass
                start = endpos

        # strings
        for m in re.finditer(r"(?P<q>\'[^\']*\'|\"[^\"]*\")", content):
            try:
                sidx = f"1.0+{m.start()}c"
                eidx = f"1.0+{m.end()}c"
                textbox.tag_add('str', sidx, eidx)
            except Exception:
                pass

        # comments per-line
        lines = content.splitlines()
        for i, ln in enumerate(lines, start=1):
            if ln.lstrip().startswith('#') or ln.lstrip().startswith('//'):
                try:
                    sidx = f"{i}.0"
                    eidx = f"{i}.end"
                    textbox.tag_add('com', sidx, eidx)
                except Exception:
                    pass
    except Exception:
        pass

    textbox.configure(state="disabled")
    textbox.pack(anchor=side_anchor, padx=10, pady=(4 if not prev_same else 2, 4), fill="x")

    # Expand/collapse button
    def _make_toggle(textbox_ref, total_lines_ref, preview_lines_ref):
        collapsed_local = True

        def toggle():
            nonlocal collapsed_local
            if collapsed_local:
                textbox_ref.configure(height=min(total_lines_ref * 18, 600))
                btn.configure(text="Collapse")
                collapsed_local = False
            else:
                textbox_ref.configure(height=min(preview_lines_ref * 18, 320))
                btn.configure(text="Expand")
                collapsed_local = True

        return toggle

    btn = ctk.CTkButton(
        bubble_frame,
        text="Expand" if total_lines > preview_lines else "Full View",
        width=80,
        height=22,
        font=("Roboto", 10),
        command=None
    )
    btn_command = _make_toggle(textbox, total_lines, preview_lines)
    try:
        btn.configure(command=btn_command)
    except Exception:
        pass
    btn.pack(anchor=side_anchor, padx=10, pady=(0, 4))
    if total_lines <= preview_lines:
        try:
            btn.configure(state="disabled")
        except Exception:
            pass

    return textbox, btn
