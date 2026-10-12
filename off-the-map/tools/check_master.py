"""Sanity-check a finished master before anyone watches it.

    python3 tools/check_master.py out/01-zimbabwe/zimbabwe_act1_1080p60.mp4

Checks the things that are embarrassing to discover after upload: video and
audio durations agreeing, a real audio stream, sane bitrate, no stretch of
black or frozen frames, and loudness near -14 LUFS. Also writes a contact
sheet sampled across the whole run.
"""
import argparse
import json
import os
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                        "-of", "json", path], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--samples", type=int, default=12)
    a = ap.parse_args()

    info = probe(a.path)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    auds = [s for s in info["streams"] if s["codec_type"] == "audio"]
    dur = float(info["format"]["duration"])
    size_mb = int(info["format"]["size"]) / 1e6
    fps = eval(v["r_frame_rate"])                                     # noqa: S307
    problems = []

    print(f"{os.path.basename(a.path)}")
    print(f"  {v['width']}x{v['height']} @ {fps:.3g} fps · {dur / 60:.2f} min · "
          f"{size_mb:.0f} MB · {size_mb * 8 / dur:.1f} Mbps")
    if not auds:
        problems.append("NO AUDIO STREAM")
    else:
        ad = float(auds[0].get("duration", dur))
        print(f"  audio: {auds[0]['codec_name']} {auds[0]['sample_rate']}Hz "
              f"{auds[0]['channels']}ch · {ad:.2f}s")
        if abs(ad - dur) > 0.5:
            problems.append(f"audio/video length differ by {abs(ad - dur):.2f}s")
        r = subprocess.run(["ffmpeg", "-i", a.path, "-af", "ebur128", "-f", "null", "-"],
                           capture_output=True, text=True)
        import re
        m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
        if m:
            lufs = float(m[-1])
            print(f"  loudness: {lufs:.2f} LUFS")
            if abs(lufs + 14) > 1.5:
                problems.append(f"loudness {lufs:.1f} LUFS is far from -14")

    cap = cv2.VideoCapture(a.path)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames, prev, frozen, dark = [], None, 0, 0
    for i in range(a.samples):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(n * (i + 0.5) / a.samples))
        ok, img = cap.read()
        if not ok:
            problems.append(f"could not read frame {i}")
            continue
        frames.append(cv2.resize(img, (480, 270), interpolation=cv2.INTER_AREA))
        if img.mean() < 8:
            dark += 1
        if prev is not None and np.abs(img.astype(int) - prev).mean() < 0.4:
            frozen += 1
        prev = img
    cap.release()
    if dark:
        problems.append(f"{dark}/{a.samples} sampled frames are nearly black")
    if frozen:
        problems.append(f"{frozen} consecutive sampled frames look identical")

    if frames:
        cols = 4
        while len(frames) % cols:
            frames.append(np.zeros_like(frames[0]))
        sheet = np.vstack([np.hstack(frames[i:i + cols]) for i in range(0, len(frames), cols)])
        out = os.path.splitext(a.path)[0] + "_check.jpg"
        cv2.imwrite(out, sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(f"  contact sheet: {out}")

    print("  OK" if not problems else "  PROBLEMS:\n   - " + "\n   - ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
