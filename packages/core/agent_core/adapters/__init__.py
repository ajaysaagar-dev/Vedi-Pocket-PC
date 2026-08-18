"""Adapters — concrete implementations of the ports.

This is the only layer allowed to import third-party libraries like
pyautogui, pycaw, pywin32, etc. Each adapter should be swappable by
the composition root without touching any other file.
"""

from agent_core.adapters.memory_token_store import MemoryTokenStore
from agent_core.adapters.pycaw_audio_driver import PyCawAudioDriver
from agent_core.adapters.pyautogui_input_driver import PyAutoGUIInputDriver
from agent_core.adapters.win32_desktop_access import ensure_windows_desktop_access
from agent_core.adapters.win32_power_driver import Win32PowerDriver

__all__ = [
    "MemoryTokenStore",
    "PyCawAudioDriver",
    "PyAutoGUIInputDriver",
    "Win32PowerDriver",
    "ensure_windows_desktop_access",
]
