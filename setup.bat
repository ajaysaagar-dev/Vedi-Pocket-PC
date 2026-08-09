@echo off
title Vedi Pocket PC - One-Click Installer
cd /d "%~dp0"

echo ========================================================
echo           Vedi Pocket PC - Master Setup
echo ========================================================
echo.

:: Check Node.js
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js is not found in PATH.
    echo Please download and install Node.js (v18+) from: https://nodejs.org/
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node -v') do set NODE_VER=%%i
echo [OK] Node.js version: %NODE_VER%

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

echo.
echo ========================================================
echo [1/3] Installing Python Dependencies (Requirements)...
echo ========================================================
python -m pip install --upgrade pip
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Python installation finished with warnings/errors.
)

echo.
echo ========================================================
echo [2/3] Installing Desktop App (Electron) Dependencies...
echo ========================================================
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install desktop dependencies.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo [3/3] Installing Mobile App (Expo) Dependencies...
echo ========================================================
cd mobile
call npm install
cd ..
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install mobile app dependencies.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo        🎉 ALL DEPENDENCIES INSTALLED SUCCESSFULLY!       
echo ========================================================
echo.
set /p LAUNCH="Would you like to start Vedi Pocket PC now? (Y/N): "
if /i "%LAUNCH%"=="Y" (
    echo.
    echo Starting Vedi Pocket PC...
    npm start
) else (
    echo.
    echo You can start the app anytime by double-clicking 'start.bat' or running 'npm start'.
)

pause
