"""Container — hand-rolled DI container for the unified Vedi Pocket PC server.

Wires adapters to application services and holds singletons for FastAPI and WebSockets.
"""

from __future__ import annotations

import socket
import time
from typing import Optional

from server.config import Settings
from server.domain.entities.pairing import PairingPin, generate_pairing_pin
from server.application.services.control_input import ControlInput
from server.application.services.control_system import ControlSystem
from server.application.services.pairing import PairDevice
from server.application.services.screen_capture import ScreenCaptureService
from server.infrastructure.adapters.memory_token_store import MemoryTokenStore
from server.infrastructure.adapters.pyautogui_input import PyAutoGUIInputDriver
from server.infrastructure.adapters.pycaw_audio import PyCawAudioDriver
from server.infrastructure.adapters.win32_power import Win32PowerDriver
from server.infrastructure.adapters.mss_screen_capturer import MSSScreenCapturer
from server.infrastructure.discovery.mdns import ServiceAdvertiser, get_local_ip


class Container:
    """Wires infrastructure adapters to application services."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()

        # Infrastructure Adapters
        self.input_driver = PyAutoGUIInputDriver()
        self.audio_driver = PyCawAudioDriver()
        self.power_driver = Win32PowerDriver()
        self.token_store = MemoryTokenStore(persistence_file=self.settings.paired_ips_file)
        self.capturer = MSSScreenCapturer()

        # Application Services
        self.control_input = ControlInput(self.input_driver)

        def _battery():
            try:
                import psutil
                b = psutil.sensors_battery()
                if not b:
                    return ControlSystem.make_battery(percent=None, plugged=None)
                return ControlSystem.make_battery(percent=b.percent, plugged=b.power_plugged)
            except Exception:
                return ControlSystem.make_battery(percent=None, plugged=None)

        self.control_system = ControlSystem(
            audio=self.audio_driver,
            power=self.power_driver,
            hostname_provider=lambda: socket.gethostname(),
            os_provider=lambda: __import__("platform").system(),
            os_release_provider=lambda: __import__("platform").release(),
            battery_provider=_battery,
        )

        self.pairing_pin = PairingPin(value=generate_pairing_pin())
        self.pair_device = PairDevice(self.pairing_pin, self.token_store)

        self.screen_capture = ScreenCaptureService(
            capturer=self.capturer,
            max_width=self.settings.stream_max_width,
            max_height=self.settings.stream_max_height,
            fps=self.settings.stream_fps,
            jpeg_quality=self.settings.stream_jpeg_quality,
            monitor_index=self.settings.stream_monitor_index,
        )

        # Discovery & Network Metadata
        self.advertiser: Optional[ServiceAdvertiser] = None
        self.local_ip: str = get_local_ip()
        self.port: int = self.settings.port
        self.started_at: float = time.time()
