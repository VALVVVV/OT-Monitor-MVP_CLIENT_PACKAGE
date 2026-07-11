@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Resetting demo data...
python reset_demo_data.py
if errorlevel 1 (
    echo.
    echo Demo data reset failed.
    pause
    exit /b 1
)
echo.
echo Demo data reset complete.
pause
