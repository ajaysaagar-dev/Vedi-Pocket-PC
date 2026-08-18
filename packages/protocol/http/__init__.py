"""HTTP routers. Each `build_router(container)` returns an APIRouter
populated with the routes for its concern."""

from . import media_router, system_router

__all__ = ["media_router", "system_router"]
