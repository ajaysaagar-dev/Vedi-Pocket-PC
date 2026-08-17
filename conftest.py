"""Root pytest configuration.

Ensures agent_core, vedi-pocketpc-backend, and screen-stream-server are all
importable across test suites.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
PATHS = [
    REPO_ROOT,
    os.path.join(REPO_ROOT, "packages", "agent-core"),
    os.path.join(REPO_ROOT, "vedi-pocketpc-backend"),
    os.path.join(REPO_ROOT, "screen-stream-server"),
    os.path.join(REPO_ROOT, "controller"),
]

for p in PATHS:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
