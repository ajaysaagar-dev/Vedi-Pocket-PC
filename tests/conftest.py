"""Root pytest configuration.

Ensures agent_core, infrastructure, the apps (agent server, streamer
server, desktop controller), and the protocol packages are all
importable across test suites.
"""

from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
PATHS = [
    os.path.join(REPO_ROOT, "apps", "desktop", "controller", "legacy"),
    os.path.join(REPO_ROOT, "apps", "desktop", "controller"),
    os.path.join(REPO_ROOT, "apps", "streamer", "server"),
    os.path.join(REPO_ROOT, "apps", "agent", "server"),  # agent-server first so `main` resolves here
    os.path.join(REPO_ROOT, "packages", "core"),         # agent_core
    REPO_ROOT,                                           # `infrastructure`, `protocol` resolve via this
    os.path.join(REPO_ROOT, "packages"),                 # protocol (already in repo root namespace)
]

for p in PATHS:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
