"""Render every shot of every act without needing the voiceover.

    python3 tools/dryrun.py [--ss 1.0]

Builds a synthetic Timing from the script text at the narrator's measured pace
(2.3 words/sec) and renders a contact sheet per act. This proves the shot code
runs and the layouts hold, so nothing blows up later when the real audio lands.
It is NOT a substitute for checking against the real narration.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from engine import Video                                             # noqa: E402
from engine.audio import Timing, Word                                # noqa: E402
from engine import shots as sh                                       # noqa: E402

WPS = 2.3          # measured from the generated part 1: 358 words in 166.2 s

JOBS = [
    ("01-zimbabwe", "act1", "part1"),
    ("01-zimbabwe", "act2", "part2"),
    ("01-zimbabwe", "act3", "part3"),
    ("10-printing", "acts:1", "part1"),
    ("10-printing", "acts:2", "part2"),
    ("10-printing", "acts:3", "part3"),
]


def synthetic_timing(text, start=0.0):
    """Even word timing at the narrator's pace, with a beat at sentence ends."""
    words, t = [], start
    for tok in text.split():
        dur = (len(tok) + 1) / (WPS * 6.0)
        words.append(Word(tok, t, t + dur))
        t += dur
        if tok.endswith((".", "!", "?")):
            t += 0.42
        elif tok.endswith(","):
            t += 0.12
    return Timing(words), t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ss", type=float, default=1.0)
    a = ap.parse_args()
    out = os.path.join(HERE, "..", "out", "dryrun")
    os.makedirs(out, exist_ok=True)
    failures = 0
    for video, mod_spec, part in JOBS:
        vdir = os.path.join(HERE, "..", "videos", video)
        sys.path.insert(0, vdir)
        mod_name, _, act_key = mod_spec.partition(":")
        mod = __import__(mod_name)
        shot_list = mod.SHOTS[int(act_key)] if act_key else mod.SHOTS
        text = open(os.path.join(vdir, "vo", f"{part}.txt")).read()
        timing, total = synthetic_timing(text)
        v = Video(1920, 1080, fps=30, ss=a.ss, grain=0.0)
        reel = sh.Reel(timing, 0.0, total)
        for cue, factory in shot_list:
            reel.add(cue, factory, lead=0.25)
        reel.build(v, end=total)
        times = [s.start + min(1.5, s.dur * 0.6) for s in v.scenes]
        name = f"{video}_{mod_spec.replace(':', '')}"
        try:
            p = v.contact_sheet(times, os.path.join(out, f"{name}.jpg"), cols=4, thumb_w=560)
            print(f"OK   {name}: {len(v.scenes)} shots, {total:.0f}s -> {os.path.basename(p)}")
        except Exception as e:                       # noqa: BLE001
            failures += 1
            print(f"FAIL {name}: {type(e).__name__}: {e}")
        sys.path.remove(vdir)
        for m in list(sys.modules):
            if m in ("act1", "act2", "act3", "acts"):
                del sys.modules[m]
    print("all acts render" if not failures else f"{failures} act(s) failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
