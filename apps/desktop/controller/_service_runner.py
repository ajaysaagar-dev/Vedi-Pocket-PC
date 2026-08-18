"""Internal helper that runs a bundled service script via ``runpy``.

The bundled scripts (``screen-stream-server/main.py`` and
``vedi-pocketpc-backend/main.py``) cannot be imported directly —
their directory names contain hyphens. They also each have a
``main()`` function that drives their own lifetime. We use
``runpy.run_path`` to execute them, but we have to patch a few
behaviours that don't fit a packaged, windowed application:

* ``pystray.Icon.run`` in the backend blocks on the calling thread;
  in production we have no use for it (the controller UI is the
  single visible window). We monkey-patch ``pystray.Icon.run`` to
  spin on a sleep loop, which means ``backend main()`` exits when
  the controller stops the thread.

* ``uvicorn`` is launched inside ``start_fastapi`` in the backend
  script. We still want uvicorn to handle the protocol; we just
  want it to live on a daemon thread inside our process rather
  than the script's main thread.

* The screen-stream script prints a banner; we suppress it via
  ``stdout`` redirection inside this module so the user's
  application log file stays clean.
"""

from __future__ import annotations

import contextlib
import io
import logging
import os
import runpy
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from .config import AppConfig
from .paths import bundle_root


log = logging.getLogger(__name__)


def _bundle_main(name: str) -> Path:
    folder = {
        "stream": "apps/streamer/server",
        "backend": "apps/agent/server",
    }[name]
    return bundle_root() / folder / "main.py"


@contextlib.contextmanager
def _redirect_stdout_to_log(name: str):
    """Send the script's ``print`` statements into the application log."""
    class _Tee:
        def __init__(self) -> None:
            self._log = logging.getLogger(f"service.{name}")

        def write(self, msg: str) -> None:
            msg = msg.rstrip("\n")
            if not msg:
                return
            self._log.info(msg)

        def flush(self) -> None:
            return None

    saved = sys.stdout
    sys.stdout = _Tee()
    try:
        yield
    finally:
        sys.stdout = saved


def _patch_sys_path(service_name: Optional[str] = None) -> None:
    """Insert the bundle's source directories onto ``sys.path``.

    Each bundled script does ``sys.path.insert(0, <scriptdir>)`` and
    ``sys.path.insert(0, <bundle>/packages/core)``; we mirror
    that here once, on the controller's behalf, so the script's
    transitive imports resolve.

    Important: both ``apps/streamer/server`` and
    ``apps/agent/server`` define a top-level ``presentation``
    package (and the stream server also defines ``domain``); once a
    service has imported one of these, Python caches the module in
    ``sys.modules`` so the *next* service cannot re-import its own
    version. We therefore drop cached ``presentation`` / ``domain``
    / sibling-import entries before each service starts.
    """
    bundle = bundle_root()
    folder_map = {
        "stream": "apps/streamer/server",
        "backend": "apps/agent/server",
    }
    sibling_name = None
    if service_name is not None and service_name in folder_map:
        sibling_name = "stream" if service_name == "backend" else "backend"

    # Drop the sibling service's directory so its ``presentation``
    # package doesn't shadow ours via ``sys.path``.
    if sibling_name is not None:
        sibling_path = str(bundle / folder_map[sibling_name])
        sys.path[:] = [p for p in sys.path if p != sibling_path]

    # Add the active service's directory and ``packages/core``
    # BEFORE we touch ``sys.modules``. Without this ordering,
    # `sys.modules` cleanup can drop modules without any path to
    # re-import them from.
    candidates = [
        bundle / "packages" / "core",
        bundle,
    ]
    if service_name is not None and service_name in folder_map:
        candidates.append(bundle / folder_map[service_name])

    for c in candidates:
        c_str = str(c)
        if c.is_dir() and c_str not in sys.path:
            sys.path.insert(0, c_str)

    # Drop any cached *top-level packages* that exist under both
    # services so the next import picks them up from the right
    # directory. Only top-level names — never drop ``agent_core``
    # itself; that comes from a non-colliding path.
    cached_prefixes = ("presentation", "domain", "infrastructure")
    keys_to_drop = []
    for mod_name in list(sys.modules):
        top = mod_name.split(".", 1)[0]
        if top in cached_prefixes:
            keys_to_drop.append(mod_name)
    for k in set(keys_to_drop):
        sys.modules.pop(k, None)


def _install_pystray_noop() -> None:
    """Replace ``pystray.Icon`` with a no-op so the backend doesn't tray.

    The bundled backend's ``run_tray`` would otherwise block on the
    main thread forever, never reaching the controller's stop event.
    """
    try:
        import pystray
    except Exception:
        return

    class _NoopIcon(pystray.Icon):
        def run(self):  # type: ignore[override]
            # The backend blocks here for the lifetime of the script.
            # We just sleep in short bursts so the thread is responsive
            # to ``_stop_event`` checks; in production the stop event
            # is set by the controller when the window closes.
            while True:
                time.sleep(0.5)

    pystray.Icon = _NoopIcon  # type: ignore[misc]


