"""Collage materials: paper, torn edges, cutouts, tape, stamps, labels,
halftone and hand-drawn marks. Everything is procedural and seeded, so a
frame renders identically every time.
"""
import math

import cv2
import numpy as np

from .canvas import Sprite, rgba
from .text import text_rgba


def noise(h, w, scale=64.0, seed=0, octaves=4, persistence=0.5):
    """Fractal value noise in roughly [-1, 1]. scale = feature size in px."""
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, total = 1.0, 0.0
    for _ in range(octaves):
        gh, gw = max(2, int(h / scale) + 2), max(2, int(w / scale) + 2)
        g = rng.uniform(-1, 1, (gh, gw)).astype(np.float32)
        out += amp * cv2.resize(g, (w, h), interpolation=cv2.INTER_CUBIC)
        total += amp
        amp *= persistence
        scale /= 2
        if scale < 1:
            break
    return out / total


def paper_tile(size=1024, seed=1, grain=0.05, fibers=0.035, blotch=0.04):
    """Tileable-ish paper texture, HxWx3 float multiplier around 1.0.

    Use with Canvas.texture() for world-anchored grain on large areas.
    """
    rng = np.random.default_rng(seed)
    n = noise(size, size, 3, seed, 2) * grain
    n += noise(size, size, size / 4, seed + 1, 3) * blotch
    f = np.zeros((size, size), np.float32)
    for _ in range(int(size * size / 900)):
        x, y = rng.uniform(0, size, 2)
        a = rng.uniform(0, math.pi)
        L = rng.uniform(4, 22)
        p0 = (int(x), int(y))
        p1 = (int(x + L * math.cos(a)), int(y + L * math.sin(a)))
        cv2.line(f, p0, p1, float(rng.choice([-1, 1])), 1, cv2.LINE_AA)
    f = cv2.GaussianBlur(f, (0, 0), 0.7) * fibers
    t = 1 + n + f
    # blend opposite edges so the wrap seam is invisible
    k = size // 8
    ramp = np.linspace(0, 1, k, dtype=np.float32)
    t[:, :k] = t[:, :k] * ramp + t[:, -k:][:, ::-1] * (1 - ramp)
    t[:k, :] = t[:k, :] * ramp[:, None] + t[-k:, :][::-1, :] * (1 - ramp[:, None])
    return np.repeat(t[..., None], 3, axis=2).astype(np.float32)


def rough_mask(mask, px, seed=0, amount=1.0):
    """Tear a binary-ish mask: edges wander by about px pixels."""
    h, w = mask.shape
    pad = int(px * 3) + 2
    m = np.pad(mask.astype(np.float32), pad)
    sig = max(px * 0.6, 0.5)
    mb = cv2.GaussianBlur(m, (0, 0), sig)
    n = noise(m.shape[0], m.shape[1], max(px * 2.5, 3), seed, 5, 0.55)
    t = mb + n * 0.32 * amount
    out = np.clip((t - 0.5) * 6 + 0.5, 0, 1)
    out = cv2.GaussianBlur(out, (0, 0), 0.6)
    return out[pad:pad + h, pad:pad + w]


def _rgb(color):
    r, g, b, _ = rgba(color)
    return np.array([r, g, b], np.float32)


def paper_sheet(w, h, res, color="#efe8da", seed=0, torn=0.0, rim="#fbf8f1",
                grain=1.0, pad=0.08):
    """A sheet of paper w x h world units. torn > 0 roughs the edges (world
    units) and shows a lighter fibrous rim, like torn newsprint."""
    W, H = int(w * res), int(h * res)
    p = int(max(w, h) * pad * res) if torn else 2
    m = np.zeros((H + 2 * p, W + 2 * p), np.float32)
    m[p:p + H, p:p + W] = 1
    tex = paper_tile(max(m.shape), seed)[:m.shape[0], :m.shape[1], 0]
    tex = 1 + (tex - 1) * grain
    col = _rgb(color)[None, None, :] * tex[..., None]
    if torn > 0:
        outer = rough_mask(m, torn * res, seed, amount=1.7)
        inner = rough_mask(cv2.erode(m, np.ones((3, 3)), iterations=max(1, int(torn * res * 0.6))),
                           torn * res * 0.8, seed + 7, amount=1.7)
        rimc = _rgb(rim)[None, None, :] * (0.97 + 0.03 * tex[..., None])
        col = col * inner[..., None] + rimc * (1 - inner[..., None])
        a = outer
    else:
        a = m
    img = np.dstack([col * a[..., None], a]).astype(np.float32)
    return Sprite(img, res)


