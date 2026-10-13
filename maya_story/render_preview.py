"""
Stand-alone 2D preview of SPARK (the same 60 s beat sheet as spark_story.py),
rendered without Maya so the story can be watched anywhere.

    python3 render_preview.py            # -> spark_preview.mp4 (1280x720, 24 fps, 60 s, with music)

Needs: Python 3, Pillow, numpy, ffmpeg on PATH.
"""

import math
import os
import random
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DURATION = 1280, 720, 24, 60.0
SS = 1.5  # supersampling for anti-aliased shapes
RW, RH = int(W * SS), int(H * SS)
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_SERIF_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"

# ----------------------------------------------------------------------------- easing / tracks


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    if isinstance(a, tuple):
        return tuple(lerp(x, y, t) for x, y in zip(a, b))
    return a + (b - a) * t


def track(keys, t, ease=smooth):
    """keys: [(time, value), ...] sorted. Eased interpolation, clamped at the ends."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            return lerp(v0, v1, ease((t - t0) / (t1 - t0)) if t1 > t0 else 1.0)
    return keys[-1][1]


def fade(t, t_in, t_out, d=0.6):
    return smooth((t - t_in) / d) * (1 - smooth((t - t_out) / d))


# ----------------------------------------------------------------------------- story timing

ROBOT_START_X, ROBOT_END_X, STAR_X = -300.0, 175.0, 250.0
WALK_T0, WALK_T1 = 16.0, 27.0


def robot_x(t):
    if t < WALK_T0:
        return ROBOT_START_X
    if t > WALK_T1:
        return ROBOT_END_X
    return lerp(ROBOT_START_X, ROBOT_END_X, (t - WALK_T0) / (WALK_T1 - WALK_T0))


def robot_pose(t):
    p = {}
    walking = WALK_T0 <= t <= WALK_T1
    phase = (t - WALK_T0) * 2 * math.pi / 1.0 if walking else 0.0  # one stride / second
    swing = 28 * math.sin(phase) * smooth((t - WALK_T0) / 0.4) * (1 - smooth((t - WALK_T1 + 0.4) / 0.4))
    p["legF"], p["legB"] = swing, -swing
    p["bob"] = abs(math.sin(phase)) * 5 if walking else 0.0

    # lean (deg, + = forward)
    p["lean"] = track([(0, 16), (11.5, 16), (12.5, -6), (13.2, 0), (28, 0), (29.5, 26), (31.5, 0),
                       (41.5, 0), (43.5, 18), (53.5, 18), (54.3, 0)], t)
    p["lean"] += math.sin(t * 1.4) * 1.5 if t < 11 else 0  # sleepy breathing

    # head tilt (deg, + = look down)
    p["head"] = track([(0, 24), (11.5, 24), (12.3, -12), (13.5, 0), (14.3, -14), (15.5, 0),
                       (32, 0), (34, 22), (36.5, 22), (38, 8), (41.5, 0), (43, 28),
                       (53.5, 28), (54.5, -22), (60, -22)], t)

    # eye brightness 0..1 (with wake-up blinks)
    if t < 11.8:
        eye = 0.0
    elif t < 12.6:
        eye = 1.0 if (12.0 <= t < 12.4 or t >= 12.55) else 0.0
    else:
        eye = 1.0
    if 41.5 <= t < 53.6:
        eye = 1 - smooth((t - 41.5) / 1.5)
        eye *= 1 if t < 42.4 or int(t * 12) % 3 else 0.4  # flicker as it dies
    if t >= 53.6:
        eye = smooth((t - 53.6) / 0.6)
    p["eye"] = eye

    # core (heart light) 0..1
    core = 0.65 + 0.25 * math.sin(t * 1.8) if t < 9 else 1.0
    if t >= 40.5:
        core = 0.0
    if t >= 53.4:
        core = smooth((t - 53.4) / 0.5)
    p["core"] = core

    # chest door 0 closed .. 1 open
    p["door"] = track([(36.5, 0), (38, 1), (52.5, 1), (54, 0)], t)

    # arms (deg from straight down, + = forward)
    arm = track([(28.5, 0), (29.5, 55), (31.5, 80), (43, 80), (44.5, 0)], t)
    p["armF"] = arm + (-0.8 * swing if walking else 0)
    p["armB"] = arm + (0.8 * swing if walking else 0)
    wave_up = track([(54.5, 0), (55.3, 1)], t)
    if wave_up > 0:
        p["armF"] = lerp(p["armF"], 160 + 20 * math.sin((t - 55.3) * 9), wave_up)
    return p


def core_world(t):
    """World position of Bolt's core window."""
    p = robot_pose(t)
    hx, hy = robot_x(t), 62 + p["bob"]
    lx, ly = rot((24, 52), p["lean"])
    return hx + lx, hy + ly


def star_state(t):
    """Fallen star: (visible, x, y, brightness, size)."""
    if t < 8.4:
        return None
    if t < 10.8:
        k = (t - 8.4) / 2.4
        k = k * k  # accelerate
        x, y = lerp(-900, STAR_X, k), lerp(1100, 12, k)
        return (x, y, 1.0, 12)
    if t < 29.5:
        return (STAR_X, 12 + 2 * math.sin(t * 3), 0.85 + 0.15 * math.sin(t * 5), 12)
    if t < 31.5:
        k = smooth((t - 29.5) / 2)
        cx, cy = core_world(t)
        return (lerp(STAR_X, cx + 40, k), lerp(12, cy + 10, k), lerp(0.9, 0.7, k), 12)
    cx, cy = core_world(t)
    hold = (cx + 40, cy + 10)
    if t < 40.5:
        b = 0.7 * (1 - smooth((t - 31.5) / 4.5)) + 0.08
        b *= 1 if t < 34 or int(t * 10) % 4 else 0.5
        return (hold[0], hold[1], b, 12)
    if t < 44:
        b = track([(40.5, 0.08), (41.5, 1.4), (44, 1.0)], t)
        return (hold[0], hold[1] + 4 * smooth((t - 41.5) / 2.5), b, 12 + 4 * smooth((t - 41.5)))
    if t < 49.5:
        k = smooth((t - 44) / 5.5)
        return (lerp(hold[0], hold[0] - 120, k), lerp(hold[1] + 4, 1300, k), 1.0, 14 + 4 * k)
    return None


def gift_state(t):
    if not 50.3 <= t <= 53.5:
        return None
    k = smooth((t - 50.3) / 3.0)
    cx, cy = core_world(t)
    # gentle swaying descent
    x = lerp(cx + 260, cx, k) + 40 * math.sin(k * math.pi * 2) * (1 - k)
    y = lerp(cy + 520, cy, k)
    return (x, y, 1.0 - 0.3 * smooth((t - 53.1) / 0.4), 7)


def camera(t):
    """(cx, cy, zoom) with hard cuts between shots."""
    shots = [
        (0.0, 8.2, [(0, (-120, 160, 0.85)), (8.2, (-260, 110, 1.35))]),
        (8.2, 11.2, [(8.2, (-60, 240, 0.62)), (11.2, (-20, 220, 0.66))]),
        (11.2, 16.0, [(11.2, (-300, 105, 1.9)), (16, (-290, 110, 1.75))]),
        (16.0, 28.0, None),  # tracking shot
        (28.0, 36.2, [(28, (230, 110, 1.45)), (36.2, (215, 105, 1.7))]),
        (36.2, 44.2, [(36.2, (205, 100, 2.1)), (44.2, (200, 105, 2.3))]),
        (44.2, 50.3, [(44.2, (190, 160, 1.3)), (49.6, (130, 560, 0.75))]),
        (50.3, 54.6, [(50.3, (230, 200, 1.0)), (54.6, (190, 115, 1.55))]),
        (54.6, 60.1, [(54.6, (180, 115, 1.6)), (60, (120, 300, 0.7))]),
    ]
    for t0, t1, keys in shots:
        if t0 <= t < t1:
            if keys is None:
                rx = robot_x(t)
                return (rx + 90, 120, 1.15)
            return track(keys, t, ease=lambda k: k * k * (3 - 2 * k) * 0.6 + k * 0.4)
    return shots[-1][2][-1][1]


