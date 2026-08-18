"""Vedi Pocket PC — Root Entry Point.

Backwards-compatible launcher: existing scripts (`python main.py`,
`python controller/main.py`) keep working in development. The
canonical entry point is now ``apps.desktop.controller.app.main`` —
the function PyInstaller's spec file targets for the packaged EXE.
"""

from __future__ import annotations

import os
import sys


_HERE = os.path.dirname(os.path.abspath(__file__))
_APPS_CONTROLLER = os.path.abspath(os.path.join(_HERE, os.pardir))
if _APPS_CONTROLLER not in sys.path:
    sys.path.insert(0, _APPS_CONTROLLER)


from app import main as _production_main  # noqa: E402


def main() -> None:
    _production_main()


if __name__ == "__main__":
    raise SystemExit(main())
