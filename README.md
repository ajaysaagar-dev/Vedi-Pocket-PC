<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f2027,50:203a43,100:2c5364&height=220&section=header&text=Vedi%20Pocket%20PC&fontSize=52&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=Your%20phone.%20Your%20PC.%20No%20cloud%20required.&descAlignY=58&descAlign=50" width="100%"/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&duration=2800&pause=900&color=38BDF8&center=true&vCenter=true&multiline=true&repeat=true&width=700&height=90&lines=Wireless+Trackpad+%2B+Keyboard+%2B+Screen+Mirror;100%25+Local+%E2%80%A2+Zero+Cloud+%E2%80%A2+Zero+Internet;Electron+%2B+FastAPI+%2B+Expo+%2B+WebSockets" alt="Typing SVG" />

<br/>

![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=for-the-badge&logo=windows11&logoColor=white)
![Electron](https://img.shields.io/badge/Desktop-Electron-47848F?style=for-the-badge&logo=electron&logoColor=white)
![Python](https://img.shields.io/badge/Backend-Python%203.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Expo](https://img.shields.io/badge/Mobile-Expo%20%2F%20RN-000020?style=for-the-badge&logo=expo&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-4c1?style=for-the-badge)

<img src="https://img.shields.io/badge/build-passing-brightgreen?style=flat-square" />
<img src="https://img.shields.io/badge/LAN%20only-no%20cloud-critical?style=flat-square&color=orange" />
<img src="https://img.shields.io/badge/latency-%3C50ms-9cf?style=flat-square" />

</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## ✨ Overview

**Vedi Pocket PC** turns your phone into a wireless trackpad, keyboard, and live screen for your desktop — streamed entirely over your **local Wi‑Fi**. No accounts, no cloud relay, no internet dependency. Pair with a QR code and you're in control.

<div align="center">
<table>
<tr>
<td align="center" width="25%">

### 🖥️
**Screen Mirror**
Low‑latency JPEG stream over WebSocket

</td>
<td align="center" width="25%">

### 🖱️
**Trackpad**
Move · Click · Drag · Scroll

</td>
<td align="center" width="25%">

### ⌨️
**Keyboard**
Soft keys + shortcut bar

</td>
<td align="center" width="25%">

### ⚡
**Power & Media**
Lock · Sleep · Shutdown · Volume

</td>
</tr>
</table>
</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## 🧩 Architecture

```mermaid
flowchart TB
    subgraph Desktop["🖥️ Windows Desktop"]
        E["⚡ Electron Controller<br/>main.js"]
        S["📡 Screen Stream Server<br/>Python · aiohttp · mss<br/>:8080"]
        B["🔧 Remote Agent Backend<br/>FastAPI · WebSockets<br/>:8000"]
        E -->|spawns & monitors| S
        E -->|spawns & monitors| B
    end

    subgraph Phone["📱 Mobile App"]
        M["Expo / React Native<br/>Screen · Trackpad · Keyboard · Controls"]
    end

    S <-->|"JPEG frames + trackpad events (WS)"| M
    B <-->|"pairing · keyboard · media · power (REST/WS)"| M
    B -.->|"mDNS advertise<br/>_pcremote._tcp.local."| M

    style E fill:#38BDF8,color:#0f172a,stroke:#0284c7,stroke-width:2px
    style S fill:#a78bfa,color:#1e1b4b,stroke:#7c3aed,stroke-width:2px
    style B fill:#34d399,color:#022c22,stroke:#059669,stroke-width:2px
    style M fill:#fb923c,color:#431407,stroke:#ea580c,stroke-width:2px
```

<details>
<summary><b>🔄 Pairing & data flow (click to expand)</b></summary>

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant E as Electron App
    participant B as Backend :8000
    participant S as Stream Server :8080
    participant M as 📱 Mobile App

    U->>E: npm start
    E->>B: spawn process
    E->>S: spawn process
    B->>B: generate PIN + QR
    B-->>M: advertise via mDNS
    U->>M: scan QR code
    M->>B: pair (PIN/QR)
    B-->>M: pairing confirmed
    M->>S: open WebSocket
    S-->>M: stream JPEG frames
    M->>S: trackpad move/click/scroll
    M->>B: keyboard / media / volume / power
    B-->>M: ack / status
```

</details>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## 🚀 Quick Start

<div align="center">

### Option A — One command, everything wired up

</div>

```bash
npm install
npm start
```

> Spins up the Electron controller → which launches the screen-stream server, the FastAPI backend, and the Expo dev server, then shows a **QR code** to scan.

<details>
<summary><b>⚙️ Option B — Run each service manually</b></summary>

<br/>

**1️⃣ Screen Stream Server**
```bash
cd screen-stream-server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python server.py
```
`http://<LAN_IP>:8080` · WS at `ws://<LAN_IP>:8080/ws`

**2️⃣ Remote Agent (Backend)**
```bash
cd vedi-pocketpc-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
`http://<LAN_IP>:8000` — prints pairing PIN + QR to terminal

**3️⃣ Mobile App**
```bash
cd veddi-pocketpc
npm install
npx expo start
```
Scan with Expo Go, then pair from within the app.

</details>

<br/>

<div align="center">

| Requirement | Version |
|:---:|:---:|
| 🪟 Windows | 10 / 11 |
| 🟢 Node.js | 18+ |
| 🐍 Python | 3.10+ (3.11 recommended) |
| 📶 Network | Phone + PC on same Wi-Fi |
| 📲 Expo Go | Latest, on your phone |

</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## 🗂️ Repository Structure

```text
Vedi-Pocket-PC/
├── main.js, preload.js, renderer.js   ⚡ Electron desktop controller
├── index.html, styles.css             🎨 Controller UI
├── package.json                       📦 Electron app + electron-builder config
│
├── screen-stream-server/              📡 Screen capture & trackpad relay  (:8080)
│   ├── capture/  mouse/  streaming/
│   ├── config.py, server.py
│   └── requirements.txt
│
├── vedi-pocketpc-backend/             🔧 FastAPI remote agent  (:8000)
│   ├── routes/ (pairing, system, media)
│   ├── discovery.py, ws_handler.py, input_control.py, state.py
│   ├── main.py
│   └── requirements.txt
│
└── veddi-pocketpc/                    📱 Expo / React Native mobile client
    ├── app/(tabs)/ (index, screen, trackpad, keyboard, controls)
    ├── app/pairing.tsx
    ├── components/, hooks/, constants/
    └── package.json
```

## 🛠️ Building a Distributable

```bash
npm run build   # 📦 NSIS installer + zip
npm run pack    # 🗜️ Unpacked directory build (for testing)
```

Freeze the backend into a standalone `.exe` — no Python required on target machines:

```bash
cd vedi-pocketpc-backend
build_agent.bat
# → dist/PCRemoteAgent.exe
```

## 🔥 Firewall Setup

If your phone can't reach the PC, open the ports (PowerShell **as Administrator**):

```powershell
New-NetFirewallRule -DisplayName "Vedi Pocket PC - Screen Stream (8080)" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow -Profile Private,Domain
New-NetFirewallRule -DisplayName "Vedi Pocket PC - Backend Agent (8000)" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private,Domain
```

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## Dependencies

This project has **4 runtimes**: one Node/Electron app, one Node/Expo app, and
two independent Python services. Each has its own dependency set — there is
no single `npm install` or `pip install` that covers everything.

---

## Node.js — Desktop Controller (`controller/` / repo root)

**Requires:** Node.js 18+, npm

```bash
cd controller   # or repo root if not using the restructured layout
npm install
```

| Package | Version | Purpose |
|---|---|---|
| `qrcode` | ^1.5.4 | Generates the pairing/Expo QR codes shown in the desktop UI |
| `electron` | ^33.4.11 *(devDependency)* | Desktop app shell/runtime |
| `electron-builder` | ^25.1.8 *(devDependency)* | Packages the app into a Windows installer (`npm run build`) |

No other runtime dependencies — `services/` and `ipc/` in the clean-architecture
scaffold use only Node built-ins (`os`, `path`, `fs`, `child_process`, `events`).

---

## Node.js — Mobile App (`veddi-pocketpc/`)

**Requires:** Node.js 18+, npm, [Expo Go](https://expo.dev/go) on the test device

```bash
cd veddi-pocketpc
npm install
```

| Package | Version | Purpose |
|---|---|---|
| `expo` | ~57.0.11 | Core Expo runtime |
| `expo-router` | ~57.0.11 | File-based navigation (`app/(tabs)/...`) |
| `expo-camera` | ~57.0.3 | QR code scanning for pairing |
| `expo-constants` | ~57.0.9 | App/device constants |
| `expo-font` | ~57.0.1 | Custom font loading |
| `expo-haptics` | ~57.0.1 | Trackpad tap/click haptic feedback |
| `expo-image` | ~57.0.2 | Optimized image rendering |
| `expo-linking` | ~57.0.5 | Deep-link handling |
| `expo-secure-store` | ~57.0.1 | Storing paired-device tokens securely on device |
| `expo-splash-screen` | ~57.0.5 | App launch splash screen |
| `expo-status-bar` | ~57.0.1 | Status bar styling |
| `expo-symbols` | ~57.0.2 | SF Symbols (iOS) support |
| `expo-system-ui` | ~57.0.2 | System UI theming |
| `expo-web-browser` | ~57.0.2 | In-app browser (external links) |
| `react` | 19.2.3 | UI library |
| `react-dom` | 19.2.3 | Web target rendering (Expo web) |
| `react-native` | 0.86.2 | Mobile runtime |
| `react-native-gesture-handler` | ~2.32.0 | Trackpad pan/tap gesture detection |
| `react-native-reanimated` | 4.5.1 | Animated trackpad feedback (spring/gesture-driven UI) |
| `react-native-safe-area-context` | ~5.7.0 | Safe-area insets across devices |
| `react-native-screens` | ~4.26.0 | Native screen container optimization |
| `react-native-svg` | 15.15.4 | SVG icon rendering |
| `react-native-web` | ~0.21.0 | Web target support |
| `react-native-worklets` | 0.10.1 | Worklet runtime backing Reanimated |
| `@expo/vector-icons` | ^15.0.3 | Icon set |
| `@react-navigation/bottom-tabs` | ^7.4.0 | Tab bar (Screen / Trackpad / Keyboard / Controls) |
| `@react-navigation/elements` | ^2.6.3 | Navigation UI primitives |
| `@react-navigation/native` | ^7.1.8 | Core navigation |
| `lucide-react-native` | ^0.379.0 | Icon components used across screens |
| `zustand` | ^4.5.2 | `deviceStore.ts` state management |

**Dev dependencies:**

| Package | Version | Purpose |
|---|---|---|
| `typescript` | ~6.0.3 | Type checking |
| `@types/react` | ~19.2.4 | React type definitions |
| `eslint` | ^9.25.0 | Linting |
| `eslint-config-expo` | ~57.0.1 | Expo's ESLint ruleset |

---

## Python — Remote Agent Backend (`vedi-pocketpc-backend/`)

**Requires:** Python 3.10+ (3.11+ recommended), Windows 10/11 (uses `pycaw`, Win32 `ctypes`)

```bash
cd vedi-pocketpc-backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

If using the clean-architecture scaffold, also install the shared domain
package first (editable install, so changes propagate immediately):

```bash
pip install -e ../packages/agent-core
```

| Package | Purpose |
|---|---|
| `fastapi` | HTTP + WebSocket framework for pairing, system, media, and `/ws` routes |
| `uvicorn[standard]` | ASGI server running FastAPI |
| `zeroconf` | mDNS advertising (`_pcremote._tcp.local.`) so the mobile app can auto-discover the PC |
| `psutil` | Battery status, network interface enumeration for LAN IP detection |
| `pycaw` | Windows Core Audio control (get/set system volume) |
| `comtypes` | COM interop required by `pycaw` |
| `pyautogui` | Mouse movement, clicks, scrolling, keyboard input, hotkeys |
| `qrcode` | Renders the pairing QR code printed to the terminal on startup |
| `pystray` | System tray icon with "Show Connection Info" / "Quit" menu |
| `pillow` | Image handling, used by both `pystray` (tray icon) and `qrcode` |
| `pytest` *(dev)* | Running the unit tests in `tests/` |

---

## Python — Screen Stream Server (`screen-stream-server/`)

**Requires:** Python 3.10+ (3.11+ recommended), Windows 10/11

```bash
cd screen-stream-server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

If using the clean-architecture scaffold, also install the shared domain
package:

```bash
pip install -e ../packages/agent-core
```

| Package | Purpose |
|---|---|
| `aiohttp` | HTTP + WebSocket server for `/`, `/health`, `/status`, `/ws` |
| `mss` | Fast cross-platform screen capture |
| `pyautogui` | Trackpad-driven mouse/keyboard control (shared logic if using `agent_core`) |
| `pillow` | JPEG encoding of captured frames, cursor-overlay drawing |

---

## Quick reference — install everything

```bash
# Desktop controller
cd controller && npm install && cd ..

# Mobile app
cd veddi-pocketpc && npm install && cd ..

# Shared Python domain package (clean-architecture scaffold only)
pip install -e packages/agent-core

# Backend agent
cd vedi-pocketpc-backend && pip install -r requirements.txt && cd ..

# Screen stream server
cd screen-stream-server && pip install -r requirements.txt && cd ..
```

## Notes

- `pycaw`, `comtypes`, and the `ctypes`/`pystray` tray/volume/power code paths
  are **Windows-only** — on macOS/Linux those features silently no-op (the
  original code already guards this with `sys.platform == 'win32'` checks).
- `pyautogui` is listed in **both** Python services' requirements today
  because the original code duplicates the input-control logic. Once merged
  onto `agent_core` (see the clean-architecture scaffold), it's still a
  direct dependency of `agent_core` itself, and both services get it
  transitively through `pip install -e packages/agent-core` — you can drop
  it from each service's own `requirements.txt` at that point.

## 🧰 Tech Stack

<div align="center">

**Desktop**
<br/>
![Electron](https://img.shields.io/badge/Electron-47848F?style=flat-square&logo=electron&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-339933?style=flat-square&logo=node.js&logoColor=white)
![electron-builder](https://img.shields.io/badge/electron--builder-2B2E3A?style=flat-square)

**Screen Streaming**
<br/>
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![aiohttp](https://img.shields.io/badge/aiohttp-2C5BB4?style=flat-square)
![Pillow](https://img.shields.io/badge/Pillow-3776AB?style=flat-square)

**Remote Agent**
<br/>
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![uvicorn](https://img.shields.io/badge/uvicorn-2C3E50?style=flat-square)
![WebSockets](https://img.shields.io/badge/WebSockets-black?style=flat-square&logo=websocket&logoColor=white)

**Mobile**
<br/>
![Expo](https://img.shields.io/badge/Expo-000020?style=flat-square&logo=expo&logoColor=white)
![React Native](https://img.shields.io/badge/React%20Native-20232A?style=flat-square&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)

</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

<div align="center">

### 📄 License

**MIT** — see `package.json`

<br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:2c5364,50:203a43,100:0f2027&height=120&section=footer&animation=fadeIn" width="100%"/>

</div>
