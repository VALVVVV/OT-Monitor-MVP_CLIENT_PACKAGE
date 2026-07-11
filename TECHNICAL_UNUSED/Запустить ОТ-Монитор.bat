@echo off
chcp 65001 >nul
cd /d "%~dp0"
setlocal

where python >nul 2>&1
if errorlevel 1 (
  echo На этом компьютере не найден Python.
  echo.
  echo Для запуска папки ОТ-Монитор нужен установленный Python.
  echo.
  echo Сначала откройте "Проверить готовность.bat".
  pause
  exit /b 1
)

python -c "import requests, bs4" >nul 2>&1
if errorlevel 1 (
  echo Не найдены библиотеки requests / beautifulsoup4.
  echo.
  echo Сначала откройте "Проверить готовность.bat".
  echo.
  pause
  exit /b 1
)

if not exist "server.py" (
  echo Не найден файл server.py.
  echo Проверьте целостность папки ОТ-Монитор.
  echo.
  pause
  exit /b 1
)

echo ОТ-Монитор MVP запускается
echo.
echo Не закрывайте это окно, пока работает MVP
echo Для остановки нажмите Ctrl+C
echo Браузер должен открыться автоматически
echo Адрес MVP: http://127.0.0.1:8000
echo.

start "" powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8000'"
python server.py

echo.
if errorlevel 1 (
  echo Сервер завершился с ошибкой.
  echo Проверьте сообщения выше.
) else (
  echo Сервер остановлен.
)
echo.
pause