def subtitle(t):
    lines = [
        (3.0, 7.6, "Under a quiet moon, a little robot named Bolt slept alone."),
        (12.6, 15.8, "Then, one night, a star fell."),
        (18.0, 26.0, "Bolt had never held a star before."),
        (32.0, 36.0, "But its light was fading..."),
        (37.5, 43.6, "So Bolt gave it the only light he had."),
        (45.0, 49.6, "The star went home."),
        (50.5, 54.3, "And the whole sky said thank you."),
    ]
    for t0, t1, text in lines:
        if t0 - 0.6 <= t <= t1 + 0.6:
            return text, fade(t, t0, t1)
    return None, 0.0


# ----------------------------------------------------------------------------- static assets

rng = random.Random(7)
STARS_BASE = [(rng.uniform(0, W), rng.uniform(0, H * 0.62), rng.uniform(0.6, 1.8), rng.uniform(0, 6.3))
              for _ in range(110)]
STARS_BLOOM = []
for _ in range(340):
    x, y = rng.uniform(0, W), rng.uniform(0, H * 0.68)
    STARS_BLOOM.append((x, y, rng.uniform(0.8, 2.4), rng.uniform(0, 6.3),
                        math.hypot(x - W * 0.45, y - H * 0.15)))  # distance from where the star rejoins the sky
STAR_HOME = (W * 0.45, H * 0.15)
JUNK = [(-520, 70, 40, 12), (-430, 40, 30, -8), (-150, 50, 26, 20), (420, 80, 50, 6), (540, 34, 24, -15)]


def make_sky():
    y = np.linspace(0, 1, RH)[:, None]
    top = np.array([6, 8, 24], float)
    mid = np.array([18, 22, 58], float)
    bot = np.array([52, 38, 86], float)
    col = np.where(y < 0.6, lerp(top, mid, y / 0.6), lerp(mid, bot, (y - 0.6) / 0.4))
    arr = np.broadcast_to(col[:, None, :], (RH, RW, 3)).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def make_vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.hypot((xx - W / 2) / (W / 2), (yy - H / 2) / (H / 2))
    v = np.clip(1.0 - 0.45 * np.clip(d - 0.55, 0, None) ** 1.6, 0, 1)
    return v[..., None]


SKY = None
VIGNETTE = None
FONT_SUB = FONT_TITLE = FONT_SMALL = None


def init_worker():
    global SKY, VIGNETTE, FONT_SUB, FONT_TITLE, FONT_SMALL
    SKY = make_sky()
    VIGNETTE = make_vignette()
    FONT_SUB = ImageFont.truetype(FONT_SERIF, 30)
    FONT_TITLE = ImageFont.truetype(FONT_SERIF_BOLD, 110)
    FONT_SMALL = ImageFont.truetype(FONT_SERIF, 26)


# ----------------------------------------------------------------------------- geometry


def rot(p, deg, about=(0, 0)):
    a = math.radians(-deg)  # + deg tips the top forward (toward +x)
    x, y = p[0] - about[0], p[1] - about[1]
    return (about[0] + x * math.cos(a) - y * math.sin(a), about[1] + x * math.sin(a) + y * math.cos(a))


class View:
    def __init__(self, cam):
        self.cx, self.cy, self.z = cam

    def __call__(self, wx, wy, parallax=1.0):
        sx = W / 2 + (wx - self.cx * parallax) * self.z
        sy = H * 0.62 - (wy - self.cy * parallax) * self.z
        return sx * SS, sy * SS

    def r(self, v):
        return v * self.z * SS


