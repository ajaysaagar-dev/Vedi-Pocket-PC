<p align="center">
  <img src="apps/desktop/controller/logo.jpeg" alt="Vedi Pocket PC Logo" width="140" style="border-radius: 24px; box-shadow: 0 8px 24px rgba(0,0,0,0.3);" />
</p>

<h1 align="center">Vedi Pocket PC</h1>

<p align="center">
  <strong>Transform your smartphone into a wireless trackpad, keyboard, media remote, and real-time screen mirror for your Windows PC — 100% offline over local Wi-Fi.</strong>
</p>

<p align="center">
  <a href="#tech-stack--libraries-deep-dive"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+" /></a>
  <a href="#tech-stack--libraries-deep-dive"><img src="https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="#tech-stack--libraries-deep-dive"><img src="https://img.shields.io/badge/React_Native-Expo-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React Native Expo" /></a>
  <a href="#tech-stack--libraries-deep-dive"><img src="https://img.shields.io/badge/Windows-10%20%2F%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows 10/11" /></a>
  <a href="#license"><img src="https://img.shields.io/badge/License-MIT-green.style=for-the-badge" alt="MIT License" /></a>
</p>

---

## 📋 Table of Contents

- [Overview & Key Features](#overview--key-features)
- [Tech Stack & Libraries Deep-Dive](#tech-stack--libraries-deep-dive)
  - [Python Backend & Streaming Stack](#1-python-backend--streaming-stack)
  - [Desktop Controller Interface](#2-desktop-controller-interface)
  - [Mobile Client Application](#3-mobile-client-application)
- [Architecture & System Flow](#architecture--system-flow)
- [Repository Structure](#repository-structure)
- [Quick Start Guide](#quick-start-guide)
  - [For End Users](#for-end-users)
  - [For Developers](#for-developers)
- [Ports & Configuration (.env)](#ports--configuration-env)
- [Logs & Persistent Data](#logs--persistent-data)
- [License](#license)

---

## 🚀 Overview & Key Features

**Vedi Pocket PC** is a zero-latency, private local network remote control suite for Windows PCs. It requires **no user accounts, no cloud relays, and no active internet connection**.

* 📲 **Wireless Trackpad & Multitouch**: Smooth cursor movement, left/right/middle clicks, click-and-drag, and 2-finger scroll gestures.
* ⌨️ **Full Remote Keyboard**: Low-latency typing input, backspace handling, modifier keys (`Ctrl`, `Alt`, `Shift`), and media hotkeys.
* 🖥️ **High-FPS Screen Mirroring**: Ultra-fast desktop capture compressed into JPEG streams over WebSockets directly to the phone display.
* 🔊 **System Media & Volume Control**: Adjust PC master volume, toggle mute, and control playback directly through Windows Core Audio APIs.
* 🔒 **Zero-Trust Local Pairing**: Secure 4-digit PIN authentication paired instantly via camera QR code scan.

---

## 🛠️ Tech Stack & Libraries Deep-Dive

### 1. Python Backend & Streaming Stack

| Library / Module | Purpose | Specific Functions & Features Used |
| :--- | :--- | :--- |
| **`mss`** | Ultra-Fast Screen Capture | `mss.mss()` for direct DXGI desktop frame grabbing without GDI overhead. |
| **`Pillow` (PIL)** | Image Processing | `Image.frombytes()`, JPEG compression, dynamic resizing (`STREAM_MAX_WIDTH` x `STREAM_MAX_HEIGHT`). |
| **`pyautogui`** | OS Mouse & Keyboard Automation | `pyautogui.moveTo()`, `click()`, `press()`, `scroll()`, `hotkey()` for simulating physical PC inputs. |
| **`fastapi`** | REST API Service | APIRouter, JWT authentication endpoints, and pairing PIN verification routes (`/api/pair`). |
| **`uvicorn[standard]`** | High-Performance ASGI Server | Drives the `fastapi` pairing and control agent with asynchronous event handlers. |
| **`aiohttp`** | Async Web Server & WebSockets | Drives the controller management server, static asset distribution, and WebSockets event bus. |
| **`websockets` / `wsproto`** | Low-Latency Binary WebSockets | Real-time bi-directional streaming for screen frame delivery and gesture event packets. |
| **`pycaw` & `comtypes`** | Windows Core Audio Integration | Direct COM interop to `IAudioEndpointVolume` for master volume adjustment and mute toggling. |
| **`zeroconf`** | mDNS Local Network Discovery | Registers `_vedi-pocketpc._tcp.local.` services so mobile devices automatically find the PC. |
| **`customtkinter`** | Native Windows Desktop GUI | Custom dark-themed Tkinter desktop application window displaying pairing QR codes, Expo/Metro status, live logs, and process controls. |
| **`pystray`** | Taskbar System Tray Icon | `pystray.Icon()` for running the app minimized in the Windows system tray. |
| **`qrcode`** | Dynamic Credentials QR | `qrcode.make()` to build inline QR code data URLs encoding IP, port, and security PIN. |
| **`psutil`** | Process Lifecycle Management | `psutil.process_iter()`, port checks, and clean child process termination. |

### 2. Desktop Controller Interface

* **CustomTkinter Native GUI**: Modern dark-themed Python desktop window (`app.py`) featuring real-time pairing QR codes, Expo / Metro launcher & controls, service status pills, and live diagnostic log view.
* **HTML5 & Vanilla CSS3**: Web management dashboard interface served at `http://127.0.0.1:8090`.
* **Vanilla JavaScript (`renderer.js`)**: Handles live WebSocket log streams and interactive server process controls.

### 3. Mobile Client Application

* **React Native / Expo Go**: Cross-platform mobile framework.
* **`expo-camera`**: Hardware camera integration for instant QR code pairing scan.
* **`react-native-reanimated`**: High-frequency 60FPS gesture handling for fluid trackpad control.

---

## 🏗️ Architecture & System Flow

```
┌────────────────────────────────────────────── Windows PC ──────────────────────────────────────────────┐
│  Vedi Pocket PC Desktop Controller (Python 3.10+ / PyInstaller)                                       │
│  ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │ ProcessManager                                                                                    │  │
│  │   ├── CustomTkinter GUI & Controller Server (aiohttp) --> http://127.0.0.1:8090 (Desktop App & Management shell) │  │
│  │   ├── Screen Streamer (aiohttp WS)     --> ws://0.0.0.0:8080/ws     (JPEG Display Stream)           │  │
│  │   └── Pairing & Remote Agent (FastAPI) --> http://0.0.0.0:8000     (REST API & Touch Control)      │  │
│  └──────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                    │
                                                    │ 🔒 QR Code Pairing & Local Wi-Fi WebSockets
                                                    ▼
┌──────────────────────────────────────── Mobile Application ───────────────────────────────────────────┐
│  React Native / Expo App (Android Release APK)                                                         │
│  ├── Camera Scan  --> Decodes PC LAN IP, Port, and 4-Digit Security PIN                                │
│  ├── Screen Mirror --> Renders 30FPS JPEG WebSocket stream                                            │
│  └── Trackpad UI   --> Translates gestures to PyAutoGUI commands on PC                                │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Repository Structure

```
Vedi-Pocket-PC/
├── .env                               # Environment configuration settings
├── requirements.txt                   # Master Python dependencies list
│
├── apps/
│   ├── desktop/controller/            # Desktop GUI shell & Process Manager
│   │   ├── app.py                     # Primary execution entry point (CustomTkinter GUI)
│   │   ├── index.html                 # Management dashboard UI
│   │   ├── styles.css                 # Dark theme styling tokens
│   │   ├── renderer.js                # Frontend WebSocket & REST controller
│   │   └── logo.jpeg / logo.ico       # Application icons
│   │
│   ├── streamer/server/               # Screen streamer engine (MSS + WebSockets)
│   ├── agent/server/                  # FastAPI remote control agent (PyAutoGUI + PyCAW)
│   └── mobile/app/                    # React Native / Expo mobile application
│
├── packages/
│   ├── core/                          # Shared domain core (`agent_core`)
│   └── protocol/                      # Shared communication protocols
│
├── scripts/                           # Master execution & build scripts
│   ├── setup.bat                      # Master setup: Installs dependencies
│   ├── start.bat                      # Master launcher: Boots CustomTkinter GUI & services
│   └── build.bat                      # Production builder: Generates standalone EXE
│
└── tests/                             # Unit and integration test suite
```

---

## 🚦 Quick Start Guide

### For End Users

1. Download **`Vedi Pocket PC Setup-1.0.0.exe`** from the release page.
2. Run the installer and launch **Vedi Pocket PC** from your Start Menu.
3. Open the **Vedi Pocket PC** app on your phone, tap **Scan QR**, and point the camera at the desktop window.
4. Your phone is now paired as your PC's wireless trackpad, keyboard, and display stream!

### For Developers

Clone the repository and set up your workspace:

```powershell
# 1. Clone repository
git clone https://github.com/ajaysaagar-dev/Vedi-Pocket-PC.git
cd Vedi-Pocket-PC

# 2. Run master setup (installs Python packages & mobile dependencies)
.\scripts\setup.bat

# 3. Launch application from source
.\scripts\start.bat
```

> [!NOTE]
> Running `.\scripts\start.bat` auto-detects free ports, verifies `.env`, sets up Windows Firewall permissions, and launches the native CustomTkinter GUI window.

---

## ⚙️ Ports & Configuration (.env)

The application configuration can be customized via `.env` in the root folder:

```ini
# Screen Stream Server Settings
STREAM_HOST=0.0.0.0
STREAM_PORT=8080
STREAM_FPS=30
STREAM_JPEG_QUALITY=50
STREAM_MAX_WIDTH=1280
STREAM_MAX_HEIGHT=720

# Backend Server Settings
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CONTROLLER_PORT=8090
```

| Default Port | Protocol | Component Service |
| :---: | :---: | :--- |
| **`8090`** | HTTP / WS | Desktop Controller Management UI (`CustomTkinter` GUI / Browser) |
| **`8080`** | WebSocket | High-Speed Screen Streamer |
| **`8000`** | HTTP REST | FastAPI Remote Control & Pairing Agent |

---

## 📊 Logs & Persistent Data

All application logs and user configurations are stored under `%LOCALAPPDATA%\Vedi Pocket PC\`:

* **Log File**: `%LOCALAPPDATA%\Vedi Pocket PC\logs\vedi-pocketpc.log` (Auto-rotating log files)
* **Configuration Overrides**: `%LOCALAPPDATA%\Vedi Pocket PC\config.json`
* **Session Reconnect Token**: `%LOCALAPPDATA%\Vedi Pocket PC\common_token.txt`

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](file:///p:/Vedi-Pocket-PC/LICENSE) for details.
