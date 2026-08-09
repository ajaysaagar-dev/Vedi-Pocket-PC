"""Ports — abstract interfaces the domain layer depends on.

These are the *boundaries* of the hexagonal architecture. Domain code
talks to ports; adapters implement them. There are no imports of
pyautogui / pycaw / pywin32 / zeroconf anywhere in this package.
"""
from __future__ import annotations


from server.domain.ports.audio_driver import AudioDriver
from server.domain.ports.input_driver import InputDriver
from server.domain.ports.power_driver import PowerDriver
from server.domain.ports.token_store import TokenStore

__all__ = [
    "AudioDriver",
    "InputDriver",
    "PowerDriver",
    "TokenStore",
]
