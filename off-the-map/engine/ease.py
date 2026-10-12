"""Easing curves and keyframe tracks.

Every animated value in a scene goes through one of these, so motion is never
linear by accident. Times are in seconds.
"""
import math


def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def lerp(a, b, u):
    if isinstance(a, (tuple, list)):
        return type(a)(lerp(x, y, u) for x, y in zip(a, b))
    return a + (b - a) * u


# --- curves: map 0..1 -> 0..1 (out_back overshoots past 1) -----------------

def linear(u):
    return u


def in_out_sine(u):
    return 0.5 - 0.5 * math.cos(math.pi * u)


def in_out_cubic(u):
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def in_out_quint(u):
    return 16 * u ** 5 if u < 0.5 else 1 - (-2 * u + 2) ** 5 / 2


def out_cubic(u):
    return 1 - (1 - u) ** 3


def out_expo(u):
    return 1.0 if u >= 1 else 1 - 2 ** (-10 * u)


def in_cubic(u):
    return u ** 3


def out_back(u, s=1.70158):
    """Pop-in with slight overshoot."""
    u -= 1
    return u * u * ((s + 1) * u + s) + 1


def soft_back(u):
    """Gentler overshoot (about 4%) for large elements."""
    return out_back(u, 0.9)


EASES = {
    "linear": linear, "sine": in_out_sine, "cubic": in_out_cubic,
    "quint": in_out_quint, "out": out_cubic, "expo": out_expo,
    "in": in_cubic, "back": out_back, "soft_back": soft_back,
}


def _ease(e):
    return EASES[e] if isinstance(e, str) else e


def ramp(t, t0, dur, ease="cubic"):
    """0 before t0, 1 after t0+dur, eased in between."""
    if dur <= 0:
        return 1.0 if t >= t0 else 0.0
    u = (t - t0) / dur
    if u <= 0:
        return 0.0
    if u >= 1:
        return 1.0
    return _ease(ease)(u)


def mix_color(a, b, u):
    """Blend two '#rrggbb' colours."""
    ca = [int(a.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    u = clamp(u)
    return "#" + "".join(f"{round(x + (y - x) * u):02x}" for x, y in zip(ca, cb))


def window(t, t_in, t_out, fade=0.35, ease="cubic"):
    """Fade in at t_in, fade out ending at t_out."""
    return min(ramp(t, t_in, fade, ease), 1 - ramp(t, t_out - fade, fade, ease))


def stagger(t, t0, i, dur=0.45, gap_frames=3, fps=60, ease="back"):
    """Staggered reveal: item i starts gap_frames after item i-1."""
    return ramp(t, t0 + i * gap_frames / fps, dur, ease)


class Track:
    """Keyframed value. keys: [(time, value), ...] or [(time, value, ease), ...].

    The ease on a key shapes the segment that ends at that key.
    """

    def __init__(self, *keys, ease="cubic"):
        self.keys = sorted(
            [(k[0], k[1], k[2] if len(k) > 2 else ease) for k in keys],
            key=lambda k: k[0])

    def __call__(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1]
        for (t0, v0, _), (t1, v1, e) in zip(ks, ks[1:]):
            if t <= t1:
                return lerp(v0, v1, _ease(e)((t - t0) / (t1 - t0)))
        return ks[-1][1]


def drift(t, amp=6.0, period=9.0, phase=0.0):
    """Slow organic wobble so nothing ever sits perfectly still."""
    w = 2 * math.pi / period
    return amp * (0.6 * math.sin(w * t + phase) + 0.4 * math.sin(1.7 * w * t + 2.1 + phase))
