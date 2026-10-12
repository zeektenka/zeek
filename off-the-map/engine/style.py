"""Off the Map design system (v2, collage) and reusable collage pieces.

Palette rule: dark ink base, two paper neutrals, ONE accent, used only for the
key point of each shot.
"""
import math

import cv2
import numpy as np

from .canvas import Sprite, rgba, REF_W, REF_H
from . import paper as P
from .text import text_rgba, measure

# ---------------------------------------------------------------- tokens
INK = "#151412"          # base (the desk)
INK_2 = "#24211d"        # lifted base, centre of the light
PAPER = "#eee6d6"        # neutral 1: newsprint / labels
KRAFT = "#c4ad86"        # neutral 2: folders, bars, tape
GREY = "#8a857a"         # secondary text, borders
ACCENT = "#ff4a1c"       # signature accent: the key point only
TEXT_DARK = "#1b1a17"

ANTON, TYPE, INTER, INTER_SEMI, INTER_BOLD = "anton", "type", "inter", "inter_semi", "inter_bold"

SHADOW = (6, 10, 9, 0.55)        # default drop shadow (dx, dy, blur, opacity)
SHADOW_LOW = (3, 5, 5, 0.45)     # for things lying flat on the page
SHADOW_HIGH = (14, 22, 18, 0.5)  # for things lifted towards camera

# ---------------------------------------------------------------- caching
# Bounded: a feature-length render touches hundreds of sprites, and an unbounded
# cache is what OOM-killed the first master render.
_cache = __import__("collections").OrderedDict()
CACHE_BYTES = 700_000_000


def _cache_put(k, sprite):
    _cache[k] = sprite
    total = 0
    for key in reversed(_cache):
        v = _cache[key]
        total += getattr(getattr(v, "img", None), "nbytes", 0)
        if hasattr(v, "_shadows"):
            total += sum(sp.img.nbytes for sp, _ in v._shadows.values())
        if total > CACHE_BYTES:
            while next(iter(_cache)) != key:
                _cache.popitem(last=False)
            _cache.popitem(last=False)
            break


def cached(cv, key, build, oversample=1.0):
    """Build a sprite once per canvas resolution. build(res) -> Sprite.
    oversample > 1 for things the camera will push in on."""
    res = cv.k * oversample
    k = (key, round(res, 3))
    if k in _cache:
        _cache.move_to_end(k)
        return _cache[k]
    sp = build(res)
    _cache_put(k, sp)
    return sp


_tiles = {}


def tile(seed=1, size=1024):
    k = ("tile", seed, size)
    if k not in _tiles:
        _tiles[k] = P.paper_tile(size, seed)
    return _tiles[k]


# ---------------------------------------------------------------- background
def desk(cv, seed=3, light=(0.5, 0.42), parallax=0.3, grain_strength=1.6):
    """Dark paper desk with a soft pool of light.

    The gradient and its paper grain are baked together once per canvas size,
    then slid behind the action to give the background parallax. Rebuilding
    this per frame was more than half the cost of a render.
    """
    from .post import _fields, radial
    from .canvas import Canvas
    key = ("desk", cv.W, cv.H, seed, light, round(grain_strength, 2))
    base = _fields.get(key)
    m = int(cv.W * 0.05) + 2
    if base is None:
        pad = Canvas(cv.out_w, cv.out_h, ss=cv.W / cv.out_w)
        radial(pad, INK_2, INK, *light, radius=1.05)
        tex = pad.texture(tile(seed), depth=1.0, tile_res=cv.k)
        pad.buf[..., :3] *= 1 + (tex - 1) * grain_strength
        pad.buf[..., 3] = 1.0
        base = cv2.copyMakeBorder(pad.buf, m, m, m, m, cv2.BORDER_REFLECT)
        _fields[key] = base
    # slide the baked plate by where a fixed world point sits at this depth
    p = cv.to_px([(REF_W / 2, REF_H / 2)], parallax)[0]
    dx = int(np.clip(p[0] - cv.W / 2, -m, m))
    dy = int(np.clip(p[1] - cv.H / 2, -m, m))
    cv.buf[:] = base[m + dy:m + dy + cv.H, m + dx:m + dx + cv.W]


