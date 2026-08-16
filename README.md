# 🖥️ Vedi Pocket PC

Turn your phone into a wireless trackpad, keyboard, and screen for your PC — no cloud, no cables, no internet required. Vedi Pocket PC streams your desktop to your phone and sends mouse, keyboard, media, and power commands back, all over your local Wi-Fi.

The project has three parts that work together, plus a desktop app that launches and manages all of them for you:

| Component | Folder | Stack | Role |
|---|---|---|---|
| **Desktop Controller** | root (`main.js`, `index.html`, …) | Electron | Launches/monitors the two Python services and the mobile dev server, shows a pairing QR code |
| **Screen Stream Server** | [`screen-stream-server/`](./screen-stream-server) | Python (aiohttp, mss, PyAutoGUI) | Captures the desktop and streams JPEG frames over WebSocket; relays trackpad move/click/scroll events |
| **Remote Agent (Backend)** | [`vedi-pocketpc-backend/`](./vedi-pocketpc-backend) | Python (FastAPI, WebSockets) | Handles pairing (PIN/QR), keyboard input, media keys, volume, and power actions (lock/sleep/shutdown); advertises itself via mDNS |
| **Mobile App** | [`veddi-pocketpc/`](./veddi-pocketpc) | Expo / React Native / TypeScript | The phone client: scan to pair, then use trackpad, keyboard, screen-view, and controls tabs |

---

## How it works

```
┌─────────────────────────────┐
│   VediPocketPC Controller    │  Electron desktop app
│   (main.js)                  │  spawns & monitors ↓
└──────┬───────────┬───────────┘
       │           │
       ▼           ▼
┌─────────────┐ ┌───────────────────┐
│ screen-      │ │ vedi-pocketpc-    │
│ stream-      │ │ backend (FastAPI) │
│ server       │ │ port 8000         │
│ port 8080    │ │                   │
│              │ │ pairing / QR /    │
│ screen frames│ │ keyboard / media /│
│ + trackpad   │ │ volume / power /  │
│ over WS      │ │ mDNS discovery    │
└──────┬───────┘ └─────────┬─────────┘
       │                   │
       └─────────┬─────────┘
                  │ same LAN / Wi-Fi
                  ▼
     ┌─────────────────────────┐
     │  Vedi Pocket PC mobile   │  Expo / React Native
     │  app (phone)             │  Screen • Trackpad •
     │                          │  Keyboard • Controls tabs
     └─────────────────────────┘
```

1. The **Electron app** boots up, detects your LAN IP, and starts the two Python services as child processes.
2. The **screen-stream-server** grabs the desktop with `mss`, encodes it as JPEG, and streams frames to the phone over a WebSocket (port `8080`), while also listening for trackpad move/click/scroll JSON messages on the same socket.
3. The **backend agent** advertises itself on the LAN via mDNS (`_pcremote._tcp.local.`), generates a pairing PIN/QR code, and exposes REST + WebSocket endpoints (port `8000`) for keyboard input, media transport, volume, and power controls.
4. The **mobile app** scans the QR code (or falls back to mDNS discovery / manual PIN entry) to pair, then talks to both services to mirror the screen and forward gestures, keystrokes, and commands back to the PC.

---

## Getting started

### Prerequisites

