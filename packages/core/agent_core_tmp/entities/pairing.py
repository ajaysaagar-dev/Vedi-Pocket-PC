"""Pairing-related entities.

The pairing flow is unchanged from the previous monolithic server: the
mobile client scans the QR code printed by the agent (`ip:port:pin`),
POSTs the PIN to `/pair`, and receives a long-lived session token. We
just moved the value objects here so both the control agent and the
screen-stream-server can share them.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from typing import Optional


# 4-digit PIN. Zero-padded so '0042' is distinct from '42'.
_PIN_FORMAT = "{:04d}"


def generate_pairing_pin() -> str:
    """Generate a fresh 4-digit numeric PIN.

    Identical behaviour to the old `state.pairing_pin` initialiser —
    the auth flow the mobile app already speaks is preserved verbatim.
    """
    return _PIN_FORMAT.format(secrets.randbelow(10_000))


def generate_session_token() -> str:
    """Generate a fresh session token (64 hex chars).

    Matches the old `state.generate_token()` length so any clients that
    cached a token-format assumption still work.
    """
    return secrets.token_hex(32)


@dataclass(frozen=True)
class PairingPin:
    """A validated 4-digit pairing PIN."""

    value: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"\d{4}", self.value):
            raise ValueError(f"Pairing PIN must be 4 digits, got {self.value!r}")


@dataclass(frozen=True)
class SessionToken:
    """An opaque session token returned to a paired device."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) < 16:
            raise ValueError("Session token must be at least 16 characters.")


@dataclass(frozen=True)
class PairResult:
    """Result of a pairing attempt.

    `device_token` is None when the attempt failed. `reason` is a short,
    human-readable explanation suitable for inclusion in an HTTP error
    body without leaking sensitive details.
    """

    accepted: bool
    device_token: Optional[SessionToken] = None
    reason: Optional[str] = None
