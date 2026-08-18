"""Vedi Remote — single-EXE multi-mode launcher.

The bundled ``VediRemote.exe`` doubles as four things:

* The Python desktop controller (UI shell with the QR code).
* The FastAPI control agent (the agent that mints auth tokens and
  forwards mouse / keyboard / power commands to the PC).
* The aiohttp screen-stream server (the JPEG frame producer the
  mobile app subscribes to).
* An installer / uninstaller.  ``VediRemote.exe --install`` writes
  the standard HKCU Run / Start Menu / Add-and-Remove-Programs
  entries so the app starts cleanly with Windows and shows up in
  Settings → Apps.  ``VediRemote.exe --uninstall`` reverses all of
  that so users have a single, self-contained uninstall.

The controller already spawns the agent and the stream server as
child processes via ``subprocess.Popen([sys.executable, "main.py"],
cwd=<subdir>, env=...)``. Because ``sys.executable`` inside the
onefile bundle points at ``VediRemote.exe`` itself, every child
re-enters this launcher; we detect the role here and dispatch.

Role detection (no controller changes required):

    1. Explicit ``VEDREMOTE_MODE`` env var, if present.
    2. Inherited env vars that the controller already sets when it
       spawns its children (``STREAM_PORT`` and ``BACKEND_PORT``).
    3. Default role: ``controller``.

This file is part of the build only — it is never imported by
existing controller / backend / stream-server code, so nothing in
the live logic is disturbed.
"""

from __future__ import annotations

import os
import runpy
import subprocess
import sys
from typing import Literal

Mode = Literal["controller", "backend", "stream"]


# ---------------------------------------------------------------------------
# Role detection — keeps zero coupling to controller/process_manager.py.
# ---------------------------------------------------------------------------
def detect_mode() -> Mode:
    """Return which role this process should run as."""
    explicit = os.environ.get("VEDREMOTE_MODE", "").strip().lower()
    if explicit in ("controller", "backend", "stream"):
        return explicit  # type: ignore[return-value]

    # The controller's existing process_manager.py passes these env
    # vars to each child process. Inheriting them here lets us run the
    # correct child role without changing the controller code.
    if "STREAM_PORT" in os.environ and "VEDREMOTE_KIND" != "backend":
        return "stream"
    if "BACKEND_PORT" in os.environ and "VEDREMOTE_KIND" != "stream":
        return "backend"

    return "controller"


# ---------------------------------------------------------------------------
# Bundle layout helpers.
# ---------------------------------------------------------------------------
def bundle_root() -> str:
    """Return the directory containing the bundled assets.

    PyInstaller onefile mode puts everything under ``sys._MEIPASS``;
    running from source puts it next to this launcher file.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return meipass
    here = os.path.dirname(os.path.abspath(__file__))
    # scripts/launcher.py → repo root
    return os.path.abspath(os.path.join(here, os.pardir))


# ---------------------------------------------------------------------------
# Subprocess-mode dispatch — runs the backend or stream server "as if" we
# had spawned a fresh python interpreter, but inside the same exe.
# ---------------------------------------------------------------------------
def _run_subprocess_mode(mode: Mode) -> None:
    root = bundle_root()
    subdir = "vedi-pocketpc-backend" if mode == "backend" else "screen-stream-server"
    target = os.path.join(root, subdir, "main.py")
    if not os.path.isfile(target):
        sys.stderr.write(f"[VediRemote] Bundled script not found: {target}\n")
        sys.exit(2)

    # Both bundled scripts assume "parent directory" is the repo root
    # (they add ``../packages/agent-core`` to ``sys.path``). Mirror
    # that contract by inserting the bundle root.
    if root not in sys.path:
        sys.path.insert(0, root)

    # The bundled script's ``__file__`` will be the data-file path
    # inside the bundle, so its ``os.path.dirname(__file__)`` and the
    # ``../packages/agent-core`` lookup will resolve correctly.
    sys.argv = [target]
    runpy.run_path(target, run_name="__main__")


# ---------------------------------------------------------------------------
# Controller-mode dispatch — the QR-code UI shell with embedded HTTP server.
# ---------------------------------------------------------------------------
def _run_controller() -> None:
    root = bundle_root()
    # Controller expects its own directory and the repo root to be on
    # ``sys.path`` so ``from controller.<…>`` resolves cleanly.
    for p in (root, os.path.join(root, "controller"), os.path.join(root, "packages", "agent-core")):
        if p not in sys.path:
            sys.path.insert(0, p)

    # The controller expects HTML / CSS / JS assets to live in the
    # repo root (it serves them as static files). In dev mode that
    # holds naturally; in onefile mode, all those assets are inside
    # the bundle root, so we mirror ``os.chdir`` to land there.
    try:
        os.chdir(root)
    except OSError:
        pass

    # Importing after chdir so the bundle layout is what the controller
    # observes on its first ``open()``.
    from controller.main import main as run_controller_main  # noqa: E402

    run_controller_main()


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------
def main() -> None:
    # Service-mode flags take precedence over role detection — they're
    # operator actions, not part of the controller-orchestrated flow.
    args = [a.lower() for a in sys.argv[1:]]
    if "--install" in args:
        _install()
        return
    if "--uninstall" in args or "--quiet-uninstall" in args:
        _uninstall(quiet="--quiet-uninstall" in args or "--quiet" in args,
                   purge="--purge" in args)
        return
    if "--version" in args or "-v" in args:
        print("VediRemote launcher 1.0.0")
        return
    if "--help" in args or "-h" in args:
        print(
            "VediRemote launcher\n"
            "  (no args)            start the QR-code UI shell\n"
            "  --install            register as auto-start + Start Menu\n"
            "  --uninstall          remove every trace of the install\n"
            "  --uninstall --purge  uninstall and wipe %LOCALAPPDATA%\\PCRemoteAgent\n"
            "  --version            print version and exit\n"
            "  --help               this message"
        )
        return

    mode = detect_mode()
    if mode == "backend":
        _run_subprocess_mode("backend")
    elif mode == "stream":
        _run_subprocess_mode("stream")
    else:
        _run_controller()


# ---------------------------------------------------------------------------
# Install / uninstall — registered auto-start + Start Menu + Add/Remove
# Programs entries.  Lives here so end-users have a single self-contained
# ``VediRemote.exe`` for the entire install / uninstall lifecycle, and so
# the production controller / backend / stream code is never touched.
#
# Everything is done under HKCU so no admin elevation is required.
# ---------------------------------------------------------------------------
INSTALL_DIR_NAME = "PCRemoteAgent"
APP_DISPLAY_NAME = "Vedi Remote"
APP_PUBLISHER = "Vedi"
APP_VERSION = "1.0.0"


def install_dir() -> str:
    """Return ``%LOCALAPPDATA%\\PCRemoteAgent`` (created on demand)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, INSTALL_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def _winreg():  # pragma: no cover - Windows-only path
    import winreg  # type: ignore[import-not-found]
    return winreg


