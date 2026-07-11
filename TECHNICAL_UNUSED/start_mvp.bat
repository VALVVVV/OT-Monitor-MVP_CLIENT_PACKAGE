@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ОТ-Монитор MVP запускается
echo Не закрывайте это окно, пока работает MVP
echo Для остановки нажмите Ctrl+C
echo Откройте http://127.0.0.1:8000, если браузер не открылся автоматически
echo.

start "" powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8000'"
python server.py
