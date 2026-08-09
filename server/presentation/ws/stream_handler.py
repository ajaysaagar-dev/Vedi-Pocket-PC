"""WebSocket transport for screen stream."""

from __future__ import annotations

import asyncio
import json
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from server.domain.entities.pairing import SessionToken
from server.application.dto.stream_dto import StreamSettingsUpdate
from server.presentation.ws.dispatch import dispatch


def build_router(container) -> APIRouter:
    router = APIRouter()

    @router.websocket("/stream")
    async def stream_endpoint(
        websocket: WebSocket,
        token: str | None = Query(default=None),
    ):
        await websocket.accept()
        authenticated = False
        client_ip = websocket.client.host if websocket.client else None

        # 1) Auth
        token_str = token or ""
        if len(token_str) >= 16:
            try:
                authenticated = container.token_store.verify(SessionToken(value=token_str), client_ip=client_ip)
            except Exception:
                authenticated = False
        elif client_ip:
            try:
                authenticated = container.token_store.verify(SessionToken(value="0" * 32), client_ip=client_ip)
            except Exception:
                authenticated = False

        if authenticated:
            await websocket.send_json({"type": "auth_result", "status": "success"})
        else:
            try:
                # Wait for auth message within 5 seconds
                data = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                message = json.loads(data)
                if message.get("type") == "auth":
                    auth_token = message.get("token", "")
                    if len(auth_token) >= 16 and container.token_store.verify(SessionToken(value=auth_token), client_ip=client_ip):
                        authenticated = True
                        await websocket.send_json({"type": "auth_result", "status": "success"})
                    else:
                        await websocket.send_json({"type": "auth_result", "status": "failed", "message": "Invalid token"})
            except Exception:
                pass

        if not authenticated:
            await websocket.close(code=1008)
            return

        print(f"[STREAM] Client connected: {client_ip}", flush=True)
        queue = await container.screen_capture.subscribe()

        # Task to send frames
        async def send_frames():
            try:
                while True:
                    jpeg_bytes = await queue.get()
                    await websocket.send_bytes(jpeg_bytes)
                    queue.task_done()
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"[STREAM] Send failed: {e}")

        sender_task = asyncio.create_task(send_frames())

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    continue
                
                # Check for settings update
                if message.get("type") == "set_stream_settings":
                    settings = StreamSettingsUpdate(
                        max_width=message.get("max_width"),
                        max_height=message.get("max_height"),
                        fps=message.get("fps"),
                        jpeg_quality=message.get("jpeg_quality"),
                    )
                    container.screen_capture.update_settings(settings)
                else:
                    response = await asyncio.to_thread(dispatch, message, container.control_input)
                    if response is not None:
                        await websocket.send_json(response)

        except WebSocketDisconnect:
            print(f"[STREAM] Client disconnected: {client_ip}")
        except Exception as e:
            print(f"[STREAM] Error: {e}")
        finally:
            sender_task.cancel()
            container.screen_capture.unsubscribe(queue)
            try:
                await websocket.close()
            except Exception:
                pass

    return router
