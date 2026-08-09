"""PyCawAudioDriver — Windows master-volume control via pycaw.

The pycaw API uses COM, and COM requires every thread to call
`CoInitialize()` before first use. FastAPI dispatches request
handlers across a thread pool, so we re-initialise on each call
(this is documented as safe: CoInitialize returns S_FALSE on the
second call, which means "already initialised" and is benign).
"""

from __future__ import annotations

import sys

from server.domain.entities.system_status import AudioLevel
from server.domain.ports.audio_driver import AudioDriver


_IS_WINDOWS = sys.platform == "win32"


class PyCawAudioDriver(AudioDriver):
    """pycaw-backed AudioDriver. Non-Windows hosts return a safe default."""

    def __init__(self, fallback_percent: int = 50) -> None:
        if not _IS_WINDOWS:
            print(
                "[AUDIO] Volume control is only implemented for Windows in this version."
            )
        self._fallback = fallback_percent

    # ----- helpers -----
    @staticmethod
    def _co_initialize() -> None:
        if not _IS_WINDOWS:
            return
        try:
            import ctypes

            ctypes.windll.ole32.CoInitialize(None)
        except Exception:
            # S_FALSE or any benign outcome — ignore.
            pass

    @staticmethod
    def _endpoint():
        """Return an activated IAudioEndpointVolume, or None on failure."""
        if not _IS_WINDOWS:
            return None
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            return cast(interface, POINTER(IAudioEndpointVolume))
        except Exception as exc:  # noqa: BLE001 — pycaw + COM raises many shapes
            print(f"[AUDIO] Failed to acquire endpoint: {exc}")
            return None

    # ----- AudioDriver protocol -----
    def get_volume(self) -> AudioLevel:
        if not _IS_WINDOWS:
            return AudioLevel(percent=self._fallback)
        self._co_initialize()
        ep = self._endpoint()
        if ep is None:
            return AudioLevel(percent=self._fallback)
        try:
            level = int(round(ep.GetMasterVolumeLevelScalar() * 100))
            return AudioLevel(percent=max(0, min(100, level)))
        except Exception as exc:  # noqa: BLE001
            print(f"[AUDIO] get_volume failed: {exc}")
            return AudioLevel(percent=self._fallback)

    def set_volume(self, level: AudioLevel) -> bool:
        if not _IS_WINDOWS:
            return False
        self._co_initialize()
        ep = self._endpoint()
        if ep is None:
            return False
        try:
            ep.SetMasterVolumeLevelScalar(level.percent / 100.0, None)
            return True
        except Exception as exc:  # noqa: BLE001
            print(f"[AUDIO] set_volume failed: {exc}")
            return False
