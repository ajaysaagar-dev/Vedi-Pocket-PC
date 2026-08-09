import sys
import os
import pyautogui

# PyAutoGUI safety configuration
pyautogui.FAILSAFE = False

# Platform-specific imports for Windows
IS_WINDOWS = sys.platform == 'win32'

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    except ImportError:
        pass

    # ---------------------------------------------------------------------------
    # COM initialization helper.
    #
    # pycaw talks to Windows audio via COM. COM requires every thread that uses
    # it to call CoInitialize() first — otherwise pycaw raises
    # `WinError -2147221008: CoInitialize has not been called`. FastAPI runs
    # request handlers on a thread pool, so we initialize COM at the start of
    # each function that touches COM. CoInitialize is idempotent: returning
    # S_FALSE on the second call simply means "already initialized on this
    # thread" and is fine to ignore.
    # ---------------------------------------------------------------------------
    def _co_initialize() -> None:
        try:
            ctypes.windll.ole32.CoInitialize(None)
        except Exception:
            # S_FALSE (already initialized) or any other benign result — ignore.
            pass

    def _ensure_windows_desktop_access() -> None:
        """Attaches the current thread to the active user input desktop on Windows."""
        try:
            user32 = ctypes.windll.user32
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
        except Exception:
            pass

    # ---------------------------------------------------------------------------
    # Monitor detection.
    #
    # pyautogui.moveTo uses coordinates in the *virtual desktop* spanning all
    # attached displays. On a multi-monitor setup (or a laptop + external /
    # RDP / virtual display), a coordinate like (200, 200) can land on a
    # monitor the user isn't looking at, making the cursor appear "stuck".
    # We solve this by:
    #   1. Asking Win32 which physical monitor the cursor currently lives on.
    #   2. Clamping every moveTo target to that monitor's pixel bounds.
    # The cursor therefore stays on whichever screen it's already on, which
    # is what the user expects from a trackpad.
    # ---------------------------------------------------------------------------
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
        """
        Return (left, top, right, bottom) of the monitor the cursor is
        currently on, or None if Win32 can't tell us.
        """
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

    def _clamp_to_active_monitor(x, y):
        """Clamp (x, y) to the bounds of the monitor the cursor is on."""
        bounds = _active_monitor_bounds()
        if bounds is None:
            return x, y
        left, top, right, bottom = bounds
        # Keep at least a 1px margin so the OS doesn't snap or hide the cursor.
        clamped_x = max(left, min(right - 1, int(x)))
        clamped_y = max(top, min(bottom - 1, int(y)))
        return clamped_x, clamped_y

    def _log_monitor_info_once():
        """Print a one-line summary of detected monitors at startup."""
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

            monitors = []

            def _callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
                mi = _MI()
                mi.cbSize = _ct.sizeof(_MI)
                if GetMonitorInfoW(hMonitor, _ct.byref(mi)):
                    r = mi.rcMonitor
                    monitors.append(
                        f"({r.left},{r.top})-({r.right},{r.bottom})"
                    )
                return True

            CMPFUNC = _ct.WINFUNCTYPE(
                _ct.c_bool, _ct.c_void_p, _ct.c_void_p, _ct.c_void_p, _ct.c_void_p
            )
            _ct.windll.user32.EnumDisplayMonitors(
                None, None, CMPFUNC(_callback), 0
            )
            if monitors:
                print(f"[INPUT] Detected monitors: {', '.join(monitors)}")
        except Exception as e:
            print(f"[INPUT] Could not enumerate monitors: {e}")
else:
    def _co_initialize() -> None:  # no-op on non-Windows
        return None

    def _active_monitor_bounds():
        return None

    def _clamp_to_active_monitor(x, y):
        return x, y

    def _log_monitor_info_once():
        pass

