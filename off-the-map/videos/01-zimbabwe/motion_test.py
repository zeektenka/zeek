"""Motion test: the five animated style frames back to back.

    python3 videos/01-zimbabwe/motion_test.py out.mp4 [--preview]

Preview = 960x540 at 30 fps, no motion blur. Full = 1920x1080 at 60 fps with
4-sample motion blur on the map zoom (the fast move).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from scenes import SCENES        # noqa: E402
from engine import Video         # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--preview", action="store_true")
a = ap.parse_args()

if a.preview:
    v = Video(960, 540, fps=30, ss=1.0, grain=0.03)
else:
    v = Video(1920, 1080, fps=60, ss=1.25)
for name, fn, dur in SCENES:
    v.add(fn, dur, mb=None if a.preview or name != "2_map" else 4, name=name)
v.render(a.out, profile="preview" if a.preview else "master")
print(a.out, f"{v.duration:.1f}s")
