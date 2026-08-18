"""Compute SHA-256 of a file and emit "<hash>  <name>" to stdout.

Used by build.bat's GENERATE_CHECKSUMS.  Kept as a tiny standalone
script so the batch file can avoid the nasty inline ``python -c``
inside ``for /f`` command-substitution blocks (those fight CMD's
tokenizer when the Python source contains apostrophes).
"""

from __future__ import annotations

import hashlib
import sys


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write("usage: hash_sha256.py <file>\n")
        return 1
    print(sha256(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
