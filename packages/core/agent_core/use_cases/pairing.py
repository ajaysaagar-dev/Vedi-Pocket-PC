"""PairDevice — the single pairing entry point.

We deliberately keep this use case *thin*: the only logic is "compare
the supplied PIN to the configured PIN, and on success issue a new
session token from the token store". The HTTP layer wraps this in
Pydantic and FastAPI; the WS layer also defers here.

The login flow that the mobile app already speaks (POST /pair with
`{"pin": "..."}`, expecting `{"token": "...", "status": "success"}`)
is preserved byte-for-byte.

Starting with the "common token" change we ALSO fetch the optional
common token from the store (which the mobile app caches to make
subsequent reconnects PIN-less). If the store doesn't expose a
common token, we just leave it `None` in the result — nothing in the
existing flow depends on it.
"""

from __future__ import annotations

from agent_core.entities.pairing import PairResult, PairingPin, SessionToken
from agent_core.ports.token_store import TokenStore


class PairDevice:
    """Pair a device by validating the supplied PIN."""

    def __init__(self, configured_pin: PairingPin, tokens: TokenStore) -> None:
        self._pin = configured_pin
        self._tokens = tokens

    def pair(self, supplied_pin: str) -> PairResult:
        """Compare `supplied_pin` against the configured PIN.

        Returns a `PairResult` whose `accepted` flag is the only thing
        the HTTP layer needs to decide between 200 and 400.
        """
        if supplied_pin != self._pin.value:
            return PairResult(accepted=False, reason="Invalid PIN code")
        token = self._tokens.issue()
        # NEW: best-effort common-token lookup. `common_token()` may
        # legitimately return None on stores that don't implement it,
        # so we tolerate both cases here without changing the rest of
        # the response shape.
        common = self._tokens.common_token()
        return PairResult(
            accepted=True,
            device_token=token,
            common_token=common if isinstance(common, SessionToken) else None,
        )
