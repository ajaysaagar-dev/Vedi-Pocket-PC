@echo off
setlocal EnableDelayedExpansion
title Vedi Pocket PC - Reload Expo App
cd /d "%~dp0.."

echo ========================================================
echo          Reload Expo Mobile App ^& Metro Cache
echo ========================================================
echo.
echo Clearing Metro packager cache and reloading Expo server...
echo (Press 'r' in this window anytime to send a reload signal to your phone).
echo.

if exist "Vedi-PocketPC-Mobile" (
    cd Vedi-PocketPC-Mobile
    call npx expo start -c
) else (
    echo [ERROR] 'Vedi-PocketPC-Mobile' directory not found.
)

echo.
pause
endlocal
