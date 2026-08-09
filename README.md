<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f2027,50:203a43,100:2c5364&height=220&section=header&text=Vedi%20Pocket%20PC&fontSize=52&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=Your%20phone.%20Your%20PC.%20No%20cloud%20required.&descAlignY=58&descAlign=50" width="100%"/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&duration=2800&pause=900&color=38BDF8&center=true&vCenter=true&multiline=true&repeat=true&width=700&height=90&lines=Wireless+Trackpad+%2B+Keyboard+%2B+Screen+Mirror;100%25+Local+%E2%80%A2+Zero+Cloud+%E2%80%A2+Zero+Internet;Electron+%2B+FastAPI+%2B+Expo+%2B+WebSockets" alt="Typing SVG" />

<br/>

![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=for-the-badge&logo=windows11&logoColor=white)
![Electron](https://img.shields.io/badge/Desktop-Electron-47848F?style=for-the-badge&logo=electron&logoColor=white)
![Python](https://img.shields.io/badge/Backend-Python%203.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Expo](https://img.shields.io/badge/Mobile-Expo%20%2F%20RN-000020?style=for-the-badge&logo=expo&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-4c1?style=for-the-badge)

<br/>

<img src="https://img.shields.io/badge/build-passing-brightgreen?style=flat-square" />
<img src="https://img.shields.io/badge/LAN%20only-no%20cloud-critical?style=flat-square&color=orange" />
<img src="https://img.shields.io/badge/latency-%3C50ms-9cf?style=flat-square" />

</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## ✨ Overview

**Vedi Pocket PC** turns your phone into a wireless trackpad, keyboard, and live screen for your desktop PC — streamed entirely over your **local Wi-Fi network**. No accounts, no third-party servers, no cloud relay, and zero internet dependency. 

Scan a QR code on your PC screen and immediately take remote control.

<div align="center">
<table>
<tr>
<td align="center" width="25%">

### 🖥️
**Screen Mirror**
Low-latency JPEG stream over WebSockets (<50ms)

</td>
<td align="center" width="25%">

### 🖱️
**Trackpad**
Move · Left/Right Click · Drag · Smooth Scroll

</td>
<td align="center" width="25%">

### ⌨️
**Keyboard**
Full soft keys + shortcut bar (Ctrl, Alt, Win, Del)

</td>
<td align="center" width="25%">

### ⚡
**Power & Media**
Lock · Sleep · Shutdown · Mute · Volume Control

</td>
</tr>
</table>
</div>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## 📋 System Requirements

| Component | Requirement | Notes |
|:---:|:---:|:---|
| **OS** | Windows 10 / 11 | Host desktop machine |
| **Node.js** | v18.0 or higher | Required for Electron desktop app & Expo server |
| **Python** | 3.10 or higher | Required for backend agent & screen stream server |
| **Network** | Local Wi-Fi (LAN) | Phone & PC must be on the same local Wi-Fi router |
| **Mobile** | Expo Go App | Available free on iOS App Store & Android Google Play |

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## 🚀 Quick Start Guide

### ⚡ Option A — 1-Click Automated Setup (Recommended)

1. **Install All Dependencies**:
   Double-click **[`setup.bat`](file:///P:/Vedi-Pocket-PC/setup.bat)** (or run `.\setup.bat` in PowerShell).
   > *This script automatically checks Node & Python, installs Python packages, root Electron packages, and mobile Expo app packages in one step.*

2. **Launch the Application**:
   Double-click **[`start.bat`](file:///P:/Vedi-Pocket-PC/start.bat)** (or run `npm start`).
   > *Launches the Electron desktop controller, starts the Screen Streamer (:8080), Remote Agent (:8000), and Mobile Expo Dev Server (:8081).*

3. **Connect Mobile App**:
   - Open **Expo Go** on your phone.
   - Scan the **Expo QR Code** shown in your terminal / desktop app.
   - Once inside the mobile app, scan the **PC Pairing QR Code** to connect!

---

### ⚙️ Option B — Manual Step-by-Step Installation

<details>
<summary><b>Click to expand manual setup instructions</b></summary>

<br/>

#### 1️⃣ Install Python Dependencies
```powershell
# Installs agent-core, mss, Pillow, aiohttp, pyautogui, fastapi, uvicorn, websockets, etc.
pip install -r requirements.txt
```

#### 2️⃣ Install Desktop & Mobile Node Dependencies
```powershell
# Install root Electron controller dependencies
npm install

# Install mobile client dependencies
cd veddi-pocketpc
npm install
cd ..
```

#### 3️⃣ Launch Desktop Controller
```powershell
npm start
```

#### 4️⃣ Running Individual Services Separately (Without Electron)
If you prefer running backends manually in individual PowerShell windows:

- **Screen Stream Server** (Port `8080`):
  ```powershell
  cd screen-stream-server
  python server.py
  ```

- **FastAPI Remote Agent Backend** (Port `8000`):
  ```powershell
  cd vedi-pocketpc-backend
  python main.py
  ```

- **Mobile Client Expo App** (Port `8081`):
  ```powershell
  cd veddi-pocketpc
  npx expo start -c
  ```

</details>

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## 📱 How to Pair Mobile App with PC

```mermaid
sequenceDiagram
    participant U as 👤 User
    participant E as 🖥️ Electron App
    participant B as 🔧 Backend (:8000)
    participant S as 📡 Stream Server (:8080)
    participant M as 📱 Mobile App

    U->>E: Run start.bat / npm start
    E->>B: Spawn FastAPI Agent process
    E->>S: Spawn Stream Server process
    B->>B: Generate Pairing PIN & QR Code
    U->>M: Scan Expo QR with Expo Go
    M->>M: Launch Vedi Pocket PC app
    U->>M: Scan PC Pairing QR Code
    M->>B: Verify PIN & Authenticate
    B-->>M: Pairing Confirmed (Token granted)
    M->>S: Open WebSocket (ws://<LAN_IP>:8080/ws)
    S-->>M: Stream low-latency JPEG frames & trackpad inputs
```

1. Make sure your **Phone and PC are connected to the same Wi-Fi**.
2. Run `start.bat` on your PC.
3. Open **Expo Go** on your phone:
   - **Android**: Scan the terminal QR code inside Expo Go.
   - **iOS**: Scan the terminal QR code with your default Camera app, then tap "Open in Expo Go".
4. In the mobile app, tap **Pair Device** and point your camera at the **PC Pairing QR code** displayed on your desktop screen (or enter the IP and 4-digit PIN manually).

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## 🧩 System Architecture

```mermaid
flowchart TB
    subgraph Desktop["🖥️ Windows Desktop"]
        E["⚡ Electron Controller<br/>main.js"]
        S["📡 Screen Stream Server<br/>Python · aiohttp · mss<br/>:8080"]
        B["🔧 Remote Agent Backend<br/>FastAPI · WebSockets<br/>:8000"]
        E -->|spawns & monitors| S
        E -->|spawns & monitors| B
    end

    subgraph Phone["📱 Mobile Client"]
        M["Expo / React Native App<br/>Screen · Trackpad · Keyboard · Controls"]
    end

    S <-->|"JPEG frames + trackpad events (WS)"| M
    B <-->|"pairing · keyboard · media · power (REST/WS)"| M
    B -.->|"mDNS service discovery<br/>_pcremote._tcp.local."| M

    style E fill:#38BDF8,color:#0f172a,stroke:#0284c7,stroke-width:2px
    style S fill:#a78bfa,color:#1e1b4b,stroke:#7c3aed,stroke-width:2px
    style B fill:#34d399,color:#022c22,stroke:#059669,stroke-width:2px
    style M fill:#fb923c,color:#431407,stroke:#ea580c,stroke-width:2px
```

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## 🗂️ Repository Structure

```text
Vedi-Pocket-PC/
├── setup.bat                          ⚡ One-click installer (Node + Python dependencies)
├── start.bat                          🚀 One-click launcher (Desktop + Backends + Expo)
├── requirements.txt                   📦 Master Python dependencies file
├── .npmrc                             ⚙️ Config for legacy peer dependency resolution
├── controller/                        ⚡ Electron desktop controller & IPC handlers
│   ├── main.js                        Central entry point for Electron
│   ├── services/                      Process manager, binary resolver & network tools
│   └── ipc/                           IPC bridge between UI & system services
├── screen-stream-server/              📡 High-performance screen capture & trackpad server (:8080)
│   ├── capture/                       Fast screen grabber using `mss` & `Pillow`
│   ├── mouse/                         Low-latency mouse input injection
│   └── server.py                      aiohttp WebSocket server
├── vedi-pocketpc-backend/             🔧 FastAPI remote management agent (:8000)
│   ├── routes/                        Pairing, system info, power & media routes
│   ├── discovery.py                   mDNS local network discovery broadcast
│   └── main.py                        FastAPI app entry point
├── veddi-pocketpc/                    📱 Expo / React Native mobile application (:8081)
│   ├── app/(tabs)/                    Screens: Home, Screen Mirror, Trackpad, Keyboard, Controls
│   ├── app/pairing.tsx                Camera QR code scanner screen
│   └── package.json                   Mobile app dependencies (React 19, Lucide, Navigation)
└── packages/agent-core/               🧠 Shared Python domain models & utilities
```

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## 🛠️ Building Standalone Distributables

### Desktop Installer (.exe)
To package the desktop application into a standalone Windows installer:

```powershell
npm run build   # Generates NSIS installer + ZIP in /dist
npm run pack    # Builds unpacked executable directory for quick testing
```

### PyInstaller Standalone Backend
To build the FastAPI backend into a single executable without requiring Python on target machines:

```powershell
cd vedi-pocketpc-backend
build_agent.bat
# Produces dist/PCRemoteAgent.exe
```

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## 🚨 Troubleshooting & FAQ

### 1. Windows Firewall Blocking Connection
If your phone cannot connect to the PC, open PowerShell **as Administrator** and allow inbound traffic on ports `8080` & `8000`:

```powershell
New-NetFirewallRule -DisplayName "Vedi Pocket PC - Screen Stream (8080)" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow -Profile Private,Domain
New-NetFirewallRule -DisplayName "Vedi Pocket PC - Backend Agent (8000)" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private,Domain
```

### 2. `Port 8081 is being used by another process`
This happens if `npx expo start` is already running in another terminal window. Close all extra terminal windows running Expo before executing `start.bat` or `npm start`.

### 3. `npm install` Peer Dependency Error (`ERESOLVE`)
Expo 57 / React Native 0.86 uses React 19. Both the root directory and `veddi-pocketpc/` contain `.npmrc` with `legacy-peer-deps=true` to automatically bypass strict peer dependency checks.

### 4. `electron is not recognized as an internal or external command`
Run `setup.bat` or run `npm install` in the root directory to install Electron into `node_modules`.

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

<div align="center">

### 📄 License

**MIT License** — See `package.json` for details.

</div>
