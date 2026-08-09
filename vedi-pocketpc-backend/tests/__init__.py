"""Tests for the backend's composition root.

We exercise `ControlInput` end-to-end against a `FakeInputDriver` so
the test asserts that the WS / HTTP layer is wired to the *shared*
use case (no more side-channel duplicates of the input code).
"""
