"""vedi-pocketpc-backend composition root.

This is the ONLY file in the backend that imports adapter classes.
Every other module pulls its dependencies through the `Container`
defined below, so we can swap an adapter without touching the
HTTP / WS layers.

The login / pairing flow is unchanged: same `/health`, `/pair`,
`/status`, and `/ws` endpoints, same wire format the mobile app
already speaks. The duplication of input / volume / power logic
that used to live in this folder has been collapsed into
`agent_core`.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time

import qrcode
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_core.adapters.memory_token_store import MemoryTokenStore
from agent_core.adapters.pycaw_audio_driver import PyCawAudioDriver
from agent_core.adapters.pyautogui_input_driver import PyAutoGUIInputDriver
from agent_core.adapters.win32_desktop_access import log_monitor_info_once
from agent_core.adapters.win32_power_driver import Win32PowerDriver
from agent_core.entities.pairing import PairingPin
from agent_core.use_cases.control_input import ControlInput
from agent_core.use_cases.control_system import ControlSystem
from agent_core.use_cases.pairing import PairDevice

from infrastructure.discovery import ServiceAdvertiser, get_local_ip, get_all_local_ips
from infrastructure.logging_config import configure_logging
from presentation.http import media_router, pairing_router, system_router
from presentation.ws import router as ws_router


# ---------------------------------------------------------------------------
# Container — hand-rolled DI so we don't need a framework.
# Holds every adapter / use case the FastAPI app and the WebSocket
# router depend on. Tests can construct their own container with fakes.
# ---------------------------------------------------------------------------
class Container:
    """Wires adapters to use cases. The single place that knows about
    concrete driver classes."""

    def __init__(self) -> None:
        # Adapters
        self.input_driver = PyAutoGUIInputDriver()
        self.audio_driver = PyCawAudioDriver()
        self.power_driver = Win32PowerDriver()
        self.token_store = MemoryTokenStore()

        # Use cases
        self.control_input = ControlInput(self.input_driver)

        # Battery provider is optional — only desktops return data.
        def _battery():
            try:
                import psutil

                b = psutil.sensors_battery()
                if not b:
                    return ControlSystem.make_battery(percent=None, plugged=None)
                return ControlSystem.make_battery(percent=b.percent, plugged=b.power_plugged)
            except Exception:
                return ControlSystem.make_battery(percent=None, plugged=None)

        self.control_system = ControlSystem(
            audio=self.audio_driver,
            power=self.power_driver,
            hostname_provider=lambda: socket.gethostname(),
            os_provider=lambda: __import__("platform").system(),
            os_release_provider=lambda: __import__("platform").release(),
            battery_provider=_battery,
        )

        # PIN is generated once per process — same behaviour as before.
        self.pairing_pin = PairingPin(value=_generate_initial_pin())
        self.pair_device = PairDevice(self.pairing_pin, self.token_store)

        # Discovery
        self.advertiser: ServiceAdvertiser | None = None
        self.local_ip: str = ""
        self.port: int = 8000

        # Health-probe start time so /health can report uptime.
        self.started_at: float = time.time()


def _generate_initial_pin() -> str:
    """Generate the initial PIN. Lives in this module so tests can
    monkey-patch it before constructing the container."""
    import secrets

    return f"{secrets.randbelow(10000):04d}"


# ---------------------------------------------------------------------------
# Banner + tray — preserved verbatim from the previous main.py.
# ---------------------------------------------------------------------------
def print_banner(container: Container) -> None:
    all_ips = get_all_local_ips()
    print("=" * 60)
    print("                 PC REMOTE SERVER ACTIVE                ")
    print("=" * 60)
    print(f" Hostname:    {socket.gethostname()}")
    print(f" Primary IP:  {container.local_ip}")
    if len(all_ips) > 1:
        print(f" All IPs:     {', '.join(all_ips)}")
    print(f" Port:        {container.port}")
    print(f" Pairing PIN: {container.pairing_pin.value}")
    print("-" * 60)
    print(" Scan the QR Code below from your PC Remote Mobile App:")
    print("-" * 60)

    try:
        qr_data = f"{container.local_ip}:{container.port}:{container.pairing_pin.value}"
        qr = qrcode.QRCode(version=1, box_size=1, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr.print_ascii(out=sys.stdout, invert=True)
    except Exception as e:
        print(f"Could not print QR Code: {e}")

    print("=" * 60)
    print(" Keep this window open or check the system tray icon.")
    print("=" * 60)


def show_pairing_info_dialog(container: Container, icon=None, item=None) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showinfo(
            "PC Remote Connection",
            f"Connect your mobile app using:\n\n"
            f"IP Address: {container.local_ip}\n"
            f"Port: {container.port}\n"
            f"Pairing PIN: {container.pairing_pin.value}",
        )
        root.destroy()
    except Exception as e:
        print(f"Error displaying dialog: {e}")


def run_tray(container: Container) -> None:
    try:
        import pystray
        from PIL import Image, ImageDraw

        def create_image():
            image = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.ellipse([4, 4, 60, 60], fill=(33, 150, 243, 255))
            draw.ellipse([4, 4, 60, 60], outline=(255, 255, 255, 255), width=2)
            draw.rectangle([28, 16, 36, 48], fill=(255, 255, 255, 255))
            draw.rectangle([16, 28, 48, 36], fill=(255, 255, 255, 255))
            return image

        def on_quit(icon, item):
            print("[SERVER] Shutting down agent...")
            if container.advertiser:
                container.advertiser.stop()
            icon.stop()
            os._exit(0)

        menu = pystray.Menu(
            pystray.MenuItem("Show Connection Info", lambda i, it: show_pairing_info_dialog(container, i, it)),
            pystray.MenuItem("Quit", on_quit),
        )

        icon = pystray.Icon(
            "pcremote",
            create_image(),
            title=f"PC Remote Server (PIN: {container.pairing_pin.value})",
            menu=menu,
        )
        icon.run()
    except Exception as e:
        print(f"[TRAY] System tray could not start: {e}. Running in headless/terminal mode.")
        import time as _time
        try:
            while True:
                _time.sleep(1)
        except KeyboardInterrupt:
            if container.advertiser:
                container.advertiser.stop()
            os._exit(0)


# ---------------------------------------------------------------------------
# App factory — builds the FastAPI app + container together.
# Exported separately so the test suite can call `create_app(test=True)`.
# ---------------------------------------------------------------------------
def create_app(container: Container | None = None) -> FastAPI:
    container = container or Container()

    app = FastAPI(title="PC Remote Agent", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Stash the container on the app so routers can grab it via
    # `request.app.state.container`.
    app.state.container = container

    app.include_router(pairing_router.build_router(container))
    app.include_router(system_router.build_router(container), prefix="/system")
    app.include_router(media_router.build_router(container), prefix="/media")
    app.include_router(ws_router.build_router(container))

    return app


def main() -> None:
    configure_logging()

    container = Container()
    container.local_ip = get_local_ip()
    container.port = 8000

    container.advertiser = ServiceAdvertiser(port=container.port)
    container.advertiser.start()

    print_banner(container)
    log_monitor_info_once()

    app = create_app(container)

    def start_fastapi():
        uvicorn.run(app, host="0.0.0.0", port=container.port, log_level="warning")

    server_thread = threading.Thread(target=start_fastapi, daemon=True)
    server_thread.start()

    startup_timer = threading.Timer(2.0, lambda: show_pairing_info_dialog(container))
    startup_timer.daemon = True
    startup_timer.start()

    run_tray(container)


if __name__ == "__main__":
    main()
