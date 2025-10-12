import imghdr
import io
import os
import sys
import tempfile
import subprocess
import tkinter as tk
from tkinter import Toplevel, filedialog, messagebox
import customtkinter as ctk
from PIL import Image, ImageDraw
from datetime import datetime


def fetch_attachment_bytes(app, att_id: str, selected_group_id: str) -> bytes | None:
    try:
        from utils.attachments import load_attachment, AttachmentNotFound
        try:
            return load_attachment(att_id, getattr(app, 'pin', ''))
        except AttachmentNotFound:
            pass
    except Exception:
        pass
    try:
        import requests
        r = requests.get(f"{app.SERVER_URL}/groups/attachments/{att_id}", params={"group_id": selected_group_id, "user_id": app.my_pub_hex}, verify=getattr(app, 'SERVER_CERT', None), timeout=60)
        if r.ok:
            return r.content
    except Exception:
        pass
    return None


def open_media_preview(parent, app, att_meta: dict, selected_group_id: str, theme: dict | None = None):
    try:
        att_id = att_meta.get('att_id')
        if not att_id:
            return
        data = fetch_attachment_bytes(app, att_id, selected_group_id)
        if data is None:
            try:
                messagebox.showerror('Attachment', 'Attachment not available')
            except Exception:
                pass
            return
        kind = None
        try:
            kind = imghdr.what(None, h=data)
        except Exception:
            kind = None

        win = Toplevel(parent)
        win.title(att_meta.get('name', 'Preview'))
        win.geometry('600x400')
        if kind:
            try:
                img = Image.open(io.BytesIO(data))
                img.thumbnail((800, 600))
                ctk_img = ctk.CTkImage(light_image=img, size=img.size)
                lbl = ctk.CTkLabel(win, image=ctk_img, text='')
                lbl.image = ctk_img
                lbl.pack(expand=True, fill='both')
            except Exception:
                try:
                    messagebox.showerror('Attachment', 'Failed to render image')
                except Exception:
                    pass
        else:
            try:
                txt = data.decode('utf-8', errors='replace')
                # Prefer to reuse the existing rich text viewer used elsewhere
                try:
                    # render_text_attachment will create a filename label, gutter, syntax highlighting
                    from gui.text_attachment_view import render_text_attachment
                    name = att_meta.get('name', 'file') if isinstance(att_meta, dict) else 'file'
                    # extension without leading dot
                    try:
                        ext = os.path.splitext(name)[1].lstrip('.')
                    except Exception:
                        ext = ''
                    # pass a reasonable wrap width for the preview window
                    wrap_len = 560
                    # render into the preview Toplevel
                    # Do not show the Expand button in media-channel previews; keep it for DMs
                    # Provide full text so the preview window can expand to the full file
                    from gui.text_attachment_view import render_text_attachment as _rt
                    _rt(win, name, ext, txt, wrap_len, 'n', False, theme, show_expand=False, full_text=txt)
                except Exception:
                    # Fallback: simple read-only Text widget
                    t = tk.Text(win)
                    t.insert('1.0', txt)
                    t.configure(state='disabled')
                    t.pack(fill='both', expand=True)
            except Exception:
                try:
                    messagebox.showerror('Attachment', 'Failed to render text file')
                except Exception:
                    pass

        def _save():
            try:
                default_name = att_meta.get('name', 'file')
                path = filedialog.asksaveasfilename(defaultextension='', initialfile=default_name)
                if path:
                    with open(path, 'wb') as f:
                        f.write(data)
                    try:
                        app.notifier.show(f"Saved {default_name}")
                    except Exception:
                        pass
            except Exception:
                pass

        btn = ctk.CTkButton(win, text='Save', command=_save, fg_color=(theme or {}).get('button_send', '#4a90e2'))
        btn.pack(pady=6)
    except Exception:
        pass


