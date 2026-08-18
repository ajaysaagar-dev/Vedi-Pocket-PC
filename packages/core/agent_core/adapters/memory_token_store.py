"""MemoryTokenStore — in-process token registry.

Mirrors the behaviour of the old `state.active_tokens` set:
issue() generates a fresh token, verify() checks membership,
revoke() removes it. Lives entirely in RAM; restarts wipe per-session
tokens.

In addition, this store now also mints a stable "common" token
(`common_token()`) that survives restarts when a `persist_path` is
provided. The common token lets the mobile app re-connect to the
same PC without re-entering the PIN, as long as the file still
exists on disk.
"""

from __future__ import annotations

import os
import threading
from typing import Optional, Set

from agent_core.entities.pairing import SessionToken, generate_session_token
from agent_core.ports.token_store import TokenStore


class MemoryTokenStore(TokenStore):
    """Thread-safe set-backed token store with optional common-token persistence."""

    def __init__(self, persist_path: Optional[str] = None) -> None:
        self._tokens: Set[str] = set()
        self._lock = threading.Lock()
        # Common ("easy-connect") token state. The token is loaded from
        # `persist_path` at construction time if that file exists, and
        # written back whenever it is first issued or rotated. This is
        # what lets the mobile app skip the PIN step on subsequent
        # re-connects.
        self._persist_path: Optional[str] = persist_path
        self._common: Optional[str] = None
        if persist_path and os.path.isfile(persist_path):
            try:
                with open(persist_path, "r", encoding="utf-8") as fh:
                    persisted = fh.read().strip()
                    if len(persisted) >= 16:
                        self._common = persisted
                        self._tokens.add(persisted)
            except OSError:
                # Corrupt / unreadable file is non-fatal — we'll just
                # mint a fresh token the first time `common_token()`
                # is called.
                pass

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
            # If the operator explicitly revokes the common token, drop
            # the persisted copy too so the next start mints a new one.
            if token.value == self._common:
                self._common = None
                self._delete_persisted()

    def common_token(self) -> Optional[SessionToken]:
        """Return the stable common token, minting+persisting on first use."""
        with self._lock:
            if self._common is None:
                self._common = generate_session_token()
                self._tokens.add(self._common)
                self._persist_common()
            return SessionToken(value=self._common)

    # ------------------------------------------------------------------
    # Disk-backed helpers — best-effort. Failures are non-fatal because
    # the in-memory fallback still works for the current process.
    # ------------------------------------------------------------------
    def _persist_common(self) -> None:
        if not self._persist_path or not self._common:
            return
        try:
            os.makedirs(os.path.dirname(self._persist_path) or ".", exist_ok=True)
            with open(self._persist_path, "w", encoding="utf-8") as fh:
                fh.write(self._common)
        except OSError:
            pass

    def _delete_persisted(self) -> None:
        if not self._persist_path:
            return
        try:
            if os.path.isfile(self._persist_path):
                os.remove(self._persist_path)
        except OSError:
            pass
