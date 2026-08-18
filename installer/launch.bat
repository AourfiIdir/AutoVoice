@echo off
title AutoVoice
cd /d "%~dp0"

echo ========================================
echo   AutoVoice - AI Voice-over Generator
echo ========================================
echo.

:: Start Rust backend
echo Starting backend...
start "AutoVoice Backend" /min cmd /c "cd backend && autovoice-server.exe"

:: Wait for backend to be ready
echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

:: Start Python frontend
echo Starting frontend...
cd app
if exist venv-win\Scripts\python.exe (
    venv-win\Scripts\python.exe main.py
) else (
    echo ERROR: Python virtual environment not found.
    echo Run: cd app ^&^& python -m venv venv ^&^& venv\Scripts\pip install -r requirements.txt
    pause
)

:: Kill backend when frontend closes
taskkill /fi "WindowTitle eq AutoVoice Backend" /t /f >nul 2>&1
