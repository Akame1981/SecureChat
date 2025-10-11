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

    cols = 3
    cell_size = 160
    r = 0
    c = 0

    def _is_video_name(name: str) -> bool:
        if not name:
            return False
        name = name.lower()
        for ext in ('.mp4', '.mov', '.mkv', '.webm', '.avi', '.flv', '.wmv'):
            if name.endswith(ext):
                return True
        return False

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

    for m in msgs:
        att = m.get('attachment_meta') or {}
        if not isinstance(att, dict):
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

        # Square cell
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

        # Render content
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

        c += 1
        if c >= cols:
            c = 0
            r += 1

    if r == 0 and c == 0:
        ctk.CTkLabel(parent_frame, text='No media yet', text_color=(theme or {}).get('sidebar_text', 'white')).pack(pady=8)
