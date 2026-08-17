"""Screen capture port — wraps MSS + Pillow implementation for high-performance,
thread-safe screen streaming.

Features:
* Thread-safe MSS instance caching via threading.local to support async thread pool execution.
* Win32 user desktop attachment for reliable frame grabbing across Windows services/threads.
* Hardware mouse cursor overlay rendering on Windows.
* Aspect-ratio preserving resolution downscaling.
* Validates JPEG headers (SOI & EOI markers) before transmission to avoid corrupted frames.
"""

from __future__ import annotations

import ctypes
import io
import os
import sys
import threading
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageDraw

try:
    import mss
except ImportError:  # pragma: no cover
    mss = None


JPEG_EOI = b"\xff\xd9"
JPEG_SOI = b"\xff\xd8"


_capture_thread_local = threading.local()


def _ensure_windows_desktop_access() -> None:
    if sys.platform == "win32":
        if getattr(_capture_thread_local, "desktop_attached", False):
            return
        try:
            user32 = ctypes.windll.user32
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                if user32.SetThreadDesktop(hdesk):
                    _capture_thread_local.desktop_attached = True
                user32.CloseDesktop(hdesk)
        except Exception:
            pass



def _looks_like_jpeg(data: bytes) -> bool:
    """Validate both SOI and EOI markers."""
    if not data or len(data) < 4:
        return False
    if data[:2] != JPEG_SOI:
        return False
    return data[-2:] == JPEG_EOI


class ScreenCapturer:
    """High-performance screen capturer using MSS + Pillow."""

    def __init__(self) -> None:
        self._last_resolution: Tuple[int, int] = (0, 0)
        self._thread_local = threading.local()

    @property
    def last_resolution(self) -> Tuple[int, int]:
        return self._last_resolution

    def _get_sct(self):
        sct = getattr(self._thread_local, "sct", None)
        if sct is None:
            if mss is None:
                return None
            mss_factory = getattr(mss, "MSS", getattr(mss, "mss", None))
            if mss_factory:
                sct = mss_factory()
                self._thread_local.sct = sct
        return sct

    def _dispose_sct(self) -> None:
        sct = getattr(self._thread_local, "sct", None)
        if sct is not None:
            try:
                if hasattr(sct, "close"):
                    sct.close()
            except Exception:
                pass
            self._thread_local.sct = None
        buf = getattr(self._thread_local, "buf", None)
        if buf is not None:
            try:
                buf.close()
            except Exception:
                pass
            self._thread_local.buf = None


    def get_monitors(self) -> List[Dict[str, Any]]:
        _ensure_windows_desktop_access()
        sct = self._get_sct()
        if not sct:
            return []

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
        _retry: int = 0,
    ) -> Tuple[bytes | None, Tuple[int, int]]:
        """Capture, encode, and validate a single frame.

        Returns ``(jpeg_bytes, (w, h))`` on success. Returns
        ``(None, (0, 0))`` on transient failure or unrecoverable error.
        """
        _ensure_windows_desktop_access()
        sct = self._get_sct()
        if sct is None:
            raise RuntimeError("mss package is not installed.")

        try:
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

            if orig_w <= 0 or orig_h <= 0:
                raise RuntimeError(f"Captured zero-dimension screen frame: {orig_w}x{orig_h}")

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

                        if 0 <= cx < orig_w and 0 <= cy < orig_h:
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

            buf = getattr(self._thread_local, "buf", None)
            if buf is None:
                buf = io.BytesIO()
                self._thread_local.buf = buf
            else:
                buf.seek(0)
                buf.truncate(0)

            img.save(buf, format="JPEG", quality=jpeg_quality, optimize=False, subsampling=2)
            jpeg_bytes = buf.getvalue()

            # --- validation ----------------------------
            if not _looks_like_jpeg(jpeg_bytes) or len(jpeg_bytes) <= 100:
                if _retry < 1:
                    return self.capture_frame(
                        monitor_index, max_width, max_height, jpeg_quality, _retry=_retry + 1
                    )
                return None, (0, 0)

            return jpeg_bytes, (img.width, img.height)


        except RuntimeError as err:
            self._dispose_sct()
            raise err
        except Exception:
            self._dispose_sct()
            raise
