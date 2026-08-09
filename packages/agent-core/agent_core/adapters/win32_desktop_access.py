"""win32_desktop_access — Windows-only helpers used by the input adapter.

Centralised so both the backend's WS handler and the screen-stream
server can call the same OpenInputDesktop / SetThreadDesktop dance.
On non-Windows platforms the function is a no-op.
"""

from __future__ import annotations

import sys


def ensure_windows_desktop_access() -> None:
    """Attach the current thread to the active user-input desktop.

    FastAPI and aiohttp both run request handlers on thread-pool
    threads, so any input we issue from those threads needs this
    attached or pyautogui's PostMessage target is the wrong desktop.
    Idempotent: safe to call repeatedly.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        user32 = ctypes.windll.user32
        # 0x01FF = DESKTOP_ALL_ACCESS
        hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception:
        # Best-effort: many test/CI environments don't expose the
        # input desktop, but they also don't run the WS handler.
        pass


# ----- monitor bounds (used to clamp absolute moves) -----
if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes as wintypes

    class _RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    class _MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", _RECT),
            ("rcWork", _RECT),
            ("dwFlags", wintypes.DWORD),
        ]

    _MONITOR_DEFAULTTONEAREST = 0x00000002

    def _active_monitor_bounds():
        """Return (left, top, right, bottom) for the monitor the
        cursor currently sits on, or None when Win32 can't tell us."""
        try:
            pt = wintypes.POINT()
            if not ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
                return None
            h = ctypes.windll.user32.MonitorFromPoint(
                pt, _MONITOR_DEFAULTTONEAREST
            )
            if not h:
                return None
            mi = _MONITORINFO()
            mi.cbSize = ctypes.sizeof(_MONITORINFO)
            if not ctypes.windll.user32.GetMonitorInfoW(h, ctypes.byref(mi)):
                return None
            return (
                mi.rcMonitor.left,
                mi.rcMonitor.top,
                mi.rcMonitor.right,
                mi.rcMonitor.bottom,
            )
        except Exception:
            return None

    def clamp_to_active_monitor(x: int, y: int):
        bounds = _active_monitor_bounds()
        if bounds is None:
            return x, y
        left, top, right, bottom = bounds
        # 1px margin so the OS doesn't snap or hide the cursor.
        clamped_x = max(left, min(right - 1, int(x)))
        clamped_y = max(top, min(bottom - 1, int(y)))
        return clamped_x, clamped_y
else:
    def _active_monitor_bounds():
        return None

    def clamp_to_active_monitor(x: int, y: int):
        return x, y


def log_monitor_info_once() -> None:
    """Print a one-line summary of detected monitors at startup.

    Called from the composition root after wiring is complete so the
    log line is always the same regardless of which server logs it.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes as _ct

        EnumDisplayMonitors = _ct.windll.user32.EnumDisplayMonitors
        GetMonitorInfoW = _ct.windll.user32.GetMonitorInfoW

        class _MI(_ct.Structure):
            _fields_ = [
                ("cbSize", _ct.c_ulong),
                ("rcMonitor", _RECT),
                ("rcWork", _RECT),
                ("dwFlags", _ct.c_ulong),
            ]

        monitors: list[str] = []

        def _callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
            mi = _MI()
            mi.cbSize = _ct.sizeof(_MI)
            if GetMonitorInfoW(hMonitor, _ct.byref(mi)):
                r = mi.rcMonitor
                monitors.append(f"({r.left},{r.top})-({r.right},{r.bottom})")
            return True

        CMPFUNC = _ct.WINFUNCTYPE(
            _ct.c_bool, _ct.c_void_p, _ct.c_void_p, _ct.c_void_p, _ct.c_void_p
        )
        _ct.windll.user32.EnumDisplayMonitors(None, None, CMPFUNC(_callback), 0)
        if monitors:
            print(f"[INPUT] Detected monitors: {', '.join(monitors)}")
    except Exception as e:  # noqa: BLE001
        print(f"[INPUT] Could not enumerate monitors: {e}")
