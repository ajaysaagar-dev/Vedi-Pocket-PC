"""Token store port — abstracts the auth token registry.

Concrete implementations: `MemoryTokenStore` (in-process set, fine for a
single-process agent), and (in tests) any fake that satisfies this ABC.
The token store is *only* used by the pairing use case and by the
HTTP / WS auth dependencies — domain code never queries it directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from agent_core.entities.pairing import SessionToken


class TokenStore(ABC):
    """Issue and verify opaque session tokens."""

    @abstractmethod
    def issue(self) -> SessionToken: ...

    @abstractmethod
    def verify(self, token: SessionToken) -> bool: ...

    @abstractmethod
    def revoke(self, token: SessionToken) -> None: ...

    def common_token(self) -> Optional[SessionToken]:
        """Return the stable "easy-connect" token, issuing one on first
        use.

        Implementations may return `None` to indicate that common tokens
        are not supported. The base class provides that fallback so
        existing test doubles don't need to implement it just to keep
        importing.
        """
        return None
