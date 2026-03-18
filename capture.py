import base64
import io
import threading

import mss
from PIL import Image

from config import SCREENSHOT_JPEG_QUALITY, SCREENSHOT_MAX_DIMENSION

_local = threading.local()


def _get_sct():
    if not hasattr(_local, "sct"):
        _local.sct = mss.mss()
    return _local.sct


def capture_screenshot() -> str:
    """Capture primary monitor and return as base64 JPEG. ~5-15ms, zero GPU impact."""
    sct = _get_sct()
    raw = sct.grab(sct.monitors[1])
    img = Image.frombytes("RGB", (raw.width, raw.height), raw.rgb)

    if max(img.size) > SCREENSHOT_MAX_DIMENSION:
        ratio = SCREENSHOT_MAX_DIMENSION / max(img.size)
        img = img.resize(
            (int(img.width * ratio), int(img.height * ratio)),
            Image.Resampling.BILINEAR,
        )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=SCREENSHOT_JPEG_QUALITY)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def screenshot_size_kb(b64_data: str) -> float:
    return len(b64_data) * 3 / 4 / 1024
