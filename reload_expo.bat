@echo off
setlocal EnableDelayedExpansion
title Vedi Pocket PC - Reload Expo App
cd /d "%~dp0"

echo ========================================================
echo          Reload Expo Mobile App ^& Metro Cache
echo ========================================================
echo.
echo Clearing Metro packager cache and reloading Expo server...
echo (Press 'r' in this window anytime to send a reload signal to your phone).
echo.

if exist "veddi-pocketpc" (
    cd veddi-pocketpc
    call npx expo start -c
) else (
    echo [ERROR] 'veddi-pocketpc' directory not found.
)

echo.
pause
endlocal
