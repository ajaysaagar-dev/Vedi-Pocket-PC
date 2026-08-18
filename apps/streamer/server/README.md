# PC Screen Stream & Remote Control Server

A high-performance, lightweight local screen streaming and remote control server written in Python. It captures your PC's desktop screen in real-time, encodes frames directly to binary JPEG images, and streams them over a WebSocket connection. Simultaneously, it receives JSON control messages from mobile devices to control the Windows mouse cursor with zero latency.

---

## What's new in this refactor

This server used to carry its **own** copy of the mouse / keyboard /
volume code. Now it shares one `ControlInput` use case with the
`vedi-pocketpc-backend` agent via the `agent_core` package:

- **No more duplicate driver code.** The `mouse/mouse_controller.py`
  file is gone; input goes through
  `agent_core.adapters.PyAutoGUIInputDriver`.
- **Auth hole closed.** Every WebSocket connection must now present a
  verified token from the shared `MemoryTokenStore` (via `?token=...`
  on the URL or an `auth` message). Previously any device on the LAN
  could issue clicks.

```
screen-stream-server/
├── main.py               composition root
├── domain/
│   └── capture.py        ScreenCapturer (MSS-backed)
├── presentation/
│   └── ws_router.py      StreamManager (auth + dispatch + frames)
└── config.py
```

---

## Features

- **Real-Time Screen Streaming**: High performance using `mss` for fast screen capture.
- **Remote Mouse Control**: Real-time trackpad movement, left/right clicks, double clicks, mouse down/up dragging, and vertical wheel scrolling via PyAutoGUI.
- **Bi-Directional Single WebSocket**:
  - `PC -> Mobile`: Binary JPEG screen frames.
  - `Mobile -> PC`: JSON control messages.
- **Authenticated**: A valid session token (issued via `POST /pair`)
  is required before any control message is processed.
- **Configurable Control**: Adjust mouse sensitivity, scroll sensitivity, target FPS, max resolution, and JPEG quality.
- **Non-Blocking Architecture**: Separate execution loops ensure screen capture and incoming control messages run independently with zero lag.
- **Zero Cloud / Offline**: Works entirely over local Wi-Fi / LAN with no external dependencies or cloud services required.

---

## Requirements

- **Python**: Python 3.11+
- **OS**: Windows 10/11

---

## Quick Start

### 1. Create Virtual Environment & Install Dependencies

```bash
# Shared domain package (required)
pip install -e ../../packages/core

# This server's deps
pip install -r requirements.txt
```

### 2. Run the Server

```bash
python main.py
```

Console Output Example:

```text
========================================
 PC Screen Stream & Remote Server
========================================
 Local:
   http://127.0.0.1:8080

 LAN:
   http://192.168.1.10:8080

 WebSocket:
   ws://192.168.1.10:8080/ws

 Resolution: 1280x720
 FPS:        30
 JPEG:       70
========================================

Waiting for mobile connection...
```

---

## WebSocket Communication Protocol

### Mobile → PC: Auth

Before any control messages are processed, the client must present a
session token. Either:

```
ws://<PC_LAN_IP>:8080/ws?token=<TOKEN>
```

or send a single JSON frame immediately after connecting:

```json
{ "type": "auth", "token": "<TOKEN>" }
```

A token can be obtained from `POST /pair`.

### PC → Mobile (Screen Streaming)
Sends raw binary JPEG image frames directly.

### Mobile → PC (Remote Mouse & Control Commands)

All control messages sent from mobile to PC are JSON text messages over the same WebSocket URL (`ws://<PC_LAN_IP>:8080/ws`).

#### 1. Mouse Movement (Relative)
```json
{
  "type": "mouse_move",
  "dx": 12,
  "dy": -5
}
```
* `dx`: Horizontal relative movement (positive = right, negative = left).
* `dy`: Vertical relative movement (positive = down, negative = up).

#### 2. Mouse Click
```json
{
  "type": "mouse_click",
  "button": "left"
}
```
* `button`: `"left"`, `"right"`, or `"middle"`.

#### 3. Mouse Double Click
```json
{
  "type": "mouse_double_click",
  "button": "left"
}
```

#### 4. Mouse Button Down & Up (Drag Operations)
```json
{
  "type": "mouse_down",
  "button": "left"
}
```
```json
{
  "type": "mouse_up",
  "button": "left"
}
```

#### 5. Scroll Wheel
```json
{
  "type": "scroll",
  "dx": 0,
  "dy": -5
}
```
* `dy`: Scroll amount (positive = scroll up, negative = scroll down).

---

## Configuration Options

Configuration options can be modified in `config.py` or overridden via environment variables:

| Setting | Default | Description | Environment Variable |
| :--- | :--- | :--- | :--- |
| `HOST` | `"0.0.0.0"` | Server listening interface | `STREAM_HOST` |
| `PORT` | `"8080"` | Server TCP port | `STREAM_PORT` |
| `FPS` | `30` | Target frames per second | `STREAM_FPS` |
| `JPEG_QUALITY` | `70` | JPEG compression quality (1-100) | `STREAM_JPEG_QUALITY` |
| `MAX_WIDTH` | `1280` | Maximum capture output width | `STREAM_MAX_WIDTH` |
| `MAX_HEIGHT` | `720` | Maximum capture output height | `STREAM_MAX_HEIGHT` |
| `MONITOR_INDEX` | `1` | Target monitor index (`1` = Primary) | `STREAM_MONITOR_INDEX` |

---

## Windows Firewall Configuration

If incoming connections are blocked on port 8080, run PowerShell as Administrator:

```powershell
New-NetFirewallRule -DisplayName "PC Screen Stream Server (Port 8080)" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow -Profile Private,Domain
```
