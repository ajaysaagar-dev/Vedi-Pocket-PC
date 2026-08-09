"""dispatch.py — wire format → use case.

Maps every JSON message type the mobile app sends (over the existing
WebSocket protocol) to a `ControlInput.execute(...)` call. The shape
of these messages is preserved byte-for-byte from the previous
`ws_handler.py` so the mobile app keeps working unchanged.
"""

from __future__ import annotations

from typing import Callable, Dict

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
from server.application.services.control_input import ControlInput, InputResult


# Type alias for a handler: takes the parsed JSON dict, returns either
# None (fire-and-forget) or a dict to send back to the client.
Handler = Callable[[dict, ControlInput], dict | None]


def _mouse_move(msg: dict, ctrl: ControlInput) -> dict | None:
    dx = float(msg.get("dx", 0))
    dy = float(msg.get("dy", 0))
    sensitivity = float(msg.get("sensitivity", 1.0))
    ctrl.execute(RelativeMove(dx=dx * sensitivity, dy=dy * sensitivity))
    return None


def _mouse_click(msg: dict, ctrl: ControlInput) -> dict | None:
    button = msg.get("button", "left")
    clicks = int(msg.get("clicks", 1))
    btn = Button(button if button in {"left", "right", "middle"} else "left")
    x = msg.get("x")
    y = msg.get("y")
    ctrl.execute(ClickCommand(
        button=btn,
        clicks=clicks,
        x=int(x) if x is not None else None,
        y=int(y) if y is not None else None,
    ))
    return None


def _mouse_scroll(msg: dict, ctrl: ControlInput) -> dict | None:
    dy = float(msg.get("dy", 0))
    ctrl.execute(ScrollCommand(dy=dy))
    return None


def _keyboard_type(msg: dict, ctrl: ControlInput) -> dict | None:
    text = msg.get("text", "")
    ctrl.execute(TextInputCommand(text=text))
    return None


def _key_press(msg: dict, ctrl: ControlInput) -> dict | None:
    key = msg.get("key", "")
    if not key:
        return None
    ctrl.execute(KeyPressCommand(key=key))
    return None


def _hotkey(msg: dict, ctrl: ControlInput) -> dict | None:
    keys = msg.get("keys", [])
    if not keys:
        return None
    ctrl.execute(HotkeyCommand(keys=list(keys)))
    return None


def _ping(_msg: dict, _ctrl: ControlInput) -> dict:
    return {"type": "pong"}


def _auth_ok(_msg: dict, _ctrl: ControlInput) -> dict:
    return {"type": "auth_result", "status": "success"}


def _media_playpause(_msg: dict, ctrl: ControlInput) -> dict | None:
    ctrl.execute(KeyPressCommand(key="playpause"))
    return None


def _media_next(_msg: dict, ctrl: ControlInput) -> dict | None:
    ctrl.execute(KeyPressCommand(key="nexttrack"))
    return None


def _media_prev(_msg: dict, ctrl: ControlInput) -> dict | None:
    ctrl.execute(KeyPressCommand(key="prevtrack"))
    return None


def _volume_up(_msg: dict, ctrl: ControlInput) -> dict | None:
    ctrl.execute(KeyPressCommand(key="volumeup"))
    return None


def _volume_down(_msg: dict, ctrl: ControlInput) -> dict | None:
    ctrl.execute(KeyPressCommand(key="volumedown"))
    return None


def _volume_mute(_msg: dict, ctrl: ControlInput) -> dict | None:
    ctrl.execute(KeyPressCommand(key="volumemute"))
    return None


# Public dispatch table — wire type → handler.
DISPATCH: Dict[str, Handler] = {
    "mouse_move": _mouse_move,
    "mouse_click": _mouse_click,
    "mouse_scroll": _mouse_scroll,
    "keyboard_type": _keyboard_type,
    "key_press": _key_press,
    "hotkey": _hotkey,
    "ping": _ping,
    "auth": _auth_ok,
    "media_playpause": _media_playpause,
    "media_next": _media_next,
    "media_prev": _media_prev,
    "volume_up": _volume_up,
    "volume_down": _volume_down,
    "volume_mute": _volume_mute,
}


def dispatch(message: dict, control_input: ControlInput) -> dict | None:
    """Look up the handler for `message["type"]` and invoke it."""
    msg_type = message.get("type")
    handler = DISPATCH.get(msg_type)
    if handler is None:
        return {"type": "error", "message": f"Unknown event type: {msg_type}"}
    return handler(message, control_input)
