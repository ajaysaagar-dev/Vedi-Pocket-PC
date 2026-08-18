"""Top-level launcher for the PyInstaller-frozen Vedi Pocket PC EXE.

When the bootloader runs ``app.py`` it sets ``__name__ = "__main__"``
and leaves ``__package__`` empty, so the relative imports at the top
of ``app.py`` (``from .paths import ...``) raise
``ImportError: attempted relative import with no known parent
package``.

This module exists solely to give the bootloader a *real* package
member to import. It is the entry point declared in
``VediPocketPC.spec``. Its only job is to import the composition root
as a member of the ``apps.desktop.controller`` package — the relative
imports inside ``app.py`` then resolve correctly.

In a developer checkout you do not need this file at all; run
``python -m apps.desktop.controller.app`` instead.
"""

from __future__ import annotations

from apps.desktop.controller.app import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())