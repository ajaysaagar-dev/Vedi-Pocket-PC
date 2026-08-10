# VediPocketPC — PySide6 Desktop Controller

The desktop controller GUI built with **Python 3.10+** and **PySide6 (Qt6)**.
It manages the lifecycle of the Screen Stream Server (:8080), FastAPI Remote Agent (:8000), and Mobile Expo packager (:8088), displaying real-time pairing QR codes and multi-tabbed system logs.

## Layout

```text
Controller/
└── app.py       # Main PySide6 Qt GUI application & process manager
```

## Running the Controller

```powershell
python Controller/app.py
```
