"""ControlInput — the single entry point for every input action.

Replaces what used to be two near-identical handlers (one in
vedi-pocketpc-backend's ws_handler.py, one in screen-stream-server's
StreamManager). Both now call `execute(InputCommand)` and let this
class route to the right driver method.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from server.domain.entities.input_command import (
    AbsoluteMove,
    ClickCommand,
    HotkeyCommand,
    InputCommand,
    KeyPressCommand,
    RelativeMove,
    ScrollCommand,
    TextInputCommand,
)
from server.domain.ports.input_driver import InputDriver


@dataclass(frozen=True)
class InputResult:
    """Result of executing an input command.

    `ok` is False when the underlying driver raised or rejected the
    command. `error` is a short, safe-to-surface reason.
    """

    ok: bool
    error: Optional[str] = None


class ControlInput:
    """Single use case covering mouse + keyboard actions."""

    def __init__(self, driver: InputDriver) -> None:
        self._driver = driver

    def execute(self, command: InputCommand) -> InputResult:
        """Dispatch an input command to the underlying driver.

        Wraps the call so a buggy adapter (or a transient OS error)
        never crashes the calling WS handler. Returns `InputResult.ok
        = False` and a short reason instead.
        """
        try:
            # Make sure the current thread is attached to the active
            # user desktop on Windows before issuing the input.
            self._driver.attach_to_active_desktop()

            if isinstance(command, AbsoluteMove):
                self._driver.move_to(command)
            elif isinstance(command, RelativeMove):
                self._driver.move_relative(command)
            elif isinstance(command, ClickCommand):
                self._driver.click(command)
            elif isinstance(command, ScrollCommand):
                self._driver.scroll(command)
            elif isinstance(command, TextInputCommand):
                self._driver.type_text(command)
            elif isinstance(command, KeyPressCommand):
                self._driver.press_key(command)
            elif isinstance(command, HotkeyCommand):
                self._driver.hotkey(command)
            else:
                return InputResult(ok=False, error=f"unsupported command: {type(command).__name__}")
            return InputResult(ok=True)
        except Exception as exc:  # noqa: BLE001 — we want to catch any driver failure
            return InputResult(ok=False, error=f"{type(exc).__name__}: {exc}")
