"""ControlSystem — power, volume, and snapshot use cases."""

from __future__ import annotations

from typing import Optional

from server.domain.entities.system_status import (
    AudioLevel,
    BatteryStatus,
    PowerAction,
    SystemSnapshot,
)
from server.domain.ports.audio_driver import AudioDriver
from server.domain.ports.power_driver import PowerDriver


class ControlSystem:
    """Owns everything that isn't direct input: volume, power, snapshot."""

    def __init__(
        self,
        audio: AudioDriver,
        power: PowerDriver,
        hostname_provider,
        os_provider,
        os_release_provider,
        battery_provider,
    ) -> None:
        self._audio = audio
        self._power = power
        self._hostname = hostname_provider
        self._os = os_provider
        self._os_release = os_release_provider
        self._battery = battery_provider

    # ----- volume -----
    def get_volume(self) -> AudioLevel:
        return self._audio.get_volume()

    def set_volume(self, level: int) -> Optional[AudioLevel]:
        """Sets volume to a 0..100 value; returns the new level if the
        driver succeeded, or None if the request was rejected."""
        clamped = max(0, min(100, int(level)))
        ok = self._audio.set_volume(AudioLevel(percent=clamped))
        return AudioLevel(percent=clamped) if ok else None

    # ----- power -----
    def lock(self) -> bool:
        return self._power.execute(PowerAction.LOCK)

    def sleep(self) -> bool:
        return self._power.execute(PowerAction.SLEEP)

    def shutdown(self) -> bool:
        return self._power.execute(PowerAction.SHUTDOWN)

    # ----- snapshot -----
    def snapshot(self) -> SystemSnapshot:
        return SystemSnapshot(
            os=self._os(),
            os_release=self._os_release(),
            hostname=self._hostname(),
            volume=self._audio.get_volume(),
            battery=self._battery(),
        )

    # Convenience to assemble a BatteryStatus (caller provides the raw values).
    @staticmethod
    def make_battery(percent, plugged) -> BatteryStatus:
        return BatteryStatus(percent=percent, plugged=plugged)
