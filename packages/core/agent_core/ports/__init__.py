"""Ports — abstract interfaces the domain layer depends on.

These are the *boundaries* of the hexagonal architecture. Domain code
talks to ports; adapters implement them. There are no imports of
pyautogui / pycaw / pywin32 / zeroconf anywhere in this package.
"""

from agent_core.ports.audio_driver import AudioDriver
from agent_core.ports.input_driver import InputDriver
from agent_core.ports.power_driver import PowerDriver
from agent_core.ports.token_store import TokenStore

__all__ = [
    "AudioDriver",
    "InputDriver",
    "PowerDriver",
    "TokenStore",
]
