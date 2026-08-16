import sys
import config

try:
    import pyautogui
    pyautogui.PAUSE = 0.0
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None


class MouseController:
    """Windows Remote Mouse Controller using PyAutoGUI."""

    def __init__(self) -> None:
        if sys.platform != "win32":
            print("[WARNING] MouseController is running on a non-Windows OS.", flush=True)

    def _ensure_windows_desktop_access(self) -> None:
        if sys.platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
                if hdesk:
                    user32.SetThreadDesktop(hdesk)
            except Exception:
                pass

    def _ensure_pyautogui(self) -> None:
        if pyautogui is None:
            raise RuntimeError("pyautogui package is not installed.")
        self._ensure_windows_desktop_access()

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:
        """Moves Windows cursor to absolute (x, y) coordinates with optional duration."""
        self._ensure_pyautogui()
        pyautogui.moveTo(int(x), int(y), duration=float(duration), _pause=False)
        print(f"[MOUSE] MOVE_TO x={x} y={y} duration={duration}", flush=True)

    def move_relative(self, dx: float, dy: float, duration: float = 0.0) -> None:
        """Moves Windows cursor relative to current position (pyautogui.move)."""
        self._ensure_pyautogui()
        actual_dx = int(dx * config.MOUSE_SENSITIVITY)
        actual_dy = int(dy * config.MOUSE_SENSITIVITY)

        if actual_dx != 0 or actual_dy != 0:
            pyautogui.move(actual_dx, actual_dy, duration=float(duration), _pause=False)

        if config.DEBUG_MOUSE:
            print(f"[MOUSE] MOVE dx={actual_dx} dy={actual_dy}", flush=True)

    def click(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        """Performs a single mouse click at current cursor position or specified (x, y)."""
        self._ensure_pyautogui()
        btn = "right" if button == "right" else ("middle" if button == "middle" else "left")
        if x is not None and y is not None:
            pyautogui.click(x=int(x), y=int(y), button=btn, _pause=False)
            print(f"[MOUSE] CLICK {btn} at ({x}, {y})", flush=True)
        else:
            pyautogui.click(button=btn, _pause=False)
            print(f"[MOUSE] CLICK {btn}", flush=True)

    def double_click(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        """Performs a double mouse click at current cursor position or specified (x, y)."""
        self._ensure_pyautogui()
        btn = "right" if button == "right" else ("middle" if button == "middle" else "left")
        if x is not None and y is not None:
            pyautogui.doubleClick(x=int(x), y=int(y), button=btn, _pause=False)
            print(f"[MOUSE] DOUBLE_CLICK {btn} at ({x}, {y})", flush=True)
        else:
            pyautogui.doubleClick(button=btn, _pause=False)
            print(f"[MOUSE] DOUBLE_CLICK {btn}", flush=True)

    def mouse_down(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        """Presses and holds a mouse button at current position or specified (x, y)."""
        self._ensure_pyautogui()
        btn = "right" if button == "right" else ("middle" if button == "middle" else "left")
        if x is not None and y is not None:
            pyautogui.mouseDown(x=int(x), y=int(y), button=btn, _pause=False)
        else:
            pyautogui.mouseDown(button=btn, _pause=False)
        print(f"[MOUSE] DOWN {btn}", flush=True)

    def mouse_up(self, x: int | None = None, y: int | None = None, button: str = "left") -> None:
        """Releases a mouse button at current position or specified (x, y)."""
        self._ensure_pyautogui()
        btn = "right" if button == "right" else ("middle" if button == "middle" else "left")
        if x is not None and y is not None:
            pyautogui.mouseUp(x=int(x), y=int(y), button=btn, _pause=False)
        else:
            pyautogui.mouseUp(button=btn, _pause=False)
        print(f"[MOUSE] UP {btn}", flush=True)

    def scroll(self, dx: float, dy: float) -> None:
        """Scrolls the vertical mouse wheel (positive dy = scroll up, negative dy = scroll down)."""
        self._ensure_pyautogui()
        amount = int(dy * config.SCROLL_SENSITIVITY)
        if amount != 0:
            pyautogui.scroll(amount, _pause=False)
        print(f"[MOUSE] SCROLL dy={amount}", flush=True)

    def key_press(self, key: str) -> None:
        """Presses a single keyboard key (e.g. 'enter', 'backspace', 'a', 'tab', 'escape')."""
        self._ensure_pyautogui()
        if not key:
            return
        clean_key = str(key).lower()
        pyautogui.press(clean_key, _pause=False)
        print(f"[KEYBOARD] PRESS key='{clean_key}'", flush=True)

    def text_input(self, text: str) -> None:
        """Types string text into active desktop window."""
        self._ensure_pyautogui()
        if not text:
            return
        pyautogui.write(str(text), _pause=False)
        print(f"[KEYBOARD] TYPE text='{text}'", flush=True)

    def key_combo(self, keys: list) -> None:
        """Presses a hotkey combination (e.g. ['ctrl', 'c'], ['alt', 'tab'])."""
        self._ensure_pyautogui()
        if not keys or not isinstance(keys, list):
            return
        pyautogui.hotkey(*keys, _pause=False)
        print(f"[KEYBOARD] HOTKEY keys={keys}", flush=True)

    def key_down(self, key: str) -> None:
        """Presses and holds a keyboard key."""
        self._ensure_pyautogui()
        pyautogui.keyDown(str(key).lower(), _pause=False)

    def key_up(self, key: str) -> None:
        """Releases a held keyboard key."""
        self._ensure_pyautogui()
        pyautogui.keyUp(str(key).lower(), _pause=False)