def cutout(rgb, alpha=None, res=1.0, border=8.0, border_color="#f7f3ea", torn=0.0,
           seed=0, print_look=0.5):
    """Photo or illustration cut out with a white paper border.

    rgb: HxWx3 uint8 (or float 0..1); alpha: HxW 0..1 subject mask (None = the
    whole rectangle); res: pixels per world unit of the source; border in
    world units.
    """
    rgb = rgb.astype(np.float32) / 255 if rgb.dtype == np.uint8 else rgb.astype(np.float32)
    H, W = rgb.shape[:2]
    if alpha is None:
        alpha = np.ones((H, W), np.float32)
    bp = int(border * res)
    pad = bp + int(max(torn, 1) * res * 3) + 4
    a = np.pad(alpha.astype(np.float32), pad)
    img = np.pad(rgb, ((pad, pad), (pad, pad), (0, 0)))
    # paper border: dilate the subject, round it off, then optionally tear
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * bp + 1, 2 * bp + 1))
    outer = cv2.dilate((a > 0.5).astype(np.float32), k)
    outer = cv2.GaussianBlur(outer, (0, 0), max(bp * 0.25, 1))
    outer = (outer > 0.5).astype(np.float32)
    outer = rough_mask(outer, torn * res, seed) if torn > 0 else cv2.GaussianBlur(outer, (0, 0), 0.7)
    tex = paper_tile(max(outer.shape), seed)[:outer.shape[0], :outer.shape[1]]
    paper = _rgb(border_color)[None, None, :] * tex
    if print_look:
        # printed-matter feel: slight desaturation, lifted blacks, paper grain
        g = img.mean(axis=2, keepdims=True)
        img = img * (1 - 0.25 * print_look) + g * 0.25 * print_look
        img = 0.04 * print_look + img * (1 - 0.07 * print_look)
        img = img * (1 + (tex - 1) * 0.8)
    col = paper * (1 - a[..., None]) + img * a[..., None]
    return Sprite(np.dstack([col * outer[..., None], outer]).astype(np.float32), res)


def tape(w, h, res, color="#e8dcc0", alpha=0.82, seed=0):
    """Strip of masking tape with torn zig-zag ends."""
    W, H = int(w * res), int(h * res)
    rng = np.random.default_rng(seed)
    m = np.zeros((H, W), np.float32)
    teeth = max(4, int(h / 3))
    left = [(rng.uniform(0, h * 0.12) * res, y) for y in np.linspace(0, H, teeth)]
    right = [(W - rng.uniform(0, h * 0.12) * res, y) for y in np.linspace(H, 0, teeth)]
    cv2.fillPoly(m, [np.int32(left + right)], 1.0, cv2.LINE_AA)
    tex = noise(H, W, 6, seed, 3) * 0.05 + noise(H, W, W / 3, seed + 3, 2) * 0.06
    col = _rgb(color)[None, None, :] * (1 + tex[..., None])
    a = m * alpha * (0.92 + 0.08 * noise(H, W, 20, seed + 5, 2))
    edge = np.zeros_like(m)
    edge[:max(1, int(res * 0.6))] = 0.12
    edge[-max(1, int(res * 0.6)):] = -0.1
    col = col + edge[..., None]
    return Sprite(np.dstack([col * a[..., None], a]).astype(np.float32), res)


def distress(a, res, seed=0, amount=0.5):
    """Knock random specks and worn patches out of an ink mask (stamps)."""
    h, w = a.shape
    n = noise(h, w, max(res * 1.5, 2), seed, 4) + noise(h, w, max(res * 12, 4), seed + 9, 2) * 0.8
    keep = np.clip((n + 0.9 - amount) * 3, 0, 1)
    return a * keep


