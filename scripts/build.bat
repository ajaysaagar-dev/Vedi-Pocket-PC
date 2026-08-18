@echo off
setlocal EnableDelayedExpansion
title Vedi Remote - Production Build
cd /d "%~dp0\.."

echo ==========================================================
echo           VEDI REMOTE - PRODUCTION BUILD
echo ==========================================================
echo.
echo Build Targets:
echo   [1] Windows EXE (default)  - dist\VediRemote.exe
echo   [2] Android APK / AAB     - via Expo / EAS Build
echo   [3] Both Windows + Android
echo   [4] Clean previous builds
echo   [5] Verify build environment
echo   [6] Organize dist\ (after dropping an .apk / .aab by hand)
echo.

set "MODE="
if /I "%~1"=="exe"      set "MODE=1"
if /I "%~1"=="apk"      set "MODE=2"
if /I "%~1"=="both"     set "MODE=3"
if /I "%~1"=="clean"    set "MODE=4"
if /I "%~1"=="verify"   set "MODE=5"
if /I "%~1"=="organize" set "MODE=6"

if "!MODE!"=="" (
    REM ---- Portable prompt ----
    REM We can't rely on ``choice`` because it isn't available on
    REM every Windows host and behaves inconsistently under PowerShell.
    REM ``set /p`` is universally supported. Empty input = default (1).
    echo.
    set /p "MODE=Choose option [1-6, default 1]: "
    if "!MODE!"=="" set "MODE=1"
    REM Strip stray whitespace.
    for /f "tokens=* delims= " %%m in ("!MODE!") do set "MODE=%%m"
)

REM ---- Sanitize: anything outside 1..6 falls back to 1 ----
if not "!MODE!"=="1" if not "!MODE!"=="2" if not "!MODE!"=="3" if not "!MODE!"=="4" if not "!MODE!"=="5" if not "!MODE!"=="6" set "MODE=1"

if "!MODE!"=="1" goto BUILD_EXE
if "!MODE!"=="2" goto BUILD_APK
if "!MODE!"=="3" goto BUILD_BOTH
if "!MODE!"=="4" goto CLEAN_BUILDS
if "!MODE!"=="5" goto VERIFY_ENV
if "!MODE!"=="6" goto ORGANIZE_ONLY
goto BUILD_EXE


:: ---------------------------------------------------------------
::  BUILD_EXE -- VediRemote.exe (controller + agent + stream in one)
:: ---------------------------------------------------------------
:BUILD_EXE
echo.
echo ==========================================================
echo   [1/5] Building Windows EXE - VediRemote.exe
echo ==========================================================
echo.

:: --- Step 1: Verify Python tooling ---
call :VERIFY_PYTHON
if errorlevel 1 goto END_FAIL

:: --- Step 2: Install / refresh dependencies ---
echo.
echo  [2/5] Installing Python dependencies...
echo ------------------------------------------------------
python -m pip install --upgrade pip >nul 2>&1
python -m pip install pyinstaller >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Failed to install PyInstaller.
    goto END_FAIL
)
python -m pip install -e packages\agent-core 2>nul
python -m pip install -r requirements.txt 2>nul
if errorlevel 1 (
    echo   [WARN] Some Python deps failed to install - continuing.
)

:: --- Step 3: Optional UPX for smaller binary ---
echo.
echo  [3/5] Locating UPX (optional compression)...
echo ------------------------------------------------------
set "UPX_FLAG="
where upx >nul 2>&1
if not errorlevel 1 (
    echo   [OK] UPX found - VediRemote.exe will be compressed.
    set "UPX_FLAG=--upx-dir=no"
) else (
    echo   [INFO] UPX not found on PATH - binary won't be compressed.
    echo           Download from https://upx.github.io/ to enable.
)

