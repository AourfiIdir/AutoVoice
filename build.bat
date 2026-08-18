@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo   AutoVoice Build Script
echo ========================================
echo.

:: 1. Build Rust backend
echo [1/3] Building Rust backend...
cd backend
cargo build --release
if errorlevel 1 (
    echo ERROR: Rust build failed.
    exit /b 1
)
cd ..

:: 2. Build Python frontend with PyInstaller
echo [2/3] Building Python frontend...
cd app
if not exist venv-win\Scripts\python.exe (
    echo ERROR: venv-win not found. Run:
    echo   cd app ^&^& python -m venv venv-win ^&^& venv-win\Scripts\pip install -r requirements.txt ^&^& venv-win\Scripts\pip install pyinstaller
    exit /b 1
)
venv-win\Scripts\pyinstaller.exe autovoice.spec --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    exit /b 1
)
cd ..

:: 3. Build installer with Inno Setup
echo [3/3] Building installer...
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\autovoice.iss
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    "C:\Program Files\Inno Setup 6\ISCC.exe" installer\autovoice.iss
) else if exist "C:\Program Files\Inno Setup 7\ISCC.exe" (
    "C:\Program Files\Inno Setup 7\ISCC.exe" installer\autovoice.iss
) else if exist "C:\Program Files (x86)\Inno Setup 7\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 7\ISCC.exe" installer\autovoice.iss
) else (
    echo ERROR: Inno Setup not found.
    echo Install via winget: winget install --id JRSoftware.InnoSetup
    echo Or download from: https://jrsoftware.org/isdl.php
    exit /b 1
)

if errorlevel 1 (
    echo ERROR: Installer build failed.
    exit /b 1
)

echo.
echo ========================================
echo   Build complete!
echo   Installer: installer_output\AutoVoice_Setup_0.1.0.exe
echo ========================================
