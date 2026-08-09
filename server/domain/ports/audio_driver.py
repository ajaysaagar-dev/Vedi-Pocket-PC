"""Audio port — abstracts the master volume control."""

from __future__ import annotations

from abc import ABC, abstractmethod

from server.domain.entities.system_status import AudioLevel


class AudioDriver(ABC):
    """Reads and writes the master audio level.

    Returns `AudioLevel` (a validated dataclass) so the domain layer
    never sees raw ints. Methods should be idempotent and safe to call
    concurrently from different threads (the concrete pycaw driver
    re-initialises COM on each call, which is documented and required).
    """

    @abstractmethod
    def get_volume(self) -> AudioLevel: ...

    @abstractmethod
    def set_volume(self, level: AudioLevel) -> bool: ...
