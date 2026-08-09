<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0f2027,50:203a43,100:2c5364&height=220&section=header&text=Vedi%20Pocket%20PC&fontSize=52&fontColor=ffffff&animation=fadeIn&fontAlignY=38&desc=Your%20phone.%20Your%20PC.%20No%20cloud%20required.&descAlignY=58&descAlign=50" width="100%"/>

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&duration=2800&pause=900&color=38BDF8&center=true&vCenter=true&multiline=true&repeat=true&width=700&height=90&lines=Wireless+Trackpad+%2B+Keyboard+%2B+Screen+Mirror;100%25+Local+%E2%80%A2+Zero+Cloud+%E2%80%A2+Zero+Internet;Electron+%2B+FastAPI+%2B+Expo+%2B+WebSockets" alt="Typing SVG" />

<br/>

![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=for-the-badge&logo=windows11&logoColor=white)
![Electron](https://img.shields.io/badge/Desktop-Electron-47848F?style=for-the-badge&logo=electron&logoColor=white)
![Python](https://img.shields.io/badge/Backend-Python%203.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Expo](https://img.shields.io/badge/Mobile-Expo%20%2F%20RN-000020?style=for-the-badge&logo=expo&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-4c1?style=for-the-badge)

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

## 🚀 Quick Start

### ⚡ Option A — 1-Click Setup (Recommended)

1. Double-click **[`setup.bat`](file:///P:/Vedi-Pocket-PC/setup.bat)** (or run `.\setup.bat` in PowerShell).
   - *Installs all Python requirements, Electron desktop dependencies, and Expo mobile app dependencies automatically.*
2. Double-click **[`start.bat`](file:///P:/Vedi-Pocket-PC/start.bat)** (or run `npm start`).
   - *Launches the desktop app controller, screen streaming server, remote backend agent, and Expo dev server.*
3. Open **Expo Go** on your phone and scan the QR code displayed on screen or printed in your terminal.

---

### ⚙️ Option B — Manual Setup & Step-by-Step Execution

<details>
<summary><b>Click to expand manual setup instructions</b></summary>

<br/>

**1️⃣ Install Master Python Libraries**
```powershell
pip install -r requirements.txt
```

**2️⃣ Install Root & Mobile Node Dependencies**
```powershell
npm install
cd veddi-pocketpc
npm install
cd ..
```

**3️⃣ Run Desktop & Backend Controller**
```powershell
npm start
```

**4️⃣ Manual Service Execution (Without Electron UI)**
If you want to run each service individually in separate terminal windows:

- **Screen Stream Server (Port 8080)**:
  ```powershell
  cd screen-stream-server
  python server.py
  ```
- **Remote Agent Backend (Port 8000)**:
  ```powershell
  cd vedi-pocketpc-backend
  python main.py
  ```
- **Mobile Client App (Port 8081)**:
  ```powershell
  cd veddi-pocketpc
  npx expo start -c
  ```

</details>

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

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## 🗂️ Repository Structure

```text
Vedi-Pocket-PC/
├── setup.bat                          ⚡ One-click installer (Node + Python)
├── start.bat                          🚀 One-click launcher (Desktop + Backends)
├── requirements.txt                   📦 Master Python dependencies
├── controller/                        ⚡ Electron desktop controller & IPC
├── screen-stream-server/              📡 Screen capture & trackpad relay (:8080)
├── vedi-pocketpc-backend/             🔧 FastAPI remote agent & pairing (:8000)
├── veddi-pocketpc/                    📱 Expo / React Native mobile client (:8081)
└── packages/agent-core/               🧠 Shared Python core domain logic
```

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

## 🔧 Firewall & Port Troubleshooting

If your mobile app cannot connect to your PC, make sure your phone and PC are on the **same Wi‑Fi network**, and open the required ports in PowerShell (**as Administrator**):

```powershell
New-NetFirewallRule -DisplayName "Vedi Pocket PC - Screen Stream (8080)" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow -Profile Private,Domain
New-NetFirewallRule -DisplayName "Vedi Pocket PC - Backend Agent (8000)" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private,Domain
```

### Common Issues & Fixes
- **Port 8081 In Use**: If you see `Port 8081 is being used by another process`, close any separate `npx expo start` terminal windows before running `start.bat` or `npm start`.
- **Peer Dependency Conflicts**: `.npmrc` is configured to set `legacy-peer-deps=true` so `npm install` succeeds without dependency errors.

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.gif" width="100%">

<div align="center">

### 📄 License

**MIT** — see `package.json`

</div>
