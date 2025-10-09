import sys
import customtkinter as ctk
import tkinter as tk
from datetime import datetime, date
from utils.recipients import get_recipient_name
import base64
from utils.attachments import load_attachment, AttachmentNotFound
import requests, base64 as _b64
from tkinter import filedialog, messagebox
from gui.identicon import generate_identicon
from PIL import Image, ImageTk
import io
import hashlib
from collections import OrderedDict
import threading
from concurrent.futures import ThreadPoolExecutor

# Thread pool for background image/attachment work
_IMAGE_EXECUTOR = ThreadPoolExecutor(max_workers=3)
# Lock to protect the image cache
_image_cache_lock = threading.Lock()


def _human_size(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    f = float(n)
    for u in units:
        if f < 1024 or u == units[-1]:
            return f"{f:.1f} {u}"
        f /= 1024
    return f"{n} B"


def _parse_bool(val, default=False):
    """Parse various truthy/falsey representations into a boolean.

    Accepts bool, strings like 'true'/'false' or numeric values.
    """
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes", "y")
    try:
        return bool(int(val))
    except Exception:
        try:
            return bool(val)
        except Exception:
            return default


def _format_time(ts: float | None) -> str:
    if not ts:
        return datetime.now().strftime('%H:%M')
    dt = datetime.fromtimestamp(ts)
    today = date.today()
    if dt.date() == today:
        return dt.strftime('%H:%M')
    return dt.strftime('%Y-%m-%d %H:%M')


def _compute_wrap(parent, max_width=520, min_width=180, padding=140):
    try:
        # Use cached value when the application width hasn't changed to avoid
        # recalculating wrap length for every bubble creation.
        parent.update_idletasks()
        try:
            top = parent.winfo_toplevel()
            app_w = top.winfo_width()
        except Exception:
            app_w = parent.winfo_width()

        if not app_w or app_w <= 1:
            return 420

        cache = getattr(parent, '_wrap_cache', None)
        if cache and cache[0] == app_w:
            return cache[1]

        target = int(app_w * 0.8)
        usable = max(min_width, min(max_width, target))
        try:
            parent._wrap_cache = (app_w, usable)
        except Exception:
            pass
        return usable
    except Exception:
        return 420


def _soft_break(text: str, limit: int = 48) -> str:
    """Insert zero-width space into very long unbroken sequences to allow wrapping."""
    out = []
    cur = []
    for ch in text:
        cur.append(ch)
        if ch.isspace():
            out.extend(cur)
            cur = []
        elif len(cur) >= limit:
            out.extend(cur)
            out.append('\u200b')  # zero-width space
            cur = []
    out.extend(cur)
    return ''.join(out)


def _blend_hex(c1: str, c2: str, t: float) -> str:
    try:
        if c1.startswith('#'): c1 = c1[1:]
        if c2.startswith('#'): c2 = c2[1:]
        r1,g1,b1 = int(c1[0:2],16), int(c1[2:4],16), int(c1[4:6],16)
        r2,g2,b2 = int(c2[0:2],16), int(c2[2:4],16), int(c2[4:6],16)
        r = int(r1 + (r2-r1)*t)
        g = int(g1 + (g2-g1)*t)
        b = int(b1 + (b2-b1)*t)
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return c2


def _fade_in(widget: ctk.CTkFrame, start_color: str, end_color: str, steps: int = 6, delay: int = 22):
    # For performance we avoid running a multi-step fade. Set the final
    # color immediately to preserve appearance without the animation cost.
    try:
        widget.configure(fg_color=end_color)
    except Exception:
        pass


# Simple in-memory cache for decoded PIL images to avoid repeated decoding
# keyed by attachment id or blob hash. Keeps a small bounded cache.
_image_cache: "OrderedDict[str, object]" = OrderedDict()
_IMAGE_CACHE_MAX = 32


def create_message_bubble(parent, sender_pub, text, my_pub_hex, pin, app=None, timestamp=None, attachment_meta=None):
    """Create a styled message bubble.

    Returns the inner bubble frame (for existing theme update logic). Adds:
    - Outer transparent container for alignment without stretching bubble.
    - Sender line + separate timestamp label.
    - Dynamic wrap length based on parent width.
    - Right-click context menu (Copy text / Copy sender).
    - Hover highlight effect.
    - Theme-aware border & colors.
    """
    display_sender = "You" if sender_pub == my_pub_hex else get_recipient_name(sender_pub, pin) or sender_pub
    is_you = display_sender == "You"

    # Resolve theme: prefer ThemeManager on the app if present
    theme = {}
    if app is not None and hasattr(app, 'theme_manager') and hasattr(app.theme_manager, 'theme_colors'):
        theme = app.theme_manager.theme_colors.get(app.theme_manager.current_theme, {})
    elif app and hasattr(app, "theme_colors") and hasattr(app, "current_theme"):
        theme = app.theme_colors.get(app.current_theme, {})

    # Theme fallbacks
    bubble_you = theme.get("bubble_you", "#5865F2")
    bubble_other = theme.get("bubble_other", "#2b2d31")
    bubble_border_you = theme.get("bubble_border_you", "#4854c6")
    bubble_border_other = theme.get("bubble_border_other", "#3a3c41")
    text_you = theme.get("bubble_you_text", theme.get("text", "#ffffff"))
    text_other = theme.get("bubble_other_text", theme.get("text", "#e5e5e5"))
    timestamp_color = theme.get("timestamp_text", "#a0a0a0")

    bubble_color = bubble_you if is_you else bubble_other
    border_color = bubble_border_you if is_you else bubble_border_other
    text_color = text_you if is_you else text_other
    # Robust parsing for bubble_transparent; default to False
    transparent_mode = _parse_bool(theme.get('bubble_transparent', False), default=False)
    # Option to align both participants' bubbles to the left
    align_both_left = _parse_bool(theme.get('bubble_align_both_left', False), default=False)

    # Parent may track last bubble for grouping
    prev_same = False
    last_bubble = getattr(parent, '_last_bubble', None)
    if last_bubble is not None and getattr(last_bubble, '_sender_pub', None) == sender_pub:
        prev_same = True

    # Container keeps layout width while bubble keeps natural width
    outer = ctk.CTkFrame(parent, fg_color="transparent")
    outer.pack(fill="x", pady=(1 if prev_same else 6, 1), padx=6)

    # Decide side/anchor. If align_both_left is True, force left alignment for everyone.
    side_anchor = "w" if align_both_left else ("e" if is_you else "w")
    # Compute packing side and padding so first messages and follow-ups align
    if align_both_left:
        _pack_side = 'left'
        _pack_pad = (4, 6)
    else:
        if is_you:
            _pack_side = 'right'
            _pack_pad = (6, 4)
        else:
            _pack_side = 'left'
            _pack_pad = (4, 6)
    row = ctk.CTkFrame(outer, fg_color="transparent")
    row.pack(fill='x')
    # If transparent mode enabled, bubble initial background is transparent
    bubble_frame = ctk.CTkFrame(
        row,
        fg_color=("transparent" if transparent_mode else bubble_color),
        corner_radius=16,
        border_width=1,
        border_color=border_color
    )
    bubble_frame.is_you = is_you
    bubble_frame._outer = outer  # reference for possible future use
    bubble_frame._sender_pub = sender_pub
    bubble_frame._timestamp_raw = timestamp

    # Dynamic width / wrap length
    wrap_len = _compute_wrap(parent)
    processed_text = _soft_break(text)

    # Top sender label (bold)
    if not prev_same:
        # Pack bubble frame into the row first (keeps previous left/right alignment)
        bubble_frame.pack(side=_pack_side, padx=_pack_pad, pady=0)

        # Create a small sender row inside the bubble (no avatar)
        try:
            sender_row = ctk.CTkFrame(bubble_frame, fg_color="transparent")
            sender_row.pack(fill='x', anchor=side_anchor, padx=10, pady=(6, 0))
            bubble_frame.sender_label = ctk.CTkLabel(
                sender_row,
                text=display_sender,
                text_color=text_color,
                font=("Roboto", 9, "bold")
            )
            bubble_frame.sender_label.pack(side='left')
        except Exception:
            # Fallback: attach sender label directly to bubble
            bubble_frame.sender_label = ctk.CTkLabel(
                bubble_frame,
                text=display_sender,
                text_color=text_color,
                font=("Roboto", 9, "bold")
            )
            bubble_frame.sender_label.pack(anchor=side_anchor, padx=10, pady=(6, 0))
    else:
        # No avatar, compact placement for continuation messages
        # Use the same packing side and padding as the initial message so runs align
        bubble_frame.pack(side=_pack_side, padx=_pack_pad, pady=0)

    # Quick image-attachment hint (extension-based) so we can adjust caption/text placement
    is_image_attachment = False
    if attachment_meta and isinstance(attachment_meta, dict) and attachment_meta.get('type', 'file') == 'file':
        nm = attachment_meta.get('name', '')
        if isinstance(nm, str) and nm.lower().split('.')[-1] in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'):
            is_image_attachment = True

    # Message text
    # Use a lightweight label instead of a Text/Textbox for performance while
    # keeping the same look. Copying is provided via Ctrl+C and the context menu.
    try:
        msg_widget = ctk.CTkLabel(
            bubble_frame,
            text=processed_text,
            wraplength=wrap_len,
            justify=("left" if align_both_left else ("right" if is_you else "left")),
            text_color=text_color,
            font=("Roboto", 12),
            fg_color='transparent'
        )
        # Make clicks focus the label so key bindings like Ctrl+C work
        msg_widget.bind('<Button-1>', lambda e=None: msg_widget.focus_set())

        def _copy_label_text(event=None):
            try:
                txt = processed_text
                bubble_frame.clipboard_clear()
                bubble_frame.clipboard_append(txt)
            except Exception:
                pass
            return 'break'

        msg_widget.bind('<Control-c>', _copy_label_text)
        msg_widget.bind('<Control-C>', _copy_label_text)
        msg_widget.pack(anchor=side_anchor, padx=10, pady=(4 if not prev_same else 2, 4))
        bubble_frame.msg_label = msg_widget  # maintain attribute name for compatibility
        bubble_frame._msg_is_textbox = False
    except Exception:
        # Extremely defensive fallback to a native tkinter Label if CTkLabel fails
        lbl = tk.Label(
            bubble_frame,
            text=processed_text,
            wraplength=wrap_len,
            justify=("left" if align_both_left else ("right" if is_you else "left")),
            fg='white' if is_you else text_other,
            font=("Roboto", 12),
            bg='SystemButtonFace'
        )
        try:
            lbl.bind('<Button-1>', lambda e=None: lbl.focus_set())
            lbl.bind('<Control-c>', lambda e=None: (bubble_frame.clipboard_clear(), bubble_frame.clipboard_append(processed_text), 'break'))
        except Exception:
            pass
        lbl.pack(anchor=side_anchor, padx=10, pady=(4 if not prev_same else 2, 4))
        bubble_frame.msg_label = lbl
        bubble_frame._msg_is_textbox = False

    # If this message references an attachment ID but doesn't include inline data,
    # it's likely going to be fetched/decoded asynchronously. In that case hide
    # the label text so the bubble shows only the background color instead of
    # any loading/caption text. The real content (image/caption) will be added
    # when the background loader completes.
    try:
        if attachment_meta and isinstance(attachment_meta, dict):
            att_id = attachment_meta.get('att_id')
            has_inline = bool(attachment_meta.get('file_b64') or attachment_meta.get('blob'))
            # If we have an att_id but no inline blob, assume lazy fetch and hide text
            if att_id and not has_inline:
                try:
                    # replace visible text with empty string to show only bubble bg
                    bubble_frame.msg_label.configure(text="")
                except Exception:
                    try:
                        # fallback for tk.Label
                        bubble_frame.msg_label.configure(text=" ")
                    except Exception:
                        pass
    except Exception:
        pass
        bubble_frame._msg_is_textbox = False

    # If this appears to be an image attachment, replace the large placeholder text with a compact caption
    try:
        if is_image_attachment and isinstance(bubble_frame.msg_label, (ctk.CTkLabel, ctk.CTkTextbox)):
            caption = None
            try:
                name = attachment_meta.get('name') if attachment_meta else None
                size = attachment_meta.get('size') if attachment_meta else None
                if name and size:
                    caption = f"{name} ({_human_size(int(size))})"
                elif name:
                    caption = name
            except Exception:
                caption = None
            if caption:
                try:
                    # For textbox, replace content; for label, set text and smaller font
                    if getattr(bubble_frame, '_msg_is_textbox', False):
                        try:
                            bubble_frame.msg_label.configure(state='normal')
                            bubble_frame.msg_label.delete('1.0', 'end')
                            bubble_frame.msg_label.insert('1.0', caption)
                            bubble_frame.msg_label.configure(state='disabled')
                        except Exception:
                            pass
                    else:
                        try:
                            bubble_frame.msg_label.configure(text=caption, font=("Roboto", 10, "italic"))
                        except Exception:
                            pass
                except Exception:
                    pass
    except Exception:
        pass

    # --- Inline image rendering for image attachments ---
    try:
        img_meta = None
        if attachment_meta and isinstance(attachment_meta, dict) and attachment_meta.get('type', 'file') == 'file':
            img_name = attachment_meta.get('name', '')
            # Quick extension-based detection
            if isinstance(img_name, str) and img_name.lower().split('.')[-1] in ('png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'):
                img_meta = attachment_meta
        # If extension didn't match but blob present, attempt to open
        if not img_meta and attachment_meta and (attachment_meta.get('file_b64') or attachment_meta.get('blob')):
            try:
                blob_b64 = attachment_meta.get('file_b64') or attachment_meta.get('blob')
                raw = base64.b64decode(blob_b64)
                # quick content sniff via PIL
                im = Image.open(io.BytesIO(raw))
                im.close()
                img_meta = attachment_meta
            except Exception:
                img_meta = None

        if img_meta:
            # Load bytes (prefer local cache)
            raw = None
            att_id = img_meta.get('att_id')
            if att_id:
                try:
                    raw = load_attachment(att_id, app.pin)
                except AttachmentNotFound:
                    raw = None
            if raw is None:
                # Try inline blob if present
                blob_b64 = img_meta.get('file_b64') or img_meta.get('blob')
                if blob_b64:
                    try:
                        raw = base64.b64decode(blob_b64)
                    except Exception:
                        raw = None
                else:
                    # Try lazy download from server if we have app context
                    try:
                        if app and att_id and hasattr(app, 'SERVER_URL') and hasattr(app, 'my_pub_hex'):
                            r = requests.get(f"{app.SERVER_URL}/download/{att_id}", params={"recipient": app.my_pub_hex}, verify=getattr(app, 'SERVER_CERT', None), timeout=20)
                            if r.ok:
                                data = r.json()
                                blob_b64 = data.get('blob')
                                if blob_b64:
                                    raw = base64.b64decode(blob_b64)
                    except Exception:
                        raw = None

            if raw:
                # Offload heavy work (decoding, PIL open, thumbnailing) to background
                # thread and update UI when ready.
                def _process_image(raw_bytes, img_meta_local, cache_key_local, wrap_len_local, bubble_frame_local, side_anchor_local):
                    import io as _io
                    pil_obj = None
                    # Try cache first (protected by lock)
                    try:
                        with _image_cache_lock:
                            if cache_key_local in _image_cache:
                                pil_obj = _image_cache[cache_key_local]
                    except Exception:
                        pil_obj = None

                    try:
                        if pil_obj is None:
                            bio = _io.BytesIO(raw_bytes)
                            pil_obj = Image.open(bio)
                    except Exception:
                        pil_obj = None

                    if pil_obj is None:
                        return None

                    # Create thumbnail copy
                    try:
                        pil_copy = pil_obj.copy()
                    except Exception:
                        pil_copy = pil_obj
                    max_dim = min(wrap_len_local, 360)
                    try:
                        pil_copy.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                    except Exception:
                        pass

                    # Cache the original pil_obj if not already cached
                    try:
                        with _image_cache_lock:
                            if cache_key_local not in _image_cache and pil_obj is not None:
                                _image_cache[cache_key_local] = pil_obj
                                try:
                                    _image_cache.move_to_end(cache_key_local)
                                except Exception:
                                    pass
                                while len(_image_cache) > _IMAGE_CACHE_MAX:
                                    try:
                                        _image_cache.popitem(last=False)
                                    except Exception:
                                        break
                    except Exception:
                        pass

                    return (pil_obj, pil_copy)

                try:
                    import io as _io
                    # Cache key: prefer att_id, otherwise hash of raw
                    cache_key = None
                    if img_meta.get('att_id'):
                        cache_key = f"id:{img_meta.get('att_id')}"
                    else:
                        h = hashlib.sha256(raw).hexdigest()
                        cache_key = f"raw:{h}"

                    # Submit background job
                    future = _IMAGE_EXECUTOR.submit(_process_image, raw, img_meta, cache_key, wrap_len, bubble_frame, side_anchor)

                    # Callback to run on main thread when ready
                    def _on_image_ready(fut):
                        try:
                            res = fut.result()
                            if not res:
                                return
                            pil_orig, pil_thumb = res
                            try:
                                ctk_img = ctk.CTkImage(light_image=pil_thumb, dark_image=pil_thumb, size=pil_thumb.size)
                            except Exception:
                                try:
                                    pil_conv = pil_thumb.convert('RGBA') if hasattr(pil_thumb, 'convert') else pil_thumb
                                    ctk_img = ctk.CTkImage(light_image=pil_conv, dark_image=pil_conv, size=pil_conv.size)
                                except Exception:
                                    return

                            # Ensure UI update happens on main thread
                            def _create_ui():
                                try:
                                    img_label = ctk.CTkLabel(bubble_frame, image=ctk_img, text="", fg_color='transparent')
                                    img_label._ctk_image = ctk_img
                                    img_label._pil_image = pil_orig
                                    img_label.pack(anchor=side_anchor, padx=10, pady=(2, 6))

                                    # Attach fullscreen/save/copy handlers (keep original logic)
                                    def _show_fullscreen(event=None):
                                        try:
                                            top = tk.Toplevel(app)
                                            top.configure(bg='black')
                                            try:
                                                top.attributes('-fullscreen', True)
                                            except Exception:
                                                w = app.winfo_screenwidth(); h = app.winfo_screenheight(); top.geometry(f"{w}x{h}+0+0")
                                            import io as _io
                                            pil_full = Image.open(_io.BytesIO(raw))
                                            sw = top.winfo_screenwidth(); sh = top.winfo_screenheight()
                                            iw, ih = pil_full.size
                                            scale = min(sw / iw, sh / ih, 1.0)
                                            new_w = int(iw * scale); new_h = int(ih * scale)
                                            pil_resized = pil_full.resize((new_w, new_h), Image.Resampling.LANCZOS)
                                            tk_img_full = ImageTk.PhotoImage(pil_resized)
                                            lbl = tk.Label(top, image=tk_img_full, bg='black')
                                            lbl.image = tk_img_full; lbl.pack(expand=True)
                                            def _close(ev=None):
                                                try: top.destroy()
                                                except Exception: pass
                                            top.bind('<Button-1>', _close); top.bind('<Escape>', _close)
                                        except Exception:
                                            try: messagebox.showinfo('Image', 'Unable to open image viewer')
                                            except Exception: pass

                                    img_label.bind('<Button-1>', _show_fullscreen)

                                    def _save_image():
                                        try:
                                            default_name = img_meta.get('name', 'image')
                                            path = filedialog.asksaveasfilename(defaultextension='', initialfile=default_name)
                                            if path:
                                                with open(path, 'wb') as f:
                                                    f.write(raw)
                                                try:
                                                    app.notifier.show(f"Saved {default_name}")
                                                except Exception:
                                                    pass
                                        except Exception as e:
                                            print('Save image failed', e)
                                            try:
                                                messagebox.showerror('Save Image', 'Failed to save image')
                                            except Exception:
                                                pass

                                    def _copy_image():
                                        try:
                                            if sys.platform.startswith('win'):
                                                try:
                                                    import ctypes, tempfile
                                                    buf = io.BytesIO(); pil_converted = Image.open(io.BytesIO(raw)).convert('RGB'); pil_converted.save(buf, format='BMP'); data = buf.getvalue()[14:]; buf.close()
                                                    CF_DIB = 8; user32 = ctypes.windll.user32; kernel32 = ctypes.windll.kernel32
                                                    user32.OpenClipboard(0); user32.EmptyClipboard(); hGlobal = kernel32.GlobalAlloc(0x0002, len(data)); ptr = kernel32.GlobalLock(hGlobal); ctypes.memmove(ptr, data, len(data)); kernel32.GlobalUnlock(hGlobal); user32.SetClipboardData(CF_DIB, hGlobal); user32.CloseClipboard()
                                                    try: app.notifier.show('Image copied to clipboard')
                                                    except Exception: pass
                                                    return
                                                except Exception as e:
                                                    print('Windows clipboard image copy failed', e)
                                            import tempfile
                                            tf = tempfile.NamedTemporaryFile(delete=False, suffix='.' + (img_meta.get('name','img').split('.')[-1]))
                                            tf.write(raw)
                                            tf.flush()
                                            tf.close()
                                            try:
                                                app.clipboard_clear()
                                                app.clipboard_append(tf.name)
                                            except Exception:
                                                try:
                                                    messagebox.showinfo('Copy Image', f'Saved temp file: {tf.name}')
                                                except Exception:
                                                    pass
                                        except Exception as e:
                                            print('Copy image failed', e)
                                            try:
                                                messagebox.showerror('Copy Image', 'Failed to copy image')
                                            except Exception:
                                                pass

                                    # Context menu
                                    try:
                                        img_menu = tk.Menu(img_label, tearoff=0)
                                        try: img_menu.configure(bg=menu_bg, fg=menu_fg, activebackground=menu_active_bg, activeforeground=menu_active_fg)
                                        except Exception: pass
                                        img_menu.add_command(label='Save Image', command=_save_image)
                                        img_menu.add_command(label='Copy Image', command=_copy_image)
                                        def _img_popup(event):
                                            try: img_menu.tk_popup(event.x_root, event.y_root)
                                            finally: img_menu.grab_release()
                                        img_label.bind('<Button-3>', _img_popup)
                                        img_label.bind('<Button-2>', _img_popup)
                                    except Exception as e:
                                        print('Image menu setup failed', e)

                                    bubble_frame._attachment_image = img_label
                                except Exception:
                                    pass

                            try:
                                parent.after(1, _create_ui)
                            except Exception:
                                # If parent isn't available, try bubble_frame
                                try:
                                    bubble_frame.after(1, _create_ui)
                                except Exception:
                                    pass

                        except Exception:
                            pass

                    # add done-callback to future
                    try:
                        future.add_done_callback(_on_image_ready)
                    except Exception:
                        # Fallback: poll result in background
                        pass
                except Exception:
                    pass
    except Exception:
        pass

    # Timestamp / meta line
    time_str = _format_time(timestamp)
    bubble_frame._time_string = time_str
    bubble_frame.time_label = ctk.CTkLabel(
        bubble_frame,
        text=time_str,
        text_color=timestamp_color,
        font=("Roboto", 8)
    )
    bubble_frame._timestamp_visible = True
    # Place timestamp on its own line below message
    bubble_frame.time_label.pack(anchor=side_anchor, padx=10, pady=(0, 4))

    # Place bubble inside outer container aligned left or right
    # Pack uses side in {left,right,top,bottom}; map e/w to right/left
    pack_side = 'right' if is_you else 'left'
    # Already packed appropriately above.
    outer._inner_bubble = bubble_frame
    bubble_frame._prev_same = prev_same
    bubble_frame._run_last = True  # assume last of its run now
    if prev_same and last_bubble is not None:
        # Previous bubble no longer last in run -> hide its timestamp by default
        try:
            last_bubble._run_last = False
            _set_timestamp_visible(last_bubble, False)
        except Exception:
            pass

    # Hover highlight (slight lighten/darken)
    base_col = "transparent" if transparent_mode else bubble_color
    hover_col = theme.get("bubble_hover_you" if is_you else "bubble_hover_other",
                          ("#6772f6" if is_you else "#32353b"))

    def on_enter(_):
        # highlight on hover even in transparent mode
        bubble_frame.configure(fg_color=hover_col)
        _set_timestamp_visible(bubble_frame, True)

    def on_leave(_):
        # revert to transparent or base color
        bubble_frame.configure(fg_color=("transparent" if transparent_mode else base_col))
        # Show timestamp only if last of run
        _set_timestamp_visible(bubble_frame, bubble_frame._run_last)

    bubble_frame.bind("<Enter>", on_enter)
    bubble_frame.bind("<Leave>", on_leave)

    # Context menu: two dark-themed options: Copy Message, Open Profile
    menu_font = ("Segoe UI", 11) if sys.platform == 'win32' else ("Arial", 11)
    menu = tk.Menu(bubble_frame, tearoff=0, font=menu_font)

    # Apply dark theme colors if available
    menu_bg = theme.get('menu_bg', '#2b2d31')
    menu_fg = theme.get('menu_fg', '#ffffff')
    menu_active_bg = theme.get('menu_active_bg', '#3a3c41')
    menu_active_fg = theme.get('menu_active_fg', '#ffffff')
    try:
        menu.configure(bg=menu_bg, fg=menu_fg, activebackground=menu_active_bg, activeforeground=menu_active_fg)
    except Exception:
        pass

    def do_copy_text():
        # Prefer selected text when available (for textbox), otherwise whole message
        try:
            if getattr(bubble_frame, '_msg_is_textbox', False):
                widget = bubble_frame.msg_label
                try:
                    widget.configure(state='normal')
                    sel = widget.get('sel.first', 'sel.last')
                except Exception:
                    sel = widget.get('1.0', 'end-1c')
                widget.configure(state='disabled')
                bubble_frame.clipboard_clear()
                bubble_frame.clipboard_append(sel)
                return
        except Exception:
            pass
        # Fallback: whole message
        bubble_frame.clipboard_clear()
        bubble_frame.clipboard_append(text)

    def do_open_profile():
        # Try to call app profile opener if available; otherwise show placeholder dialog
        try:
            if app is not None and hasattr(app, 'open_profile'):
                app.open_profile(sender_pub)
                return
            if app is not None and hasattr(app, 'show_profile'):
                app.show_profile(sender_pub)
                return
        except Exception:
            pass
        # Placeholder dialog
        try:
            from tkinter import messagebox
            messagebox.showinfo("Profile", f"Open profile for:\n{display_sender}\n\nPublic key:\n{sender_pub}")
        except Exception:
            print("Open profile placeholder for:", sender_pub)

    menu.add_command(label="Copy Message", command=do_copy_text)
    # Attachment download option if placeholder
    try:
        if attachment_meta and isinstance(attachment_meta, dict) and attachment_meta.get('type', 'file') == 'file':
            def do_save_attachment():
                # Need original encrypted blob; not stored in bubble, must be fetched from chat cache entry if available
                try:
                    raw = None
                    att_id = attachment_meta.get('att_id')
                    if att_id:
                        try:
                            raw = load_attachment(att_id, app.pin)
                        except AttachmentNotFound:
                            # Try lazy fetch from server
                            try:
                                r = requests.get(f"{app.SERVER_URL}/download/{att_id}", params={"recipient": app.my_pub_hex}, verify=app.SERVER_CERT, timeout=20)
                                if r.ok:
                                    data = r.json()
                                    blob_b64 = data.get('blob')
                                    if not blob_b64:
                                        messagebox.showerror("Attachment", "Server returned no data")
                                        return
                                    raw = _b64.b64decode(blob_b64)
                                else:
                                    messagebox.showerror("Attachment", f"Download failed: {r.status_code}")
                                    return
                            except Exception as de:
                                messagebox.showerror("Attachment", f"Download error: {de}")
                                return
                    else:
                        blob_b64 = attachment_meta.get('file_b64') or attachment_meta.get('blob')
                        if not blob_b64:
                            messagebox.showerror("Attachment", "Missing file data.")
                            return
                        raw = base64.b64decode(blob_b64)
                    default_name = attachment_meta.get('name', 'file')
                    path = filedialog.asksaveasfilename(defaultextension='', initialfile=default_name)
                    if path:
                        with open(path, 'wb') as f:
                            f.write(raw)
                        try:
                            app.notifier.show(f"Saved {default_name}")
                        except Exception:
                            pass
                except Exception as e:
                    print("Attachment save failed", e)
                    messagebox.showerror("Attachment", "Failed to save attachment")
            menu.add_command(label="Save Attachment", command=do_save_attachment)
    except Exception:
        pass
    menu.add_command(label="Open User Profile", command=do_open_profile)

    def popup(event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # Bind popup to clickable widgets
    try:
        bubble_frame.msg_label.bind("<Button-3>", popup)
    except Exception:
        pass
    if hasattr(bubble_frame, 'sender_label'):
        try:
            bubble_frame.sender_label.bind("<Button-3>", popup)
        except Exception:
            pass
    try:
        bubble_frame.time_label.bind("<Button-3>", popup)
    except Exception:
        pass

    # For theme refresh logic elsewhere
    bubble_frame._theme_roles = {
        "base_col": base_col,
        "hover_col": hover_col,
        "text_color": text_color,
        "timestamp_color": timestamp_color,
        "border_color": border_color,
    }

    # Fade-in animation (skip if transparent to preserve background)
    if not transparent_mode:
        back = theme.get('background', '#1e1f22') if isinstance(theme.get('background', '#1e1f22'), str) else '#1e1f22'
        _fade_in(bubble_frame, _blend_hex(back, base_col, 0.15), base_col)

    # Update parent last bubble tracking
    parent._last_bubble = bubble_frame
    parent._last_sender = sender_pub

    # Auto-scroll to bottom
    try:
        parent._parent_canvas.update_idletasks()
        parent._parent_canvas.yview_moveto(1.0)
    except Exception:
        pass

    return bubble_frame
    


def recolor_message_bubble(bubble_frame, theme: dict):
    """Recolor an existing bubble when theme changes."""
    if not hasattr(bubble_frame, 'is_you'):
        return
    is_you = bubble_frame.is_you
    bubble_you = theme.get("bubble_you", "#5865F2")
    bubble_other = theme.get("bubble_other", "#2b2d31")
    bubble_border_you = theme.get("bubble_border_you", "#4854c6")
    bubble_border_other = theme.get("bubble_border_other", "#3a3c41")
    text_you = theme.get("bubble_you_text", theme.get("text", "#ffffff"))
    text_other = theme.get("bubble_other_text", theme.get("text", "#e5e5e5"))
    timestamp_color = theme.get("timestamp_text", "#a0a0a0")
    transparent_mode = _parse_bool(theme.get('bubble_transparent', False), default=False)
    base_col = "transparent" if transparent_mode else (bubble_you if is_you else bubble_other)
    border_color = bubble_border_you if is_you else bubble_border_other
    text_color = text_you if is_you else text_other
    hover_col = theme.get("bubble_hover_you" if is_you else "bubble_hover_other",
                          ("#6772f6" if is_you else "#32353b"))
    # Respect transparent mode when setting fg_color
    try:
        bubble_frame.configure(fg_color=("transparent" if transparent_mode else base_col), border_color=border_color)
    except Exception:
        bubble_frame.configure(border_color=border_color)
    if hasattr(bubble_frame, 'sender_label'):
        try:
            bubble_frame.sender_label.configure(text_color=text_color)
        except Exception:
            pass
    # Recolor message widget (textbox or label)
    try:
        # CTk widgets use `text_color`, native tk.Label uses `fg`.
        try:
            bubble_frame.msg_label.configure(text_color=text_color)
        except Exception:
            try:
                bubble_frame.msg_label.configure(fg=text_color)
            except Exception:
                pass
        try:
            bubble_frame.time_label.configure(text_color=timestamp_color)
        except Exception:
            try:
                bubble_frame.time_label.configure(fg=timestamp_color)
            except Exception:
                pass
    except Exception:
        pass
    bubble_frame._theme_roles = {
        "base_col": base_col,
        "hover_col": hover_col,
        "text_color": text_color,
        "timestamp_color": timestamp_color,
        "border_color": border_color,
    }

    # Restore timestamp visibility according to run status
    _set_timestamp_visible(bubble_frame, getattr(bubble_frame, '_run_last', True))


def _set_timestamp_visible(bubble_frame, visible: bool):
    if not hasattr(bubble_frame, 'time_label'):
        return
    if visible:
        if bubble_frame.time_label.cget('text') != bubble_frame._time_string:
            bubble_frame.time_label.configure(text=bubble_frame._time_string)
    else:
        if bubble_frame.time_label.cget('text') != '':
            bubble_frame.time_label.configure(text='')