"""pytest config — make `agent_core` importable without installing it.

Points `sys.path` at packages/core (the directory containing the
`agent_core/` Python package) so tests can run from a clean checkout
without `pip install -e ./packages/core`.
"""

from __future__ import annotations

import os
import sys

# tests/unit/core/ → tests/unit/ → tests/ → repo root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
ROOT = os.path.join(REPO_ROOT, "packages", "core")  # contains agent_core/
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
