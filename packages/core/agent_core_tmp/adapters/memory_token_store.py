"""MemoryTokenStore — in-process token registry.

Mirrors the behaviour of the old `state.active_tokens` set:
issue() generates a fresh token, verify() checks membership,
revoke() removes it. Lives entirely in RAM; restarts wipe all sessions.
"""

from __future__ import annotations

import threading
from typing import Set

from agent_core.entities.pairing import SessionToken, generate_session_token
from agent_core.ports.token_store import TokenStore


class MemoryTokenStore(TokenStore):
    """Thread-safe set-backed token store."""

    def __init__(self) -> None:
        self._tokens: Set[str] = set()
        self._lock = threading.Lock()

    def issue(self) -> SessionToken:
        token = SessionToken(value=generate_session_token())
        with self._lock:
            self._tokens.add(token.value)
        return token

    def verify(self, token: SessionToken) -> bool:
        with self._lock:
            return token.value in self._tokens

    def revoke(self, token: SessionToken) -> None:
        with self._lock:
            self._tokens.discard(token.value)
