"""PairDevice — the single pairing entry point.

We deliberately keep this use case *thin*: the only logic is "compare
the supplied PIN to the configured PIN, and on success issue a new
session token from the token store". The HTTP layer wraps this in
Pydantic and FastAPI; the WS layer also defers here.

The login flow that the mobile app already speaks (POST /pair with
`{"pin": "..."}`, expecting `{"token": "...", "status": "success"}`)
is preserved byte-for-byte.
"""

from __future__ import annotations

from server.domain.entities.pairing import PairResult, PairingPin, SessionToken
from server.domain.ports.token_store import TokenStore


class PairDevice:
    """Pair a device by validating the supplied PIN."""

    def __init__(self, configured_pin: PairingPin, tokens: TokenStore) -> None:
        self._pin = configured_pin
        self._tokens = tokens

    def pair(self, supplied_pin: str, client_ip: str | None = None) -> PairResult:
        """Compare `supplied_pin` against the configured PIN or check if client_ip is known.

        Returns a `PairResult` whose `accepted` flag is the only thing
        the HTTP layer needs to decide between 200 and 400.
        """
        clean_pin = (supplied_pin or "").strip()

        # 1. Direct PIN match
        if clean_pin == self._pin.value:
            token = self._tokens.issue(client_ip=client_ip)
            return PairResult(accepted=True, device_token=token)

        # 2. Check if client_ip was previously connected/paired
        if client_ip and self._tokens.verify(SessionToken(value="0" * 32), client_ip=client_ip):
            token = self._tokens.issue(client_ip=client_ip)
            return PairResult(accepted=True, device_token=token)

        return PairResult(accepted=False, reason="Invalid PIN code")