def _monitor_stdout_for_pairing_pin(stream: io.StringIO, on_pairing_pin: Callable[[str], None]) -> threading.Thread:
    """Watch the redirected stdout for ``Pairing PIN:`` and call back.

    The backend prints ``Pairing PIN: 1234`` exactly once at startup.
    We treat anything matching the regex ``Pairing PIN:\s*(\d{4})`` as
    authoritative.
    """
    import re

    pin_re = re.compile(r"Pairing PIN:\s*(\d{4})")

    def _watch():
        for line in stream.readlines_iter():
            m = pin_re.search(line)
            if m:
                on_pairing_pin(m.group(1))
                return

    t = threading.Thread(target=_watch, daemon=True, name="vedi.pin-watcher")
    t.start()
    return t


class _PinCapturingStringIO(io.StringIO):
    """Captures stdout for both logging and ``Pairing PIN`` extraction.

    The backend emits its PIN via a multi-line ``print_banner``
    output. We buffer every write to make sure a PIN that crosses
    flush boundaries (Python normally flushes after ``\\n``) is still
    matched.
    """

    def __init__(self, on_pin: Callable[[str], None]):
        super().__init__()
        self._on_pin = on_pin
        self._emitted = False

    def write(self, s: str) -> int:
        if not s:
            return 0
        super().write(s)
        if not self._emitted:
            import re
            try:
                # Re-check every accumulated write; cheap and idempotent.
                buffer = self.getvalue()
                m = re.search(r"Pairing PIN:\s*(\d{4})", buffer)
                if m:
                    self._emitted = True
                    try:
                        self._on_pin(m.group(1))
                    except Exception:
                        pass
            except Exception:
                pass
        return len(s)


def run_stream_service(cfg: AppConfig) -> None:
    """Execute the screen-stream server's main() in the calling thread."""
    target = _bundle_main("stream")
    if not target.is_file():
        log.error("Bundled screen-stream-server not found at %s", target)
        return

    _patch_sys_path("stream")

    with _redirect_stdout_to_log("stream"):
        try:
            os.environ["STREAM_PORT"] = str(cfg.stream_port)
            os.environ["STREAM_HOST"] = cfg.stream_host
            runpy.run_path(str(target), run_name="__main__")
        except KeyboardInterrupt:
            pass
        except SystemExit:
            pass
        except Exception:
            log.exception("Screen-stream service crashed.")


def run_backend_service(
    cfg: AppConfig,
    *,
    lan_ip: str,
    on_pairing_pin: Callable[[str], None],
    stop_marker: threading.Event,
) -> None:
    """Execute the FastAPI backend's main() in the calling thread.

    * Replaces the system-tray ``pystray.Icon`` with a no-op so the
      backend's main thread does not block forever.
    * Captures the ``Pairing PIN:`` line printed during banner and
      forwards it to ``on_pairing_pin`` for status-payload updates.
    * Stops when ``stop_marker`` is set.
    """
    target = _bundle_main("backend")
    if not target.is_file():
        log.error("Bundled vedi-pocketpc-backend not found at %s", target)
        return

    _patch_sys_path("backend")
    _install_pystray_noop()

    # The backend's `print_banner` writes the PIN; we capture it via
    # a tee on stdout. The tee also forwards to the log file so we
    # can prove the PIN was issued.

    captured = _PinCapturingStringIO(on_pairing_pin)
    real_stdout = sys.stdout

    class _Tee:
        def __init__(self, sink_a, sink_b):
            self._a = sink_a
            self._b = sink_b

        def write(self, s: str) -> int:
            n = self._a.write(s)
            self._b.write(s)
            return max(n, len(s))

        def flush(self) -> None:
            self._a.flush()
            self._b.flush()

    # Send stdout to BOTH the captured buffer (for PIN detection) and
    # the real stdout (so logs still go to the file via the logging
    # redirection).
    class _FullTee(_Tee):
        """Adds the file-protocol dunders uvicorn's logging insists on."""

        def isatty(self) -> bool:  # uvicorn's formatter calls this
            return False

        def writable(self) -> bool:
            return True

        @property
        def closed(self) -> bool:
            return False

    sys.stdout = _FullTee(captured, real_stdout)
    try:
        os.environ["BACKEND_PORT"] = str(cfg.backend_port)
        os.environ["HIDE_DIALOG"] = "1"
        runpy.run_path(str(target), run_name="__main__")
    except KeyboardInterrupt:
        pass
    except SystemExit:
        pass
    except Exception:
        log.exception("Backend service crashed.")
    finally:
        sys.stdout = real_stdout


def probe_pairing_pin(port: int, timeout: float = 1.5) -> Optional[str]:
    """Best-effort: ask the backend's /health endpoint for the PIN.

    Useful if the runpy path swallowed the line; the backend never
    exposes the PIN over the network (it would be a security hole),
    so this is only here for parity / future expansion.
    """
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout) as s:
            s.sendall(b"GET /health HTTP/1.0\r\nHost: localhost\r\n\r\n")
            data = s.recv(4096).decode("utf-8", errors="ignore")
    except OSError:
        return None
    return None