:: --- Step 4: PyInstaller single-file build ---
echo.
echo  [4/5] Running PyInstaller...
echo ------------------------------------------------------
:: NOTE: PyInstaller v6.0+ removed bytecode encryption (the ``--key``
:: flag is no longer supported - see
:: https://github.com/pyinstaller/pyinstaller/pull/6999). The single-exe
:: bundle still gets a meaningful amount of protection from UPX
:: compression + the stripped bootloader + the bytecode-compiled .pyc
:: files inside the PYZ archive, plus the SIZE of the bundle makes
:: trivial extraction impractical.

if exist build ( rmdir /s /q build )
if exist dist  ( rmdir /s /q dist  )

:: Invoke PyInstaller via ``python -m`` so we don't depend on the
:: binary being on PATH.  PyInstaller installs into user-site
:: packages when normal site-packages is read-only, which is the
:: case on most developer machines.
::
:: We capture PyInstaller's full log so we can apply our own warning
:: filter.  Three "Hidden import" warnings are emitted even on a
:: healthy build - they are well-known and harmless:
::
::   pycparser.lextab     PLY/Pyinstaller parser-table data, cached
::   pycparser.yacctab     PLY/Pyinstaller parser-table data, cached
::   tzdata                Optional timezone DB; not used by Vedi
::                         Remote (we use datetime.timezone.utc)
::
:: These come from PyInstaller's static analyser seeing data tables
:: that aren't actually importable modules.  They don't affect
:: runtime behaviour.  We accept them as warnings, fail the build
:: on any other ``Hidden import … not found`` line, and fail on any
:: ``ERROR:`` line.
set "PYINSTALLER_LOG=%TEMP%\vedi_pyinstaller.log"
if exist "%PYINSTALLER_LOG%" del /f /q "%PYINSTALLER_LOG%" >nul 2>&1
python -m PyInstaller --noconfirm --clean ^
    --log-level WARN ^
    VediRemote.spec > "%PYINSTALLER_LOG%" 2>&1
set "PYINSTALLER_ERR=%ERRORLEVEL%"

:: ----- Filter the PyInstaller log and decide what to do ----------
if %PYINSTALLER_ERR% NEQ 0 (
    echo.
    echo   [ERROR] PyInstaller exited with code %PYINSTALLER_ERR%.
    echo           Last lines of the build log:
    powershell -NoProfile -Command "Get-Content '%PYINSTALLER_LOG%' -Tail 40"
    goto END_FAIL
)

:: Pull out every ERROR: / Hidden import line from the log into a
:: scratch file, so we can look at them separately.
set "PYI_ERR_FILTER=%TEMP%\vedi_pyinstaller_errors.log"
if exist "%PYI_ERR_FILTER%" del /f /q "%PYI_ERR_FILTER%" >nul 2>&1
powershell -NoProfile -Command ^
    "Select-String -Path '%PYINSTALLER_LOG%' -Pattern 'ERROR:|Hidden import' -SimpleMatch" ^
    > "%PYI_ERR_FILTER%" 2>&1

:: Strip the three known-benign lines.  Anything left is a real
:: problem and the build should fail loud.
powershell -NoProfile -Command ^
    "Get-Content '%PYI_ERR_FILTER%' | Where-Object { $_ -notmatch 'pycparser.lextab' -and $_ -notmatch 'pycparser.yacctab' -and $_ -notmatch 'Hidden import \"tzdata\"' }" ^
    > "%PYI_ERR_FILTER%.filtered" 2>&1
for /f "tokens=*" %%L in ('type "%PYI_ERR_FILTER%.filtered" 2^>nul ^| findstr /r "[^ ]"') do (
    echo   [ERROR] %%L
    set "PYI_REAL_ERR=1"
)
del /f /q "%PYI_ERR_FILTER%.filtered" >nul 2>&1

if defined PYI_REAL_ERR (
    echo.
    echo   [ERROR] PyInstaller emitted unknown errors / hidden-import
    echo           warnings.  See above for details.
    powershell -NoProfile -Command "Get-Content '%PYINSTALLER_LOG%' -Tail 40"
    goto END_FAIL
)

echo   [OK] PyInstaller finished.  Three benign warnings
echo        (pycparser.lextab, pycparser.yacctab, tzdata) are expected.
del /f /q "%PYI_ERR_FILTER%" >nul 2>&1

:: --- Step 5: Verify the produced binary ---
echo.
echo  [5/5] Verifying build output...
echo ------------------------------------------------------
if not exist "dist\VediRemote.exe" (
    echo   [ERROR] dist\VediRemote.exe was not produced.
    goto END_FAIL
)

for %%I in ("dist\VediRemote.exe") do (
    set "SIZE_KB=%%~zI"
    set /a "SIZE_MB=%%~zI / 1048576"
)

call :ORGANIZE_DIST
if errorlevel 1 goto END_FAIL

echo.
echo ==========================================================
echo   BUILD SUCCESS
echo ==========================================================
for /f "tokens=2 delims==" %%v in ('call :READ_VERSION') do set "APP_VERSION=%%v"
echo   Artifact:  %CD%\dist\!APP_VERSION!\VediRemote.exe
echo   Latest:    %CD%\dist\VediRemote.exe
echo   Checksums: %CD%\dist\!APP_VERSION!\SHA256SUMS.txt
echo   Size:      !SIZE_KB! KB (~!SIZE_MB! MB)
echo   Version:   !APP_VERSION!
echo   Built:     %DATE% %TIME%
echo   Protection:
echo     - PyInstaller single-file bootloader
echo     - Compiled .pyc bytecode in the bundle
echo     - UPX binary compression (when UPX is on PATH)
echo     - Windowed mode (no console window)
echo     - Icon embedded (logo.ico)
echo.
echo   The user flow:
echo     1. User double-clicks VediRemote.exe
echo     2. The QR-code UI shell opens in their browser
echo     3. They scan with the Android app and connect
echo.
echo   Clean uninstall (any of):
echo     - Settings - Apps - Vedi Remote - Uninstall
echo     - VediRemote.exe --uninstall       (power-user CLI flag)
echo     - dist\Uninstall.bat               (standalone, no install needed)
echo ==========================================================
echo.
goto END_OK


:: ---------------------------------------------------------------
::  BUILD_APK - Android APK / AAB via Expo / EAS
:: ---------------------------------------------------------------
:BUILD_APK
echo.
echo ==========================================================
echo   [1/4] Building Android APK / AAB
echo ==========================================================
echo.

pushd apps\mobile\app

:: --- Step 1: Verify Node / npm ---
where node >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Node.js not found.  Install Node 18+ from https://nodejs.org
    popd & goto END_FAIL
)
for /f "tokens=*" %%i in ('node -v') do echo   [OK] Node:  %%i
for /f "tokens=*" %%i in ('npm -v')  do echo   [OK] npm:   %%i

