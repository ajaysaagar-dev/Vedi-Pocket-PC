"""MemoryTokenStore — in-process token registry.

Mirrors the behaviour of the old `state.active_tokens` set:
issue() generates a fresh token, verify() checks membership,
revoke() removes it. Lives entirely in RAM; restarts wipe all sessions.
"""

from __future__ import annotations

import json
import os
import threading
from typing import Set

from server.domain.entities.pairing import SessionToken, generate_session_token
from server.domain.ports.token_store import TokenStore


def is_lan_ip(ip: str | None) -> bool:
    if not ip:
        return True
    if ip in ("127.0.0.1", "localhost", "::1"):
        return True
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    try:
        a, b = int(parts[0]), int(parts[1])
        if a == 10: return True
        if a == 172 and 16 <= b <= 31: return True
        if a == 192 and b == 168: return True
    except ValueError:
        pass
    return False


class MemoryTokenStore(TokenStore):
    """Thread-safe set-backed token store with persistent IP authorization."""

    def __init__(self, persistence_file: str | None = None) -> None:
        self._tokens: Set[str] = set()
        self._ips: Set[str] = set()
        self._lock = threading.Lock()
        self._persistence_file = persistence_file or os.path.join(
            os.path.expanduser("~"), ".vedi_paired_ips.json"
        )
        self._load_persisted_ips()

    def _load_persisted_ips(self) -> None:
        try:
            if os.path.exists(self._persistence_file):
                with open(self._persistence_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._ips.update(data)
        except Exception as e:
            print(f"[AUTH] Could not load persisted IP registry: {e}")

    def _save_persisted_ips(self) -> None:
        try:
            with open(self._persistence_file, "w", encoding="utf-8") as f:
                json.dump(list(self._ips), f)
        except Exception as e:
            print(f"[AUTH] Could not save persisted IP registry: {e}")

    def register_ip(self, ip: str) -> None:
        if not ip or ip in ("127.0.0.1", "localhost", "unknown", "::1"):
            return
        with self._lock:
            if ip not in self._ips:
                self._ips.add(ip)
                self._save_persisted_ips()

    def issue(self, client_ip: str | None = None) -> SessionToken:
        token = SessionToken(value=generate_session_token())
        with self._lock:
            self._tokens.add(token.value)
            if client_ip:
                self.register_ip(client_ip)
        return token

    def verify(self, token: SessionToken, client_ip: str | None = None) -> bool:
        with self._lock:
            # 1. Direct token match
            if token and token.value in self._tokens:
                if client_ip:
                    self.register_ip(client_ip)
                return True

            # 2. Check if client IP address was previously connected/paired or on LAN
            if client_ip and (client_ip in self._ips or is_lan_ip(client_ip)):
                self.register_ip(client_ip)
                return True

            return False

    def revoke(self, token: SessionToken) -> None:
        with self._lock:
            self._tokens.discard(token.value)
