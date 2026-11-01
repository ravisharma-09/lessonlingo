@echo off
setlocal
cd /d "%~dp0"
title LessonLingo - Web App

echo ============================================================
echo                    Starting LessonLingo
echo ============================================================
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment (.venv) not found.
    echo Please run setup.bat first to complete the one-time installation.
    echo.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo [*] Opening LessonLingo in your browser at http://127.0.0.1:7860...
start http://127.0.0.1:7860

echo [*] Starting LessonLingo server (warm light model, offline mode)...
echo Close this window to stop LessonLingo.
echo.

lessonlingo app --warm light --offline

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] LessonLingo exited with error code %ERRORLEVEL%.
    pause
)