def _powershell_shortcut(link_path: str, target: str, args: str, icon: str) -> bool:
    """Create a Windows shortcut (.lnk) without requiring pywin32."""
    if sys.platform != "win32":
        return False
    os.makedirs(os.path.dirname(link_path), exist_ok=True)
    # Use a one-liner PowerShell call so we don't need a dependency on
    # winshell / pywin32.  Returns immediately if the user is on a
    # non-Windows platform.
    ps = (
        "$s=(New-Object -COM WScript.Shell).CreateShortcut('"
        + link_path.replace("'", "''")
        + "');"
        + "$s.TargetPath='"
        + target.replace("'", "''")
        + "';"
    )
    if args:
        ps += "$s.Arguments='" + args.replace("'", "''") + "';"
    if icon:
        ps += "$s.IconLocation='" + icon.replace("'", "''") + "';"
    ps += "$s.Save()"
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            check=False,
            timeout=10,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return os.path.isfile(link_path)
    except (OSError, subprocess.SubprocessError):
        return False


def _install() -> None:
    """Register Vedi Remote so it auto-starts with the current user
    and appears in Settings → Apps.  Idempotent."""
    print(f"[VediRemote] Installing {APP_DISPLAY_NAME} ...")
    exe_src = sys.executable  # this frozen exe IS the installed binary
    exe_dst = os.path.join(install_dir(), "VediRemote.exe")

    # 1) Copy the EXE into the install dir so the Run-key path is stable
    #    even if the user moves / deletes the original download.
    try:
        if os.path.abspath(exe_src).lower() != os.path.abspath(exe_dst).lower():
            import shutil
            shutil.copy2(exe_src, exe_dst)
            print(f"[VediRemote]   installed to {exe_dst}")
    except OSError as exc:
        print(f"[VediRemote]   could not copy EXE: {exc}")

    # 2) HKCU Run key (auto-start at login) — wrapped autostart so
    #    a reboot is not required to take effect.
    if sys.platform == "win32":
        try:
            winreg = _winreg()
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.SetValueEx(
                    key,
                    "VediRemote",
                    0,
                    winreg.REG_SZ,
                    f'"{exe_dst}"',
                )
                winreg.SetValueEx(
                    key,
                    "VediRemoteUninstaller",
                    0,
                    winreg.REG_SZ,
                    f'"{exe_dst}" --uninstall',
                )
            print("[VediRemote]   HKCU Run entry written")
        except OSError as exc:
            print(f"[VediRemote]   HKCU Run entry failed: {exc}")

        # 3) Add / Remove Programs entry under HKCU (no admin).
        try:
            uninstall_key = (
                r"Software\Microsoft\Windows\CurrentVersion\Uninstall\VediRemote"
            )
            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER, uninstall_key
            ) as key:
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_DISPLAY_NAME)
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, APP_PUBLISHER)
                winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir())
                winreg.SetValueEx(
                    key,
                    "UninstallString",
                    0,
                    winreg.REG_SZ,
                    f'"{exe_dst}" --quiet-uninstall',
                )
                winreg.SetValueEx(
                    key,
                    "QuietUninstallString",
                    0,
                    winreg.REG_SZ,
                    f'"{exe_dst}" --quiet-uninstall',
                )
                winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
                winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
            print("[VediRemote]   Add / Remove Programs entry written")
        except OSError as exc:
            print(f"[VediRemote]   uninstall entry failed: {exc}")

        # 4) Start Menu + Desktop shortcuts.
        start_dir = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")),
            "Microsoft", "Windows", "Start Menu", "Programs", "Vedi Remote",
        )
        link = os.path.join(start_dir, "Vedi Remote.lnk")
        if _powershell_shortcut(
            link,
            exe_dst,
            "",
            exe_dst + ",0",
        ):
            print(f"[VediRemote]   Start Menu shortcut: {link}")
        desktop = os.path.join(
            os.environ.get("USERPROFILE", os.path.expanduser("~")),
            "Desktop",
            "Vedi Remote.lnk",
        )
        if _powershell_shortcut(
            desktop,
            exe_dst,
            "",
            exe_dst + ",0",
        ):
            print(f"[VediRemote]   Desktop shortcut: {desktop}")

    print(f"[VediRemote] {APP_DISPLAY_NAME} installed.")
    print(f"[VediRemote]   Run        : \"{exe_dst}\"")
    print(f"[VediRemote]   Uninstall  : \"{exe_dst}\" --uninstall")
    print(f"[VediRemote]   Settings   : Apps ^& Features → {APP_DISPLAY_NAME}")


