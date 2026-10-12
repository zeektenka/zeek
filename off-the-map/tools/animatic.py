"""Render a complete video as a silent animatic, before the voiceover exists.

    python3 tools/animatic.py 01-zimbabwe
    python3 tools/animatic.py 10-printing --height 720

Word timings are ESTIMATED from the script at the narrator's measured pace
(2.3 words/sec), so pacing is approximately right and the whole visual flow can
be judged end to end. It is not the finished video: there is no narration, and
every shot will shift slightly once the real audio lands and `make.py` re-times
it against the actual speech.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))

from engine import Video                                             # noqa: E402
from engine import shots as sh                                       # noqa: E402
from dryrun import synthetic_timing                                  # noqa: E402

PLAN = {
    "01-zimbabwe": [("act1", "part1"), ("act2", "part2"), ("act3", "part3")],
    "10-printing": [("acts:1", "part1"), ("acts:2", "part2"), ("acts:3", "part3")],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", choices=sorted(PLAN))
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--gap", type=float, default=0.65, help="pause between acts")
    ap.add_argument("--check", action="store_true", help="assemble only, do not render")
    a = ap.parse_args()

    vdir = os.path.join(HERE, "..", "videos", a.video)
    sys.path.insert(0, vdir)
    out_dir = os.path.join(HERE, "..", "out", a.video)
    os.makedirs(out_dir, exist_ok=True)

    words, offset, shot_list = [], 0.0, []
    for mod_spec, part in PLAN[a.video]:
        mod_name, _, act_key = mod_spec.partition(":")
        mod = __import__(mod_name)
        lst = mod.SHOTS[int(act_key)] if act_key else mod.SHOTS
        text = open(os.path.join(vdir, "vo", f"{part}.txt")).read()
        T, end = synthetic_timing(text, offset)
        words.extend(T.words)
        shot_list.extend(lst)
        offset = end + a.gap

    from engine.audio import Timing
    timing = Timing(words)
    total = offset - a.gap + 1.0

    width = int(round(a.height * 16 / 9 / 2) * 2)
    v = Video(width, a.height, fps=a.fps, ss=1.0, grain=0.022)
    reel = sh.Reel(timing, 0.0, total)
    for cue, factory in shot_list:
        reel.add(cue, factory, lead=0.25)
    reel.build(v, end=total)

    out = os.path.join(out_dir, f"animatic_{a.height}p{a.fps}_silent.mp4")
    print(f"{a.video}: {len(v.scenes)} shots, {total / 60:.1f} min -> {out}")
    if a.check:
        v.frame(v.scenes[0].start + 0.5)          # prove a frame actually draws
        print("  check ok")
        return
    v.render(out, profile="preview", workers=a.workers, chunk=5.0)
    print("done", out)


if __name__ == "__main__":
    main()
