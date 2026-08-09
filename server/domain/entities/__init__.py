"""Domain entities — plain data types representing the core concepts.

These are framework-free dataclasses. They are *not* Pydantic models
(those live in the presentation layer), and they do not import any
adapter or driver — that is the whole point of the entities layer.
"""
from __future__ import annotations


from server.domain.entities.input_command import (
    AbsoluteMove,
    Button,
    ClickCommand,
    HotkeyCommand,
    InputCommand,
    KeyPressCommand,
    RelativeMove,
    ScrollCommand,
    TextInputCommand,
)
from server.domain.entities.pairing import PairResult, PairingPin, SessionToken
from server.domain.entities.system_status import (
    AudioLevel,
    BatteryStatus,
    PowerAction,
    SystemSnapshot,
)

__all__ = [
    # input_command
    "AbsoluteMove",
    "Button",
    "ClickCommand",
    "HotkeyCommand",
    "InputCommand",
    "KeyPressCommand",
    "RelativeMove",
    "ScrollCommand",
    "TextInputCommand",
    # pairing
    "PairResult",
    "PairingPin",
    "SessionToken",
    # system_status
    "AudioLevel",
    "BatteryStatus",
    "PowerAction",
    "SystemSnapshot",
]
