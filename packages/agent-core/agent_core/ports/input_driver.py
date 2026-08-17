"""Input port — abstracts mouse + keyboard drivers.

Implementations: `pyautogui_input_driver.PyAutoGUIInputDriver`,
`win32_desktop_access` helpers. The domain layer only sees this ABC.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agent_core.entities.input_command import (
    AbsoluteMove,
    ClickCommand,
    HotkeyCommand,
    KeyPressCommand,
    MouseDownCommand,
    MouseUpCommand,
    RelativeMove,
    ScrollCommand,
    TextInputCommand,
)


class InputDriver(ABC):
    """Abstract input device.

    All methods are blocking; the WS / HTTP layers are responsible for
    running them in a thread / executor so they don't stall the event
    loop. The driver itself makes no assumptions about concurrency.
    """

    # ----- mouse -----
    @abstractmethod
    def move_to(self, cmd: AbsoluteMove) -> None: ...

    @abstractmethod
    def move_relative(self, cmd: RelativeMove) -> None: ...

    @abstractmethod
    def click(self, cmd: ClickCommand) -> None: ...

    @abstractmethod
    def mouse_down(self, cmd: MouseDownCommand) -> None: ...

    @abstractmethod
    def mouse_up(self, cmd: MouseUpCommand) -> None: ...

    @abstractmethod
    def scroll(self, cmd: ScrollCommand) -> None: ...

    # ----- keyboard -----
    @abstractmethod
    def type_text(self, cmd: TextInputCommand) -> None: ...

    @abstractmethod
    def press_key(self, cmd: KeyPressCommand) -> None: ...

    @abstractmethod
    def hotkey(self, cmd: HotkeyCommand) -> None: ...

    # ----- lifecycle -----
    def attach_to_active_desktop(self) -> None:
        """Optional hook for Windows to attach the current thread to the
        active user-input desktop. Default is a no-op so non-Windows
        adapters don't need to override."""
        return None
