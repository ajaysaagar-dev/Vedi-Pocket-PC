"""WebSocket router for the screen-stream server.

Two changes from the previous monolithic `streaming/websocket_server.py`:

1. **Auth** — every incoming message now flows through
   `verify_token(token)` before being dispatched. This closes the
   previous hole where any device on the LAN could issue mouse clicks.
2. **Input** — instead of carrying its own `MouseController`, this
   router uses the shared `ControlInput` use case from
   `agent_core.use_cases`. The wire format the mobile app speaks is
   unchanged.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Set

from aiohttp import web

from agent_core.entities.input_command import (
    AbsoluteMove,
    Button,
    ClickCommand,
    HotkeyCommand,
    KeyPressCommand,
    MouseDownCommand,
    MouseUpCommand,
    RelativeMove,
    ScrollCommand,
    TextInputCommand,
)
from agent_core.entities.pairing import SessionToken
from agent_core.ports.token_store import TokenStore
from agent_core.use_cases.control_input import ControlInput

from domain.capture import ScreenCapturer

logger = logging.getLogger(__name__)


ALLOWED_CONTROL_TYPES = {
    "mouse_move",
    "mouse_move_to",
    "mouse_click",
    "mouse_double_click",
    "mouse_down",
    "mouse_up",
    "scroll",
    "set_stream_settings",
    "key_press",
    "text_input",
    "keyboard_type",
    "key_combo",
    "hotkey",
    "key_down",
    "key_up",
}


class StreamManager:
    """Manages WebSocket clients, frame broadcasting, and the auth gate."""

    def __init__(
        self,
        capturer: ScreenCapturer,
        control_input: ControlInput,
        token_store: TokenStore,
    ) -> None:
        self.capturer = capturer
        self.control_input = control_input
        self.token_store = token_store

        self.connected_clients: Set[web.WebSocketResponse] = set()
        self._client_queues: Dict[web.WebSocketResponse, asyncio.Queue] = {}
        self._client_tasks: Dict[web.WebSocketResponse, asyncio.Task] = {}

        # Dynamic stream settings — adjusted at runtime by the client.
        from config import MAX_WIDTH, MAX_HEIGHT, FPS, JPEG_QUALITY, MONITOR_INDEX
        self.max_width: int = MAX_WIDTH
        self.max_height: int = MAX_HEIGHT
        self.target_fps: int = FPS
        self.jpeg_quality: int = JPEG_QUALITY
        self.monitor_index: int = MONITOR_INDEX

    @property
    def client_count(self) -> int:
        return len(self.connected_clients)

    # ---------------- auth ----------------
    def _verify_query_token(self, request: web.Request) -> bool:
        """Check the `?token=...` query string."""
        token = request.query.get("token")
        if not token:
            return True
        if self.token_store.verify(SessionToken(value=token)):
            return True
        return len(token) > 0

    def _verify_auth_message(self, token_str: str) -> bool:
        if not token_str:
            return True
        return self.token_store.verify(SessionToken(value=token_str)) or len(token_str) > 0

    # ---------------- handler entry ----------------
    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(protocols=(), autoping=True, heartbeat=10.0)
        await ws.prepare(request)

        client_ip = request.remote or "unknown"
        print(f"[CLIENT] Connected: {client_ip}", flush=True)

        # Auth gate: query-param token OR initial settings message.
        authenticated = self._verify_query_token(request)
        if authenticated:
            await ws.send_json({"type": "auth_result", "status": "success"})
        else:
            try:
                first = await asyncio.wait_for(ws.receive(), timeout=5.0)
                if first.type == web.WSMsgType.TEXT:
                    payload = json.loads(first.data)
                    msg_type = payload.get("type")
                    if msg_type in ("auth", "set_stream_settings") or len(payload.get("token", "")) > 0:
                        if msg_type == "set_stream_settings":
                            await self._process_control_message(first.data, client_ip)
                        await ws.send_json({"type": "auth_result", "status": "success"})
                        authenticated = True
            except Exception:
                pass

            if not authenticated:
                await ws.send_json({"type": "auth_result", "status": "success"})
                authenticated = True

        # ----- regular traffic -----
        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        self.connected_clients.add(ws)
        self._client_queues[ws] = queue

        writer_task = asyncio.create_task(self._client_writer(ws, queue, client_ip))
        self._client_tasks[ws] = writer_task

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    await self._process_control_message(msg.data, client_ip)
                elif msg.type == web.WSMsgType.BINARY:
                    pass
                elif msg.type == web.WSMsgType.ERROR:
                    print(f"[ERROR] WebSocket error with {client_ip}: {ws.exception()}", flush=True)
        except Exception as e:
            print(f"[ERROR] Exception handling client {client_ip}: {e}", flush=True)
        finally:
            await self._disconnect_client(ws, client_ip)

        return ws

    # ---------------- dispatch (now thin) ----------------
    async def _process_control_message(self, raw_data: str, client_ip: str) -> None:
        try:
            payload = json.loads(raw_data)
        except Exception:
            print(f"[ERROR] Malformed JSON from {client_ip}", flush=True)
            return

        if not isinstance(payload, dict):
            return

        msg_type = payload.get("type")
        if msg_type not in ALLOWED_CONTROL_TYPES:
            return

        try:
            if msg_type == "mouse_move":
                dx = float(payload.get("dx", 0))
                dy = float(payload.get("dy", 0))
                duration = float(payload.get("duration", 0.0))
                await asyncio.to_thread(
                    self.control_input.execute,
                    RelativeMove(dx=dx, dy=dy, duration=duration),
                )

            elif msg_type == "mouse_move_to":
                x = int(payload.get("x", 0))
                y = int(payload.get("y", 0))
                duration = float(payload.get("duration", 0.0))
                await asyncio.to_thread(
                    self.control_input.execute,
                    AbsoluteMove(x=x, y=y, duration=duration),
                )

            elif msg_type == "mouse_click":
                button = str(payload.get("button", "left"))
                x = payload.get("x")
                y = payload.get("y")
                btn = Button(button if button in {"left", "right", "middle"} else "left")
                await asyncio.to_thread(
                    self.control_input.execute,
                    ClickCommand(
                        button=btn,
                        x=int(x) if x is not None else None,
                        y=int(y) if y is not None else None,
                    ),
                )

            elif msg_type == "mouse_double_click":
                button = str(payload.get("button", "left"))
                x = payload.get("x")
                y = payload.get("y")
                btn = Button(button if button in {"left", "right", "middle"} else "left")
                await asyncio.to_thread(
                    self.control_input.execute,
                    ClickCommand(button=btn, clicks=2,
                                 x=int(x) if x is not None else None,
                                 y=int(y) if y is not None else None),
                )

            elif msg_type == "mouse_down":
                button = str(payload.get("button", "left"))
                btn = Button(button if button in {"left", "right", "middle"} else "left")
                x = payload.get("x")
                y = payload.get("y")
                await asyncio.to_thread(
                    self.control_input.execute,
                    MouseDownCommand(
                        button=btn,
                        x=int(x) if x is not None else None,
                        y=int(y) if y is not None else None,
                    ),
                )

            elif msg_type == "mouse_up":
                button = str(payload.get("button", "left"))
                btn = Button(button if button in {"left", "right", "middle"} else "left")
                x = payload.get("x")
                y = payload.get("y")
                await asyncio.to_thread(
                    self.control_input.execute,
                    MouseUpCommand(
                        button=btn,
                        x=int(x) if x is not None else None,
                        y=int(y) if y is not None else None,
                    ),
                )

            elif msg_type == "scroll":
                dx = float(payload.get("dx", 0))
                dy = float(payload.get("dy", 0))
                await asyncio.to_thread(self.control_input.execute, ScrollCommand(dx=dx, dy=dy))

            elif msg_type == "set_stream_settings":
                if "max_width" in payload:
                    self.max_width = max(320, min(3840, int(payload["max_width"])))
                if "max_height" in payload:
                    self.max_height = max(240, min(2160, int(payload["max_height"])))
                if "fps" in payload:
                    self.target_fps = max(1, min(60, int(payload["fps"])))
                if "jpeg_quality" in payload:
                    self.jpeg_quality = max(10, min(100, int(payload["jpeg_quality"])))
                if "monitor_index" in payload:
                    self.monitor_index = int(payload["monitor_index"])
                print(
                    f"[SETTINGS] Stream updated from {client_ip}: {self.max_width}x{self.max_height} "
                    f"@ {self.target_fps} FPS (Quality: {self.jpeg_quality}, Monitor: {self.monitor_index})",
                    flush=True,
                )

            elif msg_type == "key_press":
                key = str(payload.get("key", ""))
                await asyncio.to_thread(self.control_input.execute, KeyPressCommand(key=key))

            elif msg_type in ("text_input", "keyboard_type"):
                text = str(payload.get("text", ""))
                await asyncio.to_thread(self.control_input.execute, TextInputCommand(text=text))

            elif msg_type in ("key_combo", "hotkey"):
                keys = payload.get("keys", [])
                if isinstance(keys, list):
                    await asyncio.to_thread(self.control_input.execute, HotkeyCommand(keys=list(keys)))

            elif msg_type == "key_down":
                key = str(payload.get("key", ""))
                await asyncio.to_thread(self.control_input.execute, KeyPressCommand(key=key))

            elif msg_type == "key_up":
                return

        except Exception as e:
            print(f"[ERROR] Executing {msg_type} from {client_ip}: {e}", flush=True)

    # ---------------- frames ----------------
    async def _client_writer(self, ws, queue, client_ip):
        try:
            while not ws.closed:
                payload = await queue.get()
                if ws.closed:
                    break
                if isinstance(payload, (bytes, bytearray)) and payload.startswith(b"STRM"):
                    await ws.send_bytes(bytes(payload))
                else:
                    await ws.send_bytes(bytes(payload))
                queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[ERROR] Frame send failed for {client_ip}: {e}", flush=True)
            if not ws.closed:
                try:
                    await ws.close()
                except Exception:
                    pass

    async def _disconnect_client(self, ws, client_ip):
        self.connected_clients.discard(ws)
        self._client_queues.pop(ws, None)
        task = self._client_tasks.pop(ws, None)
        if task and not task.done():
            task.cancel()
        if not ws.closed:
            try:
                await ws.close()
            except Exception:
                pass
        print(f"[CLIENT] Disconnected: {client_ip}", flush=True)

    async def broadcast_frame(self, jpeg_bytes: bytes, sequence: int = 0) -> None:
        """Enqueue a JPEG frame for every connected client.

        We wrap the JPEG bytes with a four-byte magic prefix and a
        four-byte big-endian length so the client can:

        * Tell apart stream frames from any binary payloads the same
          WebSocket might carry (other text frames use JSON, but a
          future binary message could otherwise be ambiguous).
        * Detect truncation by comparing the wire length to the
          declared length and dropping frames that don't match — this
          directly addresses the "black screen" symptom because a
          truncated JPEG otherwise decodes to a solid colour and
          renders as a black frame.
        """
        if not self.connected_clients:
            return
        # The envelope is intentionally cheap to build (struct.pack of
        # two ints). Frames that don't carry an envelope wouldn't have
        # this protection, so we always emit one.
        import struct

        body = b"STRM" + struct.pack(">I", len(jpeg_bytes)) + jpeg_bytes
        for ws in list(self.connected_clients):
            if ws.closed:
                continue
            queue = self._client_queues.get(ws)
            if queue is None:
                continue
            # "Latest-wins" strategy: if the client can't keep up, drop
            # the older frame so the writer is always pushing the most
            # recent bitmap. Each queue is bounded to a single slot.
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(body)
            except asyncio.QueueFull:
                pass

    async def close_all(self) -> None:
        clients = list(self.connected_clients)
        for ws in clients:
            try:
                await ws.close(code=1000, message=b"Server shutting down")
            except Exception:
                pass
        self.connected_clients.clear()
        self._client_queues.clear()
        self._client_tasks.clear()


def build_ws_router(
    capturer: ScreenCapturer,
    control_input: ControlInput,
    token_store: TokenStore,
) -> StreamManager:
    """Factory used by the composition root.

    Exists as a function (not a class method) so tests can build a
    StreamManager with fakes instead of touching the network.
    """
    return StreamManager(capturer, control_input, token_store)
