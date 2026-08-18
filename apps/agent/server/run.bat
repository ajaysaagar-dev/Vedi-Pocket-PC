@echo off
setlocal
title Vedi Pocket PC Agent Server
cd /d "%~dp0\..\..\.."
python -m apps.agent.server.main %*
endlocal
