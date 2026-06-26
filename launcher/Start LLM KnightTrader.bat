@echo off
title Start LLM KnightTrader
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\start_core.ps1" -OpenBrowser
if errorlevel 1 (
    echo.
    echo Start failed. See data\logs\ and messages above.
    pause
    exit /b 1
)
echo.
echo Started. Dashboard: http://127.0.0.1:8765
timeout /t 4 >nul 2>nul
