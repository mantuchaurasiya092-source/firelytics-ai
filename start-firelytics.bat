@echo off
setlocal
set "ROOT=%~dp0"

where python.exe >nul 2>&1
if errorlevel 1 (
    where py.exe >nul 2>&1
    if errorlevel 1 (
        echo Python 3.12-3.15 is required. Install Python and rerun this script.
        exit /b 1
    )
)

where node.exe >nul 2>&1
if errorlevel 1 if not exist "%ROOT%.tools\node-v22.23.5-win-x64\node.exe" (
    echo Node.js 22 is required. Install Node.js 22 or restore the bundled .tools runtime.
    exit /b 1
)

if not exist "%ROOT%start-local.ps1" (
    echo The existing startup helper start-local.ps1 is missing.
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%start-local.ps1" %*
exit /b %errorlevel%
