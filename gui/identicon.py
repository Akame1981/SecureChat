"""Identicon generation utilities.

This module provides the `generate_identicon` function which creates a
circular identicon PIL Image from string data (e.g. a public key).
"""
from PIL import Image, ImageDraw
import hashlib


def generate_identicon(data: str, size: int = 96, block_size: int = 8) -> Image.Image:
    """
    Generate a circular identicon avatar from the provided string data.

    - data: input string (for example, a public key)
    - size: output image size in pixels (square)
    - block_size: size of the squares used when drawing the identicon

    Returns a PIL Image with an alpha channel (RGBA) containing a circular
    identicon.
    """
    # Hash the data to bytes
    hash_bytes = hashlib.sha256(data.encode()).digest()

    # Define colors based on hash
    colors = [
        f"#{hash_bytes[0]:02x}{hash_bytes[1]:02x}{hash_bytes[2]:02x}",
        f"#{hash_bytes[3]:02x}{hash_bytes[4]:02x}{hash_bytes[5]:02x}",
        f"#{hash_bytes[6]:02x}{hash_bytes[7]:02x}{hash_bytes[8]:02x}"
    ]

    img = Image.new("RGB", (size, size), "white")
    draw = ImageDraw.Draw(img)

    blocks = max(1, size // block_size)

    for y in range(blocks):
        for x in range((blocks + 1) // 2):  # symmetry
            idx = (y * blocks + x) % len(hash_bytes)
            color_idx = hash_bytes[idx] % len(colors)
            if hash_bytes[idx] % 2 == 0:
                fill_color = colors[color_idx]
                # Draw symmetric blocks
                draw.rectangle([x * block_size, y * block_size, (x + 1) * block_size - 1, (y + 1) * block_size - 1], fill=fill_color)
                draw.rectangle([(blocks - 1 - x) * block_size, y * block_size, (blocks - x) * block_size - 1, (y + 1) * block_size - 1], fill=fill_color)

    # Make it circular by applying an alpha mask
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)

    return img
