"""Win32PowerDriver — Windows lock / sleep / shutdown."""

from __future__ import annotations

import os
import sys

from agent_core.entities.system_status import PowerAction
from agent_core.ports.power_driver import PowerDriver


_IS_WINDOWS = sys.platform == "win32"


class Win32PowerDriver(PowerDriver):
    """Maps PowerAction → the matching Win32 / shell call."""

    def execute(self, action: PowerAction) -> bool:
        if not _IS_WINDOWS:
            print("[POWER] Power actions are only supported on Windows.")
            return False

        try:
            if action == PowerAction.LOCK:
                import ctypes

                ctypes.windll.user32.LockWorkStation()
                return True
            if action == PowerAction.SLEEP:
                import ctypes

                # SetSuspendState(hibernate, force, disable_wake_events)
                ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)
                return True
            if action == PowerAction.SHUTDOWN:
                # 5-second delay so a mobile client has time to show
                # a "shutting down" toast before the screen goes dark.
                os.system("shutdown /s /t 5")
                return True
            return False
        except Exception as exc:  # noqa: BLE001
            print(f"[POWER] {action.value} failed: {exc}")
            return False
