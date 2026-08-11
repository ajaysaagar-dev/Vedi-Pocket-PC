"""Domain — port for screen capture. Wraps the existing MSS-based
implementation behind a stable interface so tests can swap a fake."""

from domain.capture import ScreenCapturer

__all__ = ["ScreenCapturer"]
