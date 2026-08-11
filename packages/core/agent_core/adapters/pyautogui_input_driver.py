"""PyAutoGUIInputDriver — pyautogui-backed implementation of InputDriver.

This is the single source of truth for "issue a mouse / keyboard event
on the host". Both vedi-pocketpc-backend and screen-stream-server
construct one of these in their composition root and pass it to
ControlInput.
"""

from __future__ import annotations

from agent_core.adapters.win32_desktop_access import (
    clamp_to_active_monitor,
    ensure_windows_desktop_access,
)
from agent_core.entities.input_command import (
    AbsoluteMove,
    ClickCommand,
    HotkeyCommand,
    KeyPressCommand,
    RelativeMove,
    ScrollCommand,
    TextInputCommand,
)
from agent_core.ports.input_driver import InputDriver as _InputDriverPort


class PyAutoGUIInputDriver(_InputDriverPort):
    """Concrete InputDriver that delegates to pyautogui.

    Lazy-imports pyautogui so this module is importable on CI / build
    machines where the library isn't installed; only the constructor
    fails if it isn't.
    """

    def __init__(self) -> None:
        try:
            import pyautogui  # type: ignore
        except ImportError as exc:  # pragma: no cover — install-time guard
            raise RuntimeError(
                "pyautogui is required for PyAutoGUIInputDriver. "
                "Install it via `pip install pyautogui`."
            ) from exc

        # Disable PyAutoGUI's fail-safe corner (we never want a trackpad
        # gesture to silently swallow a move-to-the-corner event).
        pyautogui.FAILSAFE = False
        # Disable per-call pauses — remote input is fire-and-forget.
        try:
            pyautogui.PAUSE = 0.0
        except Exception:
            pass
        self._pyautogui = pyautogui

    # ----- lifecycle -----
    def attach_to_active_desktop(self) -> None:
        ensure_windows_desktop_access()

    # ----- mouse -----
    def move_to(self, cmd: AbsoluteMove) -> None:
        x, y = clamp_to_active_monitor(int(cmd.x), int(cmd.y))
        self._pyautogui.moveTo(x, y, duration=float(cmd.duration), _pause=False)

    def move_relative(self, cmd: RelativeMove) -> None:
        idx, idy = int(round(cmd.dx)), int(round(cmd.dy))
        if idx == 0 and idy == 0:
            return
        self._pyautogui.move(idx, idy, _pause=False)

    def click(self, cmd: ClickCommand) -> None:
        kwargs = {"button": cmd.button.value, "clicks": cmd.clicks, "_pause": False}
        if cmd.x is not None and cmd.y is not None:
            x, y = clamp_to_active_monitor(int(cmd.x), int(cmd.y))
            kwargs["x"] = x
            kwargs["y"] = y
        self._pyautogui.click(**kwargs)

    def scroll(self, cmd: ScrollCommand) -> None:
        if int(cmd.dy) != 0:
            self._pyautogui.scroll(int(cmd.dy), _pause=False)
        # Horizontal scroll isn't part of the public pyautogui API on
        # every version, so we silently drop dx for portability.

    # ----- keyboard -----
    def type_text(self, cmd: TextInputCommand) -> None:
        if not cmd.text:
            return
        self._pyautogui.write(cmd.text, _pause=False)

    def press_key(self, cmd: KeyPressCommand) -> None:
        if not cmd.key:
            return
        self._pyautogui.press(cmd.key, _pause=False)

    def hotkey(self, cmd: HotkeyCommand) -> None:
        if not cmd.keys:
            return
        self._pyautogui.hotkey(*cmd.keys, _pause=False)
