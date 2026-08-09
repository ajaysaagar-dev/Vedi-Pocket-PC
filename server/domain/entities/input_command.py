"""Input command entities.

A discriminated union of every kind of input we can issue against the host.
The presentation layer (HTTP / WebSocket) maps wire-format messages onto
these entities before handing them to `ControlInput.execute`. This keeps
the wire protocol decoupled from the driver.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Union


class Button(str, Enum):
    """Mouse buttons. String-valued so they survive JSON round-trips."""

    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


@dataclass(frozen=True)
class AbsoluteMove:
    """Move the cursor to absolute screen coordinates (x, y)."""

    x: int
    y: int
    duration: float = 0.0


@dataclass(frozen=True)
class RelativeMove:
    """Move the cursor by (dx, dy) from its current position."""

    dx: float
    dy: float
    duration: float = 0.0


@dataclass(frozen=True)
class ClickCommand:
    """Click N times with the given button. (x, y) is optional — if
    omitted the click happens at the cursor's current location."""

    button: Button = Button.LEFT
    clicks: int = 1
    x: Optional[int] = None
    y: Optional[int] = None


@dataclass(frozen=True)
class ScrollCommand:
    """Scroll the mouse wheel. Positive dy = up, negative dy = down."""

    dx: float = 0.0
    dy: float = 0.0


@dataclass(frozen=True)
class TextInputCommand:
    """Type a string into the focused window."""

    text: str


@dataclass(frozen=True)
class KeyPressCommand:
    """Press a single named key (e.g. 'enter', 'volumeup')."""

    key: str


@dataclass(frozen=True)
class HotkeyCommand:
    """Press a key combination (e.g. ['ctrl', 'c'])."""

    keys: List[str]


# Discriminated union — exhaustive over every supported input action.
InputCommand = Union[
    AbsoluteMove,
    RelativeMove,
    ClickCommand,
    ScrollCommand,
    TextInputCommand,
    KeyPressCommand,
    HotkeyCommand,
]
