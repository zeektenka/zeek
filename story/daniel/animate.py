"""2.5D parallax animation for Daniel, Scene 01 ("The Message").

Splits daniel_v2.png into depth layers (city, room, Daniel, foreground),
fills the hidden areas behind each layer, then renders a slow push-in with
layer parallax, a head tilt, a blink, flickering phone light, city twinkle,
drifting haze, dust in the lamp light and film grain.

Usage: python3 animate.py [out_dir]
Needs: opencv-python-headless, numpy, pillow, rembg, ffmpeg on PATH.
"""
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "daniel_v2.png")
OUT = sys.argv[1] if len(sys.argv) > 1 else HERE
LAYER_DIR = os.path.join(OUT, "layers")

FPS = 30
SECONDS = 10
OUT_W, OUT_H = 1080, 1920
RNG = np.random.default_rng(7)

img_u8 = np.array(Image.open(SRC).convert("RGB"))
H, W = img_u8.shape[:2]
img = img_u8.astype(np.float32) / 255.0
# The prompts were laid out on a 1125x2000 preview; scale those to source px.
K = W / 1125.0


def poly_mask(points, feather=0):
    m = np.zeros((H, W), np.float32)
    pts = (np.array(points, np.float32) * K).astype(np.int32)
    cv2.fillPoly(m, [pts], 1.0)
    if feather:
        m = cv2.GaussianBlur(m, (0, 0), feather)
    return m


