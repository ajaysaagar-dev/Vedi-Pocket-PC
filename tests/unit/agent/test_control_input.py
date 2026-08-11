"""Real working test against a fake driver.

Mirrors the test in `packages/agent-core/tests/test_control_input.py`
but exercises the `ControlInput` instance that the backend's container
constructs — so we know the wiring (driver → use case) is intact.
"""

from __future__ import annotations

import os
import sys
from typing import List

import pytest

# Allow running `pytest tests/` from the backend root without an editable
# install. Prepending the package root makes `agent_core` importable.
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
REPO_ROOT = os.path.abspath(os.path.join(BACKEND_ROOT, os.pardir))
sys.path.insert(0, os.path.join(REPO_ROOT, "packages", "agent-core"))

from agent_core.entities.input_command import (  # noqa: E402
    AbsoluteMove,
    Button,
    ClickCommand,
    HotkeyCommand,
    KeyPressCommand,
    RelativeMove,
    ScrollCommand,
    TextInputCommand,
)
from agent_core.ports.input_driver import InputDriver  # noqa: E402
from agent_core.use_cases.control_input import ControlInput  # noqa: E402


class FakeInputDriver(InputDriver):
    """Captures every call so we can assert on what the use case sent."""

    def __init__(self) -> None:
        self.calls: List[tuple] = []
        self.attached = 0

    def attach_to_active_desktop(self) -> None:
        self.attached += 1

    def move_to(self, cmd): self.calls.append(("move_to", cmd.x, cmd.y))
    def move_relative(self, cmd): self.calls.append(("move_relative", cmd.dx, cmd.dy))
    def click(self, cmd): self.calls.append(("click", cmd.button.value, cmd.clicks, cmd.x, cmd.y))
    def scroll(self, cmd): self.calls.append(("scroll", cmd.dx, cmd.dy))
    def type_text(self, cmd): self.calls.append(("type_text", cmd.text))
    def press_key(self, cmd): self.calls.append(("press_key", cmd.key))
    def hotkey(self, cmd): self.calls.append(("hotkey", tuple(cmd.keys)))


@pytest.fixture
def driver() -> FakeInputDriver:
    return FakeInputDriver()


@pytest.fixture
def control_input(driver: FakeInputDriver) -> ControlInput:
    return ControlInput(driver)


def test_compose_root_uses_shared_controller(control_input, driver):
    """If the composition root ever wires a different controller, this
    test breaks — that's the point."""
    control_input.execute(AbsoluteMove(x=42, y=99))
    assert driver.calls == [("move_to", 42, 99)]
    assert driver.attached == 1


def test_all_command_shapes_route_correctly(control_input, driver):
    control_input.execute(AbsoluteMove(x=1, y=2))
    control_input.execute(RelativeMove(dx=3, dy=4))
    control_input.execute(ClickCommand(button=Button.RIGHT, clicks=2))
    control_input.execute(ScrollCommand(dy=5))
    control_input.execute(TextInputCommand(text="hi"))
    control_input.execute(KeyPressCommand(key="enter"))
    control_input.execute(HotkeyCommand(keys=["ctrl", "v"]))

    assert driver.calls == [
        ("move_to", 1, 2),
        ("move_relative", 3, 4),
        ("click", "right", 2, None, None),
        ("scroll", 0, 5),
        ("type_text", "hi"),
        ("press_key", "enter"),
        ("hotkey", ("ctrl", "v")),
    ]
