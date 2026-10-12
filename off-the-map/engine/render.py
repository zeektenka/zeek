"""Timeline of scenes, stills, contact sheets and chunked parallel rendering."""
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp

import cv2
import numpy as np

from .canvas import Canvas
from . import post

PROFILES = {
    # name: ffmpeg video args
    "preview": ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p"],
    # CRF 14 plus film grain pushes ~200 Mbps and encodes slower than it renders.
    # YouTube re-encodes anyway, so ~25 Mbps is the sensible ceiling for a master.
    "master": ["-c:v", "libx264", "-preset", "medium", "-crf", "18",
               "-profile:v", "high", "-pix_fmt", "yuv420p",
               "-maxrate", "48M", "-bufsize", "96M"],
    "master10": ["-c:v", "libx265", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p10le",
                 "-tag:v", "hvc1"],
}


class Scene:
    def __init__(self, fn, start, dur, mb=None, name=None):
        self.fn, self.start, self.dur, self.mb = fn, start, dur, mb
        self.name = name or getattr(fn, "__name__", "scene")


class Video:
    """Scenes are functions fn(canvas, t) where t is seconds since the scene began.

    motion_blur = sub-frame samples per frame (1 = off). Scenes with fast moves
    can ask for more with mb=; shutter is the fraction of a frame the shutter
    stays open (0.5 = 180 degrees).
    """

    def __init__(self, width=1920, height=1080, fps=60, ss=1.5, grain=0.028,
                 motion_blur=1, shutter=0.5):
        self.width, self.height, self.fps, self.ss = width, height, fps, ss
        self.grain, self.motion_blur, self.shutter = grain, motion_blur, shutter
        self.scenes = []

    def add(self, fn, dur, start=None, mb=None, name=None):
        if start is None:
            start = self.duration
        self.scenes.append(Scene(fn, start, dur, mb, name))
        return self

    @property
    def duration(self):
        return max((s.start + s.dur for s in self.scenes), default=0.0)

    def scene_at(self, t):
        hit = None
        for s in self.scenes:                       # later scenes win overlaps
            if s.start <= t < s.start + s.dur:
                hit = s
        return hit or (self.scenes[-1] if self.scenes else None)

    def _draw(self, s, t):
        cv = Canvas(self.width, self.height, self.ss)
        cv.t = t
        s.fn(cv, t - s.start)
        return cv.output()

    def frame(self, t, motion_blur=None):
        s = self.scene_at(t)
        n = motion_blur or s.mb or self.motion_blur
        if n <= 1:
            img = self._draw(s, t)
        else:
            span = self.shutter / self.fps
            acc = np.zeros((self.height, self.width, 3), np.float32)
            for i in range(n):
                acc += self._draw(s, t - span / 2 + span * (i + 0.5) / n)
            img = np.clip(acc / n + 0.5, 0, 255).astype(np.uint8)
        if self.grain:
            img = post.grain(img, t, self.grain, size=max(1.0, self.height / 1080))
        return img

    def still(self, t, path, motion_blur=None):
        img = self.frame(t, motion_blur)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        cv2.imwrite(path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        return path

    def contact_sheet(self, times, path, cols=4, thumb_w=640):
        """Grid of stills at key moments, labelled with their time (stage 8)."""
        thumbs = []
        for t in times:
            img = self.frame(t)
            th = cv2.resize(img, (thumb_w, int(thumb_w * self.height / self.width)),
                            interpolation=cv2.INTER_AREA)
            cv2.putText(th, f"{t:.2f}s", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (255, 255, 0), 2, cv2.LINE_AA)
            thumbs.append(th)
        while len(thumbs) % cols:
            thumbs.append(np.zeros_like(thumbs[0]))
        rows = [np.hstack(thumbs[i:i + cols]) for i in range(0, len(thumbs), cols)]
        cv2.imwrite(path, cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR))
        return path

    # ------------------------------------------------------------------ video
    def render(self, path, t0=0.0, t1=None, profile="preview", workers=None,
               chunk=4.0, audio=None):
        """Render [t0, t1) in chunks of `chunk` seconds across processes, then
        join them losslessly and mux audio (if given)."""
        t1 = self.duration if t1 is None else t1
        n0, n1 = int(round(t0 * self.fps)), int(round(t1 * self.fps))
        step = max(1, int(chunk * self.fps))
        jobs = [(a, min(a + step, n1)) for a in range(n0, n1, step)]
        tmp = tempfile.mkdtemp(prefix="otm_render_")
        workers = workers or os.cpu_count() or 2
        global _VIDEO
        _VIDEO = self
        try:
            ctx = mp.get_context("fork")
            with ProcessPoolExecutor(workers, mp_context=ctx) as ex:
                parts = list(ex.map(_render_chunk,
                                    [(a, b, os.path.join(tmp, f"{i:05d}.mp4"), profile)
                                     for i, (a, b) in enumerate(jobs)]))
            lst = os.path.join(tmp, "list.txt")
            with open(lst, "w") as f:
                f.writelines(f"file '{p}'\n" for p in parts)
            cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst]
            if audio:
                cmd += ["-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", audio,
                        "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "320k"]
            cmd += ["-c:v", "copy", "-movflags", "+faststart", path]
            subprocess.run(cmd, check=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return path


_VIDEO = None


def _render_chunk(args):
    a, b, out, profile = args
    v = _VIDEO
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{v.width}x{v.height}", "-r", str(v.fps), "-i", "-",
           *PROFILES[profile], "-r", str(v.fps), out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for n in range(a, b):
        p.stdin.write(v.frame(n / v.fps).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg failed on frames {a}-{b}")
    return out