def move_to(x: int, y: int, duration: float = 0.0):
    """
    Moves the mouse to absolute (x, y) coordinates with optional duration.
    """
    _ensure_windows_desktop_access()
    try:
        pyautogui.moveTo(int(x), int(y), duration=float(duration), _pause=False)
    except Exception as e:
        print(f"Error moving mouse to ({x}, {y}): {e}")

def move_mouse(dx: float, dy: float):
    """
    Moves the mouse relative to its current position.
    """
    _ensure_windows_desktop_access()
    try:
        idx, idy = int(round(dx)), int(round(dy))
        if idx != 0 or idy != 0:
            pyautogui.move(idx, idy, _pause=False)
    except Exception as e:
        print(f"Error moving mouse: {e}")

def click_mouse(button: str = 'left', clicks: int = 1):
    """
    Performs a click action.
    button: 'left', 'right', 'middle'
    clicks: 1 or 2
    """
    _ensure_windows_desktop_access()
    try:
        pyautogui.click(button=button, clicks=clicks, _pause=False)
    except Exception as e:
        print(f"Error clicking mouse: {e}")

def scroll_mouse(dy: float):
    """
    Scrolls the mouse wheel.
    Positive dy is scroll up, negative dy is scroll down.
    """
    _ensure_windows_desktop_access()
    try:
        # PyAutoGUI scroll is integer steps
        pyautogui.scroll(int(dy), _pause=False)
    except Exception as e:
        print(f"Error scrolling mouse: {e}")

def type_text(text: str):
    """
    Types the given string.
    """
    _ensure_windows_desktop_access()
    try:
        pyautogui.write(text, _pause=False)
    except Exception as e:
        print(f"Error typing text: {e}")

def press_key(key: str):
    """
    Presses a specific key (e.g., 'enter', 'backspace', 'volumeup', etc.).
    """
    _ensure_windows_desktop_access()
    try:
        pyautogui.press(key, _pause=False)
    except Exception as e:
        print(f"Error pressing key {key}: {e}")

def hotkey(keys: list):
    """
    Performs a keyboard shortcut combo (e.g., ['ctrl', 'c'] for Ctrl+C).
    All keys are held down together and then released.
    """
    _ensure_windows_desktop_access()
    try:
        pyautogui.hotkey(*keys, _pause=False)
    except Exception as e:
        print(f"Error performing hotkey {keys}: {e}")

def get_volume() -> int:
    """
    Gets the current master volume level (0 to 100).
    """
    if not IS_WINDOWS:
        print("Volume control is only implemented for Windows in this version.")
        return 50
    _co_initialize()
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return int(round(volume.GetMasterVolumeLevelScalar() * 100))
    except Exception as e:
        print(f"Error getting volume: {e}")
        return 50

def set_volume(level: int) -> bool:
    """
    Sets the current master volume level (0 to 100).
    """
    if not IS_WINDOWS:
        print("Volume control is only implemented for Windows in this version.")
        return False
    _co_initialize()
    try:
        # Clamp value between 0 and 100
        level = max(0, min(100, level))
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        return True
    except Exception as e:
        print(f"Error setting volume: {e}")
        return False

def system_lock():
    """
    Locks the computer.
    """
    if IS_WINDOWS:
        try:
            ctypes.windll.user32.LockWorkStation()
            return True
        except Exception as e:
            print(f"Error locking computer: {e}")
            return False
    else:
        print("Lock is only supported on Windows.")
        return False

def system_sleep():
    """
    Puts the computer to sleep.
    """
    if IS_WINDOWS:
        try:
            # SetSuspendState(hibernate, force, disable_wake_events)
            ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)
            return True
        except Exception as e:
            print(f"Error putting computer to sleep: {e}")
            return False
    else:
        print("Sleep is only supported on Windows.")
        return False

def system_shutdown():
    """
    Shuts down the computer.
    """
    if IS_WINDOWS:
        try:
            os.system("shutdown /s /t 5")
            return True
        except Exception as e:
            print(f"Error shutting down computer: {e}")
            return False
    else:
        print("Shutdown is only supported on Windows.")
        return False
