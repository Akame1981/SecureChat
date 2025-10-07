"""Identicon generation utilities.

This module provides the `generate_identicon` function which creates a
circular identicon PIL Image from string data (e.g. a public key).
"""
from PIL import Image, ImageDraw
import hashlib


def generate_identicon(data: str, size: int = 96, *, grid: int = 6) -> Image.Image:
    """Generate a circular identicon avatar from the provided string data.

    Why your small (sidebar) identicon looked different than the large (profile window):
    Previously the pattern density was derived from the output size (blocks = size // block_size).
    So a 32px icon used far fewer squares than a 96px icon, producing a *different* pattern that
    felt "zoomed" instead of the same pattern at a different scale.

    This version uses a fixed grid (default 6x6 with horizontal symmetry) and renders a canonical
    high-resolution image, then scales it to the requested size. That guarantees the *same pattern*
    independent of the size you ask for.

    Args:
        data:     Input string (e.g. public key)
        size:     Final output size (square) in pixels
        grid:     Number of columns (full width). Pattern is mirrored horizontally.

    Returns:
        A PIL RGBA Image of the identicon.
    """
    if not data:
        data = "?"

    hash_bytes = hashlib.sha256(data.encode()).digest()

    # Choose a stable color triad from the hash
    colors = [
        f"#{hash_bytes[0]:02x}{hash_bytes[1]:02x}{hash_bytes[2]:02x}",
        f"#{hash_bytes[3]:02x}{hash_bytes[4]:02x}{hash_bytes[5]:02x}",
        f"#{hash_bytes[6]:02x}{hash_bytes[7]:02x}{hash_bytes[8]:02x}",
    ]

    # Render at a canonical base size for crisp downscaling (e.g. each cell 16px)
    cell_px = 16
    base_size = grid * cell_px
    base_img = Image.new("RGB", (base_size, base_size), "white")
    draw = ImageDraw.Draw(base_img)

    half_cols = (grid + 1) // 2  # include middle if odd

    for y in range(grid):
        for x in range(half_cols):
            idx = (y * grid + x) % len(hash_bytes)
            byte = hash_bytes[idx]
            if byte % 2 == 0:  # fill condition
                color = colors[byte % len(colors)]
                x0 = x * cell_px
                y0 = y * cell_px
                x1 = x0 + cell_px - 1
                y1 = y0 + cell_px - 1
                draw.rectangle([x0, y0, x1, y1], fill=color)
                # mirror
                mx = grid - 1 - x
                if mx != x:  # avoid double-drawing center column when odd
                    mx0 = mx * cell_px
                    mx1 = mx0 + cell_px - 1
                    draw.rectangle([mx0, y0, mx1, y1], fill=color)

    # Apply circular mask on base
    mask = Image.new("L", (base_size, base_size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, base_size, base_size), fill=255)
    base_img.putalpha(mask)

    # Scale to requested size if different
    if base_size != size:
        base_img = base_img.resize((size, size), Image.Resampling.LANCZOS)

    return base_img
