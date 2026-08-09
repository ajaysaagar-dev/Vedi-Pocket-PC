"""Abstract screen capture port."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

class ScreenCapturer(ABC):
    @abstractmethod
    def capture_frame(self, monitor_index: int = 1, max_width: int = 1280, max_height: int = 720, jpeg_quality: int = 70) -> Tuple[bytes, Tuple[int, int]]: ...
    @abstractmethod
    def get_monitors(self) -> List[Dict[str, Any]]: ...
    @property
    @abstractmethod
    def last_resolution(self) -> Tuple[int, int]: ...
