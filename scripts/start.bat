@echo off
setlocal EnableDelayedExpansion
title Vedi Pocket PC - Launcher (Python Controller)
cd /d "%~dp0\.."

echo ========================================================
echo           Vedi Pocket PC - Launcher
echo ========================================================
echo.
echo Launch Options:
echo   [1] Start Vedi Pocket PC (Controller + Backend + Screen Stream + Mobile)
echo   [2] Reload Expo App (Clear Metro Cache - Non-Interactive)
echo   [3] Start Expo App (Interactive Terminal Mode for Devs)
echo   [4] Create / Verify .env File
echo   [5] Download / Reinstall All Dependencies
echo   [6] Run Master Setup
echo.
set "CHOICE=1"
choice /c 123456 /t 5 /d 1 /m "Select option (Auto-starting option 1 in 5s)... " >nul 2>&1
if !ERRORLEVEL! EQU 2 goto RELOAD_EXPO
if !ERRORLEVEL! EQU 3 goto START_EXPO_INTERACTIVE
if !ERRORLEVEL! EQU 4 goto CREATE_ENV_MENU
if !ERRORLEVEL! EQU 5 goto DOWNLOAD_DEPS_MENU
if !ERRORLEVEL! EQU 6 goto RUN_SETUP
goto MAIN_PREFLIGHT

:RELOAD_EXPO
echo.
echo ========================================================
echo     Reloading Expo Mobile App ^& Clearing Metro Cache...
echo ========================================================
echo.
if exist "apps\mobile\app" (
    cd apps\mobile\app
    call npx expo start -c --host lan --port 8088
) else (
    echo   [ERROR] Mobile directory 'apps\mobile\app' not found.
)
pause
exit /b 0

:START_EXPO_INTERACTIVE
echo.
echo ========================================================
echo     Starting Expo Mobile App ^(Interactive Terminal^)...
echo ========================================================
echo.
if exist "apps\mobile\app" (
    cd apps\mobile\app
    call npx expo start -c --host lan --port 8088
) else (
    echo   [ERROR] Mobile directory 'apps\mobile\app' not found.
)
pause
exit /b 0

:CREATE_ENV_MENU
echo.
echo ========================================================
echo         Creating / Verifying .env File...
echo ========================================================
echo.
call :ENSURE_ENV_FILE 1
pause
exit /b 0

:DOWNLOAD_DEPS_MENU
echo.
echo ========================================================
echo         Downloading All Dependencies...
echo ========================================================
echo.
call :DOWNLOAD_PYTHON_DEPS 1
call :DOWNLOAD_NODE_DEPS 1
echo.
echo   [OK] All dependencies successfully downloaded and installed.
echo.
pause
exit /b 0

:RUN_SETUP
call setup.bat
exit /b 0

:MAIN_PREFLIGHT
:: ----------------------------------------------------------------
:: 1. Pre-flight checks
:: ----------------------------------------------------------------
echo [1/5] Checking prerequisites...

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PATH=%~dp0.venv\Scripts;!PATH!"
)

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo   [ERROR] Python was not found in your PATH or .venv.
    echo   Vedi Pocket PC needs Python 3.10+ to run the desktop
    echo   controller, screen stream server, and FastAPI pairing backend.
    echo.
    echo   Install from https://www.python.org/ ^(tick "Add Python to PATH"^)
    echo   then re-run this file.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo   [OK] Python    !PY_VER!

where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo   [ERROR] Node.js was not found in your PATH.
    echo   Node.js v18+ is required to bundle the Expo mobile app.
    echo   Install from https://nodejs.org/ then re-run this file.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node -v') do set NODE_VER=%%i
echo   [OK] Node.js   !NODE_VER!

:: ----------------------------------------------------------------
:: 2. Check / Create .env configuration file
:: ----------------------------------------------------------------
echo.
echo [2/5] Verifying environment configuration ^(.env^)...
call :ENSURE_ENV_FILE 0

:: ----------------------------------------------------------------
:: 3. Port check
:: ----------------------------------------------------------------
echo.
echo [3/5] Checking ports ^(8080, 8000, 8088, 8090^)...
for %%P in (8080 8000 8088 8090) do (
    netstat -ano | findstr ":%%P " | findstr "LISTENING" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo   [INFO] Port %%P is in use. Controller will auto-bind to next free port if needed.
    )
)
echo   [OK] Port check complete.

