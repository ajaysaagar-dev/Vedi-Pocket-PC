"""protocol.http — FastAPI HTTP routers for the PC Remote Agent.

Each module exposes a `build_router(container)` function that returns
an `APIRouter` populated with routes for its concern.
"""

from protocol.http import media_router, pairing_router, system_router

__all__ = ["media_router", "pairing_router", "system_router"]