def stamp(text, res, size=60, color="#d8432b", seed=0, border=True, font="anton",
          tracking=0.06, ink=0.88):
    """Rubber stamp: bold text in a double box, unevenly inked."""
    t = text_rgba(text, font, size, res, "#ffffff", tracking=tracking, pad=0.0)[..., 3]
    t = t.astype(np.float32) / 255
    if border:
        bp = int(size * 0.32 * res)
        t = np.pad(t, bp + int(size * 0.2 * res))
        h, w = t.shape
        th = max(1, int(size * 0.07 * res))
        o = int(size * 0.12 * res)
        cv2.rectangle(t, (o, o), (w - o - 1, h - o - 1), 1.0, th, cv2.LINE_AA)
        o2 = o + th * 2
        cv2.rectangle(t, (o2, o2), (w - o2 - 1, h - o2 - 1), 1.0, max(1, th // 2), cv2.LINE_AA)
    t = np.pad(t, int(size * 0.1 * res) + 2)
    a = distress(t, res, seed) * ink
    col = _rgb(color)
    img = np.zeros(a.shape + (4,), np.float32)
    img[..., :3] = col * a[..., None]
    img[..., 3] = a
    return Sprite(img, res)


def label(text, res, size=28, paper="#efe6cf", ink="#1b1a17", seed=0, torn=1.2,
          font="type"):
    """Typewritten label on a torn paper strip."""
    t = text_rgba(text, font, size, res, "#ffffff", pad=0.0)[..., 3].astype(np.float32) / 255
    th, tw = t.shape
    padx, pady = size * 0.55, size * 0.35
    w, h = tw / res + 2 * padx, th / res + 2 * pady
    sheet = paper_sheet(w, h, res, paper, seed, torn=torn)
    img = sheet.img.copy()
    H, W = img.shape[:2]
    y0, x0 = (H - th) // 2, (W - tw) // 2
    # typewriter ink: slightly uneven density
    inkm = t * (0.82 + 0.18 * noise(th, tw, max(res * 3, 2), seed + 2, 2))
    region = img[y0:y0 + th, x0:x0 + tw]
    c = _rgb(ink)
    region[..., :3] = region[..., :3] * (1 - inkm[..., None]) + c * inkm[..., None] * region[..., 3:4]
    return Sprite(img, res)


def halftone(gray, cell=8.0, angle=45.0, gain=1.0):
    """Ink-dot mask (1 = ink) from a darkness map (0..1, 1 = darkest)."""
    h, w = gray.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = math.radians(angle)
    u = (xx * math.cos(a) + yy * math.sin(a)) / cell
    v = (-xx * math.sin(a) + yy * math.cos(a)) / cell
    du, dv = u - np.round(u), v - np.round(v)
    d = np.sqrt(du * du + dv * dv)
    r = np.sqrt(np.clip(gray * gain, 0, 1)) * 0.72
    aa = 1.2 / cell
    return np.clip((r - d) / aa + 0.5, 0, 1).astype(np.float32)


def halftone_sprite(darkness, res, color="#1b1a17", cell=8.0, angle=45.0, alpha=1.0):
    m = halftone(darkness, cell * res, angle) * alpha
    img = np.zeros(m.shape + (4,), np.float32)
    img[..., :3] = _rgb(color) * m[..., None]
    img[..., 3] = m
    return Sprite(img, res)


def hand_ellipse(cx, cy, rx, ry, seed=0, turns=1.12, wobble=0.05, start=-100.0, n=160):
    """A pen circle drawn by hand: slightly wobbly, overshoots its start."""
    rng = np.random.default_rng(seed)
    th = np.radians(start) + np.linspace(0, 2 * math.pi * turns, n)
    ph = rng.uniform(0, 6.28, 3)
    k = 1 + wobble * (np.sin(th * 2 + ph[0]) * 0.6 + np.sin(th * 3 + ph[1]) * 0.4)
    k *= 1 + np.linspace(0, wobble * 1.4, n)          # spirals out a little
    tilt = math.radians(rng.uniform(-6, 6))
    x, y = rx * k * np.cos(th), ry * k * np.sin(th)
    return np.stack([cx + x * math.cos(tilt) - y * math.sin(tilt),
                     cy + x * math.sin(tilt) + y * math.cos(tilt)], 1)


def hand_underline(x0, x1, y, seed=0, wobble=3.0, n=40, double=False):
    rng = np.random.default_rng(seed)
    xs = np.linspace(x0, x1, n)
    ys = y + np.cumsum(rng.normal(0, wobble * 0.15, n)) + np.linspace(0, rng.uniform(-wobble, wobble), n)
    pts = np.stack([xs, ys], 1)
    if double:
        back = np.stack([xs[::-1] - (x1 - x0) * 0.03, ys[::-1] + wobble * 2.2], 1)
        pts = np.vstack([pts, back])
    return pts


def disintegrate(sprite, amount=0.6, seed=0, direction=1.0, specks=160):
    """Erode a sprite's alpha into fragments, strongest on one side, with a
    scatter of detached flecks drifting off. Used for 'this money turned to ash'.

    direction: 1.0 eats from the right, -1.0 from the left.
    """
    img = sprite.img.copy()
    h, w = img.shape[:2]
    res = sprite.res
    xs = np.linspace(0, 1, w, dtype=np.float32)
    if direction < 0:
        xs = xs[::-1]
    grad = np.clip((xs - (1 - amount)) / max(amount, 1e-3), 0, 1)[None, :]
    n = noise(h, w, max(res * 2.5, 3), seed, 5, 0.55) * 0.5 + 0.5
    keep = np.clip((n - grad * 1.15) * 7 + 0.5, 0, 1)
    img *= keep[..., None]
    # flecks that have broken away
    rng = np.random.default_rng(seed + 11)
    pad = int(w * 0.22)
    out = np.zeros((h + 2 * pad, w + pad, 4), np.float32)
    out[pad:pad + h, :w] = img
    for _ in range(specks):
        u = rng.random() ** 0.5
        sx = int(w * (1 - amount * 0.9) + u * (w * amount + pad * 0.85))
        sy = int(pad + rng.random() * h + (rng.random() - 0.5) * pad * u * 1.4)
        s = max(1, int(rng.uniform(1.0, 3.4) * res))
        if 0 <= sy < out.shape[0] - s and 0 <= sx < out.shape[1] - s:
            src_y = min(max(int(rng.random() * h), 0), h - 1)
            col = img[src_y, min(int(w * 0.75), w - 1), :3]
            a = rng.uniform(0.25, 0.9) * (1 - u * 0.7)
            out[sy:sy + s, sx:sx + s, :3] = col * a
            out[sy:sy + s, sx:sx + s, 3] = a
    return Sprite(out, res)