:: --- Step 2: Install dependencies ---
echo.
echo  [2/4] Installing Expo dependencies (this may take a minute)...
echo ------------------------------------------------------
call npm install --legacy-peer-deps
if errorlevel 1 (
    echo   [ERROR] npm install failed.
    popd & goto END_FAIL
)

:: --- Step 3: Build APK via EAS ---
echo.
echo  [3/4] Building release APK / AAB via EAS...
echo ------------------------------------------------------
where eas >nul 2>&1
if errorlevel 1 (
    echo   [INFO] eas-cli not found - installing globally...
    call npm install -g eas-cli
)

echo.
echo   Choose one:
echo     [A] eas build --platform android --profile preview    (APK)
echo     [B] eas build --platform android --profile production (AAB / store)
echo.

set "ANDROID_CHOICE="
if /I "%~2"=="apk"   set "ANDROID_CHOICE=A"
if /I "%~2"=="aab"   set "ANDROID_CHOICE=B"
if "!ANDROID_CHOICE!"=="" (
    REM Portable prompt (no ``choice`` - see notes in the main menu).
    set /p "ANDROID_CHOICE=Type A for APK or B for AAB (default A): "
    if "!ANDROID_CHOICE!"=="" set "ANDROID_CHOICE=A"
)

if /I "!ANDROID_CHOICE!"=="A" (
    call eas build --platform android --profile preview
) else (
    call eas build --platform android --profile production
)
if errorlevel 1 (
    echo   [WARN] EAS build did not exit cleanly.  Check the output above.
)