def rect_pts(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def rounded_pts(x0, y0, x1, y1, r, n=5):
    pts = []
    for cx, cy, a0 in ((x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# ----------------------------------------------------------------------------- drawing


def glow_dot(glow, view, wx, wy, radius, color, strength):
    """Paint onto the low-res glow buffer (W/2 x H/2), blurred later."""
    if strength <= 0:
        return
    sx, sy = view(wx, wy)
    sx, sy, r = sx / SS / 2, sy / SS / 2, view.r(radius) / SS / 2
    c = tuple(int(min(255, v * strength)) for v in color)
    glow.ellipse([sx - r, sy - r, sx + r, sy + r], fill=c)


def draw_robot(d, glow, view, t):
    p = robot_pose(t)
    hx, hy = robot_x(t), 62 + p["bob"]
    copper, copper_dark = (196, 110, 52), (130, 70, 36)
    steel, steel_dark = (48, 50, 62), (30, 31, 40)
    moonlit = (226, 150, 88)

    def W2S(local, base=(0, 0), ang=0.0, pivot=(0, 0)):
        # local (torso space) -> rotate by limb around pivot -> lean around hip -> world -> screen
        x, y = rot((local[0] + base[0], local[1] + base[1]), ang, pivot)
        x, y = rot((x, y), p["lean"])
        return view(hx + x, hy + y)

    def poly(pts, fill, **kw):
        d.polygon([W2S(q, **kw) for q in pts], fill=fill)

    def limb(top, length, width, ang, color, end_color, end_r):
        pts = rect_pts(top[0] - width / 2, top[1] - length, top[0] + width / 2, top[1])
        pts = [rot(q, ang, top) for q in pts]
        d.polygon([W2S(q) for q in pts], fill=color)
        ex, ey = rot((top[0], top[1] - length), ang, top)
        sx, sy = W2S((ex, ey))
        r = view.r(end_r)
        d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=end_color)

    # back leg / arm (behind the body)
    def leg(ang, shade):
        top = (0, 0)
        x, y = rot((0, -56), ang)
        pts = [rot(q, ang) for q in rect_pts(-8, -56, 8, 0)]
        d.polygon([view(hx + q[0], hy + q[1]) for q in pts], fill=shade[0])
        foot = [(x - 12, y - 8), (x + 22, y - 8), (x + 22, y + 6), (x - 12, y + 6)]
        d.polygon([view(hx + q[0], hy + q[1]) for q in foot], fill=shade[1])

    leg(p["legB"], (steel_dark, copper_dark))
    limb((0, 80), 50, 13, p["armB"], steel_dark, copper_dark, 10)

    # torso
    poly(rounded_pts(-38, -2, 40, 96, 14), copper)
    poly(rounded_pts(-38, 60, -8, 96, 10), moonlit)  # rim light from the moon (behind/left)
    poly(rect_pts(-30, 6, 32, 12), copper_dark)
    for bx in (-26, 26):  # rivets
        sx, sy = W2S((bx, 86))
        r = view.r(2.6)
        d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=copper_dark)

    # core window + core
    cxs, cys = W2S((24, 52))
    rr = view.r(15)
    d.ellipse([cxs - rr, cys - rr, cxs + rr, cys + rr], fill=(24, 18, 16))
    core = p["core"]
    if core > 0:
        rc = view.r(11)
        col = tuple(int(lerp(a, b, core)) for a, b in zip((60, 35, 20), (255, 196, 92)))
        d.ellipse([cxs - rc, cys - rc, cxs + rc, cys + rc], fill=col)
        hx_, hy_ = rot((24, 52), p["lean"])
        glow_dot(glow, view, hx + hx_, hy + hy_, 20, (255, 170, 70), core * 0.75)
    # chest door hinged on its top edge, swinging outward (shown as foreshortening)
    door = p["door"]
    if door < 0.98:
        h = 30 * math.cos(door * math.pi * 0.55)
        poly(rect_pts(8, 67 - h, 40, 67), steel)
        poly(rect_pts(10, 67 - h, 38, 67 - h + 3), steel_dark)
    if door > 0.02:
        flap = 14 * math.sin(door * math.pi * 0.5)
        poly([(40, 67), (40 + flap, 64), (40 + flap, 60), (40, 63)], steel_dark)

    # head (tilts about the neck)
    neck = (0, 98)
    hang = p["head"]
    poly(rect_pts(-6, 94, 6, 106), steel)
    head_pts = [rot(q, hang, neck) for q in rounded_pts(-34, 102, 38, 156, 12)]
    d.polygon([W2S(q) for q in head_pts], fill=copper)
    rim = [rot(q, hang, neck) for q in rounded_pts(-34, 130, -14, 156, 9)]
    d.polygon([W2S(q) for q in rim], fill=moonlit)
    visor = [rot(q, hang, neck) for q in rounded_pts(6, 116, 40, 146, 8)]
    d.polygon([W2S(q) for q in visor], fill=(20, 22, 30))
    ex, ey = rot((26, 131), hang, neck)
    sx, sy = W2S((ex, ey))
    eye = p["eye"]
    re = view.r(8.5)
    eye_col = tuple(int(lerp(a, b, eye)) for a, b in zip((34, 40, 52), (140, 240, 255)))
    d.ellipse([sx - re, sy - re * 0.85, sx + re, sy + re * 0.85], fill=eye_col)
    if eye > 0:
        wx, wy = rot((ex, ey), p["lean"])
        glow_dot(glow, view, hx + wx, hy + wy, 20, (90, 210, 255), eye * 0.9)
    # antenna
    a0, a1 = rot((-4, 156), hang, neck), rot((-6, 182), hang, neck)
    d.line([W2S(a0), W2S(a1)], fill=steel, width=max(1, int(view.r(3))))
    sx, sy = W2S(a1)
    ra = view.r(5)
    blink = eye * (0.6 + 0.4 * (math.sin(t * 4) > 0))
    d.ellipse([sx - ra, sy - ra, sx + ra, sy + ra], fill=tuple(int(lerp(a, b, blink)) for a, b in zip((60, 40, 40), (255, 90, 80))))
    if blink > 0:
        wx, wy = rot(a1, p["lean"])
        glow_dot(glow, view, hx + wx, hy + wy, 10, (255, 80, 60), blink * 0.7)

    # front leg / arm
    leg(p["legF"], (steel, copper))
    limb((0, 80), 50, 13, p["armF"], steel, copper, 10)


def draw_star_shape(d, glow, view, x, y, b, size, t, color=(255, 236, 160)):
    sx, sy = view(x, y)
    r = view.r(size)
    spin = t * 1.3
    pts = []
    for i in range(10):
        rad = r if i % 2 == 0 else r * 0.45
        a = spin + i * math.pi / 5
        pts.append((sx + rad * math.cos(a), sy + rad * math.sin(a)))
    col = tuple(int(lerp(70, c, min(1, b))) for c in color)
    d.polygon(pts, fill=col)
    glow_dot(glow, view, x, y, size * 3, (255, 220, 130), min(1.0, b))
    glow_dot(glow, view, x, y, size * 1.6, (255, 255, 230), min(1.2, b))


def render_frame(i):
    t = i / FPS
    view = View(camera(t))
    img = SKY.copy()
    d = ImageDraw.Draw(img)
    glow_img = Image.new("RGB", (W // 2, H // 2))
    glow = ImageDraw.Draw(glow_img)

    # sky moves a little with the camera (very far away)
    sky_dx = -view.cx * 0.04 * view.z
    sky_dy = (view.cy - 110) * 0.18 * view.z

    for x, y, r, ph in STARS_BASE:
        tw = 0.55 + 0.45 * math.sin(t * 2.2 + ph)
        sx, sy = ((x + sky_dx) % W) * SS, (y + sky_dy) * SS
        rr = r * SS * 0.8
        c = int(150 + 105 * tw)
        d.ellipse([sx - rr, sy - rr, sx + rr, sy + rr], fill=(c, c, min(255, c + 20)))

    # the sky answers: stars bloom outward from where the fallen star rejoined it
    if t >= 48.6:
        for x, y, r, ph, dist in STARS_BLOOM:
            appear = 48.6 + dist / 520.0
            k = smooth((t - appear) / 0.5)
            if k <= 0:
                continue
            pop = 1 + 1.4 * math.exp(-max(0, t - appear) * 4)
            tw = 0.6 + 0.4 * math.sin(t * 3 + ph)
            sx, sy = ((x + sky_dx) % W) * SS, (y + sky_dy) * SS
            rr = r * SS * k * pop
            c = (int(255 * tw), int(235 * tw), int(190 + 50 * tw))
            d.ellipse([sx - rr, sy - rr, sx + rr, sy + rr], fill=c)
            if r > 1.9:
                glow.ellipse([sx / SS / 2 - 3, sy / SS / 2 - 3, sx / SS / 2 + 3, sy / SS / 2 + 3],
                             fill=(int(120 * k * tw),) * 2 + (int(90 * k),))
    if 48.6 <= t <= 50.5:  # flash where the star arrives home
        k = math.exp(-(t - 48.9) ** 2 * 6)
        hx, hy = (STAR_HOME[0] + sky_dx) / 2, (STAR_HOME[1] + sky_dy) / 2
        rr = 10 + 30 * k
        glow.ellipse([hx - rr, hy - rr, hx + rr, hy + rr], fill=(int(255 * k), int(230 * k), int(160 * k)))
        rr = view.r(0) + 6 * SS
        d.ellipse([hx * 2 * SS - rr, hy * 2 * SS - rr, hx * 2 * SS + rr, hy * 2 * SS + rr], fill=(255, 250, 220))

    # moon
    mx, my = (230 + sky_dx * 1.5) * SS, (120 + sky_dy * 1.2) * SS
    mr = 46 * SS
    glow.ellipse([mx / SS / 2 - 50, my / SS / 2 - 50, mx / SS / 2 + 50, my / SS / 2 + 50], fill=(60, 66, 90))
    d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(238, 236, 214))
    for ox, oy, cr in ((-14, -10, 9), (12, 14, 7), (18, -16, 5)):
        d.ellipse([mx + ox * SS - cr * SS, my + oy * SS - cr * SS, mx + ox * SS + cr * SS, my + oy * SS + cr * SS],
                  fill=(214, 212, 192))

    # shooting star trail
    st = star_state(t)
    if st and t < 10.8:
        k0 = max(0, (t - 0.45 - 8.4) / 2.4)
        tx, ty = lerp(-900, STAR_X, k0 * k0), lerp(1100, 12, k0 * k0)
        p0, p1 = view(tx, ty), view(st[0], st[1])
        for wdt, col in ((10, (90, 80, 60)), (5, (220, 200, 140)), (2, (255, 255, 230))):
            d.line([p0, p1], fill=col, width=int(wdt * SS))
        gx0, gy0 = p0[0] / SS / 2, p0[1] / SS / 2
        gx1, gy1 = p1[0] / SS / 2, p1[1] / SS / 2
        glow.line([(gx0, gy0), (gx1, gy1)], fill=(140, 120, 80), width=8)

    # far hills (parallax)
    pts = [view(x, 40 + 50 * math.sin(x * 0.004) + 25 * math.sin(x * 0.011 + 1), 0.45) for x in range(-2400, 2401, 40)]
    pts += [view(2400, -900, 0.45), view(-2400, -900, 0.45)]
    d.polygon(pts, fill=(22, 24, 46))
    # near ground
    pts = [view(x, 6 * math.sin(x * 0.02) + (0 if abs(x - STAR_X) > 60 else -6 * math.cos((x - STAR_X) / 60 * math.pi / 2)))
           for x in range(-2400, 2401, 20)]
    pts += [view(2400, -900), view(-2400, -900)]
    d.polygon(pts, fill=(14, 18, 32))
    # moonlit grass tufts
    for gx in range(-1200, 1201, 37):
        h = 8 + (gx * 7919 % 13)
        a, b = view(gx, 2), view(gx + 4, 2 + h)
        d.line([a, b], fill=(40, 52, 80), width=max(1, int(view.r(2))))
    # junk silhouettes
    for jx, jw, jh, ang in JUNK:
        q = [rot(c, ang, (jx, 0)) for c in rect_pts(jx - jw / 2, -4, jx + jw / 2, jh)]
        d.polygon([view(*c) for c in q], fill=(28, 26, 38))
    # crater glow while the star rests there
    if st and 10.8 <= t < 30:
        glow_dot(glow, view, STAR_X, 2, 60, (255, 190, 90), 0.6)

    draw_robot(d, glow, view, t)

    if st:
        draw_star_shape(d, glow, view, st[0], st[1], st[2], st[3], t)
    # impact flash
    if 10.75 <= t <= 12.0:
        k = math.exp(-(t - 10.8) * 4)
        glow_dot(glow, view, STAR_X, 10, 260 * (1.2 - k * 0.2), (255, 220, 160), k)
    # the core drifts from Bolt's chest into the star
    if 38.5 <= t < 41.0:
        k = smooth((t - 38.5) / 2.0)
        cx, cy = core_world(t)
        sx_, sy_ = cx + 40, cy + 10
        x, y = lerp(cx, sx_, k), lerp(cy, sy_, k) + 30 * math.sin(k * math.pi)
        rr = view.r(9)
        s = view(x, y)
        d.ellipse([s[0] - rr, s[1] - rr, s[0] + rr, s[1] + rr], fill=(255, 210, 120))
        glow_dot(glow, view, x, y, 30, (255, 170, 70), 1.0)
    g = gift_state(t)
    if g:
        draw_star_shape(d, glow, view, g[0], g[1], g[2], g[3], t * 2)
    if 53.2 <= t <= 54.4:  # the gift settles in: warm burst
        k = math.exp(-(t - 53.4) ** 2 * 8)
        cx, cy = core_world(t)
        glow_dot(glow, view, cx, cy, 70, (255, 190, 100), k)

    # compose: downsample, add bloom, vignette
    frame = img.resize((W, H), Image.LANCZOS)
    blurred = glow_img.filter(ImageFilter.GaussianBlur(9)).resize((W, H), Image.BILINEAR)
    frame = ImageChops.add(frame, blurred)
    frame = ImageChops.add(frame, glow_img.filter(ImageFilter.GaussianBlur(3)).resize((W, H), Image.BILINEAR))
    arr = np.asarray(frame, dtype=np.float32) * VIGNETTE

    # letterbox + text
    frame = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(frame, "RGBA")
    d.rectangle([0, 0, W, 42], fill=(0, 0, 0, 255))
    d.rectangle([0, H - 42, W, H], fill=(0, 0, 0, 255))

    text, a = subtitle(t)
    if text and a > 0:
        tw = d.textlength(text, font=FONT_SUB)
        d.text(((W - tw) / 2 + 2, H - 112 + 2), text, font=FONT_SUB, fill=(0, 0, 0, int(200 * a)))
        d.text(((W - tw) / 2, H - 112), text, font=FONT_SUB, fill=(250, 240, 220, int(255 * a)))

    title_a = fade(t, 0.6, 2.8, 0.8) + fade(t, 56.0, 61, 0.9)
    if title_a > 0:
        ty = H * 0.30 if t < 50 else H * 0.12
        for txt, font, y in (("SPARK", FONT_TITLE, ty), ("a very short story about giving", FONT_SMALL, ty + 128)):
            if t > 50 and font is FONT_SMALL:
                txt = "The End"
            tw = d.textlength(txt, font=font)
            d.text(((W - tw) / 2, y), txt, font=font, fill=(255, 226, 160, int(255 * min(1, title_a))))

    # fade from / to black
    k = min(smooth(t / 1.0), 1 - smooth((t - 58.8) / 1.2))
    if k < 1:
        frame = Image.blend(Image.new("RGB", (W, H)), frame, k)
    return frame.tobytes()


# ----------------------------------------------------------------------------- audio

SR = 44100


def synth_audio(path):
    n = int(SR * DURATION)
    tt = np.arange(n) / SR
    out = np.zeros(n)

    def note(f, t0, dur, amp, attack=0.8, release=1.5, harm=(1, 0.5, 0.25)):
        i0, i1 = int(t0 * SR), min(n, int((t0 + dur + release) * SR))
        if i0 >= n:
            return
        x = tt[i0:i1] - t0
        env = np.minimum(1, x / attack) * np.where(x > dur, np.exp(-(x - dur) / (release / 3)), 1)
        sig = sum(a * np.sin(2 * np.pi * f * (h + 1) * x) / (h + 1) for h, a in enumerate(harm))
        out[i0:i1] += amp * env * sig

    def bell(f, t0, amp):
        i0, i1 = int(t0 * SR), min(n, int((t0 + 3) * SR))
        if i0 >= n:
            return
        x = tt[i0:i1] - t0
        sig = np.sin(2 * np.pi * f * x) + 0.4 * np.sin(2 * np.pi * f * 2.76 * x) * np.exp(-x * 3)
        out[i0:i1] += amp * np.exp(-x * 1.6) * np.minimum(1, x / 0.005) * sig

    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    # Am - F - C - G pad, 4 s per chord; sadder Dm - Am for the sacrifice, bright C - G - F - C ending
    prog = [[57, 60, 64], [53, 57, 60], [48, 55, 64], [55, 59, 62]] * 4 + [[50, 53, 57], [45, 52, 60], [53, 57, 60], [48, 55, 64]] * 2
    for k in range(15):
        t0 = k * 4.0
        chord = prog[k]
        if t0 >= 36 and t0 < 44:
            chord = [[50, 53, 57], [45, 52, 57]][int((t0 - 36) / 4)]
        if t0 >= 44:
            chord = [[48, 55, 64], [55, 59, 67], [53, 57, 65], [48, 52, 60], [48, 55, 64]][int((t0 - 44) / 4) % 5]
        for m in chord:
            note(hz(m), t0, 3.6, 0.05, attack=1.2, release=2.0)
        note(hz(chord[0] - 12), t0, 3.6, 0.06, attack=0.5, release=1.5, harm=(1, 0.2))
    # music box melody, sparse at first
    melody = [(3, 76), (4, 74), (5, 72), (7, 69), (13, 76), (13.5, 79), (14, 81),
              (18, 72), (19, 74), (20, 76), (22, 79), (23, 76), (24, 74), (26, 72),
              (29, 69), (31, 67), (33, 65), (35, 64),
              (38, 62), (40, 64), (42, 65), (43, 64),
              (45, 72), (46, 76), (47, 79), (48, 84),
              (55, 79), (55.5, 76), (56, 72), (57, 76), (58, 72)]
    for t0, m in melody:
        bell(hz(m), t0, 0.08)
    # star bloom: shimmering cascade
    rs = np.random.RandomState(3)
    for k in range(40):
        bell(hz(rs.choice([84, 86, 88, 91, 93, 96])), 48.7 + k * 0.06 + rs.uniform(0, 0.05), 0.03)
    # shooting-star whoosh + impact
    i0, i1 = int(8.4 * SR), int(10.9 * SR)
    noise = rs.randn(i1 - i0)
    x = (tt[i0:i1] - 8.4) / 2.5
    sweep = np.convolve(noise, np.ones(30) / 30, mode="same")
    out[i0:i1] += 0.12 * sweep * x ** 2
    i0, i1 = int(10.8 * SR), int(13 * SR)
    x = tt[i0:i1] - 10.8
    out[i0:i1] += 0.35 * np.sin(2 * np.pi * (60 - 20 * x) * x) * np.exp(-x * 3)
    out[i0:i1] += 0.08 * np.convolve(rs.randn(i1 - i0), np.ones(80) / 80, "same") * np.exp(-x * 4)
    # core transfer sparkle, gift arrival
    for k in range(8):
        bell(hz(88 + k), 39 + k * 0.25, 0.03)
    bell(hz(84), 53.3, 0.1)
    bell(hz(91), 53.45, 0.07)
    # eye-off "power down" and wake "power up"
    for t0, f0, f1 in ((42.2, 600, 120), (11.9, 200, 900), (53.7, 200, 900)):
        i0, i1 = int(t0 * SR), int((t0 + 0.6) * SR)
        x = tt[i0:i1] - t0
        f = np.linspace(f0, f1, i1 - i0)
        out[i0:i1] += 0.04 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 3)

    # simple reverb (feedback delays) + fades
    wet = out.copy()
    for dly, g in ((0.031, 0.5), (0.047, 0.45), (0.071, 0.4), (0.113, 0.3)):
        dn = int(dly * SR)
        buf = np.zeros(n)
        for rep in range(1, 6):
            s = dn * rep
            buf[s:] += out[:-s] * g ** rep
        wet += buf * 0.35
    wet *= np.minimum(1, tt / 1.0) * np.minimum(1, (DURATION - tt) / 1.5)
    wet /= np.max(np.abs(wet)) * 1.1
    stereo = np.stack([wet, np.roll(wet, int(0.012 * SR))], axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((stereo * 32767).astype(np.int16).tobytes())


# ----------------------------------------------------------------------------- main


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "spark_preview.mp4")
    frames = int(DURATION * FPS)
    wav = out + ".wav"
    synth_audio(wav)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
         "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)
    with Pool(os.cpu_count(), initializer=init_worker) as pool:
        for i, buf in enumerate(pool.imap(render_frame, range(frames), chunksize=4)):
            ff.stdin.write(buf)
            if i % 120 == 0:
                print("frame %d/%d" % (i, frames), flush=True)
    ff.stdin.close()
    ff.wait()
    os.remove(wav)
    print("wrote", out)


if __name__ == "__main__":
    main()
