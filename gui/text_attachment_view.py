import re
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox


def render_text_attachment(bubble_frame, filename, ext, content, wrap_len, side_anchor, prev_same, theme, show_expand: bool = True):
    """Render a filename label + CTkTextbox with simple syntax highlighting.

    show_expand: if False, do not render the Expand/Collapse button (useful for preview windows).

    Returns (textbox_widget, expand_button_or_None)
    """
    # Show filename on top
    try:
        file_label = ctk.CTkLabel(bubble_frame, text=filename, text_color=theme.get('muted_text', '#bfbfbf'), font=("Roboto", 9, "bold"))
        file_label.pack(anchor=side_anchor, padx=10, pady=(6, 0))
    except Exception:
        pass

    preview_lines = 23
    # Protect against extremely large attachments: cap the number of lines
    MAX_ATTACHMENT_LINES = 10000
    total_lines_raw = content.count('\n') + 1
    total_lines = min(total_lines_raw, MAX_ATTACHMENT_LINES)
    truncated_lines = total_lines_raw > MAX_ATTACHMENT_LINES
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
        # Only generate up to the capped number of lines to avoid OOM/timeouts.
        nums_gen = (str(i) for i in range(1, total_lines + 1))
        nums = "\n".join(nums_gen)
        if truncated_lines:
            nums = nums + "\n..."
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

    # Prepare preview content (first N lines) to avoid inserting the whole file initially
    preview_lines = int(preview_lines)
    all_lines = content.splitlines(True)
    preview_content = ''.join(all_lines[:preview_lines])

    # Helper: apply basic syntax tags to a textbox for given content
    def _apply_syntax_tags(tb_widget, text_content, extension):
        try:
            lang = extension.lower()
            tb_widget.tag_config('str', foreground='#a8ff60')
            tb_widget.tag_config('com', foreground='#888888')
            tb_widget.tag_config('kw', foreground='#66b8ff')

            if lang in ('py', 'pyw'):
                keywords = [
                    'def', 'class', 'import', 'from', 'return', 'if', 'elif', 'else', 'for', 'while', 'try', 'except', 'with', 'as', 'pass', 'break', 'continue', 'lambda', 'yield', 'True', 'False', 'None'
                ]
            elif lang in ('js', 'ts'):
                keywords = ['function', 'var', 'let', 'const', 'if', 'else', 'for', 'while', 'return', 'class', 'import', 'from', 'export', 'try', 'catch']
            else:
                keywords = []

            for kw in keywords:
                start = '1.0'
                pattern = r'\b' + re.escape(kw) + r'\b'
                while True:
                    pos = tb_widget.search(pattern, start, stopindex='end', regexp=True)
                    if not pos:
                        break
                    endpos = f"{pos}+{len(kw)}c"
                    try:
                        tb_widget.tag_add('kw', pos, endpos)
                    except Exception:
                        pass
                    start = endpos

            for m in re.finditer(r"(?P<q>\'[^\']*\'|\"[^\"]*\")", text_content):
                try:
                    sidx = f"1.0+{m.start()}c"
                    eidx = f"1.0+{m.end()}c"
                    tb_widget.tag_add('str', sidx, eidx)
                except Exception:
                    pass

            txt_lines = text_content.splitlines()
            for i, ln in enumerate(txt_lines, start=1):
                if ln.lstrip().startswith('#') or ln.lstrip().startswith('//'):
                    try:
                        sidx = f"{i}.0"
                        eidx = f"{i}.end"
                        tb_widget.tag_add('com', sidx, eidx)
                    except Exception:
                        pass
        except Exception:
            pass

    # Insert only preview content initially
    try:
        textbox.insert("1.0", preview_content)
        _apply_syntax_tags(textbox, preview_content, ext)
    except Exception:
        try:
            textbox.insert("1.0", content[:1000])
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

    # Initially disable synced scrolling in the collapsed preview and block mouse wheel
    try:
        textbox.configure(yscrollcommand=None)
    except Exception:
        pass
    try:
        line_numbers.configure(yscrollcommand=None)
    except Exception:
        pass

    def _on_mousewheel(event, widget_src, widget_target):
        try:
            if hasattr(event, 'num') and event.num in (4, 5):
                delta = -1 if event.num == 4 else 1
            else:
                delta = -1 * int(event.delta / 120)
            widget_src.yview_scroll(delta, 'units')
            widget_target.yview_scroll(delta, 'units')
            return 'break'
        except Exception:
            return None

    # Block scrolling by default in the collapsed preview so it doesn't scroll the main view
    def _block_scroll(event=None):
        return 'break'

    try:
        textbox.bind('<MouseWheel>', lambda e: _block_scroll())
        textbox.bind('<Button-4>', lambda e: _block_scroll())
        textbox.bind('<Button-5>', lambda e: _block_scroll())
        line_numbers.bind('<MouseWheel>', lambda e: _block_scroll())
        line_numbers.bind('<Button-4>', lambda e: _block_scroll())
        line_numbers.bind('<Button-5>', lambda e: _block_scroll())
    except Exception:
        pass

    # Expand/collapse button
    def _make_toggle(textbox_ref, line_numbers_ref, total_lines_ref, preview_lines_ref):
        collapsed_local = True

        def toggle():
            nonlocal collapsed_local
            if collapsed_local:
                # Expand to render the whole file (use raw lines). Limit the height to avoid creating enormous windows
                new_h = min(total_lines_raw * 18, 2000)
                try:
                    textbox_ref.configure(height=new_h)
                except Exception:
                    try:
                        textbox_ref.configure(height=min(new_h, 2000))
                    except Exception:
                        pass
                try:
                    # Rebuild gutter to full raw lines (in chunks to avoid huge allocations)
                    line_numbers_ref.configure(state='normal')
                    line_numbers_ref.delete('1.0', 'end')
                    CHUNK = 1000
                    i = 1
                    while i <= total_lines_raw:
                        end = min(i + CHUNK - 1, total_lines_raw)
                        try:
                            line_numbers_ref.insert('end', "\n".join(str(j) for j in range(i, end + 1)) + ("\n" if end < total_lines_raw else ""))
                        except Exception:
                            break
                        i = end + 1
                    line_numbers_ref.configure(state='disabled')
                    # Populate textbox with full content and apply syntax tags
                    try:
                        textbox_ref.configure(state='normal')
                        textbox_ref.delete('1.0', 'end')
                        textbox_ref.insert('1.0', content)
                        _apply_syntax_tags(textbox_ref, content, ext)
                        textbox_ref.configure(state='disabled')
                    except Exception:
                        pass
                    # Enable synced scrolling and mouse wheel for the expanded full view
                    try:
                        textbox_ref.configure(yscrollcommand=_sync_ln_from_text)
                        line_numbers_ref.configure(yscrollcommand=_sync_text_from_ln)
                        textbox_ref.unbind('<MouseWheel>'); textbox_ref.unbind('<Button-4>'); textbox_ref.unbind('<Button-5>')
                        line_numbers_ref.unbind('<MouseWheel>'); line_numbers_ref.unbind('<Button-4>'); line_numbers_ref.unbind('<Button-5>')
                        textbox_ref.bind('<MouseWheel>', lambda e: _on_mousewheel(e, textbox_ref, line_numbers_ref))
                        textbox_ref.bind('<Button-4>', lambda e: _on_mousewheel(e, textbox_ref, line_numbers_ref))
                        textbox_ref.bind('<Button-5>', lambda e: _on_mousewheel(e, textbox_ref, line_numbers_ref))
                        line_numbers_ref.bind('<MouseWheel>', lambda e: _on_mousewheel(e, line_numbers_ref, textbox_ref))
                        line_numbers_ref.bind('<Button-4>', lambda e: _on_mousewheel(e, line_numbers_ref, textbox_ref))
                        line_numbers_ref.bind('<Button-5>', lambda e: _on_mousewheel(e, line_numbers_ref, textbox_ref))
                    except Exception:
                        pass
                except Exception:
                    pass
                btn.configure(text="Collapse")
                collapsed_local = False
            else:
                # Collapse back to preview: show capped number of lines and disable internal scrolling
                new_h = min(preview_lines_ref * 18, 320)
                textbox_ref.configure(height=new_h)
                try:
                    line_numbers_ref.configure(state='normal')
                    line_numbers_ref.delete('1.0', 'end')
                    nums_gen = (str(i) for i in range(1, total_lines + 1))
                    nums = "\n".join(nums_gen)
                    if truncated_lines:
                        nums = nums + "\n..."
                    line_numbers_ref.insert('1.0', nums)
                    line_numbers_ref.configure(state='disabled')
                except Exception:
                    pass
                # Disable synced scrolling and block mouse wheel again
                try:
                    textbox_ref.configure(yscrollcommand=None)
                    line_numbers_ref.configure(yscrollcommand=None)
                except Exception:
                    pass
                try:
                    textbox_ref.unbind('<MouseWheel>'); textbox_ref.unbind('<Button-4>'); textbox_ref.unbind('<Button-5>')
                    line_numbers_ref.unbind('<MouseWheel>'); line_numbers_ref.unbind('<Button-4>'); line_numbers_ref.unbind('<Button-5>')
                    textbox_ref.bind('<MouseWheel>', lambda e: _block_scroll())
                    textbox_ref.bind('<Button-4>', lambda e: _block_scroll())
                    textbox_ref.bind('<Button-5>', lambda e: _block_scroll())
                    line_numbers_ref.bind('<MouseWheel>', lambda e: _block_scroll())
                    line_numbers_ref.bind('<Button-4>', lambda e: _block_scroll())
                    line_numbers_ref.bind('<Button-5>', lambda e: _block_scroll())
                except Exception:
                    pass
                btn.configure(text="Expand")
                collapsed_local = True

        return toggle

    btn = None
    if show_expand:
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
        try:
            btn.pack(anchor=side_anchor, padx=10, pady=(0, 4))
        except Exception:
            pass
        if total_lines <= preview_lines:
            try:
                btn.configure(state="disabled")
            except Exception:
                pass

    # If content was truncated due to line cap, offer a Full view button to open entire content safely
    if truncated_lines:
        def _open_full_attachment():
            try:
                top = tk.Toplevel(bubble_frame)
                top.title(filename)
                top.geometry('900x700')
                # Use the same renderer used elsewhere for code/text attachments so
                # the viewer is consistent (syntax highlighting, gutter, expand).
                try:
                    # Wrap length: leave some padding from window width
                    wrap_len_full = 860
                    # render_text_attachment will create its own controls inside the Toplevel
                    render_text_attachment(top, filename, ext, content, wrap_len_full, 'n', False, theme, show_expand=False)
                except Exception:
                    # Fallback to a plain Text widget if the renderer fails
                    txt = tk.Text(top, wrap='word')
                    txt.insert('1.0', content)
                    txt.configure(state='disabled')
                    txt.pack(fill='both', expand=True)
                # Add a Close button for convenience
                try:
                    btn_close = ctk.CTkButton(top, text='Close', command=top.destroy)
                    btn_close.pack(pady=6)
                except Exception:
                    pass
            except Exception:
                try:
                    messagebox.showinfo('Attachment', 'Unable to open full view')
                except Exception:
                    pass

        try:
            full_btn = ctk.CTkButton(bubble_frame, text='Open full', width=80, height=22, command=_open_full_attachment)
            full_btn.pack(anchor=side_anchor, padx=10, pady=(0,4))
        except Exception:
            pass

    return textbox, btn