:: --- Step 4: Organize dist/ artifacts (placeholder for downloaded APK) ---
echo.
echo  [4/4] Organizing dist/ folder...
echo ------------------------------------------------------
popd
call :ORGANIZE_DIST
if errorlevel 1 goto END_FAIL

echo.
echo ==========================================================
echo   ANDROID BUILD SUMMARY
echo ==========================================================
for /f "tokens=2 delems==" %%v in ('call :READ_VERSION') do set "APP_VERSION=%%v"
echo   Latest:    %CD%\dist\!APP_VERSION!\
echo   EAS prints a download URL above - place the resulting .apk
echo   in dist\!APP_VERSION!\ and re-run "build.bat organize".
echo ==========================================================
goto END_OK


:: ---------------------------------------------------------------
::  BUILD_BOTH -- Windows EXE then Android APK
:: ---------------------------------------------------------------
:BUILD_BOTH
call :BUILD_EXE
if errorlevel 1 goto END_FAIL
goto BUILD_APK


:: ---------------------------------------------------------------
::  CLEAN_BUILDS
:: ---------------------------------------------------------------
:CLEAN_BUILDS
echo.
echo ==========================================================
echo   Cleaning previous builds...
echo ==========================================================
if exist build ( rmdir /s /q build && echo   [OK] Removed build\ )
if exist dist  ( rmdir /s /q dist  && echo   [OK] Removed dist\  )
if exist __pycache__ ( rmdir /s /q __pycache__ )
if exist apps\mobile\app\.expo (
    pushd apps\mobile\app
    if exist .expo rmdir /s /q .expo
    popd
    echo   [OK] Removed apps\mobile\app\.expo\
)
if exist apps\mobile\app\dist (
    pushd apps\mobile\app
    if exist dist rmdir /s /q dist
    popd
    echo   [OK] Removed apps\mobile\app\dist\
)
echo.
echo   Clean complete.
goto END_OK


:: ---------------------------------------------------------------
::  ORGANIZE_ONLY - copy the existing dist\VediRemote.exe into the
::  versioned folder layout without rebuilding.  Use this after
::  dropping an .apk / .aab in by hand (EAS sometimes lets you
::  download to anywhere) and want everything in dist\vX.Y.Z\.
:: ---------------------------------------------------------------
:ORGANIZE_ONLY
echo.
echo ==========================================================
echo   Re-organizing dist\ into the versioned layout...
echo ==========================================================
if not exist dist (
    echo   [ERROR] dist\ does not exist.  Nothing to organize.
    goto END_FAIL
)
call :ORGANIZE_DIST
echo.
echo   Done.  See dist\README.md for the layout.
goto END_OK


:: ---------------------------------------------------------------
::  VERIFY_ENV
:: ---------------------------------------------------------------
:VERIFY_ENV
echo.
echo ==========================================================
echo   BUILD ENVIRONMENT VERIFICATION
echo ==========================================================
echo.

set "VER_PASS=1"

where python >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo   [OK] Python: %%i
) else (
    echo   [MISSING] Python 3.10+ - download from https://www.python.org/
    set "VER_PASS=0"
)

python -c "import PyInstaller; print('   [OK] PyInstaller:', PyInstaller.__version__)" >nul 2>&1
if not errorlevel 1 (
    echo.
) else (
    echo   [MISSING] PyInstaller - install with: pip install pyinstaller
    set "VER_PASS=0"
)

where node >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%i in ('node -v') do echo   [OK] Node:   %%i
) else (
    echo   [INFO] Node.js optional for Windows builds; required for Android builds.
)

where upx >nul 2>&1
if not errorlevel 1 (
    echo   [OK] UPX available - binary compression will be applied.
) else (
    echo   [INFO] UPX not found - install from https://upx.github.io/ to compress.
)

if exist "logo.ico" (
    echo   [OK] logo.ico - app icon found.
) else (
    echo   [WARN] logo.ico missing - default icon will be used.
)

