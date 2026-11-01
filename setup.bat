@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title LessonLingo - Automated Setup

echo ============================================================
echo               LessonLingo - Setup Wizard
echo    Free lessons in your language. Offline once set up.
echo ============================================================
echo.

:: 1. Detect Python 3.11
echo [1/6] Checking for Python 3.11...
set PYTHON_CMD=

py -3.11 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=py -3.11
    goto :python_found
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo %PY_VER% | findstr /i "3.11" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=python
    goto :python_found
)

echo [!] Python 3.11 was not detected on your system.
where winget >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [*] Attempting to install Python 3.11 via Windows Package Manager (winget)...
    winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
    if %ERRORLEVEL% EQU 0 (
        echo [*] Python 3.11 installed. Refreshing environment...
        set PYTHON_CMD=py -3.11
        goto :python_found
    )
)

echo [ERROR] Please install Python 3.11 manually from:
echo https://www.python.org/downloads/release/python-3119/
echo Make sure to check "Add python.exe to PATH" during installation.
echo After installing Python 3.11, re-run this setup script.
echo.
pause
exit /b 1

:python_found
echo [*] Using Python: %PYTHON_CMD%
%PYTHON_CMD% --version

:: 2. Create Virtual Environment
echo.
echo [2/6] Preparing Python virtual environment (.venv)...
if not exist ".venv\Scripts\activate.bat" (
    echo [*] Creating virtual environment in .venv...
    %PYTHON_CMD% -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [*] Existing virtual environment found.
)

call .venv\Scripts\activate.bat
echo [*] Upgrading pip...
python -m pip install --upgrade pip

:: 3. GPU / PyTorch Detection and Installation
echo.
echo [3/6] Configuring PyTorch (GPU / CPU)...
nvidia-smi >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [*] NVIDIA GPU detected. Installing PyTorch with CUDA 12.4 support...
    python -m pip install torch --index-url https://download.pytorch.org/whl/cu124
) else (
    echo [*] No NVIDIA GPU detected. Installing standard PyTorch for CPU...
    python -m pip install torch
)

:: 4. Install Dependencies & LessonLingo
echo.
echo [4/6] Installing dependencies and LessonLingo...
python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Dependency installation encountered an issue.
    echo If IndicTransToolkit failed to build, please install the C++ build tools:
    echo https://visualstudio.microsoft.com/visual-cpp-build-tools/
    echo (Select "Desktop development with C++" workload)
    echo.
    pause
    exit /b 1
)

:: 5. Check FFmpeg
echo.
echo [5/6] Checking for FFmpeg (required for lecture videos)...
where ffmpeg >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [*] FFmpeg is installed and available.
) else (
    echo [!] FFmpeg not found in PATH.
    where winget >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo [*] Installing FFmpeg via winget...
        winget install ffmpeg --accept-package-agreements --accept-source-agreements
        echo [*] Note: If newly installed, you may need to restart terminal/script for PATH to update.
    ) else (
        echo [!] Please install FFmpeg manually from https://ffmpeg.org/ or run:
        echo     winget install ffmpeg
    )
)

:: 6. Hugging Face Login and Model Download
echo.
echo [6/6] Model Download and Hugging Face Setup
echo ============================================================
echo IndicTrans2 models require free access approval on Hugging Face:
echo   1. https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M
echo   2. https://huggingface.co/ai4bharat/indictrans2-en-indic-1B
echo.
echo Please ensure you are logged into Hugging Face in your browser
echo and have clicked "Access repository" on both model pages.
echo ============================================================
echo.
set /p RUN_SETUP="Do you want to log in and download models now? (Y/N): "
if /i "%RUN_SETUP%"=="Y" (
    echo [*] Starting Hugging Face authentication and model download...
    python -m lessonlingo.cli setup
    if %ERRORLEVEL% EQU 0 (
        echo [*] Verifying offline cache...
        python -m lessonlingo.cli verify
    ) else (
        echo [!] Model setup did not finish. You can rerun `setup.bat` or run `lessonlingo setup` later.
    )
) else (
    echo [*] Skipping model download for now.
    echo You can download models later anytime by running:
    echo     lessonlingo setup
)

echo.
echo ============================================================
echo                    SETUP COMPLETE!
echo ============================================================
echo You can now launch LessonLingo anytime by double-clicking:
echo     start.bat
echo ============================================================
echo.
pause
