@echo off
setlocal EnableDelayedExpansion
title Vedi Pocket PC - Launcher
cd /d "%~dp0"

echo ========================================================
echo           Vedi Pocket PC - Launcher
echo ========================================================
echo.

:: ----------------------------------------------------------------
:: 1. Pre-flight checks — fail fast with a clear message if the
::    developer's machine is missing a runtime.
:: ----------------------------------------------------------------
echo [1/5] Checking prerequisites...

where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo   [ERROR] Node.js was not found in your PATH.
    echo   Vedi Pocket PC needs Node.js v18+ to run the desktop
    echo   controller and the Expo dev server.
    echo.
    echo   Install from https://nodejs.org/ then re-run this file.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node -v') do set NODE_VER=%%i
echo   [OK] Node.js  !NODE_VER!

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PATH=%~dp0.venv\Scripts;!PATH!"
)

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo   [ERROR] Python was not found in your PATH or .venv.
    echo   Vedi Pocket PC needs Python 3.10+ to run the screen
    echo   stream server and the FastAPI pairing backend.
    echo.
    echo   Install from https://www.python.org/ ^(tick "Add Python
    echo   to PATH" in the installer^) then re-run this file.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo   [OK] Python    !PY_VER!

:: ----------------------------------------------------------------
:: 2. Auto-clear occupied ports (8080, 8000, 8081)
:: ----------------------------------------------------------------
echo.
echo [2/5] Checking and preparing required ports ^(8080, 8000, 8081^)...
for %%P in (8080 8000 8081) do (
    for /f "tokens=5" %%A in ('netstat -aon ^| findstr "LISTENING" ^| findstr ":%%P " 2^>nul') do (
        echo   [INFO] Port %%P is in use by PID %%A. Auto-terminating stale process...
        taskkill /f /pid %%A /t >nul 2>&1
    )
)
echo   [OK] All ports clear.

:: ----------------------------------------------------------------
:: 3. Install Python deps if missing — a fresh checkout won't have
::    agent-core, mss, pycaw, etc. We do this here so the user
::    never has to remember to run setup.bat first.
:: ----------------------------------------------------------------
echo.
echo [3/5] Verifying Python dependencies...
python -c "import mss, aiohttp, fastapi, pyautogui, websockets" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   [INFO] Missing Python deps. Running pip install...
    python -m pip install --upgrade pip
    python -m pip install -e packages\agent-core
    python -m pip install -r requirements.txt
    if !ERRORLEVEL! NEQ 0 (
        echo.
        echo   [ERROR] pip install failed. Check your network / proxy
        echo   settings and re-run, or run setup.bat manually for the
        echo   full installation log.
        echo.
        pause
        exit /b 1
    )
    echo   [OK] Python deps installed.
) else (
    echo   [OK] Python deps present.
)

:: ----------------------------------------------------------------
:: 4. Install Node deps if missing — same story for the Electron
::    controller and the Expo mobile app.
:: ----------------------------------------------------------------
echo.
echo [4/5] Verifying Node dependencies...
if not exist node_modules\electron\package.json (
    echo   [INFO] Installing root Electron deps...
    call npm install --legacy-peer-deps
    if !ERRORLEVEL! NEQ 0 (
        echo   [ERROR] Root npm install failed.
        pause
        exit /b 1
    )
) else (
    echo   [OK] Root deps present.
)

if not exist veddi-pocketpc\node_modules\expo\package.json (
    echo   [INFO] Installing mobile app deps ^(this can take a few minutes^)...
    cd veddi-pocketpc
    call npm install --legacy-peer-deps
    set "MOBILE_ERR=!ERRORLEVEL!"
    cd ..
    if !MOBILE_ERR! NEQ 0 (
        echo   [ERROR] Mobile app npm install failed.
        pause
        exit /b 1
    )
) else (
    echo   [OK] Mobile deps present.
)

:: ----------------------------------------------------------------
:: 5. Launch.
:: ----------------------------------------------------------------
echo.
echo [5/5] Launching Vedi Pocket PC...
echo   (Close the window or press Ctrl+C inside the app to quit.)
echo.

npm start
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo   [ERROR] Electron exited with code %ERRORLEVEL%.
    echo   Check the Controller window's "Python Server Logs" tab
    echo   for the real error.
    echo.
    pause
    exit /b %ERRORLEVEL%
)

endlocal