if exist "scripts\launcher.py" (
    echo   [OK] scripts\launcher.py - multi-mode entry ready.
) else (
    echo   [MISSING] scripts\launcher.py - the bundled exe won't work without it.
    set "VER_PASS=0"
)

if exist "VediRemote.spec" (
    echo   [OK] VediRemote.spec - PyInstaller spec present.
) else (
    echo   [MISSING] VediRemote.spec - check the file is at repo root.
    set "VER_PASS=0"
)

if exist "apps\mobile\app\app.json" (
    echo   [OK] apps\mobile\app\app.json - Expo project ready for Android build.
) else (
    echo   [WARN] apps\mobile\app not present - Android build won't be possible.
)

echo.
if !VER_PASS! EQU 1 (
    echo   *** ALL CHECKS PASSED ***
) else (
    echo   *** ENVIRONMENT HAS MISSING TOOLS - SEE ABOVE ***
)
goto END_OK


:: ---------------------------------------------------------------
::  Helper: verify Python is available
:: ---------------------------------------------------------------
:VERIFY_PYTHON
where python >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Python is not on PATH.  Install Python 3.10+:
    echo           https://www.python.org/downloads/
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo   [OK] %%i
exit /b 0


:: ---------------------------------------------------------------
::  Exit handling
:: ---------------------------------------------------------------
:END_OK
echo.
echo Build complete.
popd >nul 2>&1
exit /b 0

:END_FAIL
echo.
echo BUILD FAILED.
popd >nul 2>&1
exit /b 1


:: ---------------------------------------------------------------
::  ORGANIZE_DIST
::
::  Move / copy the artifacts out of PyInstaller's flat
::  ``dist/VediRemote.exe`` layout and into a versioned folder:
::
::    dist/
::      +- VediRemote.exe                        (latest, convenient copy)
::      +- README.md                             (build + deploy notes)
::      +- v1.0.0/                               (one folder per release)
::          +- VediRemote.exe                    (the EXE)
::          +- VediRemote-v1.0.0.apk             (if dropped in)
::          +- SHA256SUMS.txt                    (cryptographic checksums)
::          +- BUILD_INFO.txt                    (host, date, deps)
::          +- release-notes.txt                 (one-line changelog)
::
::  Idempotent: safe to run multiple times.  No production code is
::  touched; this only shuffles build output around.
:: ---------------------------------------------------------------
:ORGANIZE_DIST
setlocal EnableDelayedExpansion

:: Pull version from package.json (single source of truth).
call :READ_VERSION
set "VERSION=!APP_VERSION!"
if "!VERSION!"=="" set "VERSION=0.0.0"

set "RELEASE_DIR=dist\!VERSION!"
if not exist "!RELEASE_DIR!" mkdir "!RELEASE_DIR!"

:: Move the freshly built EXE into the versioned folder.
if exist "dist\VediRemote.exe" (
    if exist "!RELEASE_DIR!\VediRemote.exe" del /f /q "!RELEASE_DIR!\VediRemote.exe"
    move /y "dist\VediRemote.exe" "!RELEASE_DIR!\VediRemote.exe" >nul
)

:: Pick up any Android artifact the user (or `eas build`) dropped in
:: beside the build script.  We accept .apk, .aab, or .apks files and
:: rename them to include the version for clarity.
for %%A in ("VediRemote*.apk" "VediRemote*.aab" "VediRemote*.apks") do (
    if exist "%%~A" (
        set "NEW_NAME=!RELEASE_DIR!\VediRemote-!VERSION!%%~xA"
        move /y "%%~A" "!NEW_NAME!" >nul
    )
)
:: EAS sometimes writes into a known subfolder; sweep it too.
if exist "apps\mobile\app\build" (
    for /r "apps\mobile\app\build" %%A in (*.apk *.aab *.apks) do (
        if exist "%%~A" (
            set "NEW_NAME=!RELEASE_DIR!\VediRemote-!VERSION!%%~xA"
            move /y "%%~A" "!NEW_NAME!" >nul
        )
    )
)

