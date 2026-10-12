"""Video 1, Zimbabwe hyperinflation: the six style frames, built as animated
scenes so the 20-30 second motion test reuses them directly.

Each scene is fn(cv, t) with t in seconds from the scene's start. The style
frame for each is its final settled state (see SETTLE).

FIGURES ON SCREEN ARE PLACEHOLDERS until stage 2 (research) confirms them.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from engine import Track, ramp, drift, stagger, geo, post
from engine.ease import mix_color           # noqa: E402
from engine import style as S, paper as P                              # noqa: E402
from engine.text import text_sprite                                    # noqa: E402

_world = None


def world():
    global _world
    if _world is None:
        _world = geo.World()
    return _world


def camera_drift(cv, t, push=0.05, dur=6.0, x=960, y=540, seed=0):
    """Default camera: slow push-in plus organic drift. Never still."""
    z = 1 + push * ramp(t, 0, dur, "sine")
    cv.cam.set(x + drift(t, 7, 11, seed), y + drift(t, 5, 13, seed + 2), z, drift(t, 0.25, 15, seed))


# ------------------------------------------------------------------ 1. HOOK
def hook(cv, t):
    camera_drift(cv, t, 0.06, 7)
    S.desk(cv)
    S.scraps(cv, t, seed=11, n=8, alpha=0.4, blur=3.5)
    note = S.cached(cv, "note", lambda r: S.banknote(r, seed=1), 1.2)
    # a fanned stack: the same note three times, staggered
    for i, (dx, dy, rot) in enumerate([(-30, 40, -14), (-12, 18, -10), (0, 0, -6)]):
        S.slap(cv, note, 640 + dx, 430 + dy, t, 0.15 + i * 0.07, rot, 1.0)
    bread = S.cached(cv, "loaf", lambda r: S.loaf(r, seed=2), 1.2)
    S.slap(cv, bread, 1390, 400, t, 0.9, 4, 1.05)
    S.write_on(cv, P.hand_ellipse(1390, 395, 290, 190, seed=4), t, 1.5, 0.7, 7)
    lab = S.cached(cv, "lab_harare08", lambda r: P.label("HARARE, 2008", r, 30, seed=3))
    S.slap(cv, lab, 1560, 655, t, 1.25, 3, shadow=S.SHADOW_LOW)
    tp = S.cached(cv, "tape1", lambda r: P.tape(110, 36, r, seed=5))
    S.slap(cv, tp, 1700, 640, t, 1.35, 32, shadow=S.SHADOW_LOW, spin=0)
    # headline: few words, large, accent on the key word
    w1 = S.cached(cv, "h_loaf", lambda r: S.title_strip("ONE LOAF =", r, 112, seed=6))
    w2 = S.cached(cv, "h_millions", lambda r: S.title_strip(
        "MILLIONS", r, 150, paper=S.ACCENT, ink="#fff8ee", seed=7))
    S.slap(cv, w1, 610, 820, t, 2.2, -3, depth=1.02)
    S.slap(cv, w2, 1180, 860, t, 2.45, 2, depth=1.04)
    S.finish(cv)


# ------------------------------------------------------------------ 2. MAP
def map_zoom(cv, t):
    """Continent to country: a real camera zoom, Zimbabwe lifts off the page."""
    W = world()
    ax, ay, az = W.frame(["ZAF", "COD", "TZA", "AGO"], fill=0.95)
    zx, zy, zz = W.frame("ZWE", fill=0.34)
    zx += 70 / zz                       # leave room for the title on the left
    cam = Track((0, (ax, ay, az * 0.8)), (0.6, (ax, ay, az * 0.8)),
                (3.2, (zx, zy, zz), "quint"))
    x, y, z = cam(t)
    cv.cam.set(x + drift(t, 0.4, 11) / z * 3, y + drift(t, 0.3, 13, 2) / z * 3, z * (1 + 0.03 * ramp(t, 3.2, 4, "sine")))
    S.desk(cv)
    tex = cv.texture(S.tile(5), 1.0, cv.k * cv.cam.zoom * 0.35)
    land = "#d6cbb3"
    lift = ramp(t, 2.6, 0.8, "back")
    col = mix_color(land, S.ACCENT, ramp(t, 2.4, 0.5, "sine"))
    geo.draw_map(cv, W, land=land, border="#8f8571", paper=tex,
                 highlight={"ZWE": col} if t >= 2.4 else None, lift=lift)
    hx, hy = W.point(31.05, -17.83)                          # Harare
    S.write_on(cv, P.hand_ellipse(hx, hy, 3.2, 2.4, seed=3), t, 3.4, 0.6, 5 / cv.cam.zoom, "#fff8ee")
    if t > 3.6:
        p = cv.to_px([(hx, hy)])[0] / cv.k
        lab = S.cached(cv, "lab_harare", lambda r: P.label("HARARE", r, 30, seed=8))
        S.slap(cv, lab, p[0] + 190, p[1] - 85, t, 3.6, -4, depth=0, shadow=S.SHADOW_LOW)
        tp = S.cached(cv, "tape2", lambda r: P.tape(90, 32, r, seed=9))
        S.slap(cv, tp, p[0] + 290, p[1] - 100, t, 3.7, 40, depth=0, shadow=S.SHADOW_LOW, spin=0)
    # neighbours, quietly
    for i, (name, lon, lat) in enumerate([("ZAMBIA", 28.0, -14.6), ("MOZAMBIQUE", 35.0, -19.6),
                                          ("BOTSWANA", 23.6, -22.3), ("SOUTH AFRICA", 26.5, -24.0)]):
        a = stagger(t, 3.0, i, 0.5, 6, ease="out")
        if a > 0:
            sp = S.cached(cv, ("nb", name), lambda r, n=name: text_sprite(
                n, S.INTER_SEMI, 17, r, "#6f6757", tracking=0.25))
            px, py = W.point(lon, lat)
            p = cv.to_px([(px, py)])[0] / cv.k
            cv.place(sp, p[0], p[1], alpha=a * 0.9, depth=0)
    title = S.cached(cv, "t_zim", lambda r: S.title_strip("ZIMBABWE", r, 120, seed=10))
    S.slap(cv, title, 360, 150, t, 3.3, -3, depth=0)
    sub = S.cached(cv, "t_sa", lambda r: P.label("SOUTHERN AFRICA", r, 26, seed=11))
    S.slap(cv, sub, 300, 262, t, 3.45, 2, depth=0, shadow=S.SHADOW_LOW)
    S.finish(cv)


# ------------------------------------------------------------------ 3. CHART
def chart(cv, t):
    camera_drift(cv, t, 0.04, 7, seed=4)
    S.desk(cv, light=(0.55, 0.5))
    S.scraps(cv, t, seed=21, n=6, alpha=0.28, blur=4)
    vals = [1, 2, 4, 8, 16, 32, 64]
    x0, base, bw, gap, hmax = 470, 900, 120, 36, 560
    strip = S.cached(cv, "baseline", lambda r: P.paper_sheet(1080, 22, r, S.PAPER, 3, torn=2))
    cv.place(strip, x0 + 3 * (bw + gap) + bw / 2 - bw / 2 + 60, base + 12, rot=-0.4,
             shadow=S.SHADOW_LOW, alpha=ramp(t, 0.1, 0.4))
    for i, v in enumerate(vals):
        h = max(14, hmax * v / vals[-1])
        g = stagger(t, 0.5, i, 0.7, 9, ease="soft_back")
        if g <= 0:
            continue
        last = i == len(vals) - 1
        bar = S.cached(cv, ("bar", i), lambda r, h=h, last=last: P.paper_sheet(
            bw, h, r, S.ACCENT if last else S.KRAFT, 30 + i, torn=2.2), 1.0)
        x = x0 + i * (bw + gap) + bw / 2
        if last:
            cv.push()
        # bars grow up from the baseline (anchor at the bottom)
        cv.place(bar, x, base, scale=1.0, anchor=(0.5, 1.0), shadow=S.SHADOW,
                 alpha=min(1, g * 3), rot=0.6 * (i % 2 * 2 - 1))
        if last:
            post.glow_pop(cv, 22, 0.55 * ramp(t, 1.8, 0.6))
        lab = S.cached(cv, ("x", i), lambda r, v=v, last=last: text_sprite(
            f"×{v}", S.ANTON, 64 if last else 34, r, S.PAPER))
        cv.place(lab, x, base - h * min(g, 1) - (52 if last else 34), alpha=ramp(t, 0.9 + i * 0.15, 0.3))
        day = S.cached(cv, ("d", i), lambda r, i=i: text_sprite(f"DAY {i + 1}", S.TYPE, 22, r, "#a59c8a"))
        cv.place(day, x, base + 50, alpha=ramp(t, 0.5 + i * 0.15, 0.3))
    t1 = S.cached(cv, "c_title", lambda r: S.title_strip("PRICES DOUBLED", r, 96, seed=12))
    S.slap(cv, t1, 560, 150, t, 0.2, -2, depth=0.6)
    t2 = S.cached(cv, "c_sub", lambda r: P.label("ABOUT EVERY 24 HOURS  ·  NOV 2008", r, 26, seed=13))
    S.slap(cv, t2, 560, 250, t, 0.4, 1, depth=0.6, shadow=S.SHADOW_LOW)
    src = S.cached(cv, "c_src", lambda r: text_sprite(
        "SOURCE: HANKE & KWOK, CATO JOURNAL (2009)  [TO VERIFY]", S.TYPE, 17, r, "#8a8270"))
    cv.place(src, 1880, 1040, anchor=(1, 0.5), alpha=ramp(t, 1.0, 0.5), depth=0)
    S.finish(cv)


# ------------------------------------------------------------------ 4. CASE FILE
def case_file(cv, t):
    camera_drift(cv, t, 0.05, 7, seed=6)
    S.desk(cv, light=(0.5, 0.5))
    fold = S.cached(cv, "folder", lambda r: S.folder(r, 1300, 800, seed=4, tab="CASE FILE 01"))
    S.slap(cv, fold, 960, 560, t, 0.0, -1.5, shadow=S.SHADOW, dur=0.5)
    photo = S.cached(cv, "bank", lambda r: S.bank_facade(r, seed=3), 1.1)
    S.slap(cv, photo, 640, 520, t, 0.35, -4, 0.95)
    clip = S.cached(cv, "clip", lambda r: P and S.paper_clip(r, 130))
    S.slap(cv, clip, 560, 330, t, 0.6, -8, shadow=S.SHADOW_LOW, spin=0)
    fig = S.cached(cv, "fig", lambda r: text_sprite("FIG. 1  ·  ILLUSTRATION", S.TYPE, 20, r, "#3b352c"))
    cv.place(fig, 640, 760, rot=-4, alpha=ramp(t, 0.8, 0.4))
    sheet = S.cached(cv, "sheet", lambda r: P.paper_sheet(560, 470, r, S.PAPER, 14, torn=0))
    S.slap(cv, sheet, 1260, 560, t, 0.5, 2.5, shadow=S.SHADOW_LOW)
    rows = [("SUBJECT", "RESERVE BANK OF ZIMBABWE"), ("ROLE", "CENTRAL BANK"),
            ("GOVERNOR", "GIDEON GONO, 2003-13"), ("METHOD", "PRINTING MONEY")]
    for i, (k, v) in enumerate(rows):
        a = stagger(t, 0.9, i, 0.25, 8, ease="out")
        sp = S.cached(cv, ("row", i), lambda r, k=k, v=v: text_sprite(
            f"{k}:\n{v}", S.TYPE, 27, r, S.TEXT_DARK, line_height=1.25))
        cv.place(sp, 1010, 375 + i * 104, rot=2.5, alpha=a, anchor=(0, 0))
    ul = P.hand_underline(1005, 1250, 0, seed=5, double=True)
    ul[:, 1] += 778 + (ul[:, 0] - 1005) * 0.044           # follow the 2.5 degree tilt
    S.write_on(cv, ul, t, 1.7, 0.5, 5)
    st = S.cached(cv, "stamp_a", lambda r: P.stamp("EXHIBIT A", r, 54, S.ACCENT, seed=6))
    S.slap(cv, st, 1390, 860, t, 2.0, -11, scale=1.0, shadow=None, dur=0.25, spin=0)
    S.finish(cv)


# ------------------------------------------------------------------ 5. CHAPTER CARD
def chapter(cv, t):
    camera_drift(cv, t, 0.07, 6, seed=8)
    S.desk(cv, light=(0.5, 0.5))
    S.scraps(cv, t, seed=31, n=10, alpha=0.5, blur=3.5)
    big = S.cached(cv, "big3", lambda r: text_sprite("03", S.ANTON, 520, r, "#2c2924"))
    cv.place(big, 1420, 520, depth=0.7, alpha=ramp(t, 0, 0.6), rot=-3)
    lab = S.cached(cv, "ch3", lambda r: P.label("CHAPTER 3", r, 30, seed=15))
    S.slap(cv, lab, 640, 215, t, 0.1, -2, shadow=S.SHADOW_LOW)
    words = [("THE", S.PAPER, S.TEXT_DARK, 120, 600, 345, -3),
             ("PRINTING", S.ACCENT, "#fff8ee", 170, 930, 570, 2),
             ("PRESS", S.PAPER, S.TEXT_DARK, 170, 850, 815, -1.5)]
    for i, (w, pc, ic, size, x, y, rot) in enumerate(words):
        sp = S.cached(cv, ("cw", w), lambda r, w=w, pc=pc, ic=ic, size=size: S.title_strip(
            w, r, size, paper=pc, ink=ic, seed=40 + len(w)))
        S.slap(cv, sp, x, y, t, 0.35 + i * 0.12, rot)
    tp = S.cached(cv, "tape3", lambda r: P.tape(170, 46, r, seed=16))
    S.slap(cv, tp, 1250, 470, t, 0.9, 30, shadow=S.SHADOW_LOW, spin=0)
    S.finish(cv)


# ------------------------------------------------------------------ 6. THUMBNAIL
def thumbnail(cv, t=10.0):
    """1280x720 frame: one idea, max three words, readable at phone size."""
    cv.cam.set(960, 540, 1.0)
    S.desk(cv, light=(0.6, 0.4))
    note = S.cached(cv, "note_t", lambda r: S.banknote(r, seed=1), 1.2)
    cv.place(note, 600, 470, 1.45, -9, shadow=S.SHADOW_HIGH)
    cv.place(note, 560, 520, 1.45, -15, shadow=S.SHADOW, alpha=1)
    cv.place(note, 640, 430, 1.45, -5, shadow=S.SHADOW_HIGH)
    bread = S.cached(cv, "loaf_t", lambda r: S.loaf(r, seed=2), 1.3)
    cv.place(bread, 1480, 470, 1.3, 5, shadow=S.SHADOW_HIGH)
    cv.stroke(P.hand_ellipse(1480, 460, 330, 235, seed=9), 12, S.ACCENT)
    w1 = S.cached(cv, "nt", lambda r: S.title_strip("NOT", r, 210, seed=17))
    w2 = S.cached(cv, "en", lambda r: S.title_strip("ENOUGH", r, 230, paper=S.ACCENT, ink="#fff8ee", seed=18))
    cv.place(w1, 390, 880, 1, -4, shadow=S.SHADOW_HIGH)
    cv.place(w2, 1170, 870, 1, 2, shadow=S.SHADOW_HIGH)
    S.finish(cv, 0.4)


SCENES = [("1_hook", hook, 4.0), ("2_map", map_zoom, 5.0), ("3_chart", chart, 4.0),
          ("4_case_file", case_file, 3.5), ("5_chapter_card", chapter, 2.5)]
SETTLE = {"1_hook": 3.6, "2_map": 4.6, "3_chart": 3.6, "4_case_file": 3.2, "5_chapter_card": 2.2}
