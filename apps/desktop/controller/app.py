"""Production composition root for Vedi Pocket PC.

Boots the controller UI HTTP server, starts every managed service
in-process, and shows a native **CustomTkinter** desktop window
with the QR code, Expo / Metro QR code, connection info, status
pills, and live logs.

The application does NOT open a webview, a browser, or a system
tray icon. Everything the user needs is in one CustomTkinter
window. Closing the window shuts every service down cleanly.

Performance notes
-----------------

The CustomTkinter mainloop only owns the main thread. The
asyncio core runs on a worker thread. Status updates and log
messages cross the thread boundary through two bounded
``queue.Queue`` instances; the GUI drains them with a single
``root.after`` callback at ~150 ms (≈6 FPS) so the queue always
drains even when the producer outpaces us. QR codes (server +
Expo) are cached by URL — only the URL changes when the PIN
rotates, so we decode each one once.

Every ProcessManager mutation that could block on subprocess I/O
(start / stop / restart / start_expo / stop_expo / reload_expo)
is dispatched to a short-lived daemon thread so the GUI stays
responsive even when the underlying call takes seconds.

Launcher modes
--------------

* No arguments — start the controller with the CustomTkinter UI
  and both services inline (default for the EXE).
* ``--no-window`` — start the services but do not open the GUI.
* ``--controller-port=N`` — override the controller UI port.
* ``--info`` — print diagnostic information and exit.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import io
import logging
import os
import queue
import shutil
import signal
import sys
import threading
import time
import webbrowser
from collections import OrderedDict
from pathlib import Path
from typing import Optional

# Always make the repository root importable *before* importing any
# of our modules so the package layouts resolve correctly. In
# production this is a no-op (PyInstaller froze everything already),
# but it makes the file usable from a developer checkout too.
from .paths import bundle_root, app_root, app_version
sys.path.insert(0, str(bundle_root()))

from .config import AppConfig, load_config  # noqa: E402
from .logging_setup import configure_logging  # noqa: E402
from .network import find_free_port, get_lan_ip  # noqa: E402
from .process_manager import AlreadyRunningError, ProcessManager  # noqa: E402


log = logging.getLogger("vedi.main")


# ---------------------------------------------------------------------------
# Pretty banner for log / console
# ---------------------------------------------------------------------------
def _print_banner(cfg: AppConfig, lan_ip: str) -> None:
    msg = (
        "\n"
        "============================================================\n"
        f"        {cfg.controller_port} controller UI for Vedi Pocket PC v{app_version()}\n"
        "============================================================\n"
        f"  Controller UI (local): http://127.0.0.1:{cfg.controller_port}\n"
        f"  LAN:                   http://{lan_ip}:{cfg.controller_port}\n"
        f"  Screen stream server:  ws://{lan_ip}:{cfg.stream_port}/ws\n"
        f"  Backend / pairing:     http://{lan_ip}:{cfg.backend_port}\n"
        "============================================================\n"
        "  The CustomTkinter desktop window is now open.\n"
        "  Close the window (or press Ctrl+C) to stop everything.\n"
        "============================================================\n"
    )
    log.info(msg)


def _install_appusermodel_id() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "VediPocketPC.Desktop.1"
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Async core — runs in a worker thread so the Tk mainloop owns main thread.
# ---------------------------------------------------------------------------
async def _run_controller_async(
    pm: ProcessManager,
    cfg: AppConfig,
    stop_event: Optional[asyncio.Event] = None,
) -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.winmm.timeBeginPeriod(1)
        except Exception:
            pass

    from aiohttp import web
    from .legacy.server import ControllerServer  # noqa: WPS433 — lazy import

    server = ControllerServer(pm, host=cfg.controller_host, port=cfg.controller_port)
    runner = web.AppRunner(server.app)
    await runner.setup()
    site = web.TCPSite(runner, cfg.controller_host, cfg.controller_port)
    await site.start()

    lan_ip = pm.lan_ip
    _print_banner(cfg, lan_ip)

    try:
        pm.start_all()
    except AlreadyRunningError as exc:
        log.error("Cannot start: %s", exc)
        return

    stop = stop_event or asyncio.Event()
    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:
                pass
    try:
        while not stop.is_set():
            await asyncio.sleep(0.4)
    finally:
        log.info("Shutting down services...")
        try:
            await loop.run_in_executor(None, pm.stop_all)
        except Exception:
            log.exception("Error during service shutdown")
        try:
            await runner.cleanup()
        except Exception:
            pass
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.winmm.timeEndPeriod(1)
            except Exception:
                pass
        log.info("Clean exit.")


# ---------------------------------------------------------------------------
# Environment probes — used to explain WHY a service can't start.
# ---------------------------------------------------------------------------
def _probe_node() -> tuple[bool, str]:
    node = shutil.which("node")
    if node:
        return True, node
    if sys.platform == "win32":
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        candidate = Path(pf) / "nodejs" / "node.exe"
        if candidate.is_file():
            return True, str(candidate)
    return False, "Node.js not found in PATH or Program Files"


def _probe_expo_dir() -> tuple[bool, str]:
    """Find the Expo mobile app directory by walking up from bundle_root."""
    from .paths import app_root  # noqa: WPS433

    candidates: list[Path] = []
    for base in (app_root(), bundle_root()):
        current = base
        for _ in range(5):
            candidates.append(current)
            current = current.parent
            if current == current.parent:
                break

    for root in candidates:
        for sub in ("apps/mobile/app", "veddi-pocketpc", "apps/mobile"):
            candidate = root / sub
            if candidate.is_dir():
                return True, str(candidate)
    return False, "Mobile app directory not found"


def _probe_expo_deps(expo_dir: str) -> tuple[bool, str]:
    p = Path(expo_dir) / "node_modules" / "expo" / "package.json"
    return p.is_file(), ("installed" if p.is_file() else "missing — run npm install")


def _make_qr_data_url(text: str) -> str:
    """Generate a PNG QR code and return it as data:image/png;base64,...

    Runs on the GUI thread; the URLs are short so this is fast
    enough — but only called when the URL actually changes
    (cached in the window).
    """
    if not text:
        return ""
    try:
        import qrcode  # noqa: WPS433

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception as exc:  # noqa: BLE001
        log.warning("QR generation failed for %r: %s", text, exc)
        return ""


# ---------------------------------------------------------------------------
# CustomTkinter GUI
# ---------------------------------------------------------------------------
_DARK_BG = "#0B0F17"
_SURFACE = "#131822"
_SURFACE_HIGH = "#1B2230"
_BORDER = "#2A3142"
_TEXT = "#F5F7FA"
_TEXT_MUTED = "#9CA3AF"
_TEXT_DIM = "#6B7280"
_ACCENT = "#22C55E"
_ACCENT_DIM = "#16A34A"
_DANGER = "#EF4444"
_DANGER_DIM = "#B91C1C"
_WARNING = "#F59E0B"
_PURPLE = "#A855F7"
_PURPLE_DIM = "#7C3AED"
_BLUE = "#3B82F6"
_BLUE_DIM = "#1D4ED8"


class ControllerWindow:
    """CustomTkinter desktop window for the controller UI."""

    def __init__(
        self,
        pm: ProcessManager,
        cfg: AppConfig,
        log_queue: "queue.Queue[tuple[str, str]]",
        status_queue: "queue.Queue[dict]",
        expo_dir: str,
    ) -> None:
        import customtkinter as ctk  # noqa: WPS433 — lazy import

        self._pm = pm
        self._cfg = cfg
        self._log_queue = log_queue
        self._status_queue = status_queue
        self._expo_dir = expo_dir
        self._ctk = ctk

        # Bounded LRU for decoded QR images (max 8 entries each).
        self._qr_cache_pair: "OrderedDict[str, object]" = OrderedDict()
        self._qr_cache_expo: "OrderedDict[str, object]" = OrderedDict()
        self._QR_CACHE_MAX = 8

        # Latest payload cache so the GUI can decide what changed.
        self._last_pairing_url = ""
        self._last_expo_url = ""
        self._last_status: dict = {}
        self._pills_state: dict = {}

        # Log buffers for tabbed log viewer
        self._python_logs: list[str] = []
        self._expo_logs: list[str] = []
        self._active_tab = "python"

        # Re-entrancy guard so a slow apply_status can't pile up calls.
        self._applying = False

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.root = ctk.CTk()
        self.root.title(f"Vedi Pocket PC v{app_version()}")
        self.root.geometry("980x680")
        self.root.minsize(880, 600)
        self.root.configure(fg_color=_DARK_BG)

        _install_appusermodel_id()
        try:
            self.root.iconbitmap(default=str(self._logo_path()))
        except Exception:
            pass

        self._build_layout()

        # Drain queues every 150 ms (≈6 fps). Fast enough to feel live,
        # slow enough to keep CPU near zero on a quiet system.
        self.root.after(150, self._drain_queues)
        # Poll ProcessManager every 2 s as a safety net.
        self.root.after(2000, self._refresh_status)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ UI
    def _logo_path(self) -> Path:
        for candidate in (
            bundle_root() / "logo.ico",
            Path(__file__).resolve().parent / "logo.ico",
        ):
            if candidate.is_file():
                return candidate
        return bundle_root() / "logo.ico"

    def _pill(self, parent, text: str, *, color: str, value_id: str):
        ctk = self._ctk
        frame = ctk.CTkFrame(parent, fg_color=_SURFACE_HIGH, corner_radius=8, height=28)
        frame.pack(fill="x", padx=8, pady=2)
        frame.pack_propagate(False)

        dot = ctk.CTkLabel(
            frame, text="●",
            text_color=color, font=ctk.CTkFont(size=12),
            width=18,
        )
        dot.pack(side="left", padx=(10, 4))
        label = ctk.CTkLabel(
            frame, text=text,
            text_color=_TEXT, font=ctk.CTkFont(size=12),
            anchor="w",
        )
        label.pack(side="left", padx=(0, 4))
        value = ctk.CTkLabel(
            frame, text="…",
            text_color=_TEXT_MUTED, font=ctk.CTkFont(size=12, weight="bold"),
        )
        value.pack(side="right", padx=10)
        return {"frame": frame, "dot": dot, "label": label, "value": value, "id": value_id}

    def _section_card(self, parent, title: str, subtitle: str = ""):
        ctk = self._ctk
        card = ctk.CTkFrame(
            parent, fg_color=_SURFACE,
            corner_radius=10, border_width=1, border_color=_BORDER,
        )
        header = ctk.CTkFrame(card, fg_color="transparent", height=38)
        header.pack(fill="x", padx=12, pady=(8, 0))
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text=title,
            text_color=_TEXT, font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(
                header, text=subtitle,
                text_color=_TEXT_MUTED, font=ctk.CTkFont(size=10),
                anchor="w",
            ).pack(anchor="w")
        return card

    def _build_layout(self) -> None:
        ctk = self._ctk
        FONT_TITLE = ctk.CTkFont(size=18, weight="bold")
        FONT_H2 = ctk.CTkFont(size=13, weight="bold")
        FONT_BODY = ctk.CTkFont(size=12)
        FONT_MONO = ctk.CTkFont(family="Consolas", size=11)
        FONT_SMALL = ctk.CTkFont(size=10)
        FONT_PIN = ctk.CTkFont(family="Consolas", size=22, weight="bold")

        # =========================
        # HEADER
        # =========================
        header = ctk.CTkFrame(self.root, fg_color=_SURFACE, height=56, corner_radius=0)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        logo_frame = ctk.CTkFrame(header, fg_color=_ACCENT_DIM, width=36, height=36, corner_radius=10)
        logo_frame.pack(side="left", padx=(16, 8), pady=10)
        logo_frame.pack_propagate(False)
        ctk.CTkLabel(
            logo_frame, text="V",
            text_color="#FFFFFF", font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(expand=True)

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left", pady=10)
        ctk.CTkLabel(
            title_box, text="Vedi Pocket PC",
            text_color=_TEXT, font=FONT_TITLE, anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_box,
            text="PC Screen Streaming & Remote Control",
            text_color=_TEXT_MUTED, font=FONT_SMALL, anchor="w",
        ).pack(anchor="w")

        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="right", padx=16)
        self._status_dot = ctk.CTkLabel(
            status_frame, text="●",
            text_color=_WARNING, font=ctk.CTkFont(size=14),
        )
        self._status_dot.pack(side="left", padx=(0, 4))
        self._status_label = ctk.CTkLabel(
            status_frame, text="Starting…",
            text_color=_TEXT, font=FONT_BODY,
        )
        self._status_label.pack(side="left")

        # =========================
        # MAIN — scrollable area
        # =========================
        main = ctk.CTkScrollableFrame(self.root, fg_color=_DARK_BG)
        main.pack(fill="both", expand=True, padx=10, pady=8)

        grid = ctk.CTkFrame(main, fg_color="transparent")
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=3, uniform="a")
        grid.columnconfigure(1, weight=3, uniform="a")
        grid.columnconfigure(2, weight=2, uniform="a")

        # ----- Card 1: PC Stream QR (pairing) -----
        card1 = self._section_card(
            grid, "Pair Device",
            "Scan with the mobile app's Pair Device camera.",
        )
        card1.grid(row=0, column=0, padx=(0, 6), pady=(0, 8), sticky="nsew")

        self._qr_label = ctk.CTkLabel(
            card1, text="Waiting…",
            fg_color=_SURFACE_HIGH, corner_radius=10,
            width=180, height=180,
            text_color=_TEXT_DIM, font=FONT_SMALL,
        )
        self._qr_label.pack(padx=12, pady=(6, 8))

        url_row = ctk.CTkFrame(card1, fg_color="transparent")
        url_row.pack(fill="x", padx=12, pady=(2, 0))
        ctk.CTkLabel(
            url_row, text="URL",
            text_color=_TEXT_MUTED, font=FONT_SMALL, width=32, anchor="w",
        ).pack(side="left")
        self._pairing_value = ctk.CTkLabel(
            url_row, text="---.---.---.---:----:----",
            text_color=_TEXT, font=FONT_MONO, anchor="w",
        )
        self._pairing_value.pack(side="left", padx=(0, 4))

        pin_row = ctk.CTkFrame(card1, fg_color=_SURFACE_HIGH, corner_radius=8, height=48)
        pin_row.pack(fill="x", padx=12, pady=(6, 10))
        pin_row.pack_propagate(False)
        ctk.CTkLabel(
            pin_row, text="PIN",
            text_color=_TEXT_MUTED, font=FONT_SMALL, width=32, anchor="w",
        ).pack(side="left", padx=(10, 0))
        self._pin_value = ctk.CTkLabel(
            pin_row, text="----",
            text_color=_ACCENT, font=FONT_PIN,
        )
        self._pin_value.pack(side="left", padx=(0, 6))

        btn_row = ctk.CTkFrame(pin_row, fg_color="transparent")
        btn_row.pack(side="right", padx=8)
        self._copy_pin_btn = ctk.CTkButton(
            btn_row, text="Copy", width=70, height=24,
            fg_color=_SURFACE, hover_color=_BORDER,
            text_color=_TEXT, font=FONT_SMALL,
            command=self._on_copy_pin,
        )
        self._copy_pin_btn.pack(side="right", padx=2)
        self._copy_url_btn = ctk.CTkButton(
            btn_row, text="URL", width=60, height=24,
            fg_color=_SURFACE, hover_color=_BORDER,
            text_color=_TEXT, font=FONT_SMALL,
            command=self._on_copy_url,
        )
        self._copy_url_btn.pack(side="right", padx=2)

        # ----- Card 2: Expo / Metro QR -----
        card2 = self._section_card(
            grid, "Expo / Metro",
            "Scan with Expo Go to open the mobile app.",
        )
        card2.grid(row=0, column=1, padx=6, pady=(0, 8), sticky="nsew")

        self._expo_qr_label = ctk.CTkLabel(
            card2, text="Off",
            fg_color=_SURFACE_HIGH, corner_radius=10,
            width=180, height=180,
            text_color=_TEXT_DIM, font=FONT_SMALL,
        )
        self._expo_qr_label.pack(padx=12, pady=(6, 8))

        expo_url_row = ctk.CTkFrame(card2, fg_color="transparent")
        expo_url_row.pack(fill="x", padx=12, pady=(2, 0))
        ctk.CTkLabel(
            expo_url_row, text="URL",
            text_color=_TEXT_MUTED, font=FONT_SMALL, width=32, anchor="w",
        ).pack(side="left")
        self._expo_url_value = ctk.CTkLabel(
            expo_url_row, text="exp://---.---.---.---:----",
            text_color=_TEXT, font=FONT_MONO, anchor="w",
        )
        self._expo_url_value.pack(side="left", padx=(0, 4))

        expo_btn_row = ctk.CTkFrame(card2, fg_color=_SURFACE_HIGH, corner_radius=8, height=48)
        expo_btn_row.pack(fill="x", padx=12, pady=(6, 10))
        expo_btn_row.pack_propagate(False)
        self._expo_start_btn = ctk.CTkButton(
            expo_btn_row, text="▶ Start", width=80, height=30,
            fg_color=_PURPLE_DIM, hover_color=_PURPLE,
            text_color="#FFFFFF", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_expo_start,
        )
        self._expo_start_btn.pack(side="left", padx=(8, 4), pady=9)
        self._expo_stop_btn = ctk.CTkButton(
            expo_btn_row, text="■ Stop", width=80, height=30,
            fg_color=_SURFACE, hover_color=_BORDER,
            text_color=_TEXT, font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_expo_stop,
        )
        self._expo_stop_btn.pack(side="left", padx=4, pady=9)
        self._expo_reload_btn = ctk.CTkButton(
            expo_btn_row, text="↻ Reload", width=80, height=30,
            fg_color=_SURFACE, hover_color=_BORDER,
            text_color=_TEXT, font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_expo_reload,
        )
        self._expo_reload_btn.pack(side="left", padx=4, pady=9)

        # ----- Card 3: Services + Network + Diagnostics -----
        card3 = self._section_card(grid, "Services & Network", "Status, ports, diagnostics.")
        card3.grid(row=0, column=2, padx=(6, 0), pady=(0, 8), sticky="nsew")

        self._pills = {}
        for key, text, color in (
            ("stream", "Python Stream", _ACCENT),
            ("backend", "FastAPI Backend", _BLUE),
            ("expo", "Expo / Metro", _PURPLE),
        ):
            self._pills[key] = self._pill(card3, text, color=color, value_id=key)

        # Port table
        ports_frame = ctk.CTkFrame(card3, fg_color="transparent")
        ports_frame.pack(fill="x", padx=12, pady=(6, 4))
        self._port_labels: dict[str, object] = {}
        for label, port_key in (
            ("Stream Port", "streamPort"),
            ("Backend REST", "backendPort"),
            ("Controller UI", "controllerPort"),
        ):
            row = ctk.CTkFrame(ports_frame, fg_color="transparent", height=18)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)
            ctk.CTkLabel(
                row, text=label,
                text_color=_TEXT_MUTED, font=FONT_SMALL, anchor="w",
            ).pack(side="left")
            v = ctk.CTkLabel(
                row, text="----",
                text_color=_TEXT, font=FONT_MONO, anchor="e",
            )
            v.pack(side="right")
            self._port_labels[port_key] = v

        # LAN IP card
        ip_card = ctk.CTkFrame(card3, fg_color=_SURFACE_HIGH, corner_radius=8, height=34)
        ip_card.pack(fill="x", padx=12, pady=(4, 2))
        ip_card.pack_propagate(False)
        ctk.CTkLabel(
            ip_card, text="LAN",
            text_color=_TEXT_MUTED, font=FONT_SMALL,
        ).pack(side="left", padx=(10, 0))
        self._ip_value = ctk.CTkLabel(
            ip_card, text="Detecting…",
            text_color=_TEXT, font=FONT_MONO,
        )
        self._ip_value.pack(side="left", padx=6)
        self._copy_ip_btn = ctk.CTkButton(
            ip_card, text="Copy", width=50, height=22,
            fg_color=_SURFACE, hover_color=_BORDER,
            text_color=_TEXT, font=FONT_SMALL,
            command=self._on_copy_ip,
        )
        self._copy_ip_btn.pack(side="right", padx=6)

        # Diagnostics panel
        diag_card = ctk.CTkFrame(card3, fg_color=_SURFACE_HIGH, corner_radius=8)
        diag_card.pack(fill="x", padx=12, pady=(2, 10))
        ctk.CTkLabel(
            diag_card, text="Diagnostics",
            text_color=_TEXT_MUTED, font=FONT_SMALL,
        ).pack(anchor="w", padx=10, pady=(6, 2))

        node_ok, node_msg = _probe_node()
        expo_ok, expo_msg = _probe_expo_dir()
        deps_ok, deps_msg = _probe_expo_deps(expo_msg) if expo_ok else (False, "n/a")

        for label, ok, msg in (
            ("Node.js", node_ok, node_msg),
            ("Mobile dir", expo_ok, expo_msg if expo_ok else "missing"),
            ("npm install", deps_ok, deps_msg),
        ):
            row = ctk.CTkFrame(diag_card, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=1)
            ctk.CTkLabel(
                row, text="●", text_color=(_ACCENT if ok else _DANGER),
                font=ctk.CTkFont(size=10), width=12,
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=label,
                text_color=_TEXT, font=FONT_SMALL, width=80, anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                row, text=msg,
                text_color=(_TEXT if ok else _TEXT_MUTED), font=FONT_SMALL,
                anchor="w",
            ).pack(side="left", padx=2)

        # =========================
        # LOG PANEL
        # =========================
        log_frame = ctk.CTkFrame(
            main, fg_color=_SURFACE,
            corner_radius=10, border_width=1, border_color=_BORDER,
        )
        log_frame.pack(fill="both", expand=True, pady=(2, 0))

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent", height=32)
        log_header.pack(fill="x", padx=6, pady=(4, 0))
        log_header.pack_propagate(False)

        self._tab_python = ctk.CTkButton(
            log_header, text="Python Logs", width=120, height=24,
            fg_color=_ACCENT_DIM, hover_color=_ACCENT,
            text_color="#FFFFFF", font=FONT_SMALL,
            command=lambda: self._switch_tab("python"),
        )
        self._tab_python.pack(side="left", padx=2)

        self._tab_expo = ctk.CTkButton(
            log_header, text="Expo Logs", width=110, height=24,
            fg_color=_SURFACE_HIGH, hover_color=_BORDER,
            text_color=_TEXT, font=FONT_SMALL,
            command=lambda: self._switch_tab("expo"),
        )
        self._tab_expo.pack(side="left", padx=2)

        clear_btn = ctk.CTkButton(
            log_header, text="Clear", width=60, height=24,
            fg_color=_SURFACE_HIGH, hover_color=_BORDER,
            text_color=_TEXT, font=FONT_SMALL,
            command=self._on_clear_logs,
        )
        clear_btn.pack(side="right", padx=2)

        copy_logs_btn = ctk.CTkButton(
            log_header, text="Copy", width=60, height=24,
            fg_color=_SURFACE_HIGH, hover_color=_BORDER,
            text_color=_TEXT, font=FONT_SMALL,
            command=self._on_copy_logs,
        )
        copy_logs_btn.pack(side="right", padx=2)

        self._log_box = ctk.CTkTextbox(
            log_frame,
            fg_color="#08090C",
            text_color=_TEXT,
            font=FONT_MONO,
            wrap="word",
            activate_scrollbars=True,
        )
        self._log_box.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self._log_box.configure(state="disabled")

        # =========================
        # FOOTER — control buttons
        # =========================
        footer = ctk.CTkFrame(self.root, fg_color=_SURFACE, height=52, corner_radius=0)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        self._start_btn = ctk.CTkButton(
            footer, text="▶ Start", width=90, height=32,
            fg_color=_ACCENT_DIM, hover_color=_ACCENT,
            text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_start,
        )
        self._start_btn.pack(side="left", padx=(12, 4), pady=10)

        self._restart_btn = ctk.CTkButton(
            footer, text="↻ Restart", width=90, height=32,
            fg_color=_SURFACE_HIGH, hover_color=_BORDER,
            text_color=_TEXT, font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_restart,
        )
        self._restart_btn.pack(side="left", padx=4, pady=10)

        self._stop_btn = ctk.CTkButton(
            footer, text="■ Stop", width=90, height=32,
            fg_color=_SURFACE_HIGH, hover_color=_BORDER,
            text_color=_DANGER, font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_stop,
        )
        self._stop_btn.pack(side="left", padx=4, pady=10)

        self._quit_btn = ctk.CTkButton(
            footer, text="✕ Quit", width=80, height=32,
            fg_color=_DANGER_DIM, hover_color=_DANGER,
            text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_close,
        )
        self._quit_btn.pack(side="right", padx=(4, 12), pady=10)

        self._active_tab = "python"

    # ------------------------------------------------------------- handlers
    def _switch_tab(self, tab: str) -> None:
        if self._active_tab == tab:
            return
        self._active_tab = tab
        if tab == "python":
            self._tab_python.configure(fg_color=_ACCENT_DIM, hover_color=_ACCENT, text_color="#FFFFFF")
            self._tab_expo.configure(fg_color=_SURFACE_HIGH, hover_color=_BORDER, text_color=_TEXT)
            active_content = "".join(self._python_logs)
        else:
            self._tab_expo.configure(fg_color=_PURPLE_DIM, hover_color=_PURPLE, text_color="#FFFFFF")
            self._tab_python.configure(fg_color=_SURFACE_HIGH, hover_color=_BORDER, text_color=_TEXT)
            active_content = "".join(self._expo_logs)

        try:
            self._log_box.configure(state="normal")
            self._log_box.delete("1.0", "end")
            if active_content:
                self._log_box.insert("end", active_content)
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        except Exception:
            pass

    def _on_copy_pin(self) -> None:
        pin = self._pills_state.get("pairingPin") or "----"
        self._clipboard_set(pin)

    def _on_copy_url(self) -> None:
        url = self._pills_state.get("pairingUrl") or ""
        if url:
            self._clipboard_set(url)

    def _on_copy_ip(self) -> None:
        ip = self._pills_state.get("lanIp") or ""
        if ip:
            self._clipboard_set(ip)

    def _on_open_browser(self) -> None:
        try:
            webbrowser.open(f"http://127.0.0.1:{self._cfg.controller_port}")
        except Exception:
            pass

    def _on_clear_logs(self) -> None:
        if self._active_tab == "python":
            self._python_logs.clear()
        else:
            self._expo_logs.clear()
        try:
            self._log_box.configure(state="normal")
            self._log_box.delete("1.0", "end")
            self._log_box.configure(state="disabled")
        except Exception:
            pass

    def _on_copy_logs(self) -> None:
        try:
            text = self._log_box.get("1.0", "end")
            self._clipboard_set(text)
        except Exception:
            pass

    # ----- Background dispatchers — never block the Tk mainloop. -----
    def _on_start(self) -> None:
        threading.Thread(target=self._pm.start_all, daemon=True, name="vedi.start").start()

    def _on_stop(self) -> None:
        threading.Thread(target=self._pm.stop_all, daemon=True, name="vedi.stop").start()

    def _on_restart(self) -> None:
        threading.Thread(target=self._pm.restart_all, daemon=True, name="vedi.restart").start()

    def _on_expo_start(self) -> None:
        threading.Thread(target=self._pm.start_expo, daemon=True, name="vedi.expo.start").start()

    def _on_expo_stop(self) -> None:
        threading.Thread(target=self._pm.stop_expo, daemon=True, name="vedi.expo.stop").start()

    def _on_expo_reload(self) -> None:
        def _do():
            try:
                self._pm.reload_expo()
            except Exception:
                log.exception("Expo reload failed.")
        threading.Thread(target=_do, daemon=True, name="vedi.expo.reload").start()

    def _on_close(self) -> None:
        log.info("Window close requested — shutting down.")
        try:
            self._pm.request_shutdown()
        except Exception:
            pass
        try:
            self.root.quit()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def _clipboard_set(self, text: str) -> None:
        if not text:
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except Exception:
            log.warning("Clipboard set failed.")

    # -------------------------------------------------------- queue draining
    def _drain_queues(self) -> None:
        new_py_logs: list[str] = []
        new_expo_logs: list[str] = []
        for _ in range(500):
            try:
                channel, msg = self._log_queue.get_nowait()
            except queue.Empty:
                break
            if channel == "expo-log":
                new_expo_logs.append(msg)
                self._expo_logs.append(msg)
            else:
                new_py_logs.append(msg)
                self._python_logs.append(msg)

        if len(self._python_logs) > 5000:
            self._python_logs = self._python_logs[-3000:]
        if len(self._expo_logs) > 5000:
            self._expo_logs = self._expo_logs[-3000:]

        latest = None
        for _ in range(20):
            try:
                latest = self._status_queue.get_nowait()
            except queue.Empty:
                break
        if latest is not None:
            self._apply_status(latest)

        if self._active_tab == "python" and new_py_logs:
            self._append_logs(new_py_logs)
        elif self._active_tab == "expo" and new_expo_logs:
            self._append_logs(new_expo_logs)

        try:
            self.root.after(150, self._drain_queues)
        except Exception:
            pass

    def _append_logs(self, lines: list[str]) -> None:
        try:
            self._log_box.configure(state="normal")
            self._log_box.insert("end", "".join(lines))
            line_count = int(self._log_box.index("end-1c").split(".")[0])
            if line_count > 3000:
                self._log_box.delete("1.0", f"{line_count - 2000}.0")
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        except Exception:
            pass

    def _refresh_status(self) -> None:
        try:
            payload = self._pm.get_status_payload()
            self._apply_status(payload)
        except Exception:
            log.exception("Status refresh failed.")
        try:
            self.root.after(2000, self._refresh_status)
        except Exception:
            pass

    def _apply_status(self, payload: dict) -> None:
        # Re-entrancy guard: if a previous apply is still running, drop this one.
        if self._applying:
            return
        self._applying = True
        try:
            self._apply_status_inner(payload)
        finally:
            self._applying = False

    def _apply_status_inner(self, payload: dict) -> None:
        if payload == self._last_status:
            return
        self._last_status = dict(payload)
        self._pills_state.update(payload)

        lan_ip = payload.get("lanIp") or self._pm.lan_ip or "----"
        pin = payload.get("pairingPin") or "----"
        pairing_url = payload.get("pairingUrl") or f"{lan_ip}:{self._cfg.backend_port}"
        expo_url = payload.get("expoUrl") or ""
        expo_running = bool(payload.get("isExpoRunning"))

        # Header status
        stream_on = bool(payload.get("streamRunning"))
        backend_on = bool(payload.get("backendRunning"))
        if stream_on and backend_on:
            self._status_dot.configure(text_color=_ACCENT)
            self._status_label.configure(text=f"All Servers Active  ({lan_ip})")
        elif stream_on or backend_on:
            self._status_dot.configure(text_color=_WARNING)
            self._status_label.configure(text=f"Partially Active  ({lan_ip})")
        else:
            self._status_dot.configure(text_color=_DANGER)
            self._status_label.configure(text="Servers Offline")

        # ----- Card 1: Pairing QR -----
        if pairing_url != self._last_pairing_url:
            self._last_pairing_url = pairing_url
            img = self._decode_qr(pairing_url, self._qr_cache_pair)
            if img is not None:
                self._qr_label.configure(image=img, text="")
            else:
                self._qr_label.configure(image=None, text="Waiting for QR…")

        self._pairing_value.configure(text=pairing_url)
        self._pin_value.configure(text=pin)

        # ----- Card 2: Expo QR -----
        if expo_url != self._last_expo_url:
            self._last_expo_url = expo_url
            if expo_url and expo_running:
                img = self._decode_qr(expo_url, self._qr_cache_expo)
                if img is not None:
                    self._expo_qr_label.configure(image=img, text="")
                else:
                    self._expo_qr_label.configure(image=None, text="Expo not running")
            else:
                self._expo_qr_label.configure(image=None, text="Expo not running")

        self._expo_url_value.configure(text=expo_url or f"exp://{lan_ip}:----")

        # ----- Card 3: Services pills -----
        pill_state = {
            "stream": (_ACCENT if stream_on else _TEXT_MUTED, "Running" if stream_on else "Stopped"),
            "backend": (_BLUE if backend_on else _TEXT_MUTED, "Running" if backend_on else "Stopped"),
            "expo": (_PURPLE if expo_running else _TEXT_MUTED, "Running" if expo_running else "Stopped"),
        }
        for key, (color, text) in pill_state.items():
            p = self._pills.get(key)
            if not p:
                continue
            p["dot"].configure(text_color=color)
            p["value"].configure(text=text, text_color=color)

        # Ports
        port_map = {
            "streamPort": payload.get("serverPort") or self._cfg.stream_port,
            "backendPort": payload.get("backendPort") or self._cfg.backend_port,
            "controllerPort": payload.get("controllerPort") or self._cfg.controller_port,
        }
        for k, v in port_map.items():
            label = self._port_labels.get(k)
            if label is not None:
                label.configure(text=str(v))

        # LAN IP
        self._ip_value.configure(text=lan_ip)

    def _decode_qr(self, text: str, cache: "OrderedDict[str, object]"):
        """Decode a QR for ``text`` to a CTkImage, with a small LRU cache."""
        if not text:
            return None
        cached = cache.get(text)
        if cached is not None:
            cache.move_to_end(text)
            return cached
        data_url = _make_qr_data_url(text)
        if not data_url:
            return None
        try:
            from PIL import Image  # noqa: WPS433
            _, b64 = data_url.split(",", 1)
            raw = base64.b64decode(b64)
            img = Image.open(io.BytesIO(raw)).convert("RGBA")
        except Exception:
            return None
        ctk_image = self._ctk.CTkImage(
            light_image=img, dark_image=img, size=(170, 170),
        )
        cache[text] = ctk_image
        cache.move_to_end(text)
        # Trim cache if it grew past the cap.
        while len(cache) > self._QR_CACHE_MAX:
            cache.popitem(last=False)
        return ctk_image

    # ------------------------------------------------------------- public
    def run(self) -> None:
        self.root.mainloop()


# ---------------------------------------------------------------------------
# Bridge: ProcessManager → CustomTkinter (cross-thread safe)
# ---------------------------------------------------------------------------
class _LogBridge:
    """Listens to ProcessManager log/status events and pushes them onto a
    thread-safe queue that the GUI drains from the Tk main loop.
    """

    def __init__(
        self,
        pm: ProcessManager,
        log_queue: "queue.Queue[tuple[str, str]]",
        status_queue: "queue.Queue[dict]",
    ) -> None:
        self._pm = pm
        self._log_queue = log_queue
        self._status_queue = status_queue

    def attach(self) -> None:
        if hasattr(self._pm, "add_log_listener"):
            self._pm.add_log_listener(self._on_log)
        if hasattr(self._pm, "add_status_listener"):
            self._pm.add_status_listener(self._on_status)

        # Mirror standard Python logging records into the GUI log queue
        class _QueueLoggingHandler(logging.Handler):
            def __init__(handler_self, bridge: "_LogBridge") -> None:
                super().__init__()
                handler_self._bridge = bridge

            def emit(handler_self, record: logging.LogRecord) -> None:
                if record.name.startswith("vedi.expo"):
                    return
                try:
                    msg = handler_self.format(record) + "\n"
                    handler_self._bridge._on_log("python-log", msg)
                except Exception:
                    pass

        formatter = logging.Formatter("%(asctime)s %(levelname)-7s [%(name)s] %(message)s", "%H:%M:%S")
        handler = _QueueLoggingHandler(self)
        handler.setFormatter(formatter)
        logging.getLogger().addHandler(handler)

    def _on_log(self, channel: str, message: str) -> None:
        try:
            self._log_queue.put_nowait((channel, message))
        except queue.Full:
            pass

    def _on_status(self, data: dict) -> None:
        try:
            try:
                while True:
                    self._status_queue.get_nowait()
            except queue.Empty:
                pass
            self._status_queue.put_nowait(data)
        except queue.Full:
            pass


# ---------------------------------------------------------------------------
# Public CLI entry
# ---------------------------------------------------------------------------
def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Vedi Pocket PC Desktop Controller")
    p.add_argument("--controller-port", type=int, default=None,
                   help="Override the controller UI port (default: 8090 or whatever was free).")
    p.add_argument("--no-window", action="store_true",
                   help="Run without the CustomTkinter window (still serves the UI over HTTP).")
    p.add_argument("--browser", action="store_true",
                   help="Also open the controller UI in the default web browser on startup.")
    p.add_argument("--no-expo", action="store_true",
                   help="Do not auto-start the Expo / Metro mobile dev server.")
    p.add_argument("--info", action="store_true",
                   help="Print diagnostic info and exit.")
    return p.parse_args()


def _print_info(cfg: AppConfig) -> None:
    print(f"Vedi Pocket PC v{app_version()}")
    print(f"  bundle_root:   {bundle_root()}")
    print(f"  app_root:      {app_root()}")
    print(f"  user_data:     {Path(__file__).parent}")
    print(f"  controller:    http://127.0.0.1:{cfg.controller_port}")
    print(f"  backend:       http://0.0.0.0:{cfg.backend_port}")
    print(f"  stream:        ws://0.0.0.0:{cfg.stream_port}/ws")
    print(f"  LAN IP:        {get_lan_ip()}")


def _run_window(pm: ProcessManager, cfg: AppConfig, open_browser: bool) -> int:
    """Boot the asyncio core on a worker thread, then run the
    CustomTkinter mainloop on the main thread until the window closes.
    """
    log_queue: "queue.Queue[tuple[str, str]]" = queue.Queue(maxsize=20_000)
    status_queue: "queue.Queue[dict]" = queue.Queue(maxsize=64)

    bridge = _LogBridge(pm, log_queue, status_queue)
    bridge.attach()

    expo_dir_ok, expo_dir = _probe_expo_dir()

    stop_async = asyncio.Event()  # type: ignore[var-annotated]

    loop_holder: dict = {"loop": None}
    loop_ready = threading.Event()

    def _asyncio_thread() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop_holder["loop"] = loop
        loop_ready.set()
        try:
            loop.run_until_complete(
                _run_controller_async(pm, cfg, stop_event=stop_async)
            )
        except Exception:
            log.exception("Asyncio core crashed.")
        finally:
            try:
                loop.close()
            except Exception:
                pass

    worker = threading.Thread(
        target=_asyncio_thread, name="vedi.asyncio", daemon=True
    )
    worker.start()
    loop_ready.wait(timeout=5.0)

    if not _wait_for_port_open(cfg.controller_port, timeout=10.0):
        log.error(
            "Controller port %d never started listening; aborting.",
            cfg.controller_port,
        )
        stop_async.set()
        return 1

    if open_browser:
        try:
            webbrowser.open(f"http://127.0.0.1:{cfg.controller_port}")
        except Exception:
            pass

    try:
        window = ControllerWindow(
            pm, cfg, log_queue, status_queue,
            expo_dir=expo_dir if expo_dir_ok else "",
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("CustomTkinter window failed to build: %s", exc)
        stop_async.set()
        return 1

    try:
        window.run()
    except Exception:  # noqa: BLE001
        log.exception("CustomTkinter mainloop crashed.")
    finally:
        stop_async.set()
        main_loop = loop_holder["loop"]
        if main_loop is not None and main_loop.is_running():
            try:
                main_loop.call_soon_threadsafe(main_loop.stop)
            except Exception:
                pass
        worker.join(timeout=5.0)

    return 0


def _wait_for_port_open(port: int, *, host: str = "127.0.0.1", timeout: float = 10.0) -> bool:
    """Poll ``host:port`` until something accepts a TCP connection, or
    ``timeout`` seconds elapse.
    """
    import socket as _socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with _socket.create_connection((host, port), timeout=0.4):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def main() -> int:
    args = _parse_args()
    configure_logging()
    _install_appusermodel_id()

    cfg = load_config()
    cfg.controller_port = find_free_port(args.controller_port or cfg.controller_port)
    if args.no_expo:
        cfg.expo_enabled = False

    if args.info:
        _print_info(cfg)
        return 0

    pm = ProcessManager(config=cfg)

    if args.no_window:
        try:
            asyncio.run(_run_controller_async(pm, cfg))
        except KeyboardInterrupt:
            log.info("KeyboardInterrupt — exiting.")
        except Exception:
            log.exception("Unhandled fatal error.")
            return 1
        return 0

    return _run_window(pm, cfg, open_browser=bool(args.browser))


if __name__ == "__main__":
    raise SystemExit(main())
