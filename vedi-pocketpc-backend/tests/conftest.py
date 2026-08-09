"""pytest config — make `agent_core` importable from a clean checkout.

We point at `packages/agent-core` (the directory that contains the
`agent_core/` Python package) so tests can `import agent_core` without
an editable install.
"""

from __future__ import annotations

import os
import sys

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
REPO_ROOT = os.path.abspath(os.path.join(BACKEND_ROOT, os.pardir))
AGENT_CORE_ROOT = os.path.join(REPO_ROOT, "packages", "agent-core")
if AGENT_CORE_ROOT not in sys.path:
    sys.path.insert(0, AGENT_CORE_ROOT)
