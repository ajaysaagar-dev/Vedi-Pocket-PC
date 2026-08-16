import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from state import state
import input_control

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """
    WebSocket endpoint for sending high-frequency mouse, scroll, keyboard, and key events.
    Authenticates either via 'token' query param OR an initial 'auth' message.
    """
    await websocket.accept()
    authenticated = False

    # Check query param auth
    if token and state.verify_token(token):
        authenticated = True
        print("[WS] WebSocket client connected and authenticated via query parameter.")
    else:
        print("[WS] Client connected. Awaiting authentication message...")

    try:
        while True:
            # Receive text or JSON data
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format"})
                continue

            msg_type = message.get("type")

            # Check authentication state
            if not authenticated:
                if msg_type == "auth":
                    auth_token = message.get("token")
                    if auth_token and state.verify_token(auth_token):
                        authenticated = True
                        print("[WS] Client authenticated via auth message.")
                        await websocket.send_json({"type": "auth_result", "status": "success"})
                    else:
                        print(f"[WS] Client authentication failed with token: {auth_token}")
                        await websocket.send_json({"type": "auth_result", "status": "failed", "message": "Invalid token"})
                        await websocket.close(code=1008) # Policy Violation
                        return
                else:
                    await websocket.send_json({"type": "error", "message": "Authentication required"})
                    await websocket.close(code=1008)
                    return
                continue

            # Process control actions if authenticated
            if msg_type == "mouse_move":
                dx = float(message.get("dx", 0))
                dy = float(message.get("dy", 0))
                # Sensitivity scaler if requested by client, otherwise use directly
                sensitivity = float(message.get("sensitivity", 1.0))
                print(f"[WS] mouse_move dx={dx:.1f} dy={dy:.1f} sens={sensitivity}")
                input_control.move_mouse(dx * sensitivity, dy * sensitivity)

            elif msg_type == "mouse_click":
                button = message.get("button", "left")
                clicks = int(message.get("clicks", 1))
                print(f"[WS] mouse_click button={button} clicks={clicks}")
                input_control.click_mouse(button=button, clicks=clicks)

            elif msg_type == "mouse_scroll":
                dy = float(message.get("dy", 0))
                print(f"[WS] mouse_scroll dy={dy}")
                input_control.scroll_mouse(dy)

            elif msg_type == "keyboard_type":
                text = message.get("text", "")
                print(f"[WS] keyboard_type text={text!r}")
                input_control.type_text(text)

            elif msg_type == "key_press":
                key = message.get("key", "")
                if key:
                    print(f"[WS] key_press key={key}")
                    input_control.press_key(key)

            elif msg_type == "volume_set":
                level = int(message.get("level", 50))
                print(f"[WS] volume_set level={level}")
                input_control.set_volume(level)

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "auth":
                await websocket.send_json({"type": "auth_result", "status": "success"})

            elif msg_type == "hotkey":
                keys = message.get("keys", [])
                if keys and len(keys) > 0:
                    print(f"[WS] hotkey keys={keys}")
                    input_control.hotkey(keys)

            else:
                print(f"[WS] Unknown event type: {msg_type}")
                await websocket.send_json({"type": "error", "message": f"Unknown event type: {msg_type}"})

    except WebSocketDisconnect:
        print("[WS] WebSocket client disconnected.")
    except Exception as e:
        print(f"[WS] Error in WebSocket connection: {e}")
        try:
            await websocket.close()
        except Exception:
            pass
