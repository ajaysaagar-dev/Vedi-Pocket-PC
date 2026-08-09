"""pytest config — make `agent_core` importable without installing it.

Tests run from a fresh checkout where `pip install -e .` hasn't
happened yet. Prepending the package root to `sys.path` lets us
import the module directly.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
