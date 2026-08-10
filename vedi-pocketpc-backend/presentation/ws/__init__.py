"""WebSocket layer. The transport lives in `router.py`; the
message-type → use-case mapping lives in `dispatch_table.py`."""

from presentation.ws import dispatch_table, router

__all__ = ["dispatch_table", "router"]
