@echo off
setlocal EnableDelayedExpansion
title Vedi Pocket PC - Launcher
cd /d "%~dp0\.."

echo ========================================================
echo           Vedi Pocket PC - Launcher
echo ========================================================
echo.
echo Launch Options:
echo   [1] Start Vedi Pocket PC (Controller + Backend + Screen Stream)
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
call :DOWNLOAD_PYTHON_DEPS
call :DOWNLOAD_NODE_DEPS
echo.
echo   [OK] All dependencies successfully downloaded and installed.
echo.
pause
exit /b 0

:RUN_SETUP
call "%~dp0setup.bat"
exit /b 0

:MAIN_PREFLIGHT
:: ----------------------------------------------------------------
:: 1. Virtual Environment & Python Detection
:: ----------------------------------------------------------------
echo [1/5] Checking prerequisites...

if exist ".venv\Scripts\python.exe" (
    set "PATH=%CD%\.venv\Scripts;!PATH!"
) else if exist "venv\Scripts\python.exe" (
    set "PATH=%CD%\venv\Scripts;!PATH!"
)

set "PYTHON_CMD="
where python >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "PYTHON_CMD=python"
) else (
    where py >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_CMD=py -3"
    )
)

if not defined PYTHON_CMD (
    echo.
    echo   [ERROR] Python was not found on this system.
    echo   Vedi Pocket PC requires Python 3.10+ to run the desktop
    echo   controller, screen streamer, and FastAPI pairing server.
    echo.
    echo   Please install Python from: https://www.python.org/
    echo   IMPORTANT: Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('!PYTHON_CMD! --version 2^>^&1') do set "PY_VER=%%i"
echo   [OK] Python    !PY_VER!

:: Check for Tkinter (Tcl/Tk support)
!PYTHON_CMD! -c "import tkinter" >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo.
    echo   [WARN] Python was installed without Tkinter [Tcl/Tk] support.
    echo   The graphical desktop controller requires Tkinter.
    echo   To fix: Re-run the Python installer, choose "Modify", and check "tcl/tk and IDLE".
    echo.
)

:: Check for Node.js (Optional for mobile bundling)
set "HAS_NODE=0"
where node >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    set "HAS_NODE=1"
    for /f "tokens=*" %%i in ('node -v') do set "NODE_VER=%%i"
    echo   [OK] Node.js   !NODE_VER!
) else (
    echo   [INFO] Node.js not detected - optional [mobile app can connect directly over LAN].
)

:: ----------------------------------------------------------------
:: 2. Check / Create .env configuration file
:: ----------------------------------------------------------------
echo.
echo [2/5] Verifying environment configuration (.env)...
call :ENSURE_ENV_FILE 0

:: ----------------------------------------------------------------
:: 3. Port check
:: ----------------------------------------------------------------
echo.
echo [3/5] Checking ports (8080, 8000, 8088, 8090)...
for %%P in (8080 8000 8088 8090) do (
    netstat -ano | findstr ":%%P " | findstr "LISTENING" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo   [INFO] Port %%P is currently listening.
    )
)
echo   [OK] Port check complete.

:: ----------------------------------------------------------------
:: 4. Verify & Auto-install Dependencies
:: ----------------------------------------------------------------
echo.
echo [4/5] Verifying Dependencies...
!PYTHON_CMD! -c "import agent_core, mss, aiohttp, fastapi, pyautogui, websockets, qrcode, customtkinter, pycaw, zeroconf" >nul 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo   [INFO] Missing or incomplete Python dependencies detected.
    echo   [INFO] Auto-installing required packages...
    call :DOWNLOAD_PYTHON_DEPS
) else (
    echo   [OK] Python packages verified.
)

if "!HAS_NODE!"=="1" (
    if not exist "apps\mobile\app\node_modules\expo\package.json" (
        echo   [INFO] Installing mobile app dependencies...
        call :DOWNLOAD_NODE_DEPS
    ) else (
        echo   [OK] Mobile dependencies present.
    )
)

:: ----------------------------------------------------------------
:: 4b. Windows Firewall rules (Best Effort)
:: ----------------------------------------------------------------
echo.
echo [4b] Checking Windows Firewall rules (8080 / 8000 / 8088 / 8090)...
set "FW_OK=1"
for %%P in (8080 8000 8088 8090) do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "try { if (-not (Get-NetFirewallRule -DisplayName 'VediPocketPC-%%P' -ErrorAction SilentlyContinue)) { New-NetFirewallRule -DisplayName 'VediPocketPC-%%P' -Direction Inbound -LocalPort %%P -Protocol TCP -Action Allow -Profile Any | Out-Null } else { Set-NetFirewallRule -DisplayName 'VediPocketPC-%%P' -Profile Any | Out-Null }; exit 0 } catch { exit 1 }" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo   [OK]  VediPocketPC-%%P [port %%P]
    ) else (
        set "FW_OK=0"
    )
)
if "!FW_OK!"=="0" (
    echo   [INFO] If your mobile phone cannot reach the PC, right-click start.bat and select "Run as Administrator" once.
)

:: ----------------------------------------------------------------
:: 5. Launch Python Desktop Controller
:: ----------------------------------------------------------------
echo.
echo [5/5] Launching Vedi Pocket PC Controller...
echo.

!PYTHON_CMD! -m apps.desktop.controller.app
set "APP_ERR=!ERRORLEVEL!"
if !APP_ERR! NEQ 0 (
    echo.
    echo   [ERROR] Controller exited with code !APP_ERR!.
    pause
    exit /b !APP_ERR!
)

endlocal
exit /b 0

:: ================================================================
:: Subroutines
:: ================================================================

:ENSURE_ENV_FILE
if exist ".env" (
    if "%~1"=="1" (
        echo   .env file already exists at "%CD%\.env".
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
) > ".env"
echo   [OK] Default .env created successfully.
exit /b 0

:DOWNLOAD_PYTHON_DEPS
echo   Updating pip...
!PYTHON_CMD! -m pip install --upgrade pip >nul 2>&1
echo   Installing shared packages\core (editable)...
!PYTHON_CMD! -m pip install -e packages\core
echo   Installing requirements.txt...
!PYTHON_CMD! -m pip install -r requirements.txt
exit /b 0

:DOWNLOAD_NODE_DEPS
if exist "apps\mobile\app" (
    echo   Installing mobile Expo dependencies in apps\mobile\app\...
    cd apps\mobile\app
    call npm install --legacy-peer-deps
    cd /d "%~dp0\.."
)
exit /b 0