- **Windows 10/11** (the agent uses Windows-specific APIs — `pycaw`, `taskkill`, etc.)
- **Node.js** 18+ and npm
- **Python** 3.10+ (3.11+ recommended)
- A phone and PC on the **same Wi-Fi network**
- [Expo Go](https://expo.dev/go) installed on the phone (for development) — a packaged build isn't required if you just want to try it via Expo

### Option A — Run everything via the desktop app (recommended)

```bash
# From the repo root
npm install
npm start
```

This launches the Electron controller, which spawns the screen-stream server, the FastAPI backend, and the Expo dev server for you, and shows a QR code to scan from the mobile app.

### Option B — Run each service manually

**1. Screen Stream Server**
```bash
cd screen-stream-server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python server.py
```
Runs at `http://<LAN_IP>:8080`, WebSocket at `ws://<LAN_IP>:8080/ws`.

**2. Remote Agent (Backend)**
```bash
cd vedi-pocketpc-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
Runs at `http://<LAN_IP>:8000`. Prints a pairing PIN and QR code to the terminal.

**3. Mobile App**
```bash
cd veddi-pocketpc
npm install
npx expo start
```
Scan the Expo QR code with the Expo Go app, then pair with the PC from within the app.

See each subfolder's README for full details:
- [`screen-stream-server/README.md`](./screen-stream-server/README.md)
- [`vedi-pocketpc-backend/README.md`](./vedi-pocketpc-backend/README.md)
- [`veddi-pocketpc/README.md`](./veddi-pocketpc/README.md)

---

## Features

- **📷 QR code pairing** with mDNS auto-discovery and manual PIN fallback
- **🖥️ Live screen mirroring** — low-latency JPEG streaming over WebSocket, configurable FPS/resolution/quality
- **🖱️ Trackpad mode** — relative mouse movement, left/right/double click, drag (mouse down/up), scroll
- **⌨️ Remote keyboard** — soft keyboard forwarding plus a quick shortcut bar (Ctrl+C, Ctrl+V, Alt+Tab, Win, Esc, Task Manager)
- **🔊 Media & volume controls** — play/pause/next/prev, system volume via `pycaw`
- **⚡ Power management** — lock, sleep, shutdown
- **📊 Status dashboard** — host info, connection latency, battery/memory stats
- **🔒 Local-only / offline** — everything runs over LAN; no cloud services or internet dependency

---

## Building a distributable

The Electron app is configured with `electron-builder` to produce a Windows installer that bundles the Python services and mobile project as extra resources:

```bash
npm run build   # NSIS installer + zip
npm run pack    # Unpacked directory build, for testing
```

The Python backend agent can also be frozen into a standalone `.exe` (no Python install required on the target machine):

```bash
cd vedi-pocketpc-backend
build_agent.bat
# Output: dist/PCRemoteAgent.exe
```

---

## Firewall

If the phone can't reach the PC, allow the ports through Windows Firewall (run PowerShell as Administrator):

```powershell
New-NetFirewallRule -DisplayName "Vedi Pocket PC - Screen Stream (8080)" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow -Profile Private,Domain
New-NetFirewallRule -DisplayName "Vedi Pocket PC - Backend Agent (8000)" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private,Domain
```

---

## Repository structure

```
Vedi-Pocket-PC/
├── main.js, preload.js, renderer.js   # Electron desktop controller
├── index.html, styles.css             # Controller UI
├── package.json                       # Electron app + electron-builder config
├── screen-stream-server/              # Python: screen capture & trackpad relay (port 8080)
│   ├── capture/  mouse/  streaming/
│   ├── config.py, server.py
│   └── requirements.txt
├── vedi-pocketpc-backend/             # Python: FastAPI remote agent (port 8000)
│   ├── routes/ (pairing, system, media)
│   ├── discovery.py, ws_handler.py, input_control.py, state.py
│   ├── main.py
│   └── requirements.txt
└── veddi-pocketpc/                    # Expo / React Native mobile client
    ├── app/(tabs)/ (index, screen, trackpad, keyboard, controls)
    ├── app/pairing.tsx
    ├── components/, hooks/, constants/
    └── package.json
```

---

## Tech stack

- **Desktop:** Electron, Node.js, `qrcode`, `electron-builder`
- **Screen streaming:** Python, `aiohttp`, `mss`, `PyAutoGUI`, `Pillow`
- **Remote agent:** Python, FastAPI, `uvicorn`, `websockets`, `zeroconf`, `pycaw`, `pystray`, `psutil`, `cryptography`
- **Mobile:** Expo (React Native), TypeScript, Expo Router

---

## License

MIT (see `package.json`).
