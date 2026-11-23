@echo off
setlocal
title Push Media Downloader to GitHub
cd /d "%~dp0"

echo ========================================================
echo        Pushing Media Downloader to GitHub
echo ========================================================
echo.
echo Target: https://github.com/barangaysys-ops/media-downloader.git
echo Branch: main
echo.

git push -u origin main

if errorlevel 1 (
    echo.
    echo ========================================================
    echo Push paused or encountered an authentication issue.
    echo If GitHub asked you to sign in, please complete the sign-in
    echo in your browser and run this file again.
    echo ========================================================
) else (
    echo.
    echo ========================================================
    echo [SUCCESS] Your code is now live on GitHub!
    echo Next step: Deploy on Render.com or Railway.app
    echo ========================================================
)

echo.
pause
