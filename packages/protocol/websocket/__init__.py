"""protocol.websocket — WebSocket layer for the PC Remote Agent.

The transport lives in `router.py`; the message-type ? use-case
mapping lives in `dispatch_table.py`.
"""

from protocol.websocket import dispatch_table, router

__all__ = ["dispatch_table", "router"]
