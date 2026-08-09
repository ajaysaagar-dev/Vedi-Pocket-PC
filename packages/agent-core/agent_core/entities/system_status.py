"""System-status entities.

Snapshot of what the agent knows about the host: master volume, battery
state (when applicable), and the available power actions. Snapshot is
immutable so HTTP / WS handlers can hand it straight to the wire layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PowerAction(str, Enum):
    """Supported power actions. Values are stable wire-format strings."""

    LOCK = "lock"
    SLEEP = "sleep"
    SHUTDOWN = "shutdown"


@dataclass(frozen=True)
class AudioLevel:
    """Master audio volume, 0..100 inclusive."""

    percent: int

    def __post_init__(self) -> None:
        if not 0 <= self.percent <= 100:
            raise ValueError(f"Audio level must be 0..100, got {self.percent}")


@dataclass(frozen=True)
class BatteryStatus:
    """Battery snapshot. `percent` is None for desktops without a battery."""

    percent: Optional[float]
    plugged: Optional[bool]


@dataclass(frozen=True)
class SystemSnapshot:
    """Aggregate system status returned by `GET /status`."""

    os: str
    os_release: str
    hostname: str
    volume: AudioLevel
    battery: BatteryStatus
