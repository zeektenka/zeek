"""Reusable shot templates, so a feature-length video is authored as a shot
list cued to the narration rather than as bespoke code per shot.

A shot is a function fn(cv, t) with t local to the shot. `Reel` turns a list of
(cue phrase, shot) into a Video, deriving each shot's start and duration from
where its phrase is actually spoken.
"""
import math

import numpy as np

from .canvas import REF_W, REF_H
from .ease import ramp, stagger, drift, Track, lerp, mix_color
from .text import text_sprite, measure
from . import paper as P
from . import style as S
from . import post


class Reel:
    """Builds a Video from (cue, shot_factory) pairs.

    Each factory is called with a `cue` function that converts a narration
    phrase into a time local to that shot, so shot code reads:
        lambda cue: lambda cv, t: ... ramp(t, cue("Black Friday"), 0.4) ...
    """

    def __init__(self, timing, offset=0.0, total=None):
        self.T, self.offset, self.total = timing, offset, total
        self.items = []

    def at(self, cue, occurrence=1):
        if isinstance(cue, (int, float)):
            return float(cue) + self.offset
        return self.T.at(cue, occurrence) + self.offset

    def add(self, cue, factory, occurrence=1, lead=0.0, name=None):
        """lead shifts the shot earlier, so a visual can land just before the
        word that names it (reads as deliberate rather than late)."""
        self.items.append((self.at(cue, occurrence) - lead, factory, name))
        return self

    def build(self, video, end=None):
        end = end if end is not None else self.total
        starts = [s for s, _, _ in self.items]
        for i, (start, factory, name) in enumerate(self.items):
            stop = starts[i + 1] if i + 1 < len(starts) else end
            fn = factory(lambda p, o=1, s=start: self.at(p, o) - s)
            video.add(fn, max(stop - start, 0.1), start, name=name or f"shot{i:02d}")
        return video


# ---------------------------------------------------------------- helpers
def cam_drift(cv, t, push=0.05, dur=8.0, seed=0, x=REF_W / 2, y=REF_H / 2, zoom0=1.0):
    """House camera move: a slow push-in plus organic drift. Never still."""
    z = zoom0 * (1 + push * ramp(t, 0, dur, "sine"))
    cv.cam.set(x + drift(t, 7, 11, seed), y + drift(t, 5, 13, seed + 2), z,
               drift(t, 0.22, 15, seed))


def base(cv, t, seed=0, scraps=True, n=7, light=(0.5, 0.42)):
    S.desk(cv, seed=3, light=light)
    if scraps:
        S.scraps(cv, t, seed=11 + seed, n=n, alpha=0.32, blur=3.5)


def headline(cv, t, lines, t0=0.0, x=None, y=260, size=96, accent_line=None,
             gap=1.52, depth=0.0, seed=0, align_left=True, sub=None, sub_size=26):
    """Stacked torn-paper headline strips, staggered in. accent_line indexes
    the one line that gets the accent colour (the key point of the shot)."""
    y0 = y
    for i, line in enumerate(lines):
        hot = i == accent_line
        sp = S.cached(cv, ("hl", line, size, hot, seed), lambda r, line=line, hot=hot: S.title_strip(
            line, r, size, paper=S.ACCENT if hot else S.PAPER,
            ink="#fff8ee" if hot else S.TEXT_DARK, seed=seed * 7 + len(line)))
        w = sp.size[0]
        px = (x if x is not None else 170 + w / 2) if align_left else (x or REF_W / 2)
        S.slap(cv, sp, px, y0, t, t0 + i * 0.14, (-2.5 if i % 2 else 2.0), depth=depth)
        y0 += size * gap
    if sub:
        sp = S.cached(cv, ("hlsub", sub, seed), lambda r: P.label(sub, r, sub_size, seed=seed + 3))
        S.slap(cv, sp, (x if x is not None else 170 + sp.size[0] / 2), y0 - size * 0.22, t,
               t0 + len(lines) * 0.14, 1.5, depth=depth, shadow=S.SHADOW_LOW)
    return y0


