@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo     VediPocketPC - Update Runtimes and Install Dependencies
echo =======================================================
echo.

:: Get project root directory (parent of script directory)
set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"
set "ROOT_DIR=%CD%"

echo Project Root: %ROOT_DIR%
echo.

:: Check prerequisites
set HAS_ERRORS=0

where npm >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] 'npm' was not found in your PATH.
    set HAS_ERRORS=1
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] 'python' was not found in your PATH.
    set HAS_ERRORS=1
)

:: =======================================================
:: STEP 1: UPDATE NODE.JS & PYTHON ENVIRONMENT
:: =======================================================
echo.
echo =======================================================
echo [STEP 1/6] Updating Node.js runtime and npm...
echo =======================================================
where winget >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Checking for Node.js runtime updates via winget...
    winget upgrade --id OpenJS.NodeJS -e --accept-source-agreements --accept-package-agreements >nul 2>&1
)
where npm >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Upgrading npm package manager globally...
    call npm install -g npm@latest
) else (
    echo [SKIP] npm not available to upgrade.
)

echo.
echo =======================================================
echo [STEP 2/6] Updating Python environment and pip...
echo =======================================================
where winget >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Checking for Python runtime updates via winget...
    winget upgrade --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements >nul 2>&1
    winget upgrade --id Python.Python.3.11 -e --accept-source-agreements --accept-package-agreements >nul 2>&1
)
where python >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Upgrading pip, setuptools, and wheel...
    python -m pip install --upgrade pip setuptools wheel
) else (
    echo [SKIP] python not available to upgrade.
)

:: =======================================================
:: STEP 2: INSTALL PROJECT LIBRARIES
:: =======================================================
echo.
echo =======================================================
echo [STEP 3/6] Installing Root Desktop App Node dependencies...
echo =======================================================
cd /d "%ROOT_DIR%"
if exist "package.json" (
    call npm install
    if !errorlevel! neq 0 (
        echo [INFO] Retrying with --legacy-peer-deps...
        call npm install --legacy-peer-deps
    )
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install root Node dependencies.
        set HAS_ERRORS=1
    ) else (
        echo [SUCCESS] Root Node dependencies installed successfully.
    )
) else (
    echo [SKIP] package.json not found in root directory.
)

echo.
echo =======================================================
echo [STEP 4/6] Installing Mobile App Node dependencies...
echo =======================================================
if exist "%ROOT_DIR%\veddi-pocketpc\package.json" (
    cd /d "%ROOT_DIR%\veddi-pocketpc"
    call npm install --legacy-peer-deps
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install Mobile App Node dependencies.
        set HAS_ERRORS=1
    ) else (
        echo [SUCCESS] Mobile App Node dependencies installed successfully.
    )
) else (
    echo [SKIP] package.json not found in veddi-pocketpc directory.
)

echo.
echo =======================================================
echo [STEP 5/6] Installing Screen Stream Server Python dependencies...
echo =======================================================
if exist "%ROOT_DIR%\screen-stream-server\requirements.txt" (
    cd /d "%ROOT_DIR%\screen-stream-server"
    python -m pip install --upgrade -r requirements.txt
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install Screen Stream Server Python dependencies.
        set HAS_ERRORS=1
    ) else (
        echo [SUCCESS] Screen Stream Server Python dependencies installed successfully.
    )
) else (
    echo [SKIP] requirements.txt not found in screen-stream-server directory.
)

echo.
echo =======================================================
echo [STEP 6/6] Installing PC Remote Backend Python dependencies...
echo =======================================================
if exist "%ROOT_DIR%\vedi-pocketpc-backend\requirements.txt" (
    cd /d "%ROOT_DIR%\vedi-pocketpc-backend"
    python -m pip install --upgrade -r requirements.txt
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to install PC Remote Backend Python dependencies.
        set HAS_ERRORS=1
    ) else (
        echo [SUCCESS] PC Remote Backend Python dependencies installed successfully.
    )
) else (
    echo [SKIP] requirements.txt not found in vedi-pocketpc-backend directory.
)

cd /d "%ROOT_DIR%"

echo.
echo =======================================================
if %HAS_ERRORS% equ 0 (
    echo    ALL UPDATES AND DEPENDENCIES INSTALLED SUCCESSFULLY!
) else (
    echo    PROCESS COMPLETED WITH WARNINGS/ERRORS.
    echo    Please check the output above for details.
)
echo =======================================================
echo.
pause