def _uninstall(*, quiet: bool = False, purge: bool = False) -> None:
    """Reverse every trace of ``_install``.

    ``quiet`` skips the confirmation prompt (used when Add / Remove
    Programs calls us).
    ``purge`` additionally wipes ``%LOCALAPPDATA%\\PCRemoteAgent``
    and the persisted common-token file used for easy reconnect.
    """
    if not quiet:
        ans = input("Uninstall Vedi Remote?  Type YES to continue: ").strip()
        if ans != "YES":
            print("[VediRemote] Cancelled.")
            return

    # 1) Stop the running app (other than ourselves) before deleting
    #    so we don't lock the EXE.
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/IM", "VediRemote.exe", "/T", "/F"],
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.SubprocessError):
            pass

    # 2) Remove the HKCU Run entry and the auto-uninstall twin.
    if sys.platform == "win32":
        try:
            winreg = _winreg()
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                for value in ("VediRemote", "VediRemoteUninstaller"):
                    try:
                        winreg.DeleteValue(key, value)
                    except FileNotFoundError:
                        pass
        except OSError:
            pass

        # 3) Remove the Add / Remove Programs entry.
        try:
            winreg = _winreg()
            winreg.DeleteKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Uninstall\VediRemote",
            )
        except OSError:
            pass

        # 4) Remove shortcuts.
        for link in (
            os.path.join(
                os.environ.get("APPDATA", os.path.expanduser("~")),
                "Microsoft", "Windows", "Start Menu", "Programs",
                "Vedi Remote", "Vedi Remote.lnk",
            ),
            os.path.join(
                os.environ.get("USERPROFILE", os.path.expanduser("~")),
                "Desktop", "Vedi Remote.lnk",
            ),
        ):
            try:
                if os.path.isfile(link):
                    os.remove(link)
            except OSError:
                pass
        # Remove the start-menu folder if empty.
        start_menu_dir = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")),
            "Microsoft", "Windows", "Start Menu", "Programs", "Vedi Remote",
        )
        try:
            if os.path.isdir(start_menu_dir):
                os.rmdir(start_menu_dir)
        except OSError:
            pass

    # 5) Optionally wipe the install dir and the persisted common token.
    if purge:
        import shutil

        target_dir = install_dir()
        if os.path.isdir(target_dir):
            try:
                shutil.rmtree(target_dir)
            except OSError:
                pass

    print("[VediRemote] Uninstalled.")
    if not quiet:
        try:
            input("Press Enter to close...")
        except EOFError:
            pass


if __name__ == "__main__":
    main()
