@echo off
setlocal EnableDelayedExpansion
title Vedi Pocket PC - One-Click Installer
cd /d "%~dp0.."

echo ========================================================
echo           Vedi Pocket PC - Master Setup
echo ========================================================
echo.

:: Check Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in PATH.
    echo Please download and install Python 3.10+ from: https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PY_VER=%%i
echo [OK] Python version:  %PY_VER%

:: Check Node.js
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js is not found in PATH.
    echo Please download and install Node.js v18+ from: https://nodejs.org/
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node -v') do set NODE_VER=%%i
echo [OK] Node.js version: %NODE_VER%

echo.
echo ========================================================
echo [1/3] Installing agent-core (editable) ...
echo ========================================================
python -m pip install -e packages\core
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] agent-core editable install returned non-zero.
)

echo.
echo ========================================================
echo [2/3] Installing Python Dependencies (PySide6 & Backends)...
echo ========================================================
python -m pip install --upgrade pip
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Python installation finished with warnings/errors.
)

echo.
echo ========================================================
echo [3/3] Installing Mobile App (Expo) Dependencies...
echo ========================================================
cd apps\mobile\app
call pnpm install
set "MOBILE_ERR=%ERRORLEVEL%"
cd ..
if !MOBILE_ERR! NEQ 0 (
    echo [ERROR] Failed to install mobile app dependencies via pnpm.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo [4/4] Creating / Verifying .env Configuration...
echo ========================================================
if not exist "%~dp0..\.env" (
    echo [INFO] Creating default .env file...
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
    ) > "%~dp0..\.env"
    echo [OK] Created .env file successfully.
) else (
    echo [OK] .env file already present.
)

echo.
echo ========================================================
echo        ALL DEPENDENCIES INSTALLED SUCCESSFULLY!
echo ========================================================
echo.
set /p LAUNCH="Would you like to start Vedi Pocket PC now? (Y/N): "
if /i "%LAUNCH%"=="Y" (
    echo.
    echo Starting Vedi Pocket PC...
    python apps\desktop\controller\app.py
) else (
    echo.
    echo You can start the app anytime by running 'scripts\start.bat' or 'python apps\desktop\controller\app.py'.
)

pause
