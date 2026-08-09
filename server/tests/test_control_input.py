"""test_control_input.py — unit test against fake driver."""

from __future__ import annotations

from typing import List

import pytest

from server.domain.entities.input_command import (
    AbsoluteMove,
    Button,
    ClickCommand,
    HotkeyCommand,
    KeyPressCommand,
    RelativeMove,
    ScrollCommand,
    TextInputCommand,
)
from server.domain.ports.input_driver import InputDriver
from server.application.services.control_input import ControlInput


class FakeInputDriver(InputDriver):
    """Records every call so tests can assert on the captured log."""

    def __init__(self) -> None:
        self.log: List[tuple] = []
        self.attached = 0

    def attach_to_active_desktop(self) -> None:
        self.attached += 1

    def move_to(self, cmd): self.log.append(("move_to", cmd.x, cmd.y))
    def move_relative(self, cmd): self.log.append(("move_relative", cmd.dx, cmd.dy))
    def click(self, cmd): self.log.append(("click", cmd.button, cmd.clicks, cmd.x, cmd.y))
    def scroll(self, cmd): self.log.append(("scroll", cmd.dx, cmd.dy))
    def type_text(self, cmd): self.log.append(("type_text", cmd.text))
    def press_key(self, cmd): self.log.append(("press_key", cmd.key))
    def hotkey(self, cmd): self.log.append(("hotkey", tuple(cmd.keys)))


@pytest.fixture
def driver() -> FakeInputDriver:
    return FakeInputDriver()


@pytest.fixture
def controller(driver: FakeInputDriver) -> ControlInput:
    return ControlInput(driver)


def test_attach_is_called_before_each_action(controller, driver):
    controller.execute(AbsoluteMove(x=10, y=20))
    controller.execute(RelativeMove(dx=1, dy=2))
    assert driver.attached == 2


def test_absolute_move(controller, driver):
    controller.execute(AbsoluteMove(x=100, y=200, duration=0.05))
    assert driver.log == [("move_to", 100, 200)]


def test_relative_move(controller, driver):
    controller.execute(RelativeMove(dx=3.7, dy=-1.2))
    assert driver.log == [("move_relative", 3.7, -1.2)]


def test_click_default_left(controller, driver):
    controller.execute(ClickCommand())
    assert driver.log == [("click", Button.LEFT, 1, None, None)]


def test_click_with_coords(controller, driver):
    controller.execute(ClickCommand(button=Button.RIGHT, clicks=2, x=5, y=6))
    assert driver.log == [("click", Button.RIGHT, 2, 5, 6)]


def test_scroll(controller, driver):
    controller.execute(ScrollCommand(dx=0.0, dy=4.0))
    assert driver.log == [("scroll", 0.0, 4.0)]


def test_type_text(controller, driver):
    controller.execute(TextInputCommand(text="hello"))
    assert driver.log == [("type_text", "hello")]


def test_press_key(controller, driver):
    controller.execute(KeyPressCommand(key="enter"))
    assert driver.log == [("press_key", "enter")]


def test_hotkey(controller, driver):
    controller.execute(HotkeyCommand(keys=["ctrl", "c"]))
    assert driver.log == [("hotkey", ("ctrl", "c"))]


def test_driver_exception_is_swallowed(controller, driver):
    def boom(_cmd): raise RuntimeError("synthetic")
    driver.move_to = boom  # type: ignore[assignment]

    result = controller.execute(AbsoluteMove(x=1, y=2))
    assert result.ok is False
    assert "RuntimeError" in (result.error or "")
