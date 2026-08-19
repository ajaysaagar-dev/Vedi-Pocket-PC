@echo off
setlocal EnableDelayedExpansion
title Vedi Pocket PC - Windows Application Builder
cd /d "%~dp0\.."

echo ========================================================
echo       Vedi Pocket PC - Windows Standalone Builder
echo ========================================================
echo.

:: --- Step 1: Verify Python Environment ---
echo [1/5] Verifying Python Environment...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in PATH.
    echo Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "PY_VER=%%i"
echo [OK] Python Version: %PY_VER%

:: --- Step 2: Ensure Dependencies and PyInstaller ---
echo.
echo [2/5] Installing and Updating Build Dependencies...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
)
python -m pip install -e packages\core >nul 2>&1
python -m pip install -r requirements.txt >nul 2>&1
echo [OK] Dependencies verified and ready.

:: --- Step 3: Clean Previous Build Artifacts ---
echo.
echo [3/5] Cleaning previous build output...
if exist "build" rmdir /s /q "build" 2>nul
if exist "dist\VediPocketPC" rmdir /s /q "dist\VediPocketPC" 2>nul
if exist "release" rmdir /s /q "release" 2>nul
echo [OK] Workspace cleaned.

:: --- Step 4: Run PyInstaller ---
echo.
echo [4/5] Running PyInstaller on apps\desktop\controller\VediPocketPC.spec...
python -m PyInstaller --noconfirm --clean apps\desktop\controller\VediPocketPC.spec
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] PyInstaller build failed with exit code %ERRORLEVEL%.
    pause
    exit /b %ERRORLEVEL%
)

if not exist "dist\VediPocketPC\VediPocketPC.exe" (
    echo.
    echo [ERROR] Build output dist\VediPocketPC\VediPocketPC.exe was not created.
    pause
    exit /b 1
)
echo [OK] PyInstaller package successfully created at dist\VediPocketPC\

:: Copy standalone EXE to root of dist for direct access
if exist "dist\VediPocketPC\VediPocketPC.exe" (
    copy /Y "dist\VediPocketPC\VediPocketPC.exe" "dist\VediPocketPC.exe" >nul 2>&1
)

:: --- Step 5: Inno Setup Installer (Optional) and Final Packaging ---
echo.
echo [5/5] Finalizing Packaging and Installer...

set "ISCC_EXE="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC_EXE=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC_EXE=C:\Program Files\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" set "ISCC_EXE=C:\Program Files (x86)\Inno Setup 5\ISCC.exe"

if not defined ISCC_EXE goto NO_INNO

echo [INFO] Inno Setup compiler found at: !ISCC_EXE!
echo [INFO] Compiling Windows Installer...

if not exist "release\Vedi Pocket PC" mkdir "release\Vedi Pocket PC"
xcopy /E /I /Y "dist\VediPocketPC\*" "release\Vedi Pocket PC\" >nul 2>&1
copy /Y "apps\desktop\controller\installer.iss" "release\setup.iss" >nul 2>&1

"!ISCC_EXE!" "release\setup.iss" /O"dist"
if !ERRORLEVEL! EQU 0 (
    echo [OK] Windows installer created successfully.
) else (
    echo [WARN] Inno Setup compilation encountered an issue. Standalone EXE is ready.
)
if exist "release" rmdir /s /q "release" 2>nul
goto DONE_INNO

:NO_INNO
echo [INFO] Inno Setup was not found on this machine.
echo [INFO] Standalone application package dist\VediPocketPC\ is ready for use.

:DONE_INNO
:: Generate SHA256 Checksums
python scripts\write_checksums.py dist dist\SHA256SUMS.txt >nul 2>&1

echo.
echo ========================================================
echo       BUILD SUCCESSFUL
echo ========================================================
echo   Standalone Application: %CD%\dist\VediPocketPC\VediPocketPC.exe
if exist "dist\Vedi Pocket PC Setup-1.0.0.exe" (
    echo   Windows Installer:      %CD%\dist\Vedi Pocket PC Setup-1.0.0.exe
)
if exist "dist\SHA256SUMS.txt" (
    echo   Checksums:              %CD%\dist\SHA256SUMS.txt
)
echo ========================================================
echo.
