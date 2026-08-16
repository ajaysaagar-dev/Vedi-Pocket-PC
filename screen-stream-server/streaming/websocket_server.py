import json
import asyncio
import logging
from typing import Set, Dict
from aiohttp import web

import config
from mouse import MouseController

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
    """Manages active WebSocket connections, frame broadcasting, and incoming remote control messages."""

    def __init__(self) -> None:
        self.connected_clients: Set[web.WebSocketResponse] = set()
        self._client_queues: Dict[web.WebSocketResponse, asyncio.Queue] = {}
        self._client_tasks: Dict[web.WebSocketResponse, asyncio.Task] = {}
        self.mouse_controller = MouseController()

        # Dynamic realtime stream configuration
        self.max_width: int = config.MAX_WIDTH
        self.max_height: int = config.MAX_HEIGHT
        self.target_fps: int = config.FPS
        self.jpeg_quality: int = config.JPEG_QUALITY

    @property
    def client_count(self) -> int:
        return len(self.connected_clients)

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """aiohttp route handler for /ws WebSocket endpoint (dual-purpose streaming & remote control)."""
        ws = web.WebSocketResponse(protocols=(), autoping=True, heartbeat=10.0)
        await ws.prepare(request)

        client_ip = request.remote or "unknown"
        print(f"[CLIENT] Connected: {client_ip}", flush=True)

        # Register client
        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        self.connected_clients.add(ws)
        self._client_queues[ws] = queue

        # Start frame writer task for this client
        writer_task = asyncio.create_task(self._client_writer(ws, queue, client_ip))
        self._client_tasks[ws] = writer_task

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    await self._process_control_message(msg.data, client_ip)
                elif msg.type == web.WSMsgType.BINARY:
                    # Ignore binary input from mobile
                    pass
                elif msg.type == web.WSMsgType.ERROR:
                    print(f"[ERROR] WebSocket error with {client_ip}: {ws.exception()}", flush=True)
        except Exception as e:
            print(f"[ERROR] Exception handling client {client_ip}: {e}", flush=True)
        finally:
            await self._disconnect_client(ws, client_ip)

        return ws

    async def _process_control_message(self, raw_data: str, client_ip: str) -> None:
        """Validates and executes incoming remote mouse/control messages immediately."""
        try:
            payload = json.loads(raw_data)
        except Exception:
            print(f"[ERROR] Malformed JSON from {client_ip}", flush=True)
            return

        if not isinstance(payload, dict):
            return

        msg_type = payload.get("type")
        if msg_type not in ALLOWED_CONTROL_TYPES:
            # Reject unauthorized or unapproved command execution attempts
            return

        try:
            if msg_type == "mouse_move":
                dx = float(payload.get("dx", 0))
                dy = float(payload.get("dy", 0))
                duration = float(payload.get("duration", 0.0))
                await asyncio.to_thread(self.mouse_controller.move_relative, dx, dy, duration)

            elif msg_type == "mouse_move_to":
                x = int(payload.get("x", 0))
                y = int(payload.get("y", 0))
                duration = float(payload.get("duration", 0.0))
                await asyncio.to_thread(self.mouse_controller.move_to, x, y, duration)

            elif msg_type == "mouse_click":
                button = str(payload.get("button", "left"))
                x = payload.get("x")
                y = payload.get("y")
                await asyncio.to_thread(self.mouse_controller.click, x, y, button)

            elif msg_type == "mouse_double_click":
                button = str(payload.get("button", "left"))
                x = payload.get("x")
                y = payload.get("y")
                await asyncio.to_thread(self.mouse_controller.double_click, x, y, button)

            elif msg_type == "mouse_down":
                button = str(payload.get("button", "left"))
                x = payload.get("x")
                y = payload.get("y")
                await asyncio.to_thread(self.mouse_controller.mouse_down, x, y, button)

            elif msg_type == "mouse_up":
                button = str(payload.get("button", "left"))
                x = payload.get("x")
                y = payload.get("y")
                await asyncio.to_thread(self.mouse_controller.mouse_up, x, y, button)

            elif msg_type == "scroll":
                dx = float(payload.get("dx", 0))
                dy = float(payload.get("dy", 0))
                await asyncio.to_thread(self.mouse_controller.scroll, dx, dy)

            elif msg_type == "set_stream_settings":
                if "max_width" in payload:
                    self.max_width = max(320, min(3840, int(payload["max_width"])))
                if "max_height" in payload:
                    self.max_height = max(240, min(2160, int(payload["max_height"])))
                if "fps" in payload:
                    self.target_fps = max(1, min(60, int(payload["fps"])))
                if "jpeg_quality" in payload:
                    self.jpeg_quality = max(10, min(100, int(payload["jpeg_quality"])))
                print(f"[SETTINGS] Stream updated from {client_ip}: {self.max_width}x{self.max_height} @ {self.target_fps} FPS (Quality: {self.jpeg_quality})", flush=True)

            elif msg_type == "key_press":
                key = str(payload.get("key", ""))
                await asyncio.to_thread(self.mouse_controller.key_press, key)

            elif msg_type in ("text_input", "keyboard_type"):
                text = str(payload.get("text", ""))
                await asyncio.to_thread(self.mouse_controller.text_input, text)

            elif msg_type in ("key_combo", "hotkey"):
                keys = payload.get("keys", [])
                if isinstance(keys, list):
                    await asyncio.to_thread(self.mouse_controller.key_combo, keys)

            elif msg_type == "key_down":
                key = str(payload.get("key", ""))
                await asyncio.to_thread(self.mouse_controller.key_down, key)

            elif msg_type == "key_up":
                key = str(payload.get("key", ""))
                await asyncio.to_thread(self.mouse_controller.key_up, key)

        except Exception as e:
            print(f"[ERROR] Executing {msg_type} from {client_ip}: {e}", flush=True)

    async def _client_writer(
        self,
        ws: web.WebSocketResponse,
        queue: asyncio.Queue,
        client_ip: str
    ) -> None:
        """Pulls JPEG frames from queue and sends binary payload to client."""
        try:
            while not ws.closed:
                jpeg_bytes = await queue.get()
                if ws.closed:
                    break
                await ws.send_bytes(jpeg_bytes)
                queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[ERROR] Frame send failed for {client_ip}: {e}", flush=True)

    async def _disconnect_client(self, ws: web.WebSocketResponse, client_ip: str) -> None:
        """Cleans up disconnected client resources."""
        if ws in self.connected_clients:
            self.connected_clients.remove(ws)

        if ws in self._client_queues:
            del self._client_queues[ws]

        task = self._client_tasks.pop(ws, None)
        if task and not task.done():
            task.cancel()

        if not ws.closed:
            await ws.close()

        print(f"[CLIENT] Disconnected: {client_ip}", flush=True)

    async def broadcast_frame(self, jpeg_bytes: bytes) -> None:
        """Broadcasts a JPEG frame to all connected clients without blocking capture loop."""
        if not self.connected_clients:
            return

        for ws in list(self.connected_clients):
            if ws.closed:
                continue

            queue = self._client_queues.get(ws)
            if queue is not None:
                if queue.full():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass

                try:
                    queue.put_nowait(jpeg_bytes)
                except asyncio.QueueFull:
                    pass

    async def close_all(self) -> None:
        """Gracefully closes all WebSocket connections."""
        clients = list(self.connected_clients)
        for ws in clients:
            try:
                await ws.close(code=1000, message=b"Server shutting down")
            except Exception:
                pass
        self.connected_clients.clear()
        self._client_queues.clear()
        self._client_tasks.clear()
