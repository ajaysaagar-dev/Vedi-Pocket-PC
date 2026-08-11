"""Use cases — application-layer orchestration.

Each use case is a small class that owns one business action and
coordinates the ports it needs. They are framework-free (no FastAPI /
aiohttp imports), which keeps them trivially unit-testable with fake
adapters.
"""

from agent_core.use_cases.control_input import ControlInput
from agent_core.use_cases.control_system import ControlSystem
from agent_core.use_cases.pairing import PairDevice

__all__ = [
    "ControlInput",
    "ControlSystem",
    "PairDevice",
]