def render_media_grid(parent_frame, app, msgs: list[dict], selected_group_id: str, theme: dict | None = None):
    try:
        for w in parent_frame.winfo_children():
            w.destroy()
    except Exception:
        pass

    grid = ctk.CTkFrame(parent_frame, fg_color=(theme or {}).get('background', '#2e2e3f'))
    grid.pack(fill='both', expand=True, padx=8, pady=8)

    # Responsive grid layout: compute columns and cell size from available width
    # Minimum cell size and spacing can be tuned
    min_cell = 140
    spacing = 12

    # We'll re-render the grid on resize events with a small debounce
    _after = {'id': None}

    def _compute_layout(avail_width: int):
        try:
            avail = max(200, avail_width - 32)  # account for padding
            cols = max(1, avail // (min_cell + spacing))
            # compute cell size to fill available space
            cell = max(min_cell, (avail - (cols + 1) * spacing) // cols)
            return cols, cell
        except Exception:
            return 3, 160

    def _is_video_name(name: str) -> bool:
        if not name:
            return False
        name = name.lower()
        for ext in ('.mp4', '.mov', '.mkv', '.webm', '.avi', '.flv', '.wmv'):
            if name.endswith(ext):
                return True
        return False

    # Helper: small caption overlay with sender name and timestamp
    def _format_sender_name(sender_id: str) -> str:
        try:
            # Prefer a human-friendly name if available in recipients store.
            # get_recipient_name requires the user's pin for decryption of the recipients file.
            from utils.recipients import get_recipient_name
            try:
                name = get_recipient_name(sender_id, getattr(app, 'pin', ''))
                if name:
                    return name
            except Exception:
                pass
        except Exception:
            pass
        # Fallback: display a shortened form of the key (first 8 chars) to avoid showing the full key
        try:
            s = str(sender_id) or ''
            if len(s) > 12:
                return s[:8] + '...'
            return s
        except Exception:
            return ''

    def _format_timestamp(ts) -> str:
        try:
            t = float(ts)
            return datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M')
        except Exception:
            return ''

    def _attach_caption(cell_widget, sender_id, ts):
        try:
            sender_text = _format_sender_name(sender_id)
            ts_text = _format_timestamp(ts)
            if sender_text and ts_text:
                caption_text = f"{sender_text} · {ts_text}"
            else:
                caption_text = sender_text or ts_text or ''
            if not caption_text:
                return
            caption = ctk.CTkLabel(cell_widget, text=caption_text, text_color=(theme or {}).get('sidebar_text', 'white'))
            try:
                caption.configure(font=('Arial', 9))
            except Exception:
                pass
            # Place near bottom-left inside the cell
            try:
                caption.place(relx=0.02, rely=0.96, anchor='sw')
            except Exception:
                try:
                    caption.pack(side='bottom', anchor='w', padx=4, pady=2)
                except Exception:
                    pass
        except Exception:
            pass

    def _open_with_system(filepath: str):
        try:
            if sys.platform.startswith('win'):
                os.startfile(filepath)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', filepath])
            else:
                subprocess.Popen(['xdg-open', filepath])
        except Exception:
            try:
                messagebox.showinfo('Open', f'File saved to {filepath}')
            except Exception:
                pass

    def _download_and_save(parent_widget, app, att, selected_group_id):
        try:
            att_id = att.get('att_id')
            if not att_id:
                try:
                    messagebox.showerror('Attachment', 'Missing attachment id')
                except Exception:
                    pass
                return
            data = fetch_attachment_bytes(app, att_id, selected_group_id)
            if data is None:
                try:
                    messagebox.showerror('Attachment', 'Attachment not available')
                except Exception:
                    pass
                return
            default_name = att.get('name', 'file')
            path = filedialog.asksaveasfilename(defaultextension='', initialfile=default_name)
            if path:
                with open(path, 'wb') as f:
                    f.write(data)
                try:
                    app.notifier.show(f'Saved {default_name}')
                except Exception:
                    pass
        except Exception as e:
            try:
                messagebox.showerror('Attachment', f'Failed to download: {e}')
            except Exception:
                pass

    # Each message may contain one or more attachments. Treat every attachment as its own post
    # and render one grid cell per attachment. Also support ATTACH: envelopes in message text.
    # We'll render inside a function so we can re-run it when the parent frame resizes.
    def _build_grid():
        try:
            for w in grid.winfo_children():
                w.destroy()
        except Exception:
            pass

        # determine available width
        try:
            avail_w = parent_frame.winfo_width()
            if not avail_w or avail_w < 100:
                avail_w = parent_frame.winfo_toplevel().winfo_width()
        except Exception:
            avail_w = 800

        cols, cell_size = _compute_layout(avail_w)
        r = 0
        c = 0

        for m in msgs:
            raw_att = m.get('attachment_meta')
            text = m.get('text')

            att_items = []
            # If the DB stored a list of attachments, expand it
            if isinstance(raw_att, list):
                att_items = list(raw_att)
            elif isinstance(raw_att, dict):
                att_items = [raw_att]
            else:
                # Try parsing ATTACH envelope in text (e.g., older messages)
                if isinstance(text, str) and text.startswith('ATTACH:'):
                    try:
                        from utils.attachment_envelope import parse_attachment_envelope
                        placeholder, parsed = parse_attachment_envelope(text)
                        if parsed:
                            att_items = [parsed]
                    except Exception:
                        att_items = []

            if not att_items:
                continue

            for att in att_items:
                if not isinstance(att, dict):
                    # If att is a simple id string, map it to a dict
                    try:
                        att = {'att_id': str(att)}
                    except Exception:
                        continue
                try:
                    att = dict(att)
                    att['group_id'] = selected_group_id
                except Exception:
                    pass

                data = None
                try:
                    data = fetch_attachment_bytes(app, att.get('att_id'), selected_group_id)
                except Exception:
                    data = None

                # Square cell (one per attachment)
                cell = ctk.CTkFrame(grid, width=cell_size, height=cell_size, fg_color=(theme or {}).get('bubble_other', '#2a2a3a'))
                cell.grid(row=r, column=c, padx=6, pady=6)
                try:
                    cell.grid_propagate(False)
                except Exception:
                    pass

                # Helper to bind right-click download
                def _bind_download(widget, a=att):
                    try:
                        def _on_right(ev, a2=a):
                            menu = tk.Menu(widget, tearoff=0)
                            menu.add_command(label='Download', command=lambda: _download_and_save(widget, app, a2, selected_group_id))
                            try:
                                menu.tk_popup(ev.x_root, ev.y_root)
                            finally:
                                menu.grab_release()
                        widget.bind('<Button-3>', _on_right)
                    except Exception:
                        pass

                # Render content for this attachment
                if data:
                    try:
                        if imghdr.what(None, h=data):
                            img = Image.open(io.BytesIO(data)).convert('RGBA')
                            # Fit into square while preserving aspect
                            img.thumbnail((cell_size - 10, cell_size - 10))
                            ctk_img = ctk.CTkImage(light_image=img, size=img.size)
                            lbl = ctk.CTkLabel(cell, image=ctk_img, text='')
                            lbl.image = ctk_img
                            lbl.place(relx=0.5, rely=0.5, anchor='center')
                            lbl.bind('<Button-1>', lambda e, a=att: open_media_preview(parent_frame, app, a, selected_group_id, theme))
                            _bind_download(lbl)
                        else:
                            # Not an image; check if looks like text
                            try:
                                txt = data.decode('utf-8', errors='replace')
                                display = txt.strip()[:400]
                                txt_lbl = ctk.CTkLabel(cell, text=display, wraplength=cell_size - 16, justify='left')
                                txt_lbl.place(relx=0.5, rely=0.5, anchor='center')
                                txt_lbl.bind('<Button-1>', lambda e, a=att: open_media_preview(parent_frame, app, a, selected_group_id, theme))
                                _bind_download(txt_lbl)
                            except Exception:
                                # Binary (likely video or other). Detect by filename.
                                name = att.get('name', '')
                                if _is_video_name(name):
                                    # Create placeholder with play triangle
                                    try:
                                        thumb = Image.new('RGBA', (cell_size - 10, cell_size - 10), (30, 30, 30, 255))
                                        draw = ImageDraw.Draw(thumb)
                                        # draw triangle
                                        w, h = thumb.size
                                        tri = [(w*0.35, h*0.25), (w*0.35, h*0.75), (w*0.75, h*0.5)]
                                        draw.polygon(tri, fill=(255, 255, 255, 255))
                                        ctk_img = ctk.CTkImage(light_image=thumb, size=thumb.size)
                                        lbl = ctk.CTkLabel(cell, image=ctk_img, text='')
                                        lbl.image = ctk_img
                                        lbl.place(relx=0.5, rely=0.5, anchor='center')
                                        def _open_video(e, a=att):
                                            # write temp file and open
                                            try:
                                                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='_' + (a.get('name') or 'video'))
                                                tmp.write(data)
                                                tmp.flush()
                                                tmp.close()
                                                _open_with_system(tmp.name)
                                            except Exception:
                                                pass
                                        lbl.bind('<Button-1>', _open_video)
                                        _bind_download(lbl)
                                    except Exception:
                                        lbl = ctk.CTkLabel(cell, text=name)
                                        lbl.place(relx=0.5, rely=0.5, anchor='center')
                                        _bind_download(lbl)
                                else:
                                    name = att.get('name', 'file')
                                    lbl = ctk.CTkLabel(cell, text=name)
                                    lbl.place(relx=0.5, rely=0.5, anchor='center')
                                    _bind_download(lbl)
                    except Exception:
                        lbl = ctk.CTkLabel(cell, text=att.get('name', 'file'))
                        lbl.place(relx=0.5, rely=0.5, anchor='center')
                        _bind_download(lbl)
                else:
                    # No bytes available; show name and allow download/preview attempt
                    name = att.get('name', 'file')
                    lbl = ctk.CTkLabel(cell, text=name)
                    lbl.place(relx=0.5, rely=0.5, anchor='center')
                    lbl.bind('<Button-1>', lambda e, a=att: open_media_preview(parent_frame, app, a, selected_group_id, theme))
                    _bind_download(lbl)

                # Add small caption with sender and timestamp for this attachment
                try:
                    _attach_caption(cell, m.get('sender_id'), m.get('timestamp'))
                except Exception:
                    pass

                c += 1
                if c >= cols:
                    c = 0
                    r += 1

        # If nothing rendered, show placeholder
        try:
            if r == 0 and c == 0:
                ctk.CTkLabel(parent_frame, text='No media yet', text_color=(theme or {}).get('sidebar_text', 'white')).pack(pady=8)
        except Exception:
            pass

    # Debounced resize handler
    def _on_config(ev=None):
        try:
            if _after.get('id'):
                parent_frame.after_cancel(_after['id'])
        except Exception:
            pass
        try:
            _after['id'] = parent_frame.after(120, _build_grid)
        except Exception:
            try:
                _build_grid()
            except Exception:
                pass

    try:
        parent_frame.bind('<Configure>', _on_config)
    except Exception:
        pass

    # initial render
    _build_grid()