def big_stat(cv, t, value, label=None, t0=0.0, x=REF_W / 2, y=REF_H / 2, size=300,
             color=None, sub=None, glow=True, depth=0.0, seed=0, rot=-2.0):
    """One enormous number. The whole point of the shot."""
    color = color or S.ACCENT
    sp = S.cached(cv, ("bs", value, size, color), lambda r: text_sprite(
        value, S.ANTON, size, r, color), 1.3)
    u = ramp(t, t0, 0.5, "soft_back")
    if u <= 0:
        return
    if glow:
        cv.push()
    cv.place(sp, x, y, 0.82 + 0.18 * u, rot, min(1, u * 2.5), depth)
    if glow:
        post.glow_pop(cv, 26, 0.5, ramp(t, t0 + 0.1, 0.5))
    if label:
        lp = S.cached(cv, ("bsl", label), lambda r: text_sprite(
            label, S.INTER_BOLD, 40, r, S.PAPER, tracking=0.22))
        cv.place(lp, x, y - size * 0.62, alpha=ramp(t, t0 + 0.12, 0.35), depth=depth)
    if sub:
        sp2 = S.cached(cv, ("bss", sub), lambda r: P.label(sub, r, 26, seed=seed))
        S.slap(cv, sp2, x, y + size * 0.55, t, t0 + 0.3, 1.5, depth=depth, shadow=S.SHADOW_LOW)


def cards(cv, t, items, t0=0.0, y=560, gap=0.12, w=360, h=430, depth=1.0, seed=0,
          spread=None, size=46, rot=5.0):
    """A row of paper cards, each with a word, dealt onto the page in sequence."""
    n = len(items)
    spread = spread or min(1500, n * (w + 60))
    xs = [REF_W / 2 + spread * ((i + 0.5) / n - 0.5) for i in range(n)]
    for i, (txt, sub) in enumerate([(x, None) if isinstance(x, str) else x for x in items]):
        sp = S.cached(cv, ("card", txt, sub, w, h, seed), lambda r, txt=txt, sub=sub, i=i:
                      _card(r, txt, sub, w, h, seed * 31 + i, size))
        S.slap(cv, sp, xs[i], y, t, t0 + i * gap, rot * ((i % 2) * 2 - 1) * 0.5, depth=depth)


def _card(res, txt, sub, w, h, seed, size):
    sheet = P.paper_sheet(w, h, res, S.PAPER, seed, torn=2.4)
    img = sheet.img
    H, W = img.shape[:2]
    from .text import text_rgba
    t = text_rgba(txt, S.ANTON, size, res, "#ffffff", pad=0, align="center")[..., 3] / 255.0
    th, tw = t.shape
    y0, x0 = int(H * 0.5 - th / 2), (W - tw) // 2
    c = np.array(__import__("engine.canvas", fromlist=["rgba"]).rgba(S.TEXT_DARK)[:3], np.float32)
    reg = img[y0:y0 + th, x0:x0 + tw]
    reg[..., :3] = reg[..., :3] * (1 - t[..., None]) + c * t[..., None] * reg[..., 3:4]
    if sub:
        t2 = text_rgba(sub, S.TYPE, size * 0.42, res, "#ffffff", pad=0, align="center")[..., 3] / 255.0
        th2, tw2 = t2.shape
        y2, x2 = int(H * 0.5 + th * 0.9), (W - tw2) // 2
        if y2 + th2 < H:
            r2 = img[y2:y2 + th2, x2:x2 + tw2]
            r2[..., :3] = r2[..., :3] * (1 - t2[..., None] * 0.8) + np.array([0.3, 0.29, 0.26], np.float32) * t2[..., None] * 0.8 * r2[..., 3:4]
    return sheet


def ledger(cv, t, rows, t0=0.0, x=380, y=330, step=132, size=52, seed=0,
           accent_rows=(), strike=(), depth=0.0, numbered=True):
    """A list that builds line by line — the spine of an explainer."""
    for i, row in enumerate(rows):
        a = stagger(t, t0, i, 0.42, 7, ease="out")
        if a <= 0:
            continue
        hot = i in accent_rows
        col = S.ACCENT if hot else S.PAPER
        if numbered:
            np_ = S.cached(cv, ("ldn", i), lambda r, i=i: text_sprite(
                f"{i + 1}", S.ANTON, size * 1.05, r, S.GREY))
            cv.place(np_, x - 78, y + i * step, alpha=a * 0.9, depth=depth)
        sp = S.cached(cv, ("ldr", row, size, hot), lambda r, row=row, col=col: text_sprite(
            row, S.ANTON, size, r, col))
        cv.place(sp, x + (1 - a) * -28, y + i * step, alpha=a, anchor=(0, 0.5), depth=depth)
        if i in strike:
            w = sp.size[0]
            S.write_on(cv, P.hand_underline(x, x + w, y + i * step + 4, seed=seed + i),
                       t, t0 + 0.5 + i * 0.12, 0.45, 6, S.ACCENT, depth)


