"""PyCawAudioDriver — Windows master-volume control via pycaw.

The pycaw API uses COM, and COM requires every thread to call
`CoInitialize()` before first use. FastAPI dispatches request
handlers across a thread pool, so we re-initialise on each call
(this is documented as safe: CoInitialize returns S_FALSE on the
second call, which means "already initialised" and is benign).
"""

from __future__ import annotations

import sys

from agent_core.entities.system_status import AudioLevel
from agent_core.ports.audio_driver import AudioDriver


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
        """Return an activated IAudioEndpointVolume, or None on failure.

        Supports every variant of pycaw shipped in the last few years:

          1. Modern pycaw (>= 20240205): `AudioUtilities.GetSpeakers()`
             returns an `AudioDevice` whose `EndpointVolume` is a
             `@property` that internally does `self._dev.Activate(...)`
             and caches the result. Reading the property is what gives
             you the activated interface.
          2. Older pycaw: `AudioDevice` exposes an `Activate(iid, ctx, None)`
             method that returns the COM interface pointer.
          3. Oldest pycaw (and many tutorials on the web): `AudioDevice`
             exposes the raw COM IMMDevice as `_dev`, and you have to
             call `_dev.Activate(...)` yourself.

        All three paths converge on the same `IAudioEndpointVolume`
        pointer; we try them in order from "cleanest API" to
        "lowest-level escape hatch" and return the first one that works.
        Without this layered lookup the backend spams
        `'AudioDevice' object has no attribute 'Activate'` on every
        volume command.
        """
        if not _IS_WINDOWS:
            return None
        try:
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            speakers = AudioUtilities.GetSpeakers()
            if speakers is None:
                print("[AUDIO] No default speaker endpoint found.")
                return None

            # ----- 1) modern pycaw: AudioDevice.EndpointVolume (property) -----
            #
            # `getattr(speakers, "EndpointVolume", None)` returns the
            # property descriptor object itself (not its value) — which
            # is truthy even on devices where the COM Activate call
            # would fail. We have to *evaluate* the property to know
            # whether it actually works.
            has_endpoint_volume_attr = isinstance(
                getattr(type(speakers), "EndpointVolume", None), property
            ) or hasattr(speakers, "EndpointVolume")

            if has_endpoint_volume_attr:
                try:
                    ep = speakers.EndpointVolume
                    if ep is not None:
                        return ep
                except Exception as prop_exc:
                    print(f"[AUDIO] EndpointVolume property raised: {prop_exc}")

            # ----- 2) mid-era pycaw: AudioDevice.Activate(iid, ctx, None) -----
            activate = getattr(speakers, "Activate", None)
            if callable(activate):
                try:
                    from ctypes import cast, POINTER

                    interface = activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    if interface is not None:
                        return cast(interface, POINTER(IAudioEndpointVolume))
                except Exception as act_exc:
                    print(f"[AUDIO] AudioDevice.Activate raised: {act_exc}")

            # ----- 3) lowest-level: speakers._dev.Activate(...) -----
            #
            # Some tutorials and older pycaw forks expose the underlying
            # IMMDevice COM pointer as `_dev`. If that's present we can
            # always Activate from there — it's the same call the
            # `EndpointVolume` property makes internally.
            dev = getattr(speakers, "_dev", None)
            dev_activate = getattr(dev, "Activate", None) if dev is not None else None
            if callable(dev_activate):
                try:
                    from ctypes import cast, POINTER

                    interface = dev_activate(
                        IAudioEndpointVolume._iid_, CLSCTX_ALL, None
                    )
                    if interface is not None:
                        return cast(interface, POINTER(IAudioEndpointVolume))
                except Exception as dev_exc:
                    print(f"[AUDIO] speakers._dev.Activate raised: {dev_exc}")

            print(
                "[AUDIO] pycaw speaker object has no usable COM entry point "
                "(no EndpointVolume, no Activate, no _dev.Activate)."
            )
            return None
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
