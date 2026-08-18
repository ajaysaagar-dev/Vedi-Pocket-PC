"""Run a Python source tree from disk using ``runpy.run_path``.

PyInstaller's analyser cannot import modules whose directory name
contains a hyphen (``screen-stream-server``, ``vedi-pocketpc-backend``)
— Python identifier rules forbid the hyphen in dotted import paths.
We therefore bundle the source trees as **data** and load them via
``runpy.run_path`` instead of freezing them.

The trade-off:

* **Pro** — no symlinks or renames during the build; the on-disk
  layout survives packaging unchanged.
* **Con** — the bundled scripts see only the frozen module archive
  for their transitive ``import`` statements, so all of their
  dependencies (PIL, mss, pyautogui, fastapi, …) **must** be frozen
  and listed in ``hiddenimports``. The PyInstaller spec does this.

The loader also sets up ``sys.path`` so the bundled scripts find
``packages/core`` at the right relative location.
"""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path
from typing import Any, Callable

from .paths import bundle_root


def _scripts_dir() -> Path:
    """Bundle directory containing ``apps/streamer/server`` /
    ``apps/agent/server`` source trees.

    When frozen, PyInstaller copies the relevant directories next to
    the EXE in ``_internal/``. When running from source the same
    tree sits at the repository root.
    """
    return bundle_root()


def script_path(name: str) -> Path:
    """Resolve a service's ``main.py`` from the bundle root."""
    folder_map = {
        "stream": "apps/streamer/server",
        "backend": "apps/agent/server",
    }
    if name not in folder_map:
        raise KeyError(name)
    return _scripts_dir() / folder_map[name] / "main.py"


def load_script(name: str, *, extra_argv: Any = None) -> Callable[[], Any]:
    """Return a thunk that runs a service script under ``runpy``.

    The thunk installs ``<bundle>/packages/core`` on ``sys.path``
    first so the ``agent_core`` package the script imports is
    resolvable in a frozen bundle.
    """
    target = script_path(name)
    bundle = _scripts_dir()
    extra_path = bundle / "packages" / "core"
    extra_argv = [str(target)] if extra_argv is None else list(extra_argv)

    def _runner() -> Any:
        if str(extra_path) not in sys.path and extra_path.is_dir():
            sys.path.insert(0, str(extra_path))
        if str(bundle) not in sys.path:
            sys.path.insert(0, str(bundle))
        saved_argv = sys.argv
        sys.argv = extra_argv
        try:
            return runpy.run_path(str(target), run_name="__main__")
        finally:
            sys.argv = saved_argv

    return _runner
