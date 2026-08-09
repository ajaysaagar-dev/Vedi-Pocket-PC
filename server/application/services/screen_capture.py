"""ScreenCaptureService — manages the capture loop and frame broadcasting."""

from __future__ import annotations

import asyncio
from typing import Set, Tuple, List

from server.application.dto.stream_dto import StreamSettingsUpdate


class ScreenCaptureService:
    """Manages the screen capture loop and broadcasting frames to subscribers."""

    def __init__(
        self, 
        capturer, 
        max_width: int, 
        max_height: int, 
        fps: int, 
        jpeg_quality: int, 
        monitor_index: int = 1
    ) -> None:
        self._capturer = capturer
        self.max_width = max_width
        self.max_height = max_height
        self.target_fps = fps
        self.jpeg_quality = jpeg_quality
        self.monitor_index = monitor_index
        
        self._queues: Set[asyncio.Queue] = set()

    def update_settings(self, settings: StreamSettingsUpdate) -> None:
        if settings.max_width is not None:
            self.max_width = settings.max_width
        if settings.max_height is not None:
            self.max_height = settings.max_height
        if settings.fps is not None:
            self.target_fps = settings.fps
        if settings.jpeg_quality is not None:
            self.jpeg_quality = settings.jpeg_quality

    @property
    def client_count(self) -> int:
        return len(self._queues)
        
    @property
    def last_resolution(self) -> Tuple[int, int]:
        return self._capturer.last_resolution

    def get_monitors(self) -> List[dict]:
        return self._capturer.get_monitors()

    async def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._queues.discard(queue)

    async def broadcast_frame(self, jpeg_bytes: bytes) -> None:
        if not self._queues:
            return
        for queue in list(self._queues):
            if queue.full():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                queue.put_nowait(jpeg_bytes)
            except asyncio.QueueFull:
                pass

    async def capture_loop(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            t0 = loop.time()
            interval = 1.0 / max(1, self.target_fps)

            try:
                jpeg_bytes, _res = await asyncio.to_thread(
                    self._capturer.capture_frame,
                    self.monitor_index,
                    self.max_width,
                    self.max_height,
                    self.jpeg_quality,
                )

                if self.client_count > 0:
                    await self.broadcast_frame(jpeg_bytes)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ERROR] Capture loop exception: {e}", flush=True)

            elapsed = loop.time() - t0
            sleep_time = max(0.001, interval - elapsed)
            await asyncio.sleep(sleep_time)
