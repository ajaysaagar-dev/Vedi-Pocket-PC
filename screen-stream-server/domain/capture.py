"""Screen capture port — wraps the existing MSS + Pillow implementation.

The capture logic is unchanged from the previous monolithic
`screen_capture.py`; we just moved it to `domain/` so the rest of the
project can refer to it as a port (no MSS / Pillow imports leak out).
"""

from __future__ import annotations

import ctypes
import io
import sys
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageDraw

try:
    import mss
except ImportError:  # pragma: no cover — captured by the caller
    mss = None


def _ensure_windows_desktop_access() -> None:
    if sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass


class ScreenCapturer:
    """High-performance screen capturer using MSS + Pillow.

    Returns JPEG bytes plus a (width, height) tuple for clients that
    want to know the captured resolution.
    """

    def __init__(self) -> None:
        self._last_resolution: Tuple[int, int] = (0, 0)

    @property
    def last_resolution(self) -> Tuple[int, int]:
        return self._last_resolution

    def get_monitors(self) -> List[Dict[str, Any]]:
        _ensure_windows_desktop_access()
        if mss is None:
            return []

        mss_factory = getattr(mss, "MSS", getattr(mss, "mss", None))
        if not mss_factory:
            return []

        with mss_factory() as sct:
            monitors_list = []
            for idx, mon in enumerate(sct.monitors):
                monitors_list.append({
                    "index": idx,
                    "left": mon.get("left", 0),
                    "top": mon.get("top", 0),
                    "width": mon.get("width", 0),
                    "height": mon.get("height", 0),
                    "is_primary": mon.get("is_primary", False) if idx > 0 else (idx == 0 and len(sct.monitors) == 1),
                    "name": mon.get("name", "All Monitors" if idx == 0 else f"Monitor {idx}"),
                })
            return monitors_list

    def capture_frame(
        self,
        monitor_index: int = 1,
        max_width: int = 1280,
        max_height: int = 720,
        jpeg_quality: int = 70,
    ) -> Tuple[bytes, Tuple[int, int]]:
        _ensure_windows_desktop_access()
        if mss is None:
            raise RuntimeError("mss package is not installed.")

        mss_factory = getattr(mss, "MSS", getattr(mss, "mss", None))
        with mss_factory() as sct:
            available_monitors = sct.monitors
            if not available_monitors:
                raise RuntimeError("No monitors detected by MSS.")

            if monitor_index < 0 or monitor_index >= len(available_monitors):
                target_idx = 1 if len(available_monitors) > 1 else 0
            else:
                target_idx = monitor_index

            mon = available_monitors[target_idx]
            raw_shot = sct.grab(mon)

            img = Image.frombytes("RGB", raw_shot.size, raw_shot.bgra, "raw", "BGRX")
            orig_w, orig_h = img.size

            # Draw hardware mouse cursor overlay (Windows-only).
            if sys.platform == "win32":
                try:
                    from ctypes import wintypes
                    class _POINT(ctypes.Structure):
                        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]
                    class _CURSORINFO(ctypes.Structure):
                        _fields_ = [
                            ("cbSize", wintypes.DWORD),
                            ("flags", wintypes.DWORD),
                            ("hCursor", wintypes.HCURSOR),
                            ("ptScreenPos", _POINT),
                        ]
                    user32 = ctypes.windll.user32
                    ci = _CURSORINFO()
                    ci.cbSize = ctypes.sizeof(_CURSORINFO)
                    if user32.GetCursorInfo(ctypes.byref(ci)) and (ci.flags & 1):
                        cx = ci.ptScreenPos.x - mon.get("left", 0)
                        cy = ci.ptScreenPos.y - mon.get("top", 0)

                        scale_x = (min(max_width / orig_w, max_height / orig_h) if (orig_w > max_width or orig_h > max_height) else 1.0)
                        scale_y = scale_x

                        mcx = int(cx * scale_x)
                        mcy = int(cy * scale_y)

                        if 0 <= mcx < (orig_w * scale_x) and 0 <= mcy < (orig_h * scale_y):
                            draw = ImageDraw.Draw(img)
                            arrow = [
                                (cx, cy),
                                (cx, cy + 16),
                                (cx + 4, cy + 12),
                                (cx + 8, cy + 18),
                                (cx + 11, cy + 16),
                                (cx + 7, cy + 11),
                                (cx + 12, cy + 11),
                            ]
                            draw.polygon(arrow, fill=(255, 255, 255), outline=(0, 0, 0))
                except Exception:
                    pass

            if orig_w > max_width or orig_h > max_height:
                ratio = min(max_width / orig_w, max_height / orig_h)
                new_w = max(1, int(orig_w * ratio))
                new_h = max(1, int(orig_h * ratio))
                img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)

            self._last_resolution = (img.width, img.height)

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=jpeg_quality)
            jpeg_bytes = buf.getvalue()

            return jpeg_bytes, (img.width, img.height)
