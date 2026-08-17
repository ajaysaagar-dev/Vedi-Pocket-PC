"""Vedi Pocket PC — Root Entry Point."""

from __future__ import annotations

import sys
import os

# Ensure repo root is in sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from controller.main import main

if __name__ == "__main__":
    main()