def newsprint(w, h, res, seed=0, headline=None, cols=3, tone=PAPER, torn=2.5):
    """Generic newspaper scrap: unreadable grey text columns and an optional
    headline. Never reproduces a real paper, so no copyright issue."""
    sheet = P.paper_sheet(w, h, res, tone, seed, torn=torn)
    img = sheet.img
    H, W = img.shape[:2]
    rng = np.random.default_rng(seed)
    ink = np.zeros((H, W), np.float32)
    m = int(0.1 * min(w, h) * res)
    y = m
    if headline:
        t = text_rgba(headline, ANTON, h * 0.11, res, "#ffffff", pad=0)[..., 3] / 255.0
        t = t[:, :W - 2 * m]
        ink[y:y + t.shape[0], m:m + t.shape[1]] = np.maximum(ink[y:y + t.shape[0], m:m + t.shape[1]], t * 0.9)
        y += t.shape[0] + int(0.04 * h * res)
    colw = (W - 2 * m - (cols - 1) * m // 2) / cols
    lh = max(2, int(h * 0.028 * res))
    for c in range(cols):
        x0 = int(m + c * (colw + m // 2))
        yy = y
        while yy < H - m:
            L = colw * (rng.uniform(0.55, 1) if rng.random() < 0.15 else 1)
            # a "line of text" is a row of short dashes (words)
            x = x0
            while x < x0 + L - 4:
                wl = rng.uniform(colw * 0.06, colw * 0.2)
                cv2.rectangle(ink, (int(x), yy), (int(min(x + wl, x0 + L)), yy + max(1, lh // 2)),
                              rng.uniform(0.35, 0.6), -1)
                x += wl + colw * 0.025
            yy += lh
    ink = cv2.GaussianBlur(ink, (0, 0), max(0.5, res * 0.6))
    img[..., :3] *= 1 - ink[..., None] * 0.8
    return sheet


def bake(cv, key, draw, world_w=2560, world_h=1440, scale=0.5, blur=0.0, alpha=1.0):
    """Render `draw(canvas)` once into an offscreen layer and reuse it as a sprite.

    The layer covers a 16:9 world rect centred on the frame, so it can be placed
    at any depth and still parallax correctly. Blur is applied once at bake
    time rather than per frame, which is the difference between a preview and a
    feature-length render finishing overnight.
    """
    from .canvas import Canvas
    res = cv.k * scale
    k = (key, round(res, 3), round(blur, 2))
    sp = _cache.get(k)
    if sp is None:
        sub = Canvas(max(2, int(world_w * res)), max(2, int(world_h * res)), ss=1.0)
        sub.cam.set(REF_W / 2, REF_H / 2, REF_W / world_w)
        draw(sub)
        img = sub.buf
        if blur > 0:
            img = cv2.GaussianBlur(img, (0, 0), blur * res)
        if alpha != 1.0:
            img = img * alpha
        sp = Sprite(np.ascontiguousarray(img), res)
        _cache_put(k, sp)
    return sp


def scraps(cv, t, seed=11, n=7, depth=0.55, blur=2.5, alpha=0.55, area=None,
           drift_amp=14.0):
    """Out-of-focus newsprint scraps drifting behind the focus (parallax + depth of field).

    Baked once into a single pre-blurred sprite; the whole layer drifts as one.
    """
    from .ease import drift
    x0, y0, x1, y1 = area or (-260, -200, 2180, 1280)

    def draw(sub):
        rng = np.random.default_rng(seed)
        for i in range(n):
            w, h = rng.uniform(260, 520), rng.uniform(300, 560)
            sp = cached(sub, ("scrap", seed, i), lambda r, w=w, h=h, i=i: newsprint(
                w, h, r * 0.75, seed * 100 + i, headline=None, cols=2, tone="#a69d8c"))
            sub.place(sp, rng.uniform(x0, x1), rng.uniform(y0, y1),
                      rot=rng.uniform(-25, 25), shadow=SHADOW_LOW)

    layer = bake(cv, ("scraps", seed, n), draw, scale=0.42, blur=blur, alpha=alpha)
    cv.place(layer, REF_W / 2 + drift(t, drift_amp, 13, seed),
             REF_H / 2 + drift(t, drift_amp * 0.7, 17, seed + 3), depth=depth)


# ---------------------------------------------------------------- illustrations
def banknote(res, value="100", word="TRILLION", seed=0, w=640, base="#9fb9b0",
             ink="#2d4a47", torn=0.0):
    """Generic hyperinflation-era banknote, drawn in code (not a reproduction)."""
    h = w / 2.05
    W, H = int(w * res), int(h * res)
    img = np.zeros((H, W, 3), np.float32)
    c0, c1 = np.array(rgba(base)[:3]), np.array(rgba("#d9cfae")[:3])
    xx = np.linspace(0, 1, W)[None, :, None]
    img[:] = c0 * (1 - xx * 0.55) + c1 * xx * 0.55
    inkc = np.array(rgba(ink)[:3])
    lines = np.zeros((H, W), np.float32)
    s = res
    # guilloche rosettes
    for cx, cy, R in [(0.27, 0.5, 0.38), (0.8, 0.52, 0.3)]:
        for k in range(26):
            th = np.linspace(0, 2 * math.pi, 900)
            r = R * h * (0.62 + 0.3 * np.sin(7 * th + k * 0.24) * np.cos(3 * th - k * 0.11))
            pts = np.stack([cx * w + r * np.cos(th + k * 0.12), cy * h + r * np.sin(th + k * 0.12)], 1) * s
            cv2.polylines(lines, [np.int32(pts * 4)], True, 0.5, 1, cv2.LINE_AA, shift=2)
    # wave band
    for k in range(18):
        x = np.linspace(0, w, 400)
        y = h * 0.82 + 7 * np.sin(x / 23 + k * 0.4) + k * 1.1 - 10
        cv2.polylines(lines, [np.int32(np.stack([x, y], 1) * s * 4)], False, 0.45, 1, cv2.LINE_AA, shift=2)
    # border frame
    for o, th in [(0.035, 0.012), (0.055, 0.004)]:
        cv2.rectangle(lines, (int(o * h * s), int(o * h * s)),
                      (int(W - o * h * s), int(H - o * h * s)), 0.9, max(1, int(th * h * s)), cv2.LINE_AA)
    img = img * (1 - lines[..., None] * 0.55) + inkc * lines[..., None] * 0.55

    def put(text, font, size, x, y, color, anchor="lt", alpha=1.0, tracking=0.0):
        t = text_rgba(text, font, size, res, "#ffffff", pad=0.05, tracking=tracking)[..., 3] / 255.0 * alpha
        th_, tw_ = t.shape
        px, py = int(x * res), int(y * res)
        if anchor[0] == "r": px -= tw_
        if anchor[0] == "c": px -= tw_ // 2
        if anchor[1] == "c": py -= th_ // 2
        px, py = max(px, 0), max(py, 0)
        t = t[:H - py, :W - px]
        reg = img[py:py + t.shape[0], px:px + t.shape[1]]
        reg[:] = reg * (1 - t[..., None]) + np.array(rgba(color)[:3]) * t[..., None]

    put(value, ANTON, h * 0.36, w * 0.06, h * 0.06, ink)
    put(word, ANTON, h * 0.2, w * 0.95, h * 0.1, ink, "rt", tracking=0.04)
    put("DOLLARS", INTER_BOLD, h * 0.09, w * 0.95, h * 0.33, ink, "rt", tracking=0.25)
    put("PAY THE BEARER ON DEMAND", TYPE, h * 0.055, w * 0.95, h * 0.47, ink, "rt", 0.8)
    put("AA 0000001", TYPE, h * 0.07, w * 0.06, h * 0.8, "#8a2a20", "lc", 0.9)
    put(value, ANTON, h * 0.16, w * 0.95, h * 0.86, ink, "rc", 0.85)
    tex = P.paper_tile(max(W, H), seed + 5)[:H, :W]
    img = img * (1 + (tex - 1) * 1.4)
    # wear: soft creases
    crease = np.zeros((H, W), np.float32)
    cv2.line(crease, (int(W * 0.48), 0), (int(W * 0.52), H), 1.0, max(1, int(res * 1.2)), cv2.LINE_AA)
    crease = cv2.GaussianBlur(crease, (0, 0), res * 2)
    img *= 1 - crease[..., None] * 0.18
    rgb8 = np.clip(img * 255, 0, 255).astype(np.uint8)
    return P.cutout(rgb8, None, res, border=0.01 if not torn else 6, torn=torn, seed=seed, print_look=0.2)


def loaf(res, w=420, seed=0, color="#c98c4a"):
    """A loaf of bread as a flat paper cutout: dome, scored top, darker crust."""
    h = w * 0.62
    pad = 0.08 * w
    W, H = int((w + 2 * pad) * res), int((h + 2 * pad) * res)
    m = np.zeros((H, W), np.float32)
    s = res
    cx, base = (w / 2 + pad) * s, (h + pad) * s
    cv2.ellipse(m, (int(cx), int(base - h * 0.42 * s)), (int(w * 0.5 * s), int(h * 0.58 * s)), 0, 180, 360, 1.0, -1, cv2.LINE_AA)
    cv2.rectangle(m, (int(pad * s + w * 0.02 * s), int(base - h * 0.45 * s)), (int((pad + w * 0.98) * s), int(base)), 1.0, -1, cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), res * 2.5)
    m = np.clip((m - 0.5) * 3 + 0.5, 0, 1)
    m = P.rough_mask(m, res * 1.2, seed)
    yy = np.linspace(0, 1, H)[:, None, None]
    c = np.array(rgba(color)[:3])
    dark = np.array(rgba("#7a4a22")[:3])
    img = c * (1 - yy * 0.5) + dark * yy * 0.5 + np.zeros((H, W, 3))
    # score marks: lighter paper strips
    for i in range(4):
        x = pad + w * (0.2 + i * 0.19)
        p0 = (int((x - w * 0.06) * s), int((pad + h * 0.12 + abs(i - 1.5) * h * 0.05) * s))
        p1 = (int((x + w * 0.06) * s), int((pad + h * 0.32 + abs(i - 1.5) * h * 0.05) * s))
        cv2.line(img, p0, p1, rgba("#f0cf98")[:3], max(2, int(w * 0.035 * s)), cv2.LINE_AA)
    tex = P.paper_tile(max(W, H), seed + 2)[:H, :W]
    img = np.clip(img * (1 + (tex - 1) * 1.5), 0, 1)
    return P.cutout((img * 255).astype(np.uint8), m, res, border=7, seed=seed, print_look=0.3)


def bank_facade(res, w=520, h=380, seed=0):
    """A columned central-bank facade as a halftone 'newspaper photo'."""
    W, H = int(w * res), int(h * res)
    d = np.zeros((H, W), np.float32)
    s = res
    yy = np.linspace(0, 1, H)[:, None]
    d[:] = 0.18 + 0.15 * yy                                # sky
    gx, gy = w * 0.5, h * 0.24
    tri = np.int32([[w * 0.1, h * 0.36], [gx, gy * 0.55], [w * 0.9, h * 0.36]]) * s
    cv2.fillPoly(d, [np.int32(tri)], 0.55, cv2.LINE_AA)
    cv2.rectangle(d, (int(w * 0.08 * s), int(h * 0.36 * s)), (int(w * 0.92 * s), int(h * 0.42 * s)), 0.7, -1)
    for i in range(6):
        x = w * (0.15 + i * 0.14)
        cv2.rectangle(d, (int(x * s), int(h * 0.42 * s)), (int((x + w * 0.05) * s), int(h * 0.8 * s)), 0.35, -1)
        cv2.rectangle(d, (int((x + w * 0.05) * s), int(h * 0.42 * s)), (int((x + w * 0.07) * s), int(h * 0.8 * s)), 0.8, -1)
    cv2.rectangle(d, (int(w * 0.12 * s), int(h * 0.42 * s)), (int(w * 0.88 * s), int(h * 0.8 * s)), 0.9, -1)
    # redraw columns over the dark interior
    for i in range(6):
        x = w * (0.15 + i * 0.14)
        cv2.rectangle(d, (int(x * s), int(h * 0.42 * s)), (int((x + w * 0.07) * s), int(h * 0.8 * s)), 0.3, -1)
    for k in range(4):
        cv2.rectangle(d, (int((w * 0.06 - k * 8) * s), int((h * 0.8 + k * h * 0.04) * s)),
                      (int((w * 0.94 + k * 8) * s), int((h * 0.84 + k * h * 0.04) * s)), 0.45 - k * 0.05, -1)
    d = cv2.GaussianBlur(d, (0, 0), res * 1.2)
    d += P.noise(H, W, res * 30, seed, 3) * 0.08
    dots = P.halftone(np.clip(d, 0, 1), cell=4.5 * res, angle=45)
    paperc = np.array(rgba("#ebe3d2")[:3])
    inkc = np.array(rgba(TEXT_DARK)[:3])
    img = paperc * (1 - dots[..., None]) + inkc * dots[..., None]
    return P.cutout((img * 255).astype(np.uint8), None, res, border=12, seed=seed, print_look=0.0)


def folder(res, w=1100, h=760, seed=0, tab="CASE FILE"):
    """Manila case-file folder with a tab."""
    tw, th = w * 0.3, h * 0.07
    W, H = int(w * res), int((h + th) * res)
    m = np.zeros((H, W), np.float32)
    s = res
    cv2.rectangle(m, (0, int(th * s)), (W - 1, H - 1), 1.0, -1)
    poly = np.int32([[w * 0.05 * s, th * s + 2], [w * 0.07 * s, 0], [(w * 0.05 + tw) * s, 0],
                     [(w * 0.07 + tw) * s, th * s + 2]])
    cv2.fillPoly(m, [poly], 1.0, cv2.LINE_AA)
    m = P.rough_mask(m, res * 0.8, seed)
    tex = P.paper_tile(max(W, H), seed)[:H, :W]
    c = np.array(rgba(KRAFT)[:3])
    img = c * tex * (0.96 + 0.06 * P.noise(H, W, res * 120, seed, 2)[..., None])
    # fold line shadow under the tab
    img[int(th * s):int(th * s) + max(1, int(res * 2))] *= 0.85
    t = text_rgba(tab, TYPE, th * 0.62, res, "#ffffff", pad=0)[..., 3] / 255.0
    x0, y0 = int(w * 0.1 * s), int(th * 0.2 * s)
    t = t[:H - y0, :W - x0]
    reg = img[y0:y0 + t.shape[0], x0:x0 + t.shape[1]]
    reg[:] = reg * (1 - 0.85 * t[..., None]) + np.array(rgba(TEXT_DARK)[:3]) * 0.85 * t[..., None]
    out = np.dstack([img * m[..., None], m]).astype(np.float32)
    return Sprite(out, res)


def paper_clip(res, h=120, color="#b9b7b0"):
    w = h * 0.32
    pad = 6
    W, H = int((w + 2 * pad) * res), int((h + 2 * pad) * res)
    m = np.zeros((H, W), np.float32)
    s = res
    th = max(2, int(3.2 * res))

    def u(x0, y0, x1, y1, r):
        cv2.ellipse(m, (int((x0 + x1) / 2 * s), int(y0 * s + r * s)), (int(r * s), int(r * s)), 0, 180, 360, 1, th, cv2.LINE_AA)
        cv2.line(m, (int(x0 * s), int((y0 + r) * s)), (int(x0 * s), int(y1 * s)), 1, th, cv2.LINE_AA)
        cv2.line(m, (int(x1 * s), int((y0 + r) * s)), (int(x1 * s), int(y1 * s)), 1, th, cv2.LINE_AA)

    u(pad, pad, pad + w, pad + h * 0.8, w / 2)
    u(pad + w * 0.2, pad + h * 0.2, pad + w * 0.8, pad + h * 0.95, w * 0.3)
    c = np.array(rgba(color)[:3])
    xx = np.linspace(0, 1, W)[None, :, None]
    img = c * (0.75 + 0.4 * np.abs(np.sin(xx * 9)))
    return Sprite(np.dstack([np.clip(img, 0, 1) * m[..., None], m]).astype(np.float32), res)


def title_strip(text, res, size=120, paper=PAPER, ink=TEXT_DARK, seed=0, torn=3.0,
                font=ANTON, tracking=0.02, padx=0.28, pady=0.12):
    """One word or line of a headline on its own torn paper strip (ransom-note collage)."""
    t = text_rgba(text, font, size, res, "#ffffff", pad=0, tracking=tracking)[..., 3] / 255.0
    th, tw = t.shape
    w, h = tw / res + 2 * size * padx, th / res + 2 * size * pady
    sheet = P.paper_sheet(w, h, res, paper, seed, torn=torn)
    img = sheet.img
    H, W = img.shape[:2]
    y0, x0 = (H - th) // 2, (W - tw) // 2
    c = np.array(rgba(ink)[:3])
    reg = img[y0:y0 + th, x0:x0 + tw]
    reg[..., :3] = reg[..., :3] * (1 - t[..., None]) + c * t[..., None] * reg[..., 3:4]
    return sheet


def finish(cv, vignette=0.5):
    from .post import vignette as vg
    vg(cv, vignette)


# ---------------------------------------------------------------- motion helpers
def slap(cv, sprite, x, y, t, t0, rot=0.0, scale=1.0, dur=0.42, depth=1.0,
         shadow=SHADOW, spin=5.0, anchor=(0.5, 0.5), alpha=1.0):
    """Collage entrance: the piece drops onto the page from above the camera,
    lands with a small overshoot, and its shadow tightens as it lands."""
    from .ease import ramp, out_back, clamp
    if t < t0:
        return
    u = clamp((t - t0) / dur)
    s = scale * (1.28 - 0.28 * out_back(u, 1.4))
    a = alpha * ramp(t, t0, dur * 0.3, "out")
    sh = None
    if shadow:
        # The offset and opacity carry the "landing" feel; the blur radius stays
        # fixed because every distinct blur builds and caches a new blurred copy.
        hi = SHADOW_HIGH
        sh = (hi[0] + (shadow[0] - hi[0]) * u,
              hi[1] + (shadow[1] - hi[1]) * u,
              shadow[2],
              hi[3] + (shadow[3] - hi[3]) * u)
    cv.place(sprite, x, y, s, rot + spin * (1 - u) ** 2, a, depth, anchor, shadow=sh)


def write_on(cv, pts, t, t0, dur=0.6, width=6.0, color=ACCENT, depth=1.0, alpha=1.0):
    """Hand-drawn mark drawn on over dur seconds (circles, underlines, arrows)."""
    from .ease import ramp
    p = ramp(t, t0, dur, "sine")
    if p > 0:
        cv.stroke(pts, width, color, depth, alpha, progress=p)
