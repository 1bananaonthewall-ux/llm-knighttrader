@echo off
title Stop LLM KnightTrader
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\stop_all.ps1"
if errorlevel 1 (
    echo.
    echo Stop failed — some processes may still be running.
    pause
    exit /b 1
)
echo.
echo Stopped.
timeout /t 3 >nul 2>nul
