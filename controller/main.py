"""Vedi Pocket PC — Python Desktop Controller Entry Point.

Replaces Electron with a pure Python desktop controller application.
Runs the background services (FastAPI agent, Screen Streamer, Expo Dev Server)
and hosts the management UI window / browser interface.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
import threading
import time
import webbrowser

# Add repo root to sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from aiohttp import web

from controller.network import find_free_port, get_lan_ip
from controller.process_manager import ProcessManager
from controller.server import ControllerServer


def print_banner(host: str, port: int, lan_ip: str) -> None:
    print("=" * 60)
    print("        VEDI POCKET PC — DESKTOP CONTROLLER (PYTHON)        ")
    print("=" * 60)
    print(f" Controller UI (Local):    http://127.0.0.1:{port}")
    print(f" Controller UI (LAN):      http://{lan_ip}:{port}")
    print("=" * 60)
    print(" Press Ctrl+C to stop all servers and exit.")
    print("=" * 60, flush=True)


async def run_server(pm: ProcessManager, port: int, open_browser: bool = True) -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.winmm.timeBeginPeriod(1)
        except Exception:
            pass

    server = ControllerServer(pm, host="0.0.0.0", port=port)
    runner = web.AppRunner(server.app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    lan_ip = get_lan_ip()
    print_banner("0.0.0.0", port, lan_ip)

    # Start child processes
    pm.start_all()

    # Open web UI in browser if requested
    ui_url = f"http://127.0.0.1:{port}"
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(ui_url)).start()

    stop_event = asyncio.Event()

    def _on_signal():
        print("\n[Controller] Stopping all servers...", flush=True)
        stop_event.set()

    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _on_signal)

    try:
        if sys.platform == "win32":
            while not stop_event.is_set():
                await asyncio.sleep(0.5)
        else:
            await stop_event.wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n[Controller] Received shutdown signal...", flush=True)
    finally:
        pm.stop_all()
        await runner.cleanup()
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.winmm.timeEndPeriod(1)
            except Exception:
                pass
        print("[Controller] Clean exit complete.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Vedi Pocket PC Desktop Controller")
    parser.add_argument("--port", type=int, default=8090, help="Controller UI Port (default: 8090)")
    parser.add_argument("--browser", action="store_true", help="Open in default web browser instead of native desktop window")
    parser.add_argument("--no-browser", action="store_true", help="Run headless without opening a desktop window or browser")
    parser.add_argument("--no-window", action="store_true", help="Disable native desktop window (open in web browser instead)")
    parser.add_argument("--window", action="store_true", help="Explicitly enable native desktop window (enabled by default)")
    args = parser.parse_args()

    port = find_free_port(args.port)
    pm = ProcessManager()

    # Launch native desktop application window (pywebview) by default on PC
    use_window = not (args.browser or args.no_window or args.no_browser)

    if use_window:
        try:
            import webview

            loop_holder = {}
            shutdown_event_holder = {}

            def start_backend_thread():
                async def _runner():
                    shutdown_event = asyncio.Event()
                    shutdown_event_holder["event"] = shutdown_event
                    await run_server(pm, port, open_browser=False)

                loop = asyncio.new_event_loop()
                loop_holder["loop"] = loop
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(_runner())
                finally:
                    loop.close()

            t = threading.Thread(target=start_backend_thread, daemon=True)
            t.start()

            # Brief pause for server initialization
            time.sleep(0.8)

            print("[Controller] Launching native PC desktop application window...", flush=True)
            window = webview.create_window(
                "Vedi Pocket PC",
                f"http://127.0.0.1:{port}",
                width=1120,
                height=800,
                min_size=(880, 650),
                background_color="#0F131A",
            )
            webview.start()

            # Window closed by user -> stop all background services
            print("\n[Controller] Application window closed. Stopping services...", flush=True)
            pm.stop_all()
            return
        except ImportError:
            print("[Controller] pywebview not found, falling back to browser UI mode.", flush=True)
        except Exception as e:
            print(f"[Controller] Native window error ({e}), falling back to browser UI mode.", flush=True)

    # Fallback or explicit browser / headless mode
    try:
        asyncio.run(run_server(pm, port, open_browser=not args.no_browser))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