def inpaint(rgb, mask, scale=4, radius=6):
    """Fill mask areas cheaply: inpaint at low res, upsample, blend in."""
    small = cv2.resize((rgb * 255).astype(np.uint8), (W // scale, H // scale), interpolation=cv2.INTER_AREA)
    m_small = cv2.resize((mask > 0.02).astype(np.uint8) * 255, (W // scale, H // scale), interpolation=cv2.INTER_NEAREST)
    m_small = cv2.dilate(m_small, np.ones((3, 3), np.uint8))
    filled = cv2.inpaint(small, m_small, radius, cv2.INPAINT_TELEA)
    filled = cv2.resize(filled, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32) / 255.0
    filled = cv2.GaussianBlur(filled, (0, 0), 2)
    a = cv2.GaussianBlur((mask > 0.02).astype(np.float32), (0, 0), 3)[..., None]
    return rgb * (1 - a) + filled * a


# ---------------------------------------------------------------- masks
def daniel_mask():
    from rembg import new_session, remove

    pil = Image.fromarray(img_u8)
    body = np.array(remove(pil, session=new_session("u2net_human_seg"), only_mask=True), np.float32) / 255.0
    fine = np.array(remove(pil, session=new_session("isnet-general-use"), only_mask=True), np.float32) / 255.0
    # Use the finer model for hair detail around the head only.
    head = np.zeros_like(body)
    head[int(300 * K):int(860 * K), int(200 * K):int(720 * K)] = 1
    head = cv2.GaussianBlur(head, (0, 0), 20)
    return np.clip(np.maximum(body, fine * head), 0, 1)


FG = np.clip(
    poly_mask([(230, 1735), (300, 1690), (520, 1648), (830, 1622), (835, 1462), (1058, 1462),
               (1060, 1560), (1125, 1548), (1125, 2000), (230, 2000)])
    + poly_mask([(0, 1140), (90, 1110), (210, 1170), (295, 1390), (270, 1700), (240, 2000), (0, 2000)]),
    0, 1)
FG = cv2.GaussianBlur(FG, (0, 0), 6)

WINDOW = poly_mask([(0, 0), (368, 0), (368, 342), (422, 342), (422, 0), (912, 0), (912, 868),
                    (740, 862), (300, 760), (60, 690), (0, 690)])
WINDOW = cv2.GaussianBlur(WINDOW, (0, 0), 2)

cache = os.path.join(OUT, ".daniel_mask.npy")
if os.path.exists(cache):
    D_raw = np.load(cache)
else:
    D_raw = daniel_mask()
    np.save(cache, D_raw)

# Daniel continues under the table so the foreground can slide over him.
near = cv2.dilate((D_raw > 0.5).astype(np.uint8), np.ones((121, 121), np.uint8)).astype(np.float32)
D_alpha = np.maximum(D_raw * (1 - FG), FG * near)
D_alpha = cv2.GaussianBlur(D_alpha, (0, 0), 1.2)

CITY_A = np.clip(WINDOW * (1 - D_raw), 0, 1)

# ---------------------------------------------------------------- plates
print("building plates…")
behind_fg = inpaint(img, cv2.dilate(FG, np.ones((15, 15), np.uint8)))
room_plate = inpaint(behind_fg, cv2.dilate(D_raw, np.ones((41, 41), np.uint8)))
city_plate = inpaint(img, cv2.dilate(np.clip((1 - WINDOW) + D_raw, 0, 1), np.ones((41, 41), np.uint8)))
daniel_plate = behind_fg
fg_plate = img

ROOM_A = 1 - WINDOW  # room is opaque everywhere outside the window glass

os.makedirs(LAYER_DIR, exist_ok=True)


def save_rgba(name, rgb, a):
    rgba = np.dstack([rgb, a[..., None] if a.ndim == 2 else a])
    Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA").save(os.path.join(LAYER_DIR, name))


save_rgba("1_city.png", city_plate, np.ones((H, W), np.float32))
save_rgba("2_room.png", room_plate, ROOM_A)
save_rgba("3_daniel.png", daniel_plate, D_alpha)
save_rgba("4_foreground.png", fg_plate, FG)

# ---------------------------------------------------------------- effects data
lum = city_plate.mean(axis=2)
lights = ((lum > 0.62) & (WINDOW > 0.9) & (D_raw < 0.05)).astype(np.uint8)
n_lights, light_lbl = cv2.connectedComponents(lights)
light_phase = RNG.uniform(0, 2 * np.pi, n_lights).astype(np.float32)
light_speed = RNG.uniform(0.6, 2.2, n_lights).astype(np.float32)
light_amp = (RNG.random(n_lights) < 0.35).astype(np.float32) * RNG.uniform(0.25, 0.6, n_lights).astype(np.float32)
light_amp[0] = 0
light_glow = cv2.GaussianBlur(lights.astype(np.float32), (0, 0), 1.5)

beacon = np.zeros((H, W), np.float32)
cv2.circle(beacon, (int(800 * K), int(196 * K)), 3, 1.0, -1)
beacon = cv2.GaussianBlur(beacon, (0, 0), 4)

# Haze: two octaves of soft noise, wider than the frame so it can drift.
hz = cv2.resize(RNG.random((24, 30)).astype(np.float32), (W * 2, H), interpolation=cv2.INTER_CUBIC)
hz += 0.5 * cv2.resize(RNG.random((60, 80)).astype(np.float32), (W * 2, H), interpolation=cv2.INTER_CUBIC)
hz = cv2.GaussianBlur(hz, (0, 0), 25)
hz = (hz - hz.min()) / (hz.max() - hz.min())
haze_tint = np.array([0.35, 0.55, 0.62], np.float32)

# Phone light: a cool glow on the hands and the underside of the face.
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
phone = np.array([590 * K, 1010 * K])
g_phone = np.exp(-(((xx - phone[0]) / (230 * K)) ** 2 + ((yy - phone[1]) / (260 * K)) ** 2))
g_face = np.exp(-(((xx - 500 * K) / (150 * K)) ** 2 + ((yy - 720 * K) / (170 * K)) ** 2))
PHONE_GLOW = (np.clip(g_phone + 0.8 * g_face, 0, 1) * D_raw)[..., None] * np.array([0.55, 0.75, 1.0], np.float32)

# Lamp: very slight warm breathing in the lamp area of the room.
LAMP = np.exp(-(((xx - 1050 * K) / (220 * K)) ** 2 + ((yy - 680 * K) / (300 * K)) ** 2))[..., None]
LAMP = LAMP * np.array([1.0, 0.75, 0.4], np.float32)

# Dust motes drifting through the lamp light.
N_MOTES = 46
motes = {
    "x": RNG.uniform(560, 1150, N_MOTES) * K,
    "y": RNG.uniform(380, 1350, N_MOTES) * K,
    "vx": RNG.uniform(-6, 4, N_MOTES) * K,
    "vy": RNG.uniform(-9, -2, N_MOTES) * K,
    "r": RNG.uniform(1.2, 3.6, N_MOTES),
    "a": RNG.uniform(0.15, 0.5, N_MOTES),
    "ph": RNG.uniform(0, 2 * np.pi, N_MOTES),
}

VIGNETTE = 1 - 0.38 * np.clip(((xx / W - 0.48) ** 2 / 0.32 + (yy / H - 0.42) ** 2 / 0.42), 0, 1)[..., None]

# ---------------------------------------------------------------- eyes
# (x0, x1, lid_top, upper_lash, lower_lash, lid_bottom) in source px.
EYES = [(420, 476, 634, 645, 662, 668), (522, 584, 657, 667, 685, 691)]


def blink(rgb, c):
    """Close both eyes by amount c in [0, 1] by sliding the upper lid down."""
    if c <= 0.001:
        return rgb
    out = rgb.copy()
    for x0, x1, top, up, lo, bot in EYES:
        h, w = bot - top, x1 - x0
        lash = up + c * (lo - up - 1)
        ys = np.arange(top, bot, dtype=np.float32)
        # Above the lash line, stretch the lid skin down; below it, keep the eye.
        src_y = np.where(ys <= lash, top + (ys - top) * (up - top) / max(lash - top, 1e-3), ys)
        map_y = np.repeat(src_y[:, None], w, axis=1).astype(np.float32)
        map_x = np.repeat(np.arange(x0, x1, dtype=np.float32)[None, :], h, axis=0)
        patch = cv2.remap(rgb, map_x, map_y, cv2.INTER_LINEAR)
        # Lash line along the closing lid.
        line = np.exp(-((ys - lash) / 1.6) ** 2)[:, None, None] * 0.55 * c
        patch = patch * (1 - line)
        ex = (np.arange(w) - w / 2) / (w / 2)
        ey = (ys - (top + bot) / 2) / (h / 2)
        m = np.clip(1 - (ex[None, :] ** 2 + ey[:, None] ** 2), 0, 1) ** 0.6
        m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 2)[..., None]
        out[top:bot, x0:x1] = rgb[top:bot, x0:x1] * (1 - m) + patch * m
    return out


# ---------------------------------------------------------------- motion
def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def head_warp(rgb_a, angle_deg, dy, t):
    """Rotate/tilt the head about the neck, fading out over the shoulders."""
    pivot = np.array([515 * K, 880 * K], np.float32)
    w = np.clip((900 * K - yy) / (200 * K), 0, 1)
    w *= np.clip(1 - np.abs(xx - 480 * K) / (330 * K), 0, 1) * 1.6
    w = np.clip(w, 0, 1)
    th = np.deg2rad(angle_deg)
    px, py = xx - pivot[0], yy - pivot[1]
    rx = np.cos(-th) * px - np.sin(-th) * py + pivot[0]
    ry = np.sin(-th) * px + np.cos(-th) * py + pivot[1] - dy
    map_x = (xx + w * (rx - xx)).astype(np.float32)
    map_y = (yy + w * (ry - yy)).astype(np.float32)
    return cv2.remap(rgb_a, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


FOCUS = np.array([505 * K, 700 * K])  # push in toward his eyes
OVERSCAN = 1.05


def layer_matrix(depth, t):
    e = smooth(t / SECONDS)
    push = 0.11 * e
    s = OVERSCAN * (1 + push * (0.3 + 0.95 * depth))
    rel = depth - 0.55
    tx = (-1 + 2 * e) * -60 * rel
    ty = (-1 + 2 * e) * -16 * rel + 3 * np.sin(t * 0.7) * rel
    m = np.array([[s, 0, 0], [0, s, 0]], np.float32)
    m[:, 2] = FOCUS - s * FOCUS + np.array([tx, ty])
    return m


def place(rgba, depth, t):
    return cv2.warpAffine(rgba, layer_matrix(depth, t), (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def over(dst, rgba):
    a = rgba[..., 3:4]
    return dst * (1 - a) + rgba[..., :3] * a


def phone_level(t):
    """Phone brightness: idle flicker, a message arriving at 2.2s, a scroll at 6.4s."""
    idle = 0.06 * np.sin(t * 9.1) * np.sin(t * 3.3) + 0.04 * np.sin(t * 17.0)
    msg = 0.42 * np.exp(-((t - 2.2) / 0.25) ** 2) + 0.18 * np.exp(-np.clip(t - 2.2, 0, None) / 1.6) * (t > 2.2)
    scroll = 0.12 * np.exp(-((t - 6.4) / 0.4) ** 2) * (0.5 + 0.5 * np.sin(t * 40))
    return 0.12 + idle + msg + scroll


def blink_amount(t):
    v = 0.0
    for t0 in (3.1, 7.9, 8.25):
        d = (t - t0) / 0.09
        v = max(v, np.exp(-d * d))
    return min(1.0, v * 1.15)


def head_pose(t):
    # Reads the message at 2.2s, pulls back slightly, then leans in at ~4.5s.
    recoil = -0.9 * np.exp(-((t - 2.7) / 0.5) ** 2)
    lean = 1.4 * smooth((t - 4.2) / 2.2)
    sway = 0.25 * np.sin(t * 0.9)
    dy = 4.0 * smooth((t - 4.2) / 2.2) - 3.0 * np.exp(-((t - 2.7) / 0.5) ** 2)
    return recoil + lean + sway, dy


# ---------------------------------------------------------------- render
city_rgba = np.dstack([city_plate, np.ones((H, W), np.float32)])
room_rgba = np.dstack([room_plate, ROOM_A])
fg_rgba = np.dstack([fg_plate, FG])

frames_dir = os.path.join(OUT, ".frames")
os.makedirs(frames_dir, exist_ok=True)
n_frames = int(os.environ.get("FRAMES", FPS * SECONDS))
only = os.environ.get("ONLY")
print(f"rendering {n_frames} frames…")
for f in (map(int, only.split(",")) if only else range(n_frames)):
    t = f / FPS

    # City: twinkle, aircraft beacon, drifting haze.
    tw = light_amp * np.sin(t * light_speed * 2 * np.pi + light_phase)
    city = city_plate * (1 + tw[light_lbl][..., None] * light_glow[..., None])
    on = 1.0 if (t % 1.6) < 0.18 else 0.0
    city = city + beacon[..., None] * np.array([1.0, 0.15, 0.1]) * 0.9 * on
    off = int(t * 9 * K) % W
    haze = hz[:, off:off + W][..., None]
    city = city + (haze * 0.10 + 0.02) * haze_tint * WINDOW[..., None] * (1 - city)
    frame = place(np.dstack([city, np.ones((H, W), np.float32)]), 0.0, t)[..., :3]

    room = room_plate * (1 + LAMP * 0.025 * np.sin(t * 1.3))
    frame = over(frame, place(np.dstack([room, ROOM_A]), 0.3, t))

    # Daniel: blink and phone light on the flat plate, then head tilt, then place.
    dan = blink(daniel_plate, blink_amount(t))
    dan = dan + PHONE_GLOW * phone_level(t) * (1 - dan)
    ang, dy = head_pose(t)
    dan_rgba = head_warp(np.dstack([dan, D_alpha]), ang, dy, t)
    frame = over(frame, place(dan_rgba, 0.55, t))

    # Dust motes in the lamp light, between Daniel and the foreground.
    dust = np.zeros((H, W), np.float32)
    mx = motes["x"] + motes["vx"] * t + 6 * np.sin(t * 0.8 + motes["ph"])
    my = motes["y"] + motes["vy"] * t
    for i in range(N_MOTES):
        a = motes["a"][i] * (0.6 + 0.4 * np.sin(t * 1.7 + motes["ph"][i]))
        cv2.circle(dust, (int(mx[i]) % W, int(my[i]) % H), int(round(motes["r"][i])), float(a), -1, cv2.LINE_AA)
    dust = cv2.GaussianBlur(dust, (0, 0), 1.6)
    dust_rgba = np.dstack([np.ones((H, W, 3), np.float32) * np.array([1.0, 0.8, 0.5]), dust * 0.6])
    frame = over(frame, place(dust_rgba, 0.75, t))

    frame = over(frame, place(fg_rgba, 1.0, t))

    # Grade: vignette, grain.
    frame = frame * VIGNETTE
    grain = RNG.normal(0, 0.018, (H // 2, W // 2)).astype(np.float32)
    grain = cv2.resize(grain, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    frame = np.clip(frame + grain * (0.4 + 0.6 * (1 - frame)), 0, 1)

    out = cv2.resize(frame, (OUT_W, OUT_H), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(frames_dir, f"{f:04d}.png"), cv2.cvtColor((out * 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
    if f % 30 == 0:
        print(f"  {f}/{n_frames}")

if only:
    sys.exit(0)
mp4 = os.path.join(OUT, "daniel_scene01.mp4")
subprocess.run([
    "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(frames_dir, "%04d.png"),
    "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4,
], check=True)
print("wrote", mp4)
