@echo off
setlocal
title Multi-Media Downloader
cd /d "%~dp0"

echo ========================================================
echo             Multi-Media Video Downloader
echo ========================================================
echo.

if not exist "%~dp0venv\Scripts\python.exe" (
    echo Setting up Python virtual environment...
    python -m venv "%~dp0venv"
    "%~dp0venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
)

echo Starting Multi-Media Downloader Server...
echo Opening browser at http://127.0.0.1:5000
echo.
echo (Keep this window open while using the downloader)
echo.

"%~dp0venv\Scripts\python.exe" "%~dp0app.py"

if errorlevel 1 (
    echo.
    echo An unexpected error occurred while running the server.
    pause
)
