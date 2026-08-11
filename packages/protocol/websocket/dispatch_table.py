"""dispatch_table.py — wire format → use case.

Maps every JSON message type the mobile app sends (over the existing
WebSocket protocol) to a `ControlInput.execute(...)` call. The shape
of these messages is preserved byte-for-byte from the previous
`ws_handler.py` so the mobile app keeps working unchanged.
"""

from __future__ import annotations

from typing import Callable, Dict

from agent_core.entities.input_command import (
    AbsoluteMove,
    Button,
    ClickCommand,
    HotkeyCommand,
    KeyPressCommand,
    RelativeMove,
    ScrollCommand,
    TextInputCommand,
)
from agent_core.use_cases.control_input import ControlInput, InputResult


# Type alias for a handler: takes the parsed JSON dict, returns either
# None (fire-and-forget) or a dict to send back to the client.
Handler = Callable[[dict, ControlInput], dict | None]


def _mouse_move(msg: dict, ctrl: ControlInput) -> dict | None:
    dx = float(msg.get("dx", 0))
    dy = float(msg.get("dy", 0))
    sensitivity = float(msg.get("sensitivity", 1.0))
    print(f"[WS] mouse_move dx={dx:.1f} dy={dy:.1f} sens={sensitivity}")
    ctrl.execute(RelativeMove(dx=dx * sensitivity, dy=dy * sensitivity))
    return None


def _mouse_click(msg: dict, ctrl: ControlInput) -> dict | None:
    button = msg.get("button", "left")
    clicks = int(msg.get("clicks", 1))
    print(f"[WS] mouse_click button={button} clicks={clicks}")
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
    print(f"[WS] mouse_scroll dy={dy}")
    ctrl.execute(ScrollCommand(dy=dy))
    return None


def _keyboard_type(msg: dict, ctrl: ControlInput) -> dict | None:
    text = msg.get("text", "")
    print(f"[WS] keyboard_type text={text!r}")
    ctrl.execute(TextInputCommand(text=text))
    return None


def _key_press(msg: dict, ctrl: ControlInput) -> dict | None:
    key = msg.get("key", "")
    if not key:
        return None
    print(f"[WS] key_press key={key}")
    ctrl.execute(KeyPressCommand(key=key))
    return None


def _hotkey(msg: dict, ctrl: ControlInput) -> dict | None:
    keys = msg.get("keys", [])
    if not keys:
        return None
    print(f"[WS] hotkey keys={keys}")
    ctrl.execute(HotkeyCommand(keys=list(keys)))
    return None


def _ping(_msg: dict, _ctrl: ControlInput) -> dict:
    return {"type": "pong"}


def _auth_ok(_msg: dict, _ctrl: ControlInput) -> dict:
    return {"type": "auth_result", "status": "success"}


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
}


def dispatch(message: dict, control_input: ControlInput) -> dict | None:
    """Look up the handler for `message["type"]` and invoke it.

    Unknown types return an error envelope to the client. This used to
    live inline in the WebSocket loop; pulling it into a table keeps
    the loop trivially auditable.
    """
    msg_type = message.get("type")
    handler = DISPATCH.get(msg_type)
    if handler is None:
        return {"type": "error", "message": f"Unknown event type: {msg_type}"}
    return handler(message, control_input)
