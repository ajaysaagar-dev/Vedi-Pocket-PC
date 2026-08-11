@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   Vedi Pocket PC - Standalone Desktop App Builder
echo ===================================================
echo.

cd /d "%~dp0"

:: 1. Verify Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not added to PATH.
    pause
    exit /b 1
)

echo [1/3] Checking dependencies...
python -m pip install pyinstaller pillow pywebview qrcode bottle --quiet

echo.
echo [2/3] Building standalone Windows executable with PyInstaller...

python -m PyInstaller --noconfirm VediPocketPCController.spec

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Build failed! Check the output logs above.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo   [SUCCESS] Build completed successfully!
echo   Output Executable: dist\Vedi Pocket PC\Vedi Pocket PC.exe
echo ===================================================
echo.
pause
