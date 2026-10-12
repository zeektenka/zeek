"""Generate the thumbnail for each video.

    python3 tools/thumbnails.py [--ss 2]

1280x720, three words maximum, readable at phone size.
"""
import argparse
import os
import sys

import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from engine import Canvas, post                                       # noqa: E402
from engine import style as S, paper as P                             # noqa: E402

OUT = os.path.join(HERE, "..", "out")


def zimbabwe(cv):
    """The 100-trillion note beside one loaf. Text: NOT ENOUGH."""
    S.desk(cv, light=(0.58, 0.40))
    note = S.cached(cv, "t_note", lambda r: S.banknote(r, value="100", word="TRILLION", seed=1), 1.2)
    for i, (dx, dy, rot) in enumerate([(-54, 64, -15), (-26, 32, -10), (0, 0, -6)]):
        cv.place(note, 600 + dx, 450 + dy, 1.5, rot, shadow=S.SHADOW_HIGH if i == 2 else S.SHADOW)
    bread = S.cached(cv, "t_loaf", lambda r: S.loaf(r, seed=2), 1.3)
    cv.place(bread, 1490, 440, 1.35, 5, shadow=S.SHADOW_HIGH)
    cv.stroke(P.hand_ellipse(1490, 430, 340, 240, seed=9), 13, S.ACCENT)
    w1 = S.cached(cv, "t_not", lambda r: S.title_strip("NOT", r, 200, seed=17))
    w2 = S.cached(cv, "t_enough", lambda r: S.title_strip(
        "ENOUGH", r, 225, paper=S.ACCENT, ink="#fff8ee", seed=18))
    cv.place(w1, 395, 860, 1, -4, shadow=S.SHADOW_HIGH)
    cv.place(w2, 1105, 850, 1, 2, shadow=S.SHADOW_HIGH)
    S.finish(cv, 0.42)


def printing(cv):
    """One note intact, one turning to ash. Text: SAME PRINTER?"""
    S.desk(cv, light=(0.5, 0.40))
    good = S.cached(cv, "p_good", lambda r: S.banknote(
        r, value="1", word="", seed=4, base="#b9c9a8", ink="#2f4a33"), 1.2)
    cv.place(good, 470, 380, 1.08, -7, shadow=S.SHADOW_HIGH)
    dead = S.cached(cv, "p_dead", lambda r: P.disintegrate(
        S.banknote(r, value="100", word="TRILLION", seed=1), 0.58, seed=5), 1.2)
    cv.place(dead, 1360, 380, 1.08, 6, shadow=S.SHADOW_HIGH, anchor=(0.42, 0.5))
    for x, txt, seed, rot in [(470, "UNITED STATES", 30, -3), (1330, "ZIMBABWE", 31, 3)]:
        lab = S.cached(cv, ("p_l", txt), lambda r, txt=txt, seed=seed: P.label(txt, r, 40, seed=seed))
        cv.place(lab, x, 620, 1, rot, shadow=S.SHADOW_LOW)
    w1 = S.cached(cv, "p_same", lambda r: S.title_strip("SAME", r, 200, seed=19))
    w2 = S.cached(cv, "p_printer", lambda r: S.title_strip(
        "PRINTER?", r, 215, paper=S.ACCENT, ink="#fff8ee", seed=20))
    cv.place(w1, 420, 855, 1, -4, shadow=S.SHADOW_HIGH)
    cv.place(w2, 1125, 845, 1, 2, shadow=S.SHADOW_HIGH)
    S.finish(cv, 0.42)


JOBS = [("01-zimbabwe", zimbabwe), ("10-printing", printing)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ss", type=float, default=2.0)
    a = ap.parse_args()
    for name, fn in JOBS:
        d = os.path.join(OUT, name)
        os.makedirs(d, exist_ok=True)
        cv = Canvas(1280, 720, ss=a.ss)
        fn(cv)
        img = post.grain(cv.output(), 0, 0.02)
        p = os.path.join(d, "thumbnail.png")
        cv2.imwrite(p, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        print("wrote", p)


if __name__ == "__main__":
    main()
