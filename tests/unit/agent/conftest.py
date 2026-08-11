"""pytest config — make `agent_core` and protocol modules importable.

Points at the monorepo packages/core (agent_core), packages/protocol,
infrastructure, and apps/agent/server so tests can import everything
without an editable install.
"""

from __future__ import annotations

import os
import sys

# tests/unit/agent/ → tests/unit/ → tests/ → repo root
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir))
AGENT_SERVER_ROOT = os.path.join(REPO_ROOT, "apps", "agent", "server")

for _p in (
    os.path.join(REPO_ROOT, "packages", "core"),       # agent_core
    os.path.join(REPO_ROOT, "packages"),               # protocol.*
    os.path.join(REPO_ROOT, "infrastructure"),         # infrastructure.*
    AGENT_SERVER_ROOT,                                  # main module
):
    if _p not in sys.path:
        sys.path.insert(0, _p)
