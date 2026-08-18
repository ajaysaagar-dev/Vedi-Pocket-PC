@echo off
setlocal EnableDelayedExpansion
title Vedi Pocket PC - Reload Expo App
cd /d "%~dp0\.."

echo ========================================================
echo          Reload Expo Mobile App ^& Metro Cache
echo ========================================================
echo.
echo Clearing Metro packager cache and reloading Expo server...
echo (Press 'r' in this window anytime to send a reload signal to your phone).
echo.

if exist "apps\mobile\app" (
    cd apps\mobile\app
    call npx expo start -c --host lan --port 8088
) else (
    echo [ERROR] 'apps\mobile\app' directory not found.
)

echo.
pause
endlocal
