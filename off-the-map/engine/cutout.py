"""Background removal for collage cutouts (IS-Net, rembg's general-use model).

Run setup.sh to download assets/models/isnet-general-use.onnx (~178 MB).
"""
import os

import cv2
import numpy as np

MODEL = os.path.join(os.path.dirname(__file__), "..", "assets", "models",
                     "isnet-general-use.onnx")
_session = None


def _sess():
    global _session
    if _session is None:
        import onnxruntime as ort
        _session = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
    return _session


def subject_mask(rgb, threshold=None):
    """Foreground mask (HxW float 0..1) for an RGB uint8 photo."""
    h, w = rgb.shape[:2]
    x = cv2.resize(rgb, (1024, 1024), interpolation=cv2.INTER_AREA).astype(np.float32) / 255
    x = (x - 0.5) / 1.0                       # rembg's isnet normalisation
    x = x.transpose(2, 0, 1)[None]
    s = _sess()
    out = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
    out = (out - out.min()) / max(out.max() - out.min(), 1e-6)
    m = cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)
    if threshold is not None:
        m = np.clip((m - threshold) * 8 + 0.5, 0, 1)
    return m.astype(np.float32)


def load_rgb(path):
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
