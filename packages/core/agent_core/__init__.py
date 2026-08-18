"""agent_core — shared domain package.

Holds the hexagonal-architecture primitives (entities, ports, use cases,
adapters) that both the FastAPI control agent (vedi-pocketpc-backend) and
the screen-stream-server depend on. The duplication of mouse / keyboard /
volume / power logic that used to live in two separate servers is now
collapsed into a single InputController + SystemController pair, wired
together in their respective composition roots.
"""

__version__ = "1.0.0"
