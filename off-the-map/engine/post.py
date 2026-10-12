"""Finishing: background gradients, glow, vignette and film grain.

The gradient and vignette fields depend only on canvas size and parameters,
never on time, so they are built once per worker process and reused. That is
most of the per-frame cost of a feature-length render.
"""
import cv2
import numpy as np

from .canvas import rgba

_fields = {}
_grain_bank = {}


def _radius_field(W, H, cx, cy, radius):
    """Normalised distance from (cx, cy), aspect-corrected. Cached."""
    key = ("r", W, H, round(cx, 4), round(cy, 4), round(radius, 4))
    f = _fields.get(key)
    if f is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        f = np.sqrt(((xx / W - cx) * W / H) ** 2 + (yy / H - cy) ** 2) / radius
        _fields[key] = f
    return f


def radial(cv, inner, outer, cx=0.5, cy=0.45, radius=0.9):
    """Soft radial gradient background (centre colour -> edge colour)."""
    key = ("grad", cv.W, cv.H, inner, outer, round(cx, 4), round(cy, 4), round(radius, 4))
    img = _fields.get(key)
    if img is None:
        u = np.clip(_radius_field(cv.W, cv.H, cx, cy, radius), 0, 1)[..., None]
        u = u * u * (3 - 2 * u)
        a, b = np.array(rgba(inner)[:3], np.float32), np.array(rgba(outer)[:3], np.float32)
        img = (a * (1 - u) + b * u).astype(np.float32)
        _fields[key] = img
    cv.buf[..., :3] = img
    cv.buf[..., 3] = 1


def vignette(cv, strength=0.45, radius=0.75):
    key = ("vig", cv.W, cv.H, round(strength, 4), round(radius, 4))
    v = _fields.get(key)
    if v is None:
        d = _radius_field(cv.W, cv.H, 0.5, 0.5, radius)
        v = np.clip(1 - strength * np.clip(d, 0, 1.4) ** 2.2, 0, 1).astype(np.float32)[..., None]
        _fields[key] = v
    cv.buf[..., :3] *= v


def fast_blur(img, sigma):
    """Gaussian blur that downsamples first when sigma is large.

    A soft glow or shadow has no detail to lose, and blurring a 2400x1350
    canvas at sigma 27 directly costs over a second a frame.
    """
    if sigma <= 0:
        return img
    if sigma <= 6:
        return cv2.GaussianBlur(img, (0, 0), sigma)
    h, w = img.shape[:2]
    f = min(int(sigma / 4), 8)
    small = cv2.resize(img, (max(2, w // f), max(2, h // f)), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), sigma / f)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


def glow_pop(cv, radius=18.0, strength=0.8, alpha=1.0):
    """Close a cv.push() group with a glow: blurred copy screened underneath."""
    layer = cv.buf
    cv.buf = cv._stack.pop()
    g = fast_blur(layer, radius * cv.k) * strength * alpha
    cv._composite(g, 0, 0, 1.0, "screen")
    cv._composite(layer, 0, 0, alpha, "normal")


def grain(img, t, amount=0.028, size=1.2, seed=0, pad=192):
    """Animated monochrome film grain on the final uint8 frame. Also hides
    colour banding after YouTube compression.

    One oversized noise plate is built per worker and a different crop of it is
    used each frame, so the grain never repeats visibly while costing a single
    saturating 8-bit add. Doing this in float was ~0.25s a frame, which is two
    hours over a feature-length render.
    """
    h, w = img.shape[:2]
    key = (h, w, round(size, 3), round(amount, 4), seed, pad)
    plate = _grain_bank.get(key)
    if plate is None:
        rng = np.random.default_rng(seed + 977)
        H, W = h + pad, w + pad
        n = rng.normal(0, 1, (int(H / size) + 1, int(W / size) + 1)).astype(np.float32)
        if size != 1:
            n = cv2.resize(n, (W, H), interpolation=cv2.INTER_LINEAR)
        n = np.round(n[:H, :W] * amount * 255 * 0.85).astype(np.int16)
        plate = np.ascontiguousarray(np.repeat(n[..., None], 3, axis=2))
        _grain_bank[key] = plate
    f = int(round(t * 1000))
    ox, oy = (f * 97) % pad, (f * 61) % pad
    return cv2.add(img, plate[oy:oy + h, ox:ox + w], dtype=cv2.CV_8U)
