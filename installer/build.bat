@echo off
echo ========================================
echo   AutoVoice - Build Release
echo ========================================
echo.

:: Build Rust backend (release)
echo [1/3] Building Rust backend...
cd backend
cargo build --release
if %errorlevel% neq 0 (
    echo ERROR: Rust build failed.
    pause
    exit /b 1
)
cd ..

:: Verify Python venv exists
echo [2/3] Checking Python venv...
if not exist app\venv-win\Scripts\python.exe (
    echo Creating Python virtual environment...
    cd app
    py -3 -m venv venv-win
    venv-win\Scripts\pip install -r requirements.txt
    cd ..
) else (
    echo   venv found.
)

:: Verify Lua script exists
echo [3/3] Checking Lua script...
if not exist backend\target\release\autovoice-server.exe (
    echo ERROR: Rust binary not found. Run cargo build --release first.
    pause
    exit /b 1
)
echo   Binary found: autovoice-server.exe

echo.
echo ========================================
echo   Build complete!
echo ========================================
echo.
echo Next steps:
echo   1. Install Inno Setup from https://jrsoftware.org/isinfo.php
echo   2. Open installer\autovoice.iss in Inno Setup
echo   3. Click Build > Compile
echo   4. Run the installer from installer_output\
echo.
pause
