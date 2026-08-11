"""Screen capture port — wraps the existing MSS + Pillow implementation
with a small layer of robustness:

* Validate the JPEG footer (EOI marker) before returning bytes — a
  truncated JPEG that passes the SOI-only check on the client can render
  as a black frame, so we filter those out here.
* Maintain a single-shot content digest of the last *good* frame so we
  can skip broadcasting duplicates. On a static desktop this can save
  ~99% of the bandwidth and one full decoder cycle per duplicate on
  the client.
* Track a rolling mean of recent frame sizes so we can spot blank /
  monotone frames that compress to a tiny JPEG (these would otherwise
  look like a legitimate frame and render as solid black on the client).
* Differentiate between transient GDI errors (keep the MSS instance) and
  genuinely stale monitor descriptions (rebuild the instance). The old
  blanket-reset path was wasteful and contributed to render stalls
  after DWM transitions.
"""

from __future__ import annotations

import ctypes
import hashlib
import io
import os
import sys
import time
from collections import deque
from threading import Lock
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageDraw

try:
    import mss
except ImportError:  # pragma: no cover — captured by the caller
    mss = None


JPEG_EOI = b"\xff\xd9"
JPEG_SOI = b"\xff\xd8"

# How many recent frame sizes to keep for the rolling-mean blank detector.
_BLANK_WINDOW = 30
# A frame whose byte count is below this fraction of the moving mean is
# treated as suspiciously blank. 0.25 works well for 360p JPEG of real
# desktop content; blank/monotone desktop compresses to ~1–5 KB while
# the same resolution of real content is 30+ KB.
_BLANK_RATIO_THRESHOLD = 0.25
# Minimum rolling-mean sample count before blank detection kicks in.
_BLANK_MIN_SAMPLES = 6


def _ensure_windows_desktop_access() -> None:
    if sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass


def _looks_like_jpeg(data: bytes) -> bool:
    """Validate both SOI and EOI markers.

    SOI alone is not enough — the previous client dropped truncated JPEGs
    because they decode as solid colour and present as a black frame.
    Server-side validation means we never put a broken JPEG on the wire.
    """
    if not data or len(data) < 4:
        return False
    if data[:2] != JPEG_SOI:
        return False
    # EOI may legitimately be hidden inside an FFD8 (restart) sequence in
    # some encoders; for Pillow's default JPEG output the marker is the
    # last two bytes.
    return data[-2:] == JPEG_EOI


class ScreenCapturer:
    """High-performance screen capturer using MSS + Pillow.

    Returns JPEG bytes plus a (width, height) tuple for clients that
    want to know the captured resolution. Captured bytes are validated
    and may be dropped for the following reasons:

    * Truncated JPEG (failed EOI check).
    * Duplicate of the previous good frame (content digest match).
    * Anomalously small JPEG (likely a blank / monotone screen).

    Callers should treat ``None`` as a normal skip, not as an error.
    """

    def __init__(self) -> None:
        self._last_resolution: Tuple[int, int] = (0, 0)
        self._sct_instance = None

        # Frame deduplication state.
        self._last_good_digest: bytes | None = None

        # Rolling-mean blank-detector state.
        self._size_samples: "deque[int]" = deque(maxlen=_BLANK_WINDOW)
        self._size_lock = Lock()

    @property
    def last_resolution(self) -> Tuple[int, int]:
        return self._last_resolution

    def _get_sct(self):
        if self._sct_instance is None:
            if mss is None:
                return None
            mss_factory = getattr(mss, "MSS", getattr(mss, "mss", None))
            if mss_factory:
                self._sct_instance = mss_factory()
        return self._sct_instance

    def _dispose_sct(self) -> None:
        # Try to close cleanly first so GDI handles are released; ignore
        # failures — we just want to drop the cached instance.
        try:
            inst = self._sct_instance
            if inst is not None and hasattr(inst, "close"):
                inst.close()
        except Exception:
            pass
        self._sct_instance = None

    def _record_size(self, size: int) -> None:
        with self._size_lock:
            self._size_samples.append(size)

    def _is_blank_size(self, size: int) -> bool:
        with self._size_lock:
            if len(self._size_samples) < _BLANK_MIN_SAMPLES:
                return False
            mean = sum(self._size_samples) / len(self._size_samples)
        # Strict ratio check: blank frames are an order of magnitude
        # smaller than content frames at the same resolution.
        return mean > 0 and size < mean * _BLANK_RATIO_THRESHOLD

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
        ``(None, (0, 0))`` when the frame is intentionally skipped:

        * the JPEG fails SOI/EOI validation (truncated / corrupt);
        * the JPEG matches the previous good frame byte-for-byte;
        * the JPEG is anomalously small versus recent history.

        The exception path is reserved for unrecoverable capture
        errors so the caller's loop can keep running.
        """
        _ensure_windows_desktop_access()
        sct = self._get_sct()
        if sct is None:
            raise RuntimeError("mss package is not installed.")

        try:
            available_monitors = sct.monitors
            if not available_monitors:
                # A missing monitor list usually means the desktop is in
                # a transition state; force a fresh MSS instance on the
                # next call.
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

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=jpeg_quality, optimize=False)
            jpeg_bytes = buf.getvalue()

            # --- validation + deduplication ----------------------------
            if not _looks_like_jpeg(jpeg_bytes):
                # Truncated or otherwise invalid output. One retry is
                # worth it (a transient Pillow write can produce this);
                # beyond that we just drop the frame.
                if _retry < 1:
                    return self.capture_frame(
                        monitor_index, max_width, max_height, jpeg_quality, _retry=_retry + 1
                    )
                return None, (0, 0)

            # Cheap pre-check before we bother hashing or recording.
            if len(jpeg_bytes) <= 100:
                return None, (0, 0)

            digest = hashlib.blake2b(jpeg_bytes, digest_size=16).digest()
            if digest == self._last_good_digest:
                # Identical to the previous good frame — static desktop
                # produces these constantly and shipping them causes the
                # client to thrash its image cache for no visible change.
                return None, (0, 0)
            self._last_good_digest = digest

            if self._is_blank_size(len(jpeg_bytes)):
                # Blank frame. Record the sample (so the detector keeps
                # calibrating) but skip the broadcast.
                self._record_size(len(jpeg_bytes))
                return None, (0, 0)

            self._record_size(len(jpeg_bytes))
            return jpeg_bytes, (img.width, img.height)

        except RuntimeError as err:
            # Unrecoverable for this iteration. Reset the MSS instance so
            # the *next* capture rebuilds it cleanly.
            self._dispose_sct()
            raise err
        except Exception:
            # Any other failure (e.g. transient GDI / DWM glitch during
            # surface lock). Don't immediately rebuild the MSS instance —
            # the next attempt at full speed is usually fine.
            raise
