# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ``VediRemote.exe`` (legacy build).

Builds a single Windows executable that bundles just enough Python
dependencies to drive the in-process controller / UI shell.  The
``scripts/launcher.py`` entry dispatches to:

* The QR-code UI controller (in-process), OR
* The FastAPI control agent (spawned as a subprocess), OR
* The aiohttp screen-stream server (spawned as a subprocess),

based on inherited env vars (STREAM_PORT / BACKEND_PORT) that the
controller already passes when launching its children.  See
``scripts/launcher.py`` for the dispatch detail.

This spec is intentionally conservative — PyInstaller 6.x with
Python 3.14 can hang during heavy ``collect_all`` passes, so we
ship a tiny data manifest and let PyInstaller's analyser find
everything else by following ``scripts/launcher.py``'s imports.
"""

import os


# ---------------------------------------------------------------------------
# Resolve repo layout (PyInstaller provides ``SPEC`` as the spec file path).
# ---------------------------------------------------------------------------
# ``SPEC`` lives in apps/desktop/controller/legacy/; the repo root is
# three parents up from it.
REPO = os.path.abspath(os.path.join(os.path.dirname(SPEC), "..", "..", "..", ".."))


# ---------------------------------------------------------------------------
# Bundled data files — only what the controller's aiohttp server serves
# verbatim.  No ``collect_all``.  No heavy backend data trees.
# ---------------------------------------------------------------------------
data_files = [
    (os.path.join(REPO, "apps", "desktop", "controller", "index.html"), "index.html"),
    (os.path.join(REPO, "apps", "desktop", "controller", "styles.css"), "styles.css"),
    (os.path.join(REPO, "apps", "desktop", "controller", "renderer.js"), "renderer.js"),
    (os.path.join(REPO, "apps", "desktop", "controller", "logo.jpeg"), "logo.jpeg"),
    (os.path.join(REPO, "apps", "desktop", "controller", "logo.ico"), "logo.ico"),

    # Bundled source trees the spawned children resolve via __file__.
    # These are loaded as data (not as frozen modules) so PyInstaller
    # does NOT analyse their imports.  PyInstaller follows import
    # statements; loadable source on disk is fine to leave as data.
    (os.path.join(REPO, "apps", "desktop", "controller", "legacy"), "apps/desktop/controller/legacy"),
    (os.path.join(REPO, "apps", "agent", "server"),                  "apps/agent/server"),
    (os.path.join(REPO, "apps", "streamer", "server"),               "apps/streamer/server"),
    (os.path.join(REPO, "packages"),                                  "packages"),
    (os.path.join(REPO, "infrastructure"),                            "infrastructure"),
]


# ---------------------------------------------------------------------------
# Hidden imports — the only ones the analyse step is likely to miss.
# Keep this list TINY; PyInstaller's analyser auto-detects everything
# reachable through ``import`` statements in our code.
# ---------------------------------------------------------------------------
hiddenimports = [
    # Controller runtime only.  The FastAPI agent (apps/agent/server)
    # and aiohttp screen-stream server are bundled as DATA, not as
    # frozen modules, because they're spawned as separate processes via
    # ``runpy.run_path`` at runtime (see scripts/launcher.py).  Their
    # imports - including ``agent_core`` - are resolved from the
    # ``packages/`` directory at runtime, not from the frozen graph,
    # so they don't need to appear here.
    "aiohttp", "qrcode", "psutil",

    # Both ``runpy``-spawned subprocesses (FastAPI control agent and
    # aiohttp screen-stream server) execute INSIDE the bootloader
    # Python - there's no separate system Python at runtime - so
    # their imports MUST live in the frozen module archive
    # (sys._MEIPASS contains data files only, not importable modules).
    # PyInstaller's auto-discover can find these via ``aiohttp`` /
    # ``fastapi``'s transitive tree, but listing them explicitly here
    # guarantees the bundle covers them.  Without these, the spawned
    # subprocesses raise ``ModuleNotFoundError`` for PIL, mss, etc.
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "mss",
    "pyautogui",
    "pycaw",
    "pycaw.pycaw",
    "comtypes",
    "pystray",
    "PIL._tkinter_finder",   # sometimes pulled by pystray on Windows
]


binaries = []


# ---------------------------------------------------------------------------
# Build.  ``noarchive=False`` keeps the PYZ archive for fast loading;
# ``excludes`` trims transitive junk to keep the binary small.
# ---------------------------------------------------------------------------
a = Analysis(
    [os.path.join(REPO, "scripts", "launcher.py")],
    pathex=[REPO],
    binaries=binaries,
    datas=data_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim unused scientific / plotting stack (transitive; we don't
        # exercise them at runtime).
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "tkinter",
        # Trim big Azure / cloud SDKs that PyInstaller's analyser might
        # spot via transitive imports - we don't use them.
        "azure",
        "boto3",
        "botocore",
        "google",
        # NOTE: PIL, mss, pyautogui, pycaw, comtypes, pythoncom, pystray
        # are NOT excluded - the spawned subprocesses (FastAPI agent and
        # screen-stream server) actually import them at runtime via
        # ``runpy.run_path``, which uses the bootloader Python. The only
        # ``sys.path`` they have is the bundle root + frozen modules, so
        # they MUST be frozen - excluding them causes ModuleNotFoundError
        # for PIL (and similar) the first time the screen stream or the
        # control agent tries to import.
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="VediRemote",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                # no console window for end-users
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(REPO, "logo.ico") if os.path.isfile(os.path.join(REPO, "logo.ico")) else None,
)
