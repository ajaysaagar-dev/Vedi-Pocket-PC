# 🐍 PC Remote — Backend Agent (Python FastAPI)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PyInstaller](https://img.shields.io/badge/PyInstaller-Executable-FFD43B?style=flat-square&logo=python&logoColor=black)](#building-the-standalone-exe)

The local server agent that runs on your laptop/PC to handle mouse, keyboard, media, volume, and power actions received from the **PC Remote Mobile App**.

> 📌 **Main Documentation**: For full system documentation and mobile setup, see the [Root README](../README.md).

---

## ⚡ Key Capabilities

- **ZeroConf mDNS Advertisement**: Automatically announces `_pcremote._tcp.local.` on the LAN.
- **Terminal & Dialog QR Code**: Displays connection credentials + QR code in terminal and popup box.
- **System Tray Icon**: Runs silently in the Windows Notification Area with connection PIN popup & exit options.
- **Low Latency WebSocket Handler**: Processes mouse gesture deltas and keyboard events in real-time.
- **OS Controls**: Integrates with `pyautogui` for mouse/keyboard, `pycaw` for Windows master audio volume, and `psutil` for host metrics.

---

## 🛠 Installation & Setup

After the hexagonal-architecture refactor this folder is a **thin shell** over the shared `agent_core` package:

```
vedi-pocketpc-backend/
├── main.py                    composition root — only place adapters get constructed
├── presentation/
│   ├── http/                  FastAPI routers (pairing, system, media)
│   └── ws/                    WebSocket transport + dispatch table
├── infrastructure/            logging, mDNS discovery
└── tests/                     composition-root smoke + fake-driver tests
```

```bash
# 1. Install the shared domain package
pip install -e ../packages/agent-core

# 2. Backend deps
pip install -r requirements.txt

# 3. Run
python main.py
```

---

## 🔐 Login Flow (unchanged)

`POST /pair` accepts `{"pin": "1234"}` and returns
`{"token": "...", "status": "success"}`. The mobile app's
`pairing.tsx` already speaks this contract — the refactor deliberately
preserves the wire format byte-for-byte so existing installs keep
working.

---

## 📦 Building the Standalone .exe

To package the agent into a single executable file that requires no Python installation:

```cmd
build_agent.bat
```

Output binary will be located at `dist/PCRemoteAgent.exe`.

## 🧪 Tests

```bash
pytest tests/
```