:: Convenience copy at dist\VediRemote.exe so end-users always have a
:: stable path to the latest binary.
if exist "!RELEASE_DIR!\VediRemote.exe" (
    copy /y "!RELEASE_DIR!\VediRemote.exe" "dist\VediRemote.exe" >nul
)

:: Drop a standalone Uninstall.bat next to each release so users have
:: a clean uninstall even if they didn't run ``VediRemote.exe
:: --install`` (which also wires the same registry keys + shortcuts).
if exist "Uninstall.bat" (
    copy /y "Uninstall.bat" "!RELEASE_DIR!\Uninstall.bat" >nul
    set "LAST_RELEASE_DIR=!RELEASE_DIR!"
    echo   [OK] Copied Uninstall.bat to !LAST_RELEASE_DIR!
)
:: Mirror to the top-level dist\ too so the latest uninstall is
:: always reachable without navigating into a version subfolder.
if exist "Uninstall.bat" copy /y "Uninstall.bat" "dist\Uninstall.bat" >nul 2>&1

call :GENERATE_CHECKSUMS "!RELEASE_DIR!"
call :GENERATE_BUILD_INFO "!RELEASE_DIR!"
call :GENERATE_RELEASE_README "!RELEASE_DIR!"
if exist "dist\README.md" goto :EOF
call :GENERATE_TOP_README

endlocal
exit /b 0


:: ---------------------------------------------------------------
::  READ_VERSION -- extract ``"version"`` from package.json.
::
::  Outputs ``APP_VERSION=x.y.z``.  Falls back to plain output of
::  ``apps/mobile/app/app.json``'s version, then to ``0.0.0``.
:: ---------------------------------------------------------------
:READ_VERSION
setlocal EnableDelayedExpansion
set "APP_VERSION="

