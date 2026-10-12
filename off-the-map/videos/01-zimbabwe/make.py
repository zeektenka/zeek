"""Build Video 1 from whatever voiceover parts exist.

    python3 videos/01-zimbabwe/make.py sheet     # contact sheet of every shot
    python3 videos/01-zimbabwe/make.py preview   # fast 540p check
    python3 videos/01-zimbabwe/make.py master    # 1080p60 + mixed audio

Timings come from the audio itself (offline forced alignment), so regenerating
the voiceover re-times the animation with no code changes.
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", ".."))

from engine import Video, audio                                       # noqa: E402
import act1, act2, act3                                               # noqa: E402

ACTS = {1: act1, 2: act2, 3: act3}

OUT = os.path.join(HERE, "..", "..", "out", "01-zimbabwe")
AUDIO = os.path.join(HERE, "audio")
VO = os.path.join(HERE, "vo")


def available_parts():
    parts = []
    for i in (1, 2, 3):
        a = os.path.join(AUDIO, f"part{i}.mp3")
        if os.path.exists(a):
            parts.append((i, a, os.path.join(VO, f"part{i}.txt")))
    return parts


def load():
    """Join the parts that exist and align them to the script."""
    parts = available_parts()
    if not parts:
        sys.exit("No voiceover in videos/01-zimbabwe/audio/ — generate it first.")
    os.makedirs(OUT, exist_ok=True)
    joined = os.path.join(OUT, "voice.wav")
    offsets = audio.join_parts([p[1] for p in parts], joined, gap=0.65)
    words = []
    for (i, a, txt), off in zip(parts, offsets):
        T = audio.align(a, open(txt).read())
        for w in T.words:
            w.start += off
            w.end += off
            words.append(w)
    return audio.Timing(words), joined, audio.duration(joined), [p[0] for p in parts]


def build(width, height, fps, ss, grain=0.028):
    """Assemble whichever acts have voiceover. Shots are cued to phrases, so an
    act animates itself the moment its audio part exists."""
    timing, voice, total, got = load()
    v = Video(width, height, fps=fps, ss=ss, grain=grain)
    from engine import shots as sh
    reel = sh.Reel(timing, 0.0, total)
    missing = []
    for part in got:
        for cue, factory in ACTS[part].SHOTS:
            try:
                reel.add(cue, factory, lead=0.25)
            except KeyError:
                missing.append(cue)
    if missing:
        print(f"WARNING: {len(missing)} cue(s) not found in the narration:")
        for m in missing:
            print("   ", m)
    reel.build(v, end=min(total, timing.words[-1].end + 1.2))
    return v, timing, voice, total, got


def music_bed(path, length):
    """A quiet, slow drone generated here — a placeholder bed, trivially
    swapped for a licensed track by replacing audio/music.wav."""
    import numpy as np
    sr = 48000
    n = int(length * sr)
    t = np.arange(n) / sr
    sig = np.zeros(n)
    for f, a in [(55, 0.5), (82.5, 0.26), (110, 0.18), (164.8, 0.07), (220, 0.04)]:
        sig += a * np.sin(2 * np.pi * f * t + 3 * np.sin(2 * np.pi * 0.03 * t))
    swell = 0.55 + 0.45 * np.sin(2 * np.pi * t / 46.0 - 1.2)
    sig *= swell
    rng = np.random.default_rng(3)
    air = rng.normal(0, 1, n)
    k = 900
    air = np.convolve(air, np.ones(k) / k, mode="same")
    sig = sig * 0.8 + air * 0.25
    sig /= max(abs(sig).max(), 1e-9)
    sig = np.tanh(sig * 1.4) * 0.5
    raw = os.path.join(OUT, "_bed.f32")
    sig.astype("<f4").tofile(raw)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1",
                    "-i", raw, "-ac", "2", path], check=True)
    os.remove(raw)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["sheet", "preview", "master"])
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    if a.mode == "sheet":
        v, timing, voice, total, got = build(1920, 1080, 30, 1.0)
        times = [s.start + min(1.4, s.dur * 0.55) for s in v.scenes]
        p = v.contact_sheet(times, os.path.join(OUT, "shots.jpg"), cols=4, thumb_w=620)
        print(f"parts {got} · {total:.1f}s · {len(v.scenes)} shots -> {p}")
        return

    if a.mode == "preview":
        v, timing, voice, total, got = build(960, 540, 30, 1.0, grain=0.03)
        out = os.path.join(OUT, "preview.mp4")
        v.render(out, profile="preview", workers=a.workers, chunk=3.0, audio=voice)
        print(out)
        return

    v, timing, voice, total, got = build(1920, 1080, 60, 1.25, grain=0.020)
    bed = music_bed(os.path.join(OUT, "music.wav"), v.duration + 1)
    mixed = audio.mix(voice, os.path.join(OUT, "mix.wav"), music=bed, music_db=-26,
                      swells=[(0.0, 6.0, 4.0)], target_lufs=-14.0, length=v.duration)
    print("mix loudness:", round(audio.loudness(mixed), 2), "LUFS")
    out = os.path.join(OUT, "zimbabwe_act1_1080p60.mp4")
    v.render(out, profile="master", workers=a.workers, chunk=4.0, audio=mixed)
    print(out)


if __name__ == "__main__":
    main()
