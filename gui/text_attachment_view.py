import re
import customtkinter as ctk
import tkinter as tk


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

    # Container holds line numbers gutter + text box
    container = ctk.CTkFrame(bubble_frame, fg_color="transparent")
    container.pack(anchor=side_anchor, padx=10, pady=(4 if not prev_same else 2, 4), fill="x")

    # Line numbers gutter (tk.Text for simpler fixed-width rendering)
    ln_bg = theme.get('preview_bg', '#23272e') if theme else '#23272e'
    ln_fg = theme.get('muted_text', '#9aa0a6') if theme else '#9aa0a6'
    line_numbers = tk.Text(container, width=5, padx=6, bd=0, highlightthickness=0, bg=ln_bg, fg=ln_fg, font=("Roboto Mono", 11))
    # populate numbers
    try:
        nums = "\n".join(str(i) for i in range(1, total_lines + 1))
        line_numbers.insert("1.0", nums)
    except Exception:
        pass
    line_numbers.configure(state='disabled')
    line_numbers.pack(side='left', fill='y')

    textbox = ctk.CTkTextbox(
        container,
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
    textbox.pack(side='left', fill='both', expand=True)

    # --- Synchronize scrolling between textbox and line_numbers gutter ---
    def _sync_ln_from_text(first, last):
        try:
            # first is a string fraction like '0.0'
            line_numbers.yview_moveto(first)
        except Exception:
            pass

    def _sync_text_from_ln(first, last):
        try:
            textbox.yview_moveto(first)
        except Exception:
            pass

    # Set yscrollcommand callbacks
    try:
        textbox.configure(yscrollcommand=_sync_ln_from_text)
    except Exception:
        pass
    try:
        line_numbers.configure(yscrollcommand=_sync_text_from_ln)
    except Exception:
        pass

    # Mouse wheel bindings (cross-platform)
    def _on_mousewheel(event, widget_src, widget_target):
        try:
            if hasattr(event, 'num') and event.num in (4, 5):
                # X11 scroll
                delta = -1 if event.num == 4 else 1
            else:
                # Windows/Mac
                delta = -1 * int(event.delta / 120)
            widget_src.yview_scroll(delta, 'units')
            widget_target.yview_scroll(delta, 'units')
            return 'break'
        except Exception:
            return None

    try:
        textbox.bind('<MouseWheel>', lambda e: _on_mousewheel(e, textbox, line_numbers))
        textbox.bind('<Button-4>', lambda e: _on_mousewheel(e, textbox, line_numbers))
        textbox.bind('<Button-5>', lambda e: _on_mousewheel(e, textbox, line_numbers))
    except Exception:
        pass
    try:
        line_numbers.bind('<MouseWheel>', lambda e: _on_mousewheel(e, line_numbers, textbox))
        line_numbers.bind('<Button-4>', lambda e: _on_mousewheel(e, line_numbers, textbox))
        line_numbers.bind('<Button-5>', lambda e: _on_mousewheel(e, line_numbers, textbox))
    except Exception:
        pass

    # Expand/collapse button
    def _make_toggle(textbox_ref, line_numbers_ref, total_lines_ref, preview_lines_ref):
        collapsed_local = True

        def toggle():
            nonlocal collapsed_local
            if collapsed_local:
                new_h = min(total_lines_ref * 18, 600)
                textbox_ref.configure(height=new_h)
                # approximate lines for gutter
                try:
                    ln_lines = min(total_lines_ref, max(3, int(new_h / 18)))
                    line_numbers_ref.configure(state='normal')
                    line_numbers_ref.delete('1.0', 'end')
                    line_numbers_ref.insert('1.0', "\n".join(str(i) for i in range(1, total_lines_ref + 1)))
                    line_numbers_ref.configure(state='disabled')
                except Exception:
                    pass
                btn.configure(text="Collapse")
                collapsed_local = False
            else:
                new_h = min(preview_lines_ref * 18, 320)
                textbox_ref.configure(height=new_h)
                try:
                    ln_lines = min(total_lines_ref, max(3, int(new_h / 18)))
                    line_numbers_ref.configure(state='normal')
                    line_numbers_ref.delete('1.0', 'end')
                    line_numbers_ref.insert('1.0', "\n".join(str(i) for i in range(1, total_lines_ref + 1)))
                    line_numbers_ref.configure(state='disabled')
                except Exception:
                    pass
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
    btn_command = _make_toggle(textbox, line_numbers, total_lines, preview_lines)
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