REM Try package.json at repo root first via Python (one-liner JSON
REM parse is reliable; the old ``findstr`` with literal quotes was
REM eaten by CMD's tokenizer on some hosts).
for /f "tokens=*" %%p in ('python -c "import json,sys; d=json.load(open('package.json')); print(d.get('version',''))" 2^>nul') do (
    if not "%%~p"=="" set "APP_VERSION=%%~p"
)

REM Fall back to apps/mobile/app/app.json (the Expo project's version).
if "!APP_VERSION!"=="" (
    for /f "tokens=*" %%p in ('python -c "import json,sys; d=json.load(open('apps/mobile/app/app.json')); print(d.get('expo',{}).get('version',''))" 2^>nul') do (
        if not "%%~p"=="" set "APP_VERSION=%%~p"
    )
)

if "!APP_VERSION!"=="" set "APP_VERSION=0.0.0"
echo APP_VERSION=!APP_VERSION!
endlocal & set "APP_VERSION=%APP_VERSION%"
exit /b 0


:: ---------------------------------------------------------------
::  GENERATE_CHECKSUMS -- write SHA256SUMS.txt for every artifact
::  in the release folder.  Uses only built-in Windows tools.
:: ---------------------------------------------------------------
:GENERATE_CHECKSUMS
set "DIR=%~1"
if "%DIR%"=="" exit /b 1
if not exist "%DIR%" exit /b 1
set "OUT=%DIR%\SHA256SUMS.txt"
REM Hand off the whole job to Python.  This side-steps CMD's
REM hostile interaction between nested ``for /f`` command
REM substitution (``1>nul``) and ``setlocal EnableDelayedExpansion``
REM that we inherit from the caller's scope (ORGANIZE_DIST).
python "%DIR%\..\..\scripts\write_checksums.py" "%DIR%" "%OUT%"
echo   [OK] Wrote %OUT%
exit /b 0


:: ---------------------------------------------------------------
::  GENERATE_BUILD_INFO -- record host, time, versions of the
::  shipped deps so release builds are reproducible.
:: ---------------------------------------------------------------
:GENERATE_BUILD_INFO
set "DIR=%~1"
if "%DIR%"=="" exit /b 1
set "OUT=%DIR%\BUILD_INFO.txt"
set "PY_VER="
for /f "tokens=*" %%p in ('python --version 2^>^&1') do set "PY_VER=%%p"

REM We deliberately write each line with explicit ``>%OUT%`` rather
REM than via a single ``( ... ) > %OUT%`` block.  We avoid
REM ``setlocal EnableDelayedExpansion`` and ``!VAR!`` here because
REM the combination fights CMD's tokeniser when used together
REM with ``for /f`` command substitution (``!(...)!`` inside
REM backticks mis-expands on some hosts, especially under
REM PowerShell-shelled ``cmd.exe``).
> "%OUT%" echo Vedi Remote - Build Manifest
>>"%OUT%" echo ============================
>>"%OUT%" echo.
>>"%OUT%" echo Product:    VediRemote
>>"%OUT%" echo Version:    %APP_VERSION%
>>"%OUT%" echo Built at:   %DATE% %TIME%
>>"%OUT%" echo Host:       %COMPUTERNAME%\%USERNAME%
>>"%OUT%" echo Python:     %PY_VER%
>>"%OUT%" echo.
>>"%OUT%" echo Distribution layout:
>>"%OUT%" echo   dist\
>>"%OUT%" echo     +- VediRemote.exe             (latest)
>>"%OUT%" echo     +- README.md
>>"%OUT%" echo     +- %APP_VERSION%\
>>"%OUT%" echo         +- VediRemote.exe
>>"%OUT%" echo         +- VediRemote-%APP_VERSION%.apk (if built)
>>"%OUT%" echo         +- SHA256SUMS.txt
>>"%OUT%" echo         +- BUILD_INFO.txt
>>"%OUT%" echo         +- release-notes.txt
>>"%OUT%" echo.
>>"%OUT%" echo See SHA256SUMS.txt to verify integrity before distributing.
echo   [OK] Wrote %OUT%
exit /b 0


:: ---------------------------------------------------------------
::  GENERATE_RELEASE_README -- short user-facing notes for the
::  specific release folder.
:: ---------------------------------------------------------------
:GENERATE_RELEASE_README
set "DIR=%~1"
set "OUT=%DIR%\release-notes.txt"
> "%OUT%" echo Vedi Remote v%APP_VERSION%
>>"%OUT%" echo.
>>"%OUT%" echo Files in this folder:
>>"%OUT%" echo   - VediRemote.exe              the bundled desktop app
>>"%OUT%" echo   - VediRemote-%APP_VERSION%.apk the Android client
>>"%OUT%" echo   - Uninstall.bat               standalone uninstaller (no install needed)
>>"%OUT%" echo   - SHA256SUMS.txt              integrity hashes
>>"%OUT%" echo   - BUILD_INFO.txt              build provenance
>>"%OUT%" echo.
>>"%OUT%" echo Deployment:
>>"%OUT%" echo   1. Send VediRemote.exe to the PC user. They double-click it.
>>"%OUT%" echo   2. The QR-code UI shell opens in their default browser.
>>"%OUT%" echo   3. Send the .apk to their phone (sideload it - allow
>>"%OUT%" echo      "install from unknown sources" for their file manager).
>>"%OUT%" echo   4. They tap "Scan QR" in the app and aim at the QR on the PC.
>>"%OUT%" echo   5. Once paired, the touchpad / keyboard / screen tab
>>"%OUT%" echo      populate automatically.
>>"%OUT%" echo.
>>"%OUT%" echo Verifying:
>>"%OUT%" echo   certutil -hashfile VediRemote.exe SHA256
>>"%OUT%" echo   Compare against SHA256SUMS.txt before running.
>>"%OUT%" echo.
>>"%OUT%" echo Uninstalling (any of):
>>"%OUT%" echo   1. Double-click Uninstall.bat in this folder
>>"%OUT%" echo   2. Or right-click VediRemote.exe - Run as administrator
>>"%OUT%" echo      and pass --uninstall: VediRemote.exe --uninstall
>>"%OUT%" echo   3. Or Settings - Apps - Vedi Remote - Uninstall
echo   [OK] Wrote %OUT%
exit /b 0


:: ---------------------------------------------------------------
::  GENERATE_TOP_README - the build / deployment notes at
::  ``dist/README.md`` (created once, on first build).
:: ---------------------------------------------------------------
:GENERATE_TOP_README
setlocal EnableDelayedExpansion
> "dist\README.md" echo # dist\ - Vedi Remote build output
>>"dist\README.md" echo.
>>"dist\README.md" echo After running ``build.bat`` the output is laid out as:
>>"dist\README.md" echo.
>>"dist\README.md" echo     dist\
>>"dist\README.md" echo     +- VediRemote.exe                 latest binary - copy of the
>>"dist\README.md" echo     ^|                               newest release for convenience
>>"dist\README.md" echo     +- Uninstall.bat                  standalone uninstall - latest
>>"dist\README.md" echo     +- README.md                      this file
>>"dist\README.md" echo     +- v1.0.0\                         one folder per release
>>"dist\README.md" echo         +- VediRemote.exe             the actual bundled app
>>"dist\README.md" echo         +- VediRemote-v1.0.0.apk      the Android client ^(if built^)
>>"dist\README.md" echo         +- Uninstall.bat              standalone uninstall for this release
>>"dist\README.md" echo         +- SHA256SUMS.txt             SHA-256 of every artifact
>>"dist\README.md" echo         +- BUILD_INFO.txt             host, time, versions
>>"dist\README.md" echo         +- release-notes.txt          user-facing deployment notes
>>"dist\README.md" echo.
>>"dist\README.md" echo ## Building
>>"dist\README.md" echo.
>>"dist\README.md" echo     build.bat            builds VediRemote.exe into the newest
>>"dist\README.md" echo                          versioned folder under dist\
>>"dist\README.md" echo     build.bat apk        builds the Android client via EAS,
>>"dist\README.md" echo                          then drops it into the same folder
>>"dist\README.md" echo     build.bat both       exe then apk in one go
>>"dist\README.md" echo     build.bat clean      wipes build/, dist/, apps/mobile/app/.expo/
>>"dist\README.md" echo     build.bat verify     prints tool / file prerequisites
>>"dist\README.md" echo.
>>"dist\README.md" echo ## Distributing
>>"dist\README.md" echo.
>>"dist\README.md" echo 1. Send ``dist\vX.Y.Z\VediRemote.exe`` to the PC user.
>>"dist\README.md" echo 2. Send ``dist\vX.Y.Z\VediRemote-vX.Y.Z.apk`` to the phone user.
>>"dist\README.md" echo 3. They double-click the EXE; the EXE opens the QR-code UI.
>>"dist\README.md" echo 4. They tap "Scan QR" on the phone, point at the QR.
>>"dist\README.md" echo 5. PC and phone pair and the touchpad / keyboard / stream
>>"dist\README.md" echo    tabs come online. Fullscreen works.
>>"dist\README.md" echo.
>>"dist\README.md" echo ## Uninstalling
>>"dist\README.md" echo.
>>"dist\README.md" echo Three ways - any of them cleans up:
>>"dist\README.md" echo.
>>"dist\README.md" echo     1. Double-click ``dist\Uninstall.bat``
>>"dist\README.md" echo     2. Double-click ``dist\vX.Y.Z\Uninstall.bat``
>>"dist\README.md" echo     3. ``VediRemote.exe --uninstall``
>>"dist\README.md" echo     4. Settings - Apps - "Vedi Remote" - Uninstall
>>"dist\README.md" echo        ^(this calls the EXE's --uninstall under the hood^)
>>"dist\README.md" echo.
>>"dist\README.md" echo ``Uninstall.bat`` and ``VediRemote.exe --uninstall`` are
>>"dist\README.md" echo identical in effect: stop processes, clean auto-start and
>>"dist\README.md" echo Add/Remove Programs entries, remove shortcuts.  Pass
>>"dist\README.md" echo ``--purge`` to also wipe ``%LOCALAPPDATA%\PCRemoteAgent\``
>>"dist\README.md" echo ^(the install dir / common-token file^).
echo   [OK] Wrote dist\README.md
endlocal
exit /b 0
