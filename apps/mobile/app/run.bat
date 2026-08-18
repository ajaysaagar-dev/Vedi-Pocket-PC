@echo off
setlocal
title Vedi Pocket PC Mobile App (Expo)
cd /d "%~dp0"
if not exist node_modules\expo\package.json (
    echo Installing mobile app deps ^(first run^)...
    call npm install --legacy-peer-deps || goto :eof
)
call npx expo start --host lan --port 8088
endlocal
