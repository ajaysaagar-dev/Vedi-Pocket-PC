"""WebSocket transport — accepts connections, runs the auth handshake,
and pipes messages through the dispatch table. All business logic is
in `dispatch_table.DISPATCH`; this file only handles protocol mechanics."""

from __future__ import annotations

import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from agent_core.entities.pairing import SessionToken

from protocol.websocket.dispatch_table import dispatch


def build_router(container) -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
        token: str | None = Query(default=None),
    ):
        await websocket.accept()
        authenticated = False

        # 1) Query-param auth (preferred path — saves a round-trip)
        if token and container.token_store.verify(SessionToken(value=token)):
            authenticated = True
            print("[WS] WebSocket client connected and authenticated via query parameter.")
        else:
            print("[WS] Client connected. Awaiting authentication message...")

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "message": "Invalid JSON format"})
                    continue

                # 2) Auth handshake (only needed if query-param auth failed)
                if not authenticated:
                    if message.get("type") == "auth":
                        auth_token = message.get("token")
                        if auth_token and container.token_store.verify(SessionToken(value=auth_token)):
                            authenticated = True
                            print("[WS] Client authenticated via auth message.")
                            await websocket.send_json({"type": "auth_result", "status": "success"})
                        else:
                            print(f"[WS] Client authentication failed with token: {auth_token}")
                            await websocket.send_json({"type": "auth_result", "status": "failed", "message": "Invalid token"})
                            await websocket.close(code=1008)
                            return
                    else:
                        await websocket.send_json({"type": "error", "message": "Authentication required"})
                        await websocket.close(code=1008)
                        return
                    continue

                # 3) Authenticated: dispatch through the table.
                response = dispatch(message, container.control_input)
                if response is not None:
                    await websocket.send_json(response)

        except WebSocketDisconnect:
            print("[WS] WebSocket client disconnected.")
        except Exception as exc:
            print(f"[WS] Error in WebSocket connection: {exc}")
            try:
                await websocket.close()
            except Exception:
                pass

    return router
