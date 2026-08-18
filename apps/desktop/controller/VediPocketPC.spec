# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ``VediPocketPC.exe`` (production build).

Outputs a **onedir** distribution::

    dist/
      VediPocketPC/
        VediPocketPC.exe
        _internal/
          apps/
            desktop/controller/    # the production composition root + legacy UI
            agent/server/          # bundled as data (see note below)
            streamer/server/       # bundled as data (see note below)
          packages/
            core/agent_core/...
          <frozen modules>
          logo.ico
          index.html
          styles.css
          renderer.js
          logo.jpeg
          VERSION

Why the two service trees are bundled as DATA, not as frozen
modules:

* Their dotted paths now live under ``apps/{agent,streamer}/server``
  which works as an import target, but the production strategy
  freezes only the controller and loads the others via
  ``runpy.run_path`` so each service can mutate its own ``sys.path``
  independently.
* Their many transitive imports (PIL, mss, pyautogui, fastapi,
  uvicorn, comtypes, pycaw, pystray, zeroconf, qrcode) ARE frozen
  — that's what ``hiddenimports`` below lists.
* The controller invokes them via ``runpy.run_path`` (see
  ``apps/desktop/controller/_service_runner.py``). Their first
  action is to add ``<bundle>/packages/core`` to ``sys.path``,
  which works because that directory is bundled along with
  everything else.
