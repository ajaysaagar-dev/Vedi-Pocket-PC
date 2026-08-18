@echo off
setlocal EnableDelayedExpansion
title Vedi Remote - Uninstaller
cd /d "%~dp0\.."

echo ==========================================================
echo           VEDI REMOTE - UNINSTALLER
echo ==========================================================
echo.
echo   Removes:
echo     - Auto-start entry (HKCU\...\Run\VediRemote)
echo     - Add / Remove Programs entry
echo     - Start Menu shortcut
echo     - Desktop shortcut
echo     - Running VediRemote processes
echo     - The install folder ^(%LOCALAPPDATA%\PCRemoteAgent\^)
echo.
echo ==========================================================
echo.

:: ---------------------------------------------------------------
::  Flags
::
::  --quiet   : no prompt - used when called from Add/Remove
::              Programs, or when called by VediRemote.exe --uninstall
::  --purge   : also wipe the install folder
::                (%LOCALAPPDATA%\PCRemoteAgent\)
::                and the persisted common-token file
::  --keep-data : never delete the install folder even if --purge
::                was passed (default safe behaviour)
:: ---------------------------------------------------------------
set "QUIET=0"
set "PURGE=0"
set "KEEP_DATA=1"
for %%A in (%*) do (
    if /I "%%~A"=="--quiet"       set "QUIET=1"
    if /I "%%~A"=="--purge"       set "PURGE=1" & set "KEEP_DATA=0"
    if /I "%%~A"=="--keep-data"  set "KEEP_DATA=1"
)

if !QUIET! EQU 0 (
    echo.
    set "ANSWER="
    set /p "ANSWER=Type YES to uninstall Vedi Remote (anything else to cancel): "
    if /I not "!ANSWER!"=="YES" (
        echo.
        echo   Uninstall cancelled - nothing was changed.
        pause
        exit /b 0
    )
)

echo.
echo  [1/6] Stopping running VediRemote processes...
echo ------------------------------------------------------
:: taskkill /IM matches any process whose image name matches;
:: /T walks the parent chain, /F forces.  Silently ignore "no
:: process" errors via 2^>nul redirection.
taskkill /IM VediRemote.exe /T /F >nul 2>&1
echo   [OK] Process termination attempted.

echo.
echo  [2/6] Removing auto-start entry (HKCU Run)...
echo ------------------------------------------------------
:: Use reg delete so an absent key is a non-error.
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "VediRemote" /f >nul 2>&1
echo   [OK] Run key cleaned.

echo.
echo  [3/6] Removing Add / Remove Programs entry...
echo ------------------------------------------------------
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\VediRemote" /f >nul 2>&1
echo   [OK] Uninstall registry entry removed.

echo.
echo  [4/6] Removing Start Menu + Desktop shortcuts...
echo ------------------------------------------------------
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Vedi Remote" (
    rmdir /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Vedi Remote"
    echo   [OK] Start Menu folder removed.
) else (
    echo   [INFO] No Start Menu folder to remove.
)
if exist "%USERPROFILE%\Desktop\Vedi Remote.lnk" (
    del /f /q "%USERPROFILE%\Desktop\Vedi Remote.lnk"
    echo   [OK] Desktop shortcut removed.
) else (
    echo   [INFO] No desktop shortcut.
)

echo.
echo  [5/6] Removing install folder...
echo ------------------------------------------------------
set "INSTALL_DIR=%LOCALAPPDATA%\PCRemoteAgent"
if exist "!INSTALL_DIR!" (
    if !KEEP_DATA! EQU 0 (
        echo   [PURGE] Deleting !INSTALL_DIR! and its contents...
        rmdir /s /q "!INSTALL_DIR!"
        echo   [OK] Install folder wiped.
    ) else (
        echo   [INFO] Keeping !INSTALL_DIR! - pass --purge to wipe it too.
        echo          (this preserves pairing data for re-install)
    )
) else (
    echo   [INFO] No install folder to remove.
)

echo.
echo  [6/6] Optional - removing this install's loose dist folder...
echo ------------------------------------------------------
:: If invoked from a per-version release folder
:: (e.g. dist\v1.0.0\Uninstall.bat) we offer to delete the loose
:: artifacts left behind in that folder - the EXE itself was already
:: stopped above. We never delete the folder the user is running from
:: without explicit confirmation.
if "%~dp0" NEQ "%CD%\" (
    set "DIST_DIR=%~dp0"
)
if defined DIST_DIR (
    echo   Loose install artifacts dir:
    echo     !DIST_DIR!
)
echo.

echo ==========================================================
echo   UNINSTALL COMPLETE
echo ==========================================================
echo.
echo   Removed:
echo     - Auto-start entry
echo     - Add / Remove Programs entry
echo     - Start Menu + Desktop shortcuts
echo     - Running processes
if !KEEP_DATA! EQU 0 (
    echo     - Install folder (purged)
) else (
    echo     - Install folder kept - reuse for re-install
)
echo.
if !QUIET! EQU 0 pause
exit /b 0
