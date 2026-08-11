@echo off
echo =======================================================
echo          BUILDING PC REMOTE WINDOWS EXECUTABLE
echo =======================================================
echo.

:: Check if PyInstaller is installed
python -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] PyInstaller is not installed. Installing it now...
    python -m pip install pyinstaller
) else (
    echo [INFO] PyInstaller is already installed.
)

echo.
echo [INFO] Installing required agent dependencies from requirements.txt...
python -m pip install -r requirements.txt
echo.
echo [INFO] Compiling agent into a single executable file...
echo [INFO] This will run in windowless/background tray mode.
echo.

:: Run PyInstaller
:: --onefile: package into a single .exe
:: --noconsole: hide the command prompt window (runs as a tray application)
:: --clean: clean PyInstaller cache before building
:: --name: name of the resulting executable
python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --clean ^
    --name PCRemoteAgent ^
    --collect-all uvicorn ^
    --collect-all fastapi ^
    --collect-all websockets ^
    --hidden-import pyautogui ^
    --hidden-import zeroconf ^
    --hidden-import pycaw ^
    --hidden-import pystray ^
    --hidden-import PIL ^
    --hidden-import qrcode ^
    --hidden-import comtypes ^
    --hidden-import cryptography ^
    --hidden-import psutil ^
    --hidden-import websockets ^
    --hidden-import wsproto ^
    --hidden-import pythoncom ^
    main.py

if %errorlevel% equ 0 (
    echo.
    echo =======================================================
    echo          BUILD COMPLETED SUCCESSFULLY!
    echo =======================================================
    echo.
    echo Your executable file is located at:
    echo agent\dist\PCRemoteAgent.exe
    echo.
    echo Double-click "PCRemoteAgent.exe" to run it in the background.
    echo Check your Windows system tray for the icon.
    echo Right-click the icon to view the Connection Info popup!
) else (
    echo.
    echo [ERROR] Build failed. Please verify python and pip are in your Path environment.
)
echo.
pause
