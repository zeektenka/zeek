"""Finishing: background gradients, glow, vignette and film grain."""
import cv2
import numpy as np

from .canvas import rgba


def radial(cv, inner, outer, cx=0.5, cy=0.45, radius=0.9):
    """Soft radial gradient background (centre colour -> edge colour)."""
    yy, xx = np.mgrid[0:cv.H, 0:cv.W].astype(np.float32)
    d = np.sqrt(((xx / cv.W - cx) * cv.W / cv.H) ** 2 + (yy / cv.H - cy) ** 2) / radius
    u = np.clip(d, 0, 1)[..., None]
    u = u * u * (3 - 2 * u)
    a, b = np.array(rgba(inner)[:3]), np.array(rgba(outer)[:3])
    cv.buf[..., :3] = a * (1 - u) + b * u
    cv.buf[..., 3] = 1


def vignette(cv, strength=0.45, radius=0.75):
    yy, xx = np.mgrid[0:cv.H, 0:cv.W].astype(np.float32)
    d = np.sqrt(((xx / cv.W - 0.5) * cv.W / cv.H) ** 2 + (yy / cv.H - 0.5) ** 2) / radius
    v = 1 - strength * np.clip(d, 0, 1.4) ** 2.2
    cv.buf[..., :3] *= np.clip(v, 0, 1)[..., None]


def glow_pop(cv, radius=18.0, strength=0.8, alpha=1.0):
    """Close a cv.push() group with a glow: blurred copy screened underneath."""
    layer = cv.buf
    cv.buf = cv._stack.pop()
    g = cv2.GaussianBlur(layer, (0, 0), radius * cv.k) * strength * alpha
    cv._composite(g, 0, 0, 1.0, "screen")
    cv._composite(layer, 0, 0, alpha, "normal")


def grain(img, t, amount=0.028, size=1.2, seed=0):
    """Animated monochrome film grain on the final uint8 frame. Also hides
    colour banding after YouTube compression."""
    h, w = img.shape[:2]
    rng = np.random.default_rng(int(t * 1000) + seed)
    n = rng.normal(0, 1, (int(h / size) + 1, int(w / size) + 1)).astype(np.float32)
    if size != 1:
        n = cv2.resize(n, (w, h), interpolation=cv2.INTER_LINEAR)
    n = n[:h, :w, None]
    f = img.astype(np.float32) / 255
    # stronger in midtones, like film
    f += n * amount * (0.4 + 2.4 * f * (1 - f))
    return np.clip(f * 255 + 0.5, 0, 255).astype(np.uint8)
