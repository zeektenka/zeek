"""Render the six style frames (and a contact sheet).

    python3 videos/01-zimbabwe/style_frames.py [out_dir] [--ss 2]
"""
import argparse
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from scenes import SCENES, SETTLE, thumbnail          # noqa: E402
from engine import Video, Canvas, post               # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("out", nargs="?", default=os.path.join(os.path.dirname(__file__), "..", "..", "out", "style_frames"))
ap.add_argument("--ss", type=float, default=2.0)
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

paths = []
for name, fn, dur in SCENES:
    v = Video(1920, 1080, ss=a.ss).add(fn, dur)
    paths.append(v.still(SETTLE[name], os.path.join(a.out, f"{name}.png")))
    print("wrote", paths[-1])

cv = Canvas(1280, 720, ss=a.ss)
thumbnail(cv)
img = post.grain(cv.output(), 0, 0.02)
p = os.path.join(a.out, "6_thumbnail.png")
cv2.imwrite(p, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
paths.append(p)
print("wrote", p)

thumbs = []
for p in paths:
    im = cv2.imread(p)
    thumbs.append(cv2.resize(im, (960, 540), interpolation=cv2.INTER_AREA))
sheet = np.vstack([np.hstack(thumbs[i:i + 2]) for i in range(0, 6, 2)])
cv2.imwrite(os.path.join(a.out, "contact_sheet.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
