@echo off
setlocal EnableDelayedExpansion
title Vedi Pocket PC - Apps Launcher
cd /d "%~dp0"

echo ========================================================
echo          Vedi Pocket PC - Apps Launcher
echo ========================================================
echo.
echo Pick the app you want to run:
echo   [1] Desktop Controller (Python aiohttp + production composition root)
echo   [2] Agent Server     (FastAPI pairing / control WS)
echo   [3] Streamer Server  (aiohttp screen stream + WS)
echo   [4] Mobile App       (Expo)
echo   [5] Master Setup     (install / verify all deps + .env)
echo.
choice /c 12345 /m "Select option: "
if !ERRORLEVEL! EQU 1 call "%~dp0desktop\controller\run.bat"
if !ERRORLEVEL! EQU 2 call "%~dp0agent\server\run.bat"
if !ERRORLEVEL! EQU 3 call "%~dp0streamer\server\run.bat"
if !ERRORLEVEL! EQU 4 call "%~dp0mobile\app\run.bat"
if !ERRORLEVEL! EQU 5 call "%~dp0..\scripts\setup.bat"
endlocal