def equation(cv, t, left, op, right, result, t0=0.0, y=520, size=118, seed=0,
             result_size=190, depth=0.0, caption=None):
    """50,000 x Z$50,000 = Z$4.2 BILLION — maths as a reveal."""
    parts = [(left, size, S.PAPER), (op, size * 0.8, S.GREY), (right, size, S.PAPER)]
    widths = [measure(p, S.ANTON, s) for p, s, _ in parts]
    total = sum(widths) + 70 * (len(parts) - 1)
    x = REF_W / 2 - total / 2
    for i, ((txt, s, col), w) in enumerate(zip(parts, widths)):
        sp = S.cached(cv, ("eq", txt, s), lambda r, txt=txt, s=s, col=col: text_sprite(txt, S.ANTON, s, r, col))
        a = stagger(t, t0, i, 0.35, 6, ease="out")
        cv.place(sp, x + w / 2, y, alpha=a, scale=lerp(1.08, 1.0, a), depth=depth)
        x += w + 70
    line_t = t0 + 0.55
    if t > line_t:
        S.write_on(cv, P.hand_underline(REF_W / 2 - total / 2, REF_W / 2 + total / 2,
                                        y + size * 0.62, seed=seed), t, line_t, 0.4, 6, S.GREY, depth)
    big_stat(cv, t, result, t0=line_t + 0.25, y=y + size * 1.35, size=result_size,
             sub=caption, depth=depth, seed=seed)


def line_chart(cv, t, series, t0=0.0, rect=(430, 300, 1100, 520), color=None,
               title=None, label_end=None, dur=1.6, depth=0.0, seed=0, fill=True):
    """A line drawing itself on, for anything that falls or climbs over time.

    series: list of (x, y) in data units, y up.
    """
    color = color or S.ACCENT
    x0, y0, w, h = rect
    d = np.asarray(series, float)
    dx = d[:, 0] - d[:, 0].min()
    dx = dx / max(dx.max(), 1e-9)
    dy = (d[:, 1] - d[:, 1].min()) / max(d[:, 1].max() - d[:, 1].min(), 1e-9)
    pts = np.stack([x0 + dx * w, y0 + (1 - dy) * h], 1)
    # axes
    ax = S.cached(cv, ("axis", w), lambda r: P.paper_sheet(w + 40, 14, r, S.PAPER, 9, torn=1.6))
    cv.place(ax, x0 + w / 2, y0 + h + 16, alpha=ramp(t, t0, 0.35), depth=depth, shadow=S.SHADOW_LOW)
    prog = ramp(t, t0 + 0.2, dur, "sine")
    if prog > 0:
        if fill:
            from .canvas import trim_path
            sub = trim_path(pts, prog)
            if len(sub) > 2:
                poly = np.vstack([sub, [[sub[-1][0], y0 + h], [sub[0][0], y0 + h]]])
                cv.fill_mask(cv.mask([poly], depth), color, 0.10)
        cv.stroke(pts, 9, color, depth, progress=prog)
        from .canvas import trim_path
        head = trim_path(pts, prog)[-1]
        if prog < 1:
            dot = S.cached(cv, "dot", lambda r: _disc(r, 13, "#fff8ee"))
            cv.place(dot, head[0], head[1], depth=depth)
    if title:
        headline(cv, t, [title], t0=t0 - 0.15, x=x0 + 40, y=y0 - 150, size=74, depth=depth, seed=seed)
    if label_end and prog >= 0.98:
        sp = S.cached(cv, ("lce", label_end), lambda r: text_sprite(label_end, S.ANTON, 86, r, color))
        S.slap(cv, sp, pts[-1][0] + 40, pts[-1][1] + 30, t, t0 + 0.2 + dur, -3,
               depth=depth, shadow=None, anchor=(0, 0.5))


