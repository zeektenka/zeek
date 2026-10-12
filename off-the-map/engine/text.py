"""Text rendering into sprites. Fonts ship in assets/fonts."""
import os
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .canvas import Sprite, rgba

FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
FONTS = {
    "anton": "Anton-Regular.ttf",              # headlines and numbers
    "type": "SpecialElite-Regular.ttf",        # typewriter labels
    "inter": "Inter-Regular.otf",              # clean text
    "inter_semi": "Inter-SemiBold.otf",
    "inter_bold": "Inter-Bold.otf",
}


@lru_cache(maxsize=256)
def font(name, px):
    return ImageFont.truetype(os.path.join(FONT_DIR, FONTS.get(name, name)), max(1, int(px)))


def measure(text, name, size):
    """Width of one line in world units at a given font size (world units)."""
    f = font(name, 200)
    return f.getlength(text) * size / 200


def text_rgba(text, name="inter", size=40, res=1.0, color="#ffffff", tracking=0.0,
              line_height=1.15, align="left", pad=0.15):
    """Render (multi-line) text to a straight-alpha uint8 RGBA array.

    size and pad are world units (pad is a fraction of size); tracking is a
    fraction of size added between letters.
    """
    px = size * res
    f = font(name, px)
    lines = text.split("\n")
    asc, desc = f.getmetrics()
    lh = px * line_height
    track = tracking * px

    def line_w(s):
        return sum(f.getlength(c) for c in s) + track * max(len(s) - 1, 0) if track else f.getlength(s)

    widths = [line_w(s) for s in lines]
    p = int(pad * px) + 2
    W = int(max(widths) + 2 * p) + 1
    H = int(lh * (len(lines) - 1) + asc + desc + 2 * p) + 1
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    for i, (s, w) in enumerate(zip(lines, widths)):
        x = p + {"left": 0, "center": (max(widths) - w) / 2, "right": max(widths) - w}[align]
        y = p + i * lh
        if track:
            for c in s:
                d.text((x, y), c, font=f, fill=255)
                x += f.getlength(c) + track
        else:
            d.text((x, y), s, font=f, fill=255)
    a = np.asarray(img)
    r, g, b, al = rgba(color)
    out = np.zeros((H, W, 4), np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = int(r * 255), int(g * 255), int(b * 255)
    out[..., 3] = (a * al).astype(np.uint8)
    return out


def text_sprite(text, name="inter", size=40, res=1.0, color="#ffffff", **kw):
    return Sprite(text_rgba(text, name, size, res, color, **kw), res)