"""

import os

from PyInstaller.utils.hooks import collect_submodules


SPEC_DIR = os.path.abspath(os.path.dirname(SPEC))
REPO = os.path.abspath(os.path.join(SPEC_DIR, "..", "..", ".."))


# ---------------------------------------------------------------------------
# Data files shipped with the EXE (assets, static HTML, services as data).
# ---------------------------------------------------------------------------
data_files = []

# Bundled static assets served by the controller UI. They live inside
# ``apps/desktop/controller/`` in the repo (NOT at the repo root), so
# look there first and fall back to the legacy top-level layout.
CONTROLLER_DIR = os.path.join(REPO, "apps", "desktop", "controller")
for filename in ("index.html", "styles.css", "renderer.js", "logo.jpeg", "logo.ico"):
    candidate = (
        os.path.join(CONTROLLER_DIR, filename)
        if os.path.isfile(os.path.join(CONTROLLER_DIR, filename))
        else os.path.join(REPO, filename)
    )
    if os.path.isfile(candidate):
        data_files.append((candidate, "."))

# Version metadata (read by ``apps/desktop/controller/paths.py``).
for version_candidate in (
    os.path.join(REPO, "VERSION"),
    os.path.join(REPO, "packaging", "VERSION"),
    os.path.join(CONTROLLER_DIR, "VERSION"),
):
    if os.path.isfile(version_candidate):
        data_files.append((version_candidate, "."))
        break

# The two service source trees get bundled verbatim. PyInstaller will
# *not* analyse their imports — those imports live in the frozen
# module archive (see hiddenimports below) so the runpy loader
# can resolve them at runtime.
for sub in ("apps/agent/server", "apps/streamer/server"):
    full = os.path.join(REPO, sub)
    if os.path.isdir(full):
        data_files.append((full, sub))

# Project-local packages used by the backend's main.py. These are
# top-level Python packages that live outside ``apps/`` so PyInstaller
# cannot auto-discover them; without them the runpy loader cannot
# resolve ``infrastructure.*`` and ``protocol.*`` imports.
infrastructure_dir = os.path.join(REPO, "infrastructure")
if os.path.isdir(infrastructure_dir):
    data_files.append((infrastructure_dir, "infrastructure"))

protocol_dir = os.path.join(REPO, "packages", "protocol")
if os.path.isdir(protocol_dir):
    data_files.append((protocol_dir, os.path.join("packages", "protocol")))

# Bundled Python source for the shared agent-core package.
agent_core_dir = os.path.join(REPO, "packages", "core", "agent_core")
if os.path.isdir(agent_core_dir):
    data_files.append((agent_core_dir, os.path.join("packages", "core", "agent_core")))

agent_core_pyproject = os.path.join(REPO, "packages", "core", "pyproject.toml")
if os.path.isfile(agent_core_pyproject):
    data_files.append((agent_core_pyproject, os.path.join("packages", "core")))


# ---------------------------------------------------------------------------
# Hidden imports — every transitive dependency the bundled scripts
# (``apps/agent/server``, ``apps/streamer/server``) actually
# import. PyInstaller's analyser cannot reach them because we ship
# the source as data, not as frozen modules.
# ---------------------------------------------------------------------------
hiddenimports = []

# --- Controller (frozen as a normal Python package) ---
hiddenimports += collect_submodules("apps.desktop.controller")

# --- aiohttp (controller + screen-stream) ---
hiddenimports += [
    "aiohttp",
    "aiohttp.web",
    "aiohttp.web_runner",
    "aiohttp.web_urldispatcher",
]

# --- FastAPI / uvicorn (backend) ---
hiddenimports += [
    "fastapi",
    "fastapi.params",
    "fastapi.dependencies",
    "fastapi.routing",
    "fastapi.middleware",
    "fastapi.middleware.cors",
    "starlette",
    "starlette.applications",
    "starlette.responses",
    "starlette.routing",
    "starlette.middleware.cors",
    "uvicorn",
    "uvicorn.config",
    "uvicorn.server",
    "uvicorn.loops",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
]

# --- Drivers and OS glue (used by screen-stream and backend) ---
hiddenimports += [
    "mss",
    "mss.windows",
    "pyautogui",
    "pyautogui._pyautogui_win",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "PIL._tkinter_finder",
    "pycaw",
    "pycaw.pycaw",
    "comtypes",
    "comtypes.server",
    "pystray",
    "pystray._win32",
    "zeroconf",
    "zeroconf.asyncio",
    "psutil",
    "psutil._pswindows",
    "qrcode",
    "qrcode.image",
    "qrcode.image.pil",
    "qrcode.image.styledpil",
    "qrcode.constants",
    "websockets",
    "websockets.sync",
    "websockets.sync.client",
    "wsproto",
]

# --- Packages we ship as DATA (the bundled services import them by
# their dotted name; PyInstaller needs to be told they exist).
hiddenimports += collect_submodules("agent_core")


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
a = Analysis(
    [os.path.join(REPO, "apps", "desktop", "controller", "launch.py")],
    pathex=[REPO],
    binaries=[],
    datas=data_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Trim large unused stacks so the bundle stays small.
    excludes=[
        "matplotlib", "numpy", "pandas", "scipy",
        "tkinter", "test", "unittest",
        # Cloud SDKs that PyInstaller's analyser sometimes pulls in
        # via transitive imports — we never use them.
        "azure", "boto3", "botocore", "google",
    ],
    noarchive=False,
    optimize=0,
)


pyz = PYZ(a.pure)


# ---------------------------------------------------------------------------
# EXE — windowed mode (no console), embedded icon + version info.
# ---------------------------------------------------------------------------
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VediPocketPC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,                          # no console window for end-users
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=(
        os.path.join(CONTROLLER_DIR, "logo.ico")
        if os.path.isfile(os.path.join(CONTROLLER_DIR, "logo.ico"))
        else (os.path.join(REPO, "logo.ico")
              if os.path.isfile(os.path.join(REPO, "logo.ico"))
              else None)
    ),
    version=(
        os.path.join(CONTROLLER_DIR, "version_info.txt")
        if os.path.isfile(os.path.join(CONTROLLER_DIR, "version_info.txt"))
        else (os.path.join(REPO, "version_info.txt")
              if os.path.isfile(os.path.join(REPO, "version_info.txt"))
              else None)
    ),
)


# ---------------------------------------------------------------------------
# Onedir collection — bundles ``_internal/`` next to the EXE.
# ---------------------------------------------------------------------------
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VediPocketPC",
)