def _disc(res, radius, color):
    import cv2
    from .canvas import Sprite, rgba
    n = int(radius * res * 2) + 6
    m = np.zeros((n, n), np.float32)
    cv2.circle(m, (n // 2, n // 2), int(radius * res), 1.0, -1, cv2.LINE_AA)
    img = np.zeros((n, n, 4), np.float32)
    img[..., :3] = np.array(rgba(color)[:3], np.float32) * m[..., None]
    img[..., 3] = m
    return Sprite(img, res)


def two_sided(cv, t, left, right, t0=0.0, y=540, seed=0, depth=0.0,
              left_label="", right_label=""):
    """Two paper columns for a contested point — the honest-explainer shot."""
    for i, (txt, lab, x, col) in enumerate([
            (left, left_label, 520, S.PAPER), (right, right_label, 1400, S.KRAFT)]):
        sp = S.cached(cv, ("ts", txt, col, seed), lambda r, txt=txt, col=col, i=i:
                      _note(r, txt, 620, 430, col, seed * 13 + i))
        S.slap(cv, sp, x, y, t, t0 + i * 0.18, -2.5 if i == 0 else 2.0, depth=depth)
        if lab:
            lp = S.cached(cv, ("tsl", lab), lambda r, lab=lab: P.stamp(lab, r, 40, S.ACCENT, seed=seed + i))
            S.slap(cv, lp, x, y - 250, t, t0 + 0.5 + i * 0.12, -7 + i * 12,
                   depth=depth, shadow=None, spin=0)


def _note(res, txt, w, h, tone, seed):
    from .text import text_rgba
    from .canvas import rgba
    sheet = P.paper_sheet(w, h, res, tone, seed, torn=2.6)
    img = sheet.img
    H, W = img.shape[:2]
    t = text_rgba(txt, S.TYPE, 34, res, "#ffffff", pad=0, align="center", line_height=1.45)[..., 3] / 255.0
    th, tw = t.shape
    y0, x0 = (H - th) // 2, (W - tw) // 2
    c = np.array(rgba(S.TEXT_DARK)[:3], np.float32)
    reg = img[y0:y0 + th, x0:x0 + tw]
    reg[..., :3] = reg[..., :3] * (1 - t[..., None] * 0.92) + c * t[..., None] * 0.92 * reg[..., 3:4]
    return sheet


def map_shot(cv, t, world, codes, highlight=None, t0=0.0, fill=0.42, label=None,
             title=None, sub=None, pins=(), zoom_from=None, zoom_dur=2.4, seed=0,
             lift_at=0.6, tex_cache=[]):
    """Camera move over the paper map, optionally zooming from a wider frame."""
    hx, hy, hz = world.frame(codes, fill=fill)
    if zoom_from:
        ax, ay, az = world.frame(zoom_from, fill=0.95)
        tr = Track((t0, (ax, ay, az)), (t0 + zoom_dur, (hx, hy, hz), "quint"))
        x, y, z = tr(t)
    else:
        x, y, z = hx, hy, hz
    z *= 1 + 0.04 * ramp(t, t0, 7, "sine")
    cv.cam.set(x + drift(t, 0.5, 12, seed) / z * 3, y + drift(t, 0.4, 15, seed + 1) / z * 3, z)
    S.desk(cv)
    tex = cv.texture(S.tile(5), 1.0, cv.k * cv.cam.zoom * 0.35)
    lift = ramp(t, t0 + lift_at, 0.8, "back")
    from . import geo
    hl = None
    if highlight:
        hl = {c: mix_color("#d6cbb3", col, ramp(t, t0 + lift_at - 0.2, 0.5, "sine"))
              for c, col in highlight.items()}
    geo.draw_map(cv, world, land="#d6cbb3", border="#8f8571", paper=tex,
                 highlight=hl, lift=lift)
    for i, (lon, lat, name) in enumerate(pins):
        px, py = world.point(lon, lat)
        p = cv.to_px([(px, py)])[0] / cv.k
        S.write_on(cv, P.hand_ellipse(px, py, 3.0 / z * 1.4, 2.2 / z * 1.4, seed=seed + i),
                   t, t0 + 1.2 + i * 0.2, 0.5, 5 / cv.cam.zoom, "#fff8ee")
        sp = S.cached(cv, ("pin", name), lambda r, name=name: P.label(name, r, 28, seed=seed + i))
        S.slap(cv, sp, p[0] + 170, p[1] - 80, t, t0 + 1.35 + i * 0.2, -3, depth=0,
               shadow=S.SHADOW_LOW)
    if title:
        headline(cv, t, [title], t0=t0 + 1.0, x=380, y=170, size=110, depth=0, sub=sub, seed=seed)
    if label:
        for i, (lon, lat, nm) in enumerate(label):
            px, py = world.point(lon, lat)
            p = cv.to_px([(px, py)])[0] / cv.k
            sp = S.cached(cv, ("cn", nm), lambda r, nm=nm: text_sprite(nm, S.INTER_SEMI, 17, r, "#6f6757", tracking=0.25))
            cv.place(sp, p[0], p[1], alpha=stagger(t, t0 + 0.8, i, 0.5, 6, ease="out") * 0.9, depth=0)


def counter(cv, t, t0, dur, lo, hi, x, y, size=190, prefix="", suffix="", color=None,
            depth=0.0, ease="expo", fmt="{:,.0f}", shake=0.0, seed=0, cache=[]):
    """A number ticking up. Values are quantised so the sprite cache stays small."""
    color = color or S.ACCENT
    u = ramp(t, t0, dur, ease)
    v = lo + (hi - lo) * u
    step = max(1, 10 ** max(0, int(math.log10(max(abs(hi), 1))) - 2))
    v = round(v / step) * step
    txt = prefix + fmt.format(v) + suffix
    sp = S.cached(cv, ("ctr", txt, size, color), lambda r: text_sprite(txt, S.ANTON, size, r, color))
    sx = shake * (1 - u) * math.sin(t * 47 + seed)
    sy = shake * (1 - u) * math.sin(t * 39 + seed + 2)
    cv.place(sp, x + sx, y + sy, alpha=ramp(t, t0, 0.25), depth=depth)
    return v


def arrow(cv, t, t0, p0, p1, dur=0.8, width=7.0, color=None, depth=0.0, bow=0.22,
          head=34.0, seed=0):
    """A hand-drawn curved arrow between two world points."""
    color = color or S.ACCENT
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    n = np.array([-d[1], d[0]])
    nl = np.linalg.norm(n)
    n = n / nl if nl > 1e-6 else n
    mid = (p0 + p1) / 2 + n * np.linalg.norm(d) * bow
    u = np.linspace(0, 1, 70)[:, None]
    pts = (1 - u) ** 2 * p0 + 2 * (1 - u) * u * mid + u ** 2 * p1
    rng = np.random.default_rng(seed)
    pts = pts + rng.normal(0, np.linalg.norm(d) * 0.004, pts.shape)
    prog = ramp(t, t0, dur, "sine")
    if prog <= 0:
        return
    cv.stroke(pts, width, color, depth, progress=prog)
    if prog > 0.97:
        tang = pts[-1] - pts[-6]
        tang = tang / max(np.linalg.norm(tang), 1e-6)
        perp = np.array([-tang[1], tang[0]])
        a = ramp(t, t0 + dur, 0.2)
        tip = pts[-1]
        for sgn in (1, -1):
            cv.stroke([tip, tip - tang * head * a + perp * head * 0.55 * sgn * a],
                      width, color, depth)


def share_blocks(cv, t, fraction, t0=0.0, cols=10, rows=4, x=REF_W / 2, y=560,
                 bw=112, bh=84, gap=16, color=None, dim="#4a453d", depth=0.0,
                 seed=0, label=None, sub=None):
    """A share of the whole as a grid of paper chips — easier to feel than a pie."""
    color = color or S.ACCENT
    n = cols * rows
    lit = fraction * n
    w = cols * bw + (cols - 1) * gap
    h = rows * bh + (rows - 1) * gap
    for i in range(n):
        r_, c_ = divmod(i, cols)
        a = stagger(t, t0, i, 0.3, 1, ease="out")
        if a <= 0:
            continue
        on = i < int(lit) or (i == int(lit) and (lit - int(lit)) > 0.35)
        sp = S.cached(cv, ("blk", on, bw, bh, seed), lambda r, on=on: P.paper_sheet(
            bw, bh, r, color if on else dim, seed + 90 + int(on), torn=1.6))
        cv.place(sp, x - w / 2 + c_ * (bw + gap) + bw / 2,
                 y - h / 2 + r_ * (bh + gap) + bh / 2,
                 alpha=a, scale=0.9 + 0.1 * a, rot=((i * 37) % 7 - 3) * 0.4,
                 depth=depth, shadow=S.SHADOW_LOW)
    if label:
        sp = S.cached(cv, ("sbl", label), lambda r: text_sprite(label, S.ANTON, 150, r, color))
        S.slap(cv, sp, x, y - h / 2 - 150, t, t0 + 0.4, -2, depth=depth, shadow=None)
    if sub:
        sp = S.cached(cv, ("sbs", sub), lambda r: P.label(sub, r, 30, seed=seed + 4))
        S.slap(cv, sp, x, y + h / 2 + 90, t, t0 + 0.6, 1.4, depth=depth, shadow=S.SHADOW_LOW)
