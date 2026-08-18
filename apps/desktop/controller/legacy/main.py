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

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("VediPocketPC.ControllerApp.1.0")
    except Exception:
        pass

from aiohttp import web

from .network import find_free_port, get_lan_ip
from .process_manager import ProcessManager
from .server import ControllerServer


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


def ensure_ico_file() -> str:
    """Ensures logo.ico exists for Windows taskbar and titlebar app icon."""
    ico_path = os.path.join(_REPO_ROOT, "logo.ico")
    jpg_path = os.path.join(_REPO_ROOT, "logo.jpeg")
    if not os.path.exists(ico_path) and os.path.exists(jpg_path):
        try:
            from PIL import Image
            img = Image.open(jpg_path)
            img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        except Exception:
            pass
    return ico_path if os.path.exists(ico_path) else ""


def _apply_icon_to_process_hwnds(ico_path: str) -> None:
    if sys.platform != "win32" or not os.path.exists(ico_path):
        return
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010

        abs_ico = os.path.abspath(ico_path)
        h_icon_big = user32.LoadImageW(None, abs_ico, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        h_icon_small = user32.LoadImageW(None, abs_ico, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        if not h_icon_big:
            h_icon_big = user32.LoadImageW(None, abs_ico, IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
        if not h_icon_small:
            h_icon_small = h_icon_big

        current_pid = os.getpid()

        def _enum_proc(hwnd, lParam):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == current_pid:
                if h_icon_big:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon_big)
                if h_icon_small:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_small)
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        enum_func = WNDENUMPROC(_enum_proc)
        user32.EnumWindows(enum_func, 0)
    except Exception:
        pass


def apply_windows_icon(title: str = "Vedi Pocket PC") -> None:
    """Sets AppUserModelID and window icon on Windows taskbar & window frame."""
    if sys.platform != "win32":
        return
    ico_path = ensure_ico_file()
    if not ico_path:
        return

    def _set_icon_loop():
        for delay in (0.2, 0.6, 1.2, 2.5, 4.0):
            time.sleep(delay)
            _apply_icon_to_process_hwnds(ico_path)

    threading.Thread(target=_set_icon_loop, daemon=True).start()


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

            apply_windows_icon("Vedi Pocket PC")

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

