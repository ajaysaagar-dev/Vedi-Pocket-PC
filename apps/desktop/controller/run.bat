@echo off
setlocal
title Vedi Pocket PC Desktop Controller
rem This script lives at apps/desktop/controller/run.bat. Three parents up
rem is the repo root, where the Python interpreter must run ``-m`` so that
rem the ``apps`` top-level package (and the controller's relative imports)
rem resolve.
cd /d "%~dp0\..\..\.."
python -m apps.desktop.controller.app %*
endlocal
