"""Token store port — abstracts the auth token registry.

Concrete implementations: `MemoryTokenStore` (in-process set, fine for a
single-process agent), and (in tests) any fake that satisfies this ABC.
The token store is *only* used by the pairing use case and by the
HTTP / WS auth dependencies — domain code never queries it directly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agent_core.entities.pairing import SessionToken


class TokenStore(ABC):
    """Issue and verify opaque session tokens."""

    @abstractmethod
    def issue(self, client_ip: str | None = None) -> SessionToken: ...

    @abstractmethod
    def verify(self, token: SessionToken, client_ip: str | None = None) -> bool: ...

    @abstractmethod
    def revoke(self, token: SessionToken) -> None: ...

    @abstractmethod
    def register_ip(self, ip: str) -> None: ...
