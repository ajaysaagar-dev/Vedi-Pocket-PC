@echo off
setlocal
title Vedi Pocket PC - Cache and Artifact Cleaner
cd /d "%~dp0\.."

echo ========================================================
echo       Vedi Pocket PC - Cache Cleaner (Python / PyInstaller)
echo ========================================================
echo.

echo [1/5] Removing Python __pycache__ directories...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -Path @('apps','packages','infrastructure','scripts','tests') -Filter '__pycache__' -Recurse -Directory -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
echo [OK] __pycache__ directories removed.

echo.
echo [2/5] Removing compiled Python bytecode (*.pyc, *.pyo)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -Path @('apps','packages','infrastructure','scripts','tests') -Include '*.pyc','*.pyo' -Recurse -File -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue"
echo [OK] Compiled bytecode removed.

echo.
echo [3/5] Removing .pytest_cache directories...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-ChildItem -Path @('.','apps','packages','infrastructure','scripts','tests') -Filter '.pytest_cache' -Recurse -Directory -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
echo [OK] .pytest_cache directories removed.

echo.
echo [4/5] Removing PyInstaller build/ and dist/ artifacts...
if exist "build" (
    echo   Removing build\ folder...
    rmdir /s /q "build" 2>nul
)
if exist "dist" (
    echo   Removing dist\ folder...
    rmdir /s /q "dist" 2>nul
)
if exist "release" (
    echo   Removing release\ folder...
    rmdir /s /q "release" 2>nul
)
echo [OK] Build output folders cleaned.

echo.
echo [5/5] Removing temporary logs and locks...
if exist "%TEMP%\vedi_pyinstaller.log" del /f /q "%TEMP%\vedi_pyinstaller.log" 2>nul
if exist "%TEMP%\vedi_pyinstaller_errors.log" del /f /q "%TEMP%\vedi_pyinstaller_errors.log" 2>nul
echo [OK] Temporary build logs cleaned.

echo.
echo ========================================================
echo       CLEAN COMPLETE - Workspace is fresh and clean.
echo ========================================================
echo.
