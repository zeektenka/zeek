"""Canvas, camera and sprites.

World space is a fixed 1920x1080 reference frame. The canvas renders it at any
output size times a supersample factor (ss), so the same scene code makes a
480p preview or a 4K master. Pixels are premultiplied float32 RGBA.

Depth gives parallax: depth 1 is the main plane and follows the camera fully,
smaller depths move and zoom less (background), larger depths move more
(foreground), depth 0 is pinned to the screen (titles, overlays).
"""
import math

import cv2
import numpy as np

REF_W, REF_H = 1920, 1080
CENTER = np.array([REF_W / 2, REF_H / 2])


def rgba(c, a=1.0):
    """'#rrggbb' or (r,g,b) 0-255 -> float tuple 0..1 with alpha."""
    if isinstance(c, str):
        c = c.lstrip("#")
        c = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    if len(c) == 4:
        a = c[3] / 255 if c[3] > 1 else c[3]
        c = c[:3]
    return (c[0] / 255, c[1] / 255, c[2] / 255, a)


class Camera:
    def __init__(self, x=REF_W / 2, y=REF_H / 2, zoom=1.0, rot=0.0):
        self.x, self.y, self.zoom, self.rot = x, y, zoom, rot

    def set(self, x=None, y=None, zoom=None, rot=None):
        if x is not None: self.x = x
        if y is not None: self.y = y
        if zoom is not None: self.zoom = zoom
        if rot is not None: self.rot = rot
        return self


class Sprite:
    """A pre-rendered RGBA image with a known resolution (pixels per world unit).

    Built once, placed many times. Holds a downscale pyramid and blurred
    shadow versions so per-frame placement is just a warp.
    """

    def __init__(self, img, res=1.0):
        img = np.asarray(img)
        if img.dtype == np.uint8:
            img = img.astype(np.float32) / 255.0
            img[..., :3] *= img[..., 3:4]           # straight -> premultiplied
        self.img = np.ascontiguousarray(img, dtype=np.float32)
        self.res = float(res)
        self._levels = {}
        self._shadows = {}

    @property
    def size(self):
        h, w = self.img.shape[:2]
        return w / self.res, h / self.res

    def level(self, px_scale):
        """Pre-shrunk copy when drawn much smaller than built (avoids aliasing)."""
        if px_scale >= 0.7:
            return self.img, 1.0
        f = 0.5
        while f / 2 > px_scale * 1.15:
            f /= 2
        if f not in self._levels:
            h, w = self.img.shape[:2]
            self._levels[f] = cv2.resize(self.img, (max(1, int(w * f)), max(1, int(h * f))),
                                         interpolation=cv2.INTER_AREA)
        return self._levels[f], f

    def shadow(self, blur):
        """Black, blurred copy of the alpha, padded by 3x blur (world units)."""
        key = round(blur, 2)
        if key not in self._shadows:
            pad = int(math.ceil(blur * self.res * 3)) + 2
            a = np.pad(self.img[..., 3], pad)
            if blur > 0:
                a = cv2.GaussianBlur(a, (0, 0), blur * self.res)
            img = np.zeros(a.shape + (4,), np.float32)
            img[..., 3] = a
            self._shadows[key] = (Sprite(img, self.res), pad / self.res)
        return self._shadows[key]


