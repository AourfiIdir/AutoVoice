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

:: Start Python frontend (single exe)
echo Starting frontend...
AutoVoice.exe

:: Kill backend when frontend closes
taskkill /fi "WindowTitle eq AutoVoice Backend" /t /f >nul 2>&1
