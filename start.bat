@echo off
setlocal EnableDelayedExpansion
title Vedi Pocket PC - Launcher
cd /d "%~dp0"

echo ========================================================
echo           Vedi Pocket PC - Launcher
echo ========================================================
echo.
echo Launch Options:
echo   [1] Start Vedi Pocket PC (Normal - Desktop + Backend + Mobile)
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
if exist "veddi-pocketpc" (
    cd veddi-pocketpc
    set EXPO_NO_INTERACTIVE=1
    set CI=1
    call npx expo start -c --non-interactive --host lan --port 8088
) else (
    echo   [ERROR] Mobile directory 'veddi-pocketpc' not found.
)
pause
exit /b 0

:START_EXPO_INTERACTIVE
echo.
echo ========================================================
echo     Starting Expo Mobile App ^(Interactive Terminal^)...
echo ========================================================
echo.
if exist "veddi-pocketpc" (
    cd veddi-pocketpc
    call npx expo start -c --host lan --port 8088
) else (
    echo   [ERROR] Mobile directory 'veddi-pocketpc' not found.
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
:: 1. Pre-flight checks — fail fast with a clear message if the
::    developer's machine is missing a runtime.
:: ----------------------------------------------------------------
echo [1/6] Checking prerequisites...

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
:: 2. Check / Create .env configuration file
:: ----------------------------------------------------------------
echo.
echo [2/6] Verifying environment configuration ^(.env^)...
call :ENSURE_ENV_FILE 0

:: ----------------------------------------------------------------
:: 3. Non-destructive port check (8080, 8000, 8088)
:: ----------------------------------------------------------------
echo.
echo [3/6] Checking required ports ^(8080, 8000, 8088^)...
for %%P in (8080 8000 8088) do (
    netstat -ano | findstr ":%%P " | findstr "LISTENING" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo   [INFO] Port %%P is in use by another app. Controller will auto-bind to next free port.
    )
)
echo   [OK] Port check complete.

:: ----------------------------------------------------------------
:: 4. Install Python deps if missing
:: ----------------------------------------------------------------
echo.
echo [4/6] Verifying Python dependencies...
python -c "import mss, aiohttp, fastapi, pyautogui, websockets" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   [INFO] Missing Python deps. Running pip install...
    call :DOWNLOAD_PYTHON_DEPS 0
) else (
    echo   [OK] Python deps present.
)

:: ----------------------------------------------------------------
:: 5. Install Node deps if missing
:: ----------------------------------------------------------------
echo.
echo [5/6] Verifying Node dependencies...
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
:: 5b. Firewall rules
:: ----------------------------------------------------------------
echo.
echo [5b] Ensuring Windows Firewall allows inbound 8080 / 8000 / 8088...
set "FW_OK=1"
for %%P in (8080 8000 8088) do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "try { if (-not (Get-NetFirewallRule -DisplayName 'VediPocketPC-%%P' -ErrorAction SilentlyContinue)) { New-NetFirewallRule -DisplayName 'VediPocketPC-%%P' -Direction Inbound -LocalPort %%P -Protocol TCP -Action Allow -Profile Private,Domain | Out-Null }; exit 0 } catch { exit 1 }" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo   [OK]  VediPocketPC-%%P ^(port %%P^)
    ) else (
        echo   [WARN] Could not add VediPocketPC-%%P ^(port %%P^).
        echo          Re-run this window as Administrator if your phone
        echo          can't reach the controller.
        set "FW_OK=0"
    )
)
if "!FW_OK!"=="0" (
    echo.
    echo   Phones may not be able to connect. Re-run start.bat as
    echo   Administrator ^(right-click start.bat ^> Run as administrator^)
    echo   to install the firewall rules automatically.
    echo.
)

:: ----------------------------------------------------------------
:: 6. Launch.
:: ----------------------------------------------------------------
echo.
echo [6/6] Launching Vedi Pocket PC...
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
            echo   Skipped overwriting .env file.
            goto :EOF
        )
    ) else (
        echo   [OK] .env file present.
        goto :EOF
    )
)

echo   [INFO] Creating .env file with default configuration...
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
) > "%~dp0.env"
echo   [OK] Created .env file successfully.
goto :EOF

:DOWNLOAD_PYTHON_DEPS
echo   [INFO] Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install -e packages\agent-core
python -m pip install -r requirements.txt
if !ERRORLEVEL! NEQ 0 (
    echo.
    echo   [ERROR] pip install failed. Check your network / proxy settings.
    if "%~1"=="1" ( exit /b 1 ) else ( pause & exit /b 1 )
)
echo   [OK] Python dependencies installed.
goto :EOF

:DOWNLOAD_NODE_DEPS
echo   [INFO] Installing Desktop App ^(Electron^) dependencies...
call npm install --legacy-peer-deps
if !ERRORLEVEL! NEQ 0 (
    echo   [ERROR] Root npm install failed.
    if "%~1"=="1" ( exit /b 1 ) else ( pause & exit /b 1 )
)

echo.
echo   [INFO] Installing Mobile App ^(Expo^) dependencies...
cd veddi-pocketpc
call npm install --legacy-peer-deps
set "MOBILE_ERR=!ERRORLEVEL!"
cd ..
if !MOBILE_ERR! NEQ 0 (
    echo   [ERROR] Mobile app npm install failed.
    if "%~1"=="1" ( exit /b 1 ) else ( pause & exit /b 1 )
)
echo   [OK] Node.js dependencies installed.
goto :EOF