class Canvas:
    def __init__(self, width=1920, height=1080, ss=1.0):
        self.out_w, self.out_h = width, height
        self.W, self.H = int(round(width * ss)), int(round(height * ss))
        self.k = self.W / REF_W                     # px per world unit
        self.buf = np.zeros((self.H, self.W, 4), np.float32)
        self.cam = Camera()
        self._stack = []
        self.t = 0.0

    # ------------------------------------------------------------ transforms
    def matrix(self, depth=1.0):
        """2x3 affine: world point -> canvas pixel, for a layer at this depth."""
        c = self.cam
        z = c.zoom ** depth
        r = math.radians(c.rot * depth)
        R = np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
        off = np.array([c.x, c.y]) * depth + CENTER * (1 - depth)
        A = self.k * z * R
        b = self.k * (CENTER - z * R @ off)
        return np.hstack([A, b[:, None]])

    def to_px(self, pts, depth=1.0):
        M = self.matrix(depth)
        pts = np.asarray(pts, np.float64).reshape(-1, 2)
        return pts @ M[:, :2].T + M[:, 2]

    def scale_at(self, depth=1.0):
        return self.k * self.cam.zoom ** depth

    # -------------------------------------------------------------- basics
    def clear(self, color="#000000"):
        r, g, b, a = rgba(color)
        self.buf[...] = (r * a, g * a, b * a, a)

    def push(self):
        """Start a group (rendered to its own layer, then blurred/faded as one)."""
        self._stack.append(self.buf)
        self.buf = np.zeros_like(self.buf)

    def pop(self, blur=0.0, alpha=1.0, blend="normal"):
        layer = self.buf
        self.buf = self._stack.pop()
        if blur > 0.05:
            layer = cv2.GaussianBlur(layer, (0, 0), blur * self.k)
        self._composite(layer, 0, 0, alpha, blend)

    def _composite(self, src, x0, y0, alpha=1.0, blend="normal"):
        h, w = src.shape[:2]
        dst = self.buf[y0:y0 + h, x0:x0 + w]
        if alpha < 1:
            src = src * alpha
        sa = src[..., 3:4]
        if blend == "normal":
            dst *= 1 - sa
            dst += src
        elif blend == "multiply":
            da = dst[..., 3:4]
            rgb = src[..., :3] * dst[..., :3] + src[..., :3] * (1 - da) + dst[..., :3] * (1 - sa)
            dst[..., 3:4] = sa + da * (1 - sa)
            dst[..., :3] = rgb
        elif blend == "screen":
            dst[..., :3] += src[..., :3] - src[..., :3] * dst[..., :3]
            dst[..., 3:4] += sa * (1 - dst[..., 3:4])
        elif blend == "add":
            dst[..., :3] += src[..., :3]
        else:
            raise ValueError(blend)

    # -------------------------------------------------------------- sprites
    def place(self, sprite, x, y, scale=1.0, rot=0.0, alpha=1.0, depth=1.0,
              anchor=(0.5, 0.5), shadow=None, blend="normal"):
        """Draw a sprite. (x, y) is where its anchor lands, in world units.

        shadow=(dx, dy, blur, opacity) in world units draws a soft drop shadow
        first; the offset stays fixed on screen so the light never rotates.
        """
        if alpha <= 0.002 or scale <= 1e-4:
            return
        if shadow:
            dx, dy, blur, op = shadow
            sh, pad = sprite.shadow(blur)
            sw, shh = sprite.size
            ax = (anchor[0] * sw + pad) / (sw + 2 * pad)
            ay = (anchor[1] * shh + pad) / (shh + 2 * pad)
            z = self.cam.zoom ** depth
            self._place(sh, x, y, scale, rot, alpha * op, depth, (ax, ay), "normal",
                        _screen_offset=(dx * z * scale, dy * z * scale))
        self._place(sprite, x, y, scale, rot, alpha, depth, anchor, blend)

    def _place(self, sprite, x, y, scale, rot, alpha, depth, anchor, blend,
               _screen_offset=(0, 0)):
        Mw = self.matrix(depth)
        px_scale = self.scale_at(depth) * scale / sprite.res
        img, f = sprite.level(px_scale)
        h, w = img.shape[:2]
        sw, sh = sprite.size
        r = math.radians(rot)
        cr, sr = math.cos(r), math.sin(r)
        s = scale / (sprite.res * f)                # sprite px -> world units
        # sprite px -> world
        L = np.array([[s * cr, -s * sr], [s * sr, s * cr]])
        t = np.array([x, y]) - L @ np.array([anchor[0] * w, anchor[1] * h])
        A = Mw[:, :2] @ L
        b = Mw[:, :2] @ t + Mw[:, 2] + np.array(_screen_offset) * self.k
        corners = np.array([[0, 0], [w, 0], [0, h], [w, h]]) @ A.T + b
        x0 = max(int(math.floor(corners[:, 0].min())) - 1, 0)
        y0 = max(int(math.floor(corners[:, 1].min())) - 1, 0)
        x1 = min(int(math.ceil(corners[:, 0].max())) + 1, self.W)
        y1 = min(int(math.ceil(corners[:, 1].max())) + 1, self.H)
        if x1 <= x0 or y1 <= y0:
            return
        M = np.hstack([A, (b - [x0, y0])[:, None]]).astype(np.float64)
        out = cv2.warpAffine(img, M, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        if out.ndim == 2:
            out = out[..., None]
        self._composite(out, x0, y0, alpha, blend)

    # -------------------------------------------------------------- vectors
    def mask(self, polys, depth=1.0, feather=0.0):
        """Full-canvas float mask (0..1) of filled world-space polygons."""
        m = np.zeros((self.H, self.W), np.uint8)
        M = self.matrix(depth)
        pts = []
        for p in polys:
            q = np.asarray(p, np.float64) @ M[:, :2].T + M[:, 2]
            if (q[:, 0].max() < 0 or q[:, 1].max() < 0 or
                    q[:, 0].min() > self.W or q[:, 1].min() > self.H):
                continue
            pts.append(np.round(q * 16).astype(np.int32))
        if pts:
            cv2.fillPoly(m, pts, 255, lineType=cv2.LINE_AA, shift=4)
        m = m.astype(np.float32) / 255
        if feather > 0:
            m = cv2.GaussianBlur(m, (0, 0), feather * self.k)
        return m

    def fill_mask(self, m, color, alpha=1.0, texture=None, offset=(0, 0)):
        """Composite a colour (optionally times a texture HxWx3) through a mask."""
        if offset != (0, 0):
            M = np.float32([[1, 0, offset[0] * self.k], [0, 1, offset[1] * self.k]])
            m = cv2.warpAffine(m, M, (self.W, self.H))
        r, g, b, a = rgba(color)
        a *= alpha
        src = np.empty((self.H, self.W, 4), np.float32)
        col = np.array([r, g, b], np.float32)
        if texture is not None:
            src[..., :3] = texture * col
        else:
            src[..., :3] = col
        src[..., 3] = m * a
        src[..., :3] *= src[..., 3:4]
        self._composite(src, 0, 0)

    def stroke(self, pts, width, color, depth=1.0, alpha=1.0, progress=1.0,
               closed=False):
        """Anti-aliased polyline; progress 0..1 draws it on by arc length."""
        pts = np.asarray(pts, np.float64)
        if progress < 1:
            pts = trim_path(pts, progress)
            closed = False
        if len(pts) < 2 or alpha <= 0:
            return
        q = np.round(self.to_px(pts, depth) * 16).astype(np.int32)
        th = max(1, int(round(width * self.scale_at(depth))))
        m = np.zeros((self.H, self.W), np.uint8)
        cv2.polylines(m, [q], closed, 255, th, cv2.LINE_AA, shift=4)
        self.fill_mask(m.astype(np.float32) / 255, color, alpha)

    def texture(self, tile, depth=1.0, tile_res=1.0):
        """World-anchored tiled texture (HxWx3) so grain moves with the camera."""
        M = self.matrix(depth)
        F = np.hstack([M[:, :2] / tile_res, M[:, 2:3]])
        return cv2.warpAffine(tile, F, (self.W, self.H), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_WRAP)

    # -------------------------------------------------------------- output
    def output(self):
        """Downscale to output size; returns uint8 RGB."""
        img = self.buf[..., :3]
        if (self.W, self.H) != (self.out_w, self.out_h):
            img = cv2.resize(img, (self.out_w, self.out_h), interpolation=cv2.INTER_AREA)
        return np.clip(img * 255 + 0.5, 0, 255).astype(np.uint8)


def trim_path(pts, u):
    """First fraction u of a polyline, by length."""
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    total = seg.sum()
    if total == 0:
        return pts[:1]
    target = total * max(0.0, min(1.0, u))
    cum = np.concatenate([[0], np.cumsum(seg)])
    i = int(np.searchsorted(cum, target, side="right")) - 1
    i = min(i, len(seg) - 1)
    f = (target - cum[i]) / seg[i] if seg[i] > 0 else 0
    return np.vstack([pts[:i + 1], pts[i] + (pts[i + 1] - pts[i]) * f])
