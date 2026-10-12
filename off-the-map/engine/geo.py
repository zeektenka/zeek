"""World map from Natural Earth (run setup.sh first), drawn as paper cutouts.

Countries are kept as vectors and projected every frame, so the camera can
zoom from a continent to a city with sharp edges at any size.
"""
import json
import math
import os

import cv2
import numpy as np

from .canvas import rgba

GEOJSON = os.path.join(os.path.dirname(__file__), "..", "assets", "geo",
                       "ne_50m_admin_0_countries.geojson")


def merc_y(lat):
    lat = np.clip(lat, -85, 85)
    return np.degrees(np.log(np.tan(np.pi / 4 + np.radians(lat) / 2)))


class World:
    """ppd = world units per degree of longitude at the map's natural size."""

    def __init__(self, path=GEOJSON, lon0=0.0, lat0=0.0, ppd=5.33):
        self.lon0, self.lat0, self.ppd = lon0, lat0, ppd
        with open(path) as f:
            data = json.load(f)
        self.rings, self.names = {}, {}
        for ft in data["features"]:
            pr = ft["properties"]
            code = pr.get("ADM0_A3") or pr.get("ISO_A3")
            self.names[code] = pr.get("NAME", code)
            g = ft["geometry"]
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            rings = []
            for poly in polys:
                for ring in poly:                   # outer ring and holes
                    rings.append(self.project(np.array(ring, np.float64)))
            self.rings[code] = rings
        self._bbox = {c: self._calc_bbox(r) for c, r in self.rings.items()}

    def project(self, lonlat):
        lonlat = np.asarray(lonlat, np.float64).reshape(-1, 2)
        x = 960 + (lonlat[:, 0] - self.lon0) * self.ppd
        y = 540 - (merc_y(lonlat[:, 1]) - merc_y(self.lat0)) * self.ppd
        return np.stack([x, y], 1)

    def point(self, lon, lat):
        return tuple(self.project([[lon, lat]])[0])

    @staticmethod
    def _calc_bbox(rings):
        pts = np.vstack(rings)
        return pts.min(0), pts.max(0)

    def bbox(self, codes, main_only=True):
        """World bbox of countries. main_only ignores far-flung islands."""
        if isinstance(codes, str):
            codes = [codes]
        pts = []
        for c in codes:
            rings = self.rings[c]
            if main_only:
                rings = [max(rings, key=lambda r: _area(r))]
            pts.append(np.vstack(rings))
        pts = np.vstack(pts)
        return pts.min(0), pts.max(0)

    def frame(self, codes, fill=0.6, aspect=16 / 9):
        """Camera (x, y, zoom) that frames countries to fill this share of the screen."""
        lo, hi = self.bbox(codes)
        cx, cy = (lo + hi) / 2
        w, h = hi - lo
        zoom = min(1920 * fill / max(w, 1e-6), 1080 * fill / max(h, 1e-6))
        return cx, cy, zoom

    def visible(self, canvas, depth=1.0, margin=0.1):
        """Codes whose bbox is on screen (cheap culling before rasterising)."""
        M = canvas.matrix(depth)
        out = []
        W, H = canvas.W, canvas.H
        for c, (lo, hi) in self._bbox.items():
            q = np.array([lo, hi, [lo[0], hi[1]], [hi[0], lo[1]]]) @ M[:, :2].T + M[:, 2]
            if (q[:, 0].max() < -W * margin or q[:, 0].min() > W * (1 + margin) or
                    q[:, 1].max() < -H * margin or q[:, 1].min() > H * (1 + margin)):
                continue
            out.append(c)
        return out


def _area(r):
    x, y = r[:, 0], r[:, 1]
    return abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2


def draw_map(cv, world, land="#d9cfb8", border="#9c917b", highlight=None, depth=1.0,
             paper=None, shadow=0.45, border_w=0.9, lift=1.0):
    """Collage map: paper land masses with soft shadows on whatever is already
    on the canvas (the sea), plus highlighted countries cut out of coloured
    paper with a white rim and a deeper shadow.

    highlight: {code: color}. lift (0..1) animates the highlight rising off the
    page. paper: world-anchored texture from cv.texture(), or None.
    Border widths are in screen units so lines stay crisp at any zoom.
    """
    highlight = highlight or {}
    codes = world.visible(cv, depth)
    rings = [r for c in codes if c not in highlight for r in world.rings[c]]
    m = cv.mask(rings, depth)
    sh = cv2.GaussianBlur(m, (0, 0), 5 * cv.k)
    cv.fill_mask(sh, "#000000", shadow, offset=(3, 5))
    cv.fill_mask(m, land, texture=paper)
    _borders(cv, rings, depth, border, border_w)
    for code, color in highlight.items():
        if code not in world.rings:
            continue
        hm = cv.mask(world.rings[code], depth)
        rim_px = max(2, int(6 * cv.k * lift))
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rim_px + 1, 2 * rim_px + 1))
        rim = cv2.GaussianBlur(cv2.dilate(hm, k), (0, 0), 0.8 * cv.k)
        s = 10 * lift + 2
        cv.fill_mask(cv2.GaussianBlur(rim, (0, 0), (4 + 10 * lift) * cv.k), "#000000",
                     0.35 + 0.25 * lift, offset=(s * 0.5, s))
        cv.fill_mask(rim, "#f7f3ea", texture=paper)
        cv.fill_mask(hm, color, texture=paper)


def _borders(cv, rings, depth, color, width):
    M = cv.matrix(depth)
    pts = [np.round((r @ M[:, :2].T + M[:, 2]) * 16).astype(np.int32) for r in rings]
    if not pts:
        return
    mm = np.zeros((cv.H, cv.W), np.uint8)
    cv2.polylines(mm, pts, True, 255, max(1, int(round(width * cv.k))), cv2.LINE_AA, shift=4)
    cv.fill_mask(mm.astype(np.float32) / 255, color, 0.8)
