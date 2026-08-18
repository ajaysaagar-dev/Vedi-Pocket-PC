@echo off
setlocal
title Vedi Pocket PC Streamer Server
cd /d "%~dp0\..\..\.."
python -m apps.streamer.server.main %*
endlocal