:: ----------------------------------------------------------------
:: 4. Verify Dependencies
:: ----------------------------------------------------------------
echo.
echo [4/5] Verifying Dependencies...
python -c "import mss, aiohttp, fastapi, pyautogui, websockets, qrcode" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   [INFO] Missing Python deps. Running pip install...
    call :DOWNLOAD_PYTHON_DEPS 0
) else (
    echo   [OK] Python deps present.
)

if not exist apps\mobile\app\node_modules\expo\package.json (
    echo   [INFO] Installing mobile app deps ^(this can take a few minutes^)...
    cd apps\mobile\app
    call npm install --legacy-peer-deps
    set "MOBILE_ERR=!ERRORLEVEL!"
    cd /d "%~dp0\.."
    if !MOBILE_ERR! NEQ 0 (
        echo   [ERROR] Mobile app npm install failed.
        pause
        exit /b 1
    )
) else (
    echo   [OK] Mobile deps present.
)

:: ----------------------------------------------------------------
:: 4b. Firewall rules
:: ----------------------------------------------------------------
echo.
echo [4b] Ensuring Windows Firewall allows inbound 8080 / 8000 / 8088 / 8090...
set "FW_OK=1"
for %%P in (8080 8000 8088 8090) do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "try { if (-not (Get-NetFirewallRule -DisplayName 'VediPocketPC-%%P' -ErrorAction SilentlyContinue)) { New-NetFirewallRule -DisplayName 'VediPocketPC-%%P' -Direction Inbound -LocalPort %%P -Protocol TCP -Action Allow -Profile Private,Domain | Out-Null }; exit 0 } catch { exit 1 }" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo   [OK]  VediPocketPC-%%P ^(port %%P^)
    ) else (
        set "FW_OK=0"
    )
)
if "!FW_OK!"=="0" (
    echo   [WARN] Run start.bat as Administrator if mobile devices cannot connect.
)

:: ----------------------------------------------------------------
:: 5. Launch Python Desktop Controller
:: ----------------------------------------------------------------
echo.
echo [5/5] Launching Vedi Pocket PC Controller (Python)...
echo.

python -m apps.desktop.controller.app
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo   [ERROR] Controller exited with code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)

endlocal
exit /b 0

:: ================================================================
:: Subroutines
:: ================================================================

:ENSURE_ENV_FILE
if exist "%~dp0.env" (
    if "%~1"=="1" (
        echo   .env file already exists at "%~dp0.env".
        set /p OVERWRITE="Do you want to overwrite .env with default values? (Y/N): "
        if /i "!OVERWRITE!" NEQ "Y" (
            echo   Keeping existing .env file.
            exit /b 0
        )
    ) else (
        echo   [OK] .env file present.
        exit /b 0
    )
)

echo   [INFO] Creating default .env configuration...
(
    echo # ========================================================
    echo # Vedi Pocket PC - Environment Configuration
    echo # ========================================================
    echo.
    echo # Screen Stream Server Settings
    echo STREAM_HOST=0.0.0.0
    echo STREAM_PORT=8080
    echo STREAM_FPS=30
    echo STREAM_JPEG_QUALITY=50
    echo STREAM_MAX_WIDTH=640
    echo STREAM_MAX_HEIGHT=360
    echo STREAM_MONITOR_INDEX=1
    echo STREAM_MOUSE_SENSITIVITY=1.5
    echo STREAM_SCROLL_SENSITIVITY=1.0
    echo STREAM_DEBUG_MOUSE=false
    echo.
    echo # Backend Server Settings
    echo BACKEND_HOST=0.0.0.0
    echo BACKEND_PORT=8000
    echo EXPO_PORT=8088
    echo CONTROLLER_PORT=8090
) > "%~dp0.env"
echo   [OK] Default .env created successfully.
exit /b 0

:DOWNLOAD_PYTHON_DEPS
echo   Installing shared packages\core (editable)...
python -m pip install -e packages\core >nul 2>&1
echo   Installing requirements.txt...
python -m pip install -r requirements.txt
exit /b 0

:DOWNLOAD_NODE_DEPS
if exist "apps\mobile\app" (
    echo   Installing mobile Expo dependencies in apps\mobile\app\...
    cd apps\mobile\app
    call npm install --legacy-peer-deps
    cd /d "%~dp0\.."
)
exit /b 0