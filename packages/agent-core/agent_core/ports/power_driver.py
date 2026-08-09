"""Power port — abstracts lock / sleep / shutdown."""

from __future__ import annotations

from abc import ABC, abstractmethod

from agent_core.entities.system_status import PowerAction


class PowerDriver(ABC):
    """Invokes a power action. Returns True on success."""

    @abstractmethod
    def execute(self, action: PowerAction) -> bool: ...
