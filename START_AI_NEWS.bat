@echo off
title AI NEWS LETTER — Intelligence Terminal Launcher
color 0B
cls
echo ====================================================================
echo             AI NEWS LETTER — FRONTIER INTELLIGENCE TERMINAL
echo ====================================================================
echo.
echo [1/3] Checking Python runtime environment...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in PATH!
    echo Please install Python 3.10+ from python.org and add to PATH.
    pause
    exit /b 1
)

echo [2/3] Checking if server is already running on port 5000...
powershell -Command "try { $r = (Invoke-WebRequest -Uri 'http://localhost:5000/' -UseBasicParsing -TimeoutSec 2); exit 0 } catch { exit 1 }" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Backend server is already active and healthy!
) else (
    echo [STARTING] Launching Python Flask backend server...
    start /B python backend\app.py
    timeout /t 2 /nobreak >nul
)

echo [3/3] Opening AI News Letter terminal in your default browser...
start http://localhost:5000

echo.
echo ====================================================================
echo  AI NEWS LETTER IS LIVE!
echo  Terminal URL : http://localhost:5000
echo  Main Feed    : http://localhost:5000/home.html
echo ====================================================================
echo.
echo Press any key to exit this launcher window (server stays running).
pause >nul
