"""server.main — composition root for unified Vedi Pocket PC backend.

Single FastAPI application hosting REST endpoints, control WebSockets,
and screen streaming WebSockets on a single port.
"""

from __future__ import annotations

import asyncio
import os
import socket
import sys
import threading
from contextlib import asynccontextmanager

import qrcode
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import Settings
from server.container import Container
from server.infrastructure.adapters.win32_desktop import log_monitor_info_once
from server.infrastructure.discovery.mdns import ServiceAdvertiser, get_all_local_ips
from server.infrastructure.logging.config import configure_logging

from server.presentation.http import health_router, media_router, pairing_router, system_router
from server.presentation.ws import control_handler, stream_handler


def print_banner(container: Container) -> None:
    all_ips = get_all_local_ips()
    print("=" * 60)
    print(f"       {container.settings.server_name.upper()} ACTIVE       ")
    print("=" * 60)
    print(f" Hostname:    {socket.gethostname()}")
    print(f" Primary IP:  {container.local_ip}")
    if len(all_ips) > 1:
        print(f" All IPs:     {', '.join(all_ips)}")
    print(f" Port:        {container.port}")
    print(f" Control WS:  ws://{container.local_ip}:{container.port}/ws")
    print(f" Stream WS:   ws://{container.local_ip}:{container.port}/stream")
    print(f" Pairing PIN: {container.pairing_pin.value}")
    print("-" * 60)
    print(" Scan the QR Code below from your mobile app:")
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


def show_pairing_info_dialog(container: Container) -> None:
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        messagebox.showinfo(
            "Vedi Pocket PC Connection",
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
            pystray.MenuItem("Show Connection Info", lambda i, it: show_pairing_info_dialog(container)),
            pystray.MenuItem("Quit", on_quit),
        )

        icon = pystray.Icon(
            "vedipocketpc",
            create_image(),
            title=f"Vedi Pocket PC Server (PIN: {container.pairing_pin.value})",
            menu=menu,
        )
        icon.run()
    except Exception as e:
        print(f"[TRAY] Tray icon omitted: {e}. Server running in background mode.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    container: Container = app.state.container
    capture_task = asyncio.create_task(container.screen_capture.capture_loop())
    yield
    capture_task.cancel()
    try:
        await capture_task
    except asyncio.CancelledError:
        pass


def create_app(container: Container | None = None) -> FastAPI:
    container = container or Container()

    app = FastAPI(
        title=container.settings.server_name,
        version=container.settings.server_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.container = container

    app.include_router(health_router.build_router(container))
    app.include_router(pairing_router.build_router(container))
    app.include_router(system_router.build_router(container), prefix="/system")
    app.include_router(media_router.build_router(container), prefix="/media")
    app.include_router(control_handler.build_router(container))
    app.include_router(stream_handler.build_router(container))

    return app


def main() -> None:
    configure_logging()

    settings = Settings()
    container = Container(settings)

    container.advertiser = ServiceAdvertiser(port=container.port)
    container.advertiser.start()

    print_banner(container)
    log_monitor_info_once()

    app = create_app(container)

    def start_fastapi():
        uvicorn.run(app, host=container.settings.host, port=container.port, log_level="warning")

    server_thread = threading.Thread(target=start_fastapi, daemon=True)
    server_thread.start()

    startup_timer = threading.Timer(2.0, lambda: show_pairing_info_dialog(container))
    startup_timer.daemon = True
    startup_timer.start()

    run_tray(container)


if __name__ == "__main__":
    main()
