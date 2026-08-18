"""Generate SHA256SUMS.txt for a release folder.

Used by build.bat's :GENERATE_CHECKSUMS subroutine.  Lives in a
standalone script so the batch file doesn't have to wrestle with
CMD's hostile ``for /f`` + ``setlocal EnableDelayedExpansion``
interaction that bit us in earlier iterations.

Invocation:
    python scripts/write_checksums.py <release_dir> <output_file>
"""

from __future__ import annotations

import hashlib
import os
import sys


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_release_artifacts(directory: str) -> list[tuple[str, str]]:
    """Return ``[(absolute path, base name)]`` for the files in the
    release folder that should be hashed."""
    out: list[tuple[str, str]] = []
    for name in (
        "VediRemote.exe",
        "VediRemote*.apk",
        "VediRemote*.aab",
        "VediRemote*.apks",
    ):
        import glob

        for path in glob.glob(os.path.join(directory, name)):
            out.append((path, os.path.basename(path)))
    return out


def main() -> int:
    if len(sys.argv) != 3:
        sys.stderr.write("usage: write_checksums.py <release_dir> <output_file>\n")
        return 1

    release_dir = sys.argv[1]
    output = sys.argv[2]

    if not os.path.isdir(release_dir):
        sys.stderr.write(f"release dir not found: {release_dir}\n")
        return 1

    artifacts = collect_release_artifacts(release_dir)
    if not artifacts:
        sys.stderr.write(f"no artifacts found in {release_dir}\n")
        return 1

    lines = []
    for path, name in sorted(artifacts):
        digest = sha256(path)
        lines.append(f"{digest}  {name}")
        print(f"  hashed: {name}")

    with open(output, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print(f"wrote {output} ({len(lines)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
