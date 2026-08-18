"""Application path resolution for Vedi Pocket PC.

Works correctly in three scenarios:

* **Development source layout** — running from the repository. The
  "app root" is the parent directory of the repository (where this
  file's parent package sits in ``vedi_app/``).
* **PyInstaller onedir bundle** (``VediPocketPC/`` directory with
  ``VediPocketPC.exe`` plus ``_internal/`` siblings).
* **PyInstaller onefile bundle** — PyInstaller extracts to ``sys._MEIPASS``
  on every launch.

Never call ``os.getcwd()`` or assume the current working directory —
the EXE is double-clicked from anywhere on disk and the working
directory is undefined.

Three distinct locations are exposed:

* ``app_root()`` — the directory containing the EXE for a packaged
  build, or the repository root in development. Read-only bundled
  resources live here (``assets/``, ``index.html``).
* ``bundle_root()`` — the directory holding **frozen** files. When
  running from a onefile bundle this is ``sys._MEIPASS`` (a temp
  directory). When running from an onedir bundle this is
  ``<app_root>/_internal``. In development this is the repository
  root. PyInstaller's bootloader finds importable modules here.
* ``user_data_dir()`` — the per-user writable directory
  (``%LOCALAPPDATA%\\Vedi Pocket PC`` on Windows). Logs, persisted
  pairing tokens, and runtime state live here. The application
  *never* writes inside Program Files because that requires admin
  rights and corrupts on uninstall.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


APP_NAME = "Vedi Pocket PC"
APP_PUBLISHER = "Vedi"
APP_DATA_DIRNAME = "Vedi Pocket PC"


def is_frozen() -> bool:
    """True when running from a PyInstaller bundle (onefile or onedir)."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def bundle_root() -> Path:
    """Directory holding the frozen module archive and bundled data files.

    * Onefile build: ``sys._MEIPASS`` (a per-launch temp directory).
    * Onedir build: ``<install_dir>/_internal``.
    * Source run: the repository root.
    """
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))  # type: ignore[arg-type]
    # Source layout — this file is at <repo>/apps/desktop/controller/paths.py,
    # so the repo root is 3 directories up.
    return Path(__file__).resolve().parents[3]


def app_root() -> Path:
    """The directory containing the running EXE.

    * Onedir build: the same directory as ``VediPocketPC.exe``.
    * Onefile build: the directory the user launched the EXE from
      (``sys.executable`` lives there).
    * Source run: the repository root, like ``bundle_root``.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return bundle_root()


def user_data_dir() -> Path:
    """Per-user writable directory under ``%LOCALAPPDATA%``.

    Creates the folder on first call so the application never has to
    worry about races when multiple modules initialize at the same
    time.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    path = Path(base) / APP_DATA_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    """Directory for production log files. Created on demand."""
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def resources_dir() -> Path:
    """Directory holding read-only assets shipped with the EXE.

    * Onedir build: ``<install_dir>/assets`` (sibling of the EXE).
    * Onefile build: ``sys._MEIPASS/assets`` because everything is
      extracted under ``_MEIPASS``.
    * Source run: ``<repo>/assets`` if it exists, else the repo root.
    """
    if is_frozen():
        return bundle_root() / "assets"
    candidate = bundle_root() / "assets"
    return candidate if candidate.is_dir() else bundle_root()


def asset(name: str) -> Optional[Path]:
    """Resolve a bundled asset by name and return its absolute path, or None."""
    for base in (resources_dir(), bundle_root()):
        candidate = base / name
        if candidate.is_file():
            return candidate
    return None


def app_version() -> str:
    """Single source of truth for the application version string.

    Reads from ``packaging/version_info.txt`` in production or
    ``version.txt`` in the repository root. Falls back to the
    constant if both files are missing (e.g. running from source
    against an old checkout).
    """
    for candidate in (
        bundle_root() / "VERSION",
        bundle_root() / "packaging" / "VERSION",
        app_root() / "VERSION",
    ):
        if candidate.is_file():
            try:
                return candidate.read_text(encoding="utf-8").strip()
            except OSError:
                pass
    return "1.0.0"
