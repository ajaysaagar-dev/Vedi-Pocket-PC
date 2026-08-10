# VediPocketPC — pywebview Desktop Controller

The desktop controller GUI built with **Python 3.10+** and **pywebview (HTML/CSS/JS Engine)**.
It manages the lifecycle of the Screen Stream Server (:8080), FastAPI Remote Agent (:8000), and Mobile Expo packager (:8088), displaying real-time pairing QR codes and multi-tabbed system logs inside an Apple Glassmorphism web view.

## Layout

```text
Controller/
└── app.py       # Main pywebview Python GUI application & process manager
```

## Running the Controller

```powershell
python Controller/app.py
```
