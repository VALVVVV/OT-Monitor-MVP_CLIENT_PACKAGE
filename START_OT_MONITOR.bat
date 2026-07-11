@echo off
cd /d "%~dp0"
setlocal

where python >nul 2>&1
if errorlevel 1 (
  echo Python was not found on this computer.
  echo Please install Python 3 for Windows and try again.
  echo.
  pause
  exit /b 1
)

if not exist "server.py" (
  echo File server.py was not found.
  echo Please check the OT-Monitor folder.
  echo.
  pause
  exit /b 1
)

echo OT-Monitor is starting...
echo Do not close this window while the local server is running.
echo Browser address: http://127.0.0.1:8000
echo.

start "" powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8000'"
python server.py

echo.
echo Server stopped.
pause