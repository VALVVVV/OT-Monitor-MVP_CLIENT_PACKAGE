@echo off
chcp 65001 >nul
cd /d "%~dp0"
setlocal EnableDelayedExpansion

set "RESULT_FILE=РЕЗУЛЬТАТ_ПРОВЕРКИ_ГОТОВНОСТИ.txt"
set "PYTHON_FOUND=нет"
set "PYTHON_VERSION=не определена"
set "LIBS_FOUND=нет"
set "FILES_STATUS=не проверены"
set "FINAL_STATUS=не готово"
set "NEXT_STEP=Установите Python или обратитесь к техническому специалисту."
set "MISSING_FILES=0"
set "MISSING_ITEMS="

break > "%RESULT_FILE%"
echo ==================================>> "%RESULT_FILE%"
echo Проверка готовности ОТ-Монитор>> "%RESULT_FILE%"
echo ==================================>> "%RESULT_FILE%"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"`) do set "CHECK_TIME=%%I"
echo Дата и время проверки: !CHECK_TIME!>> "%RESULT_FILE%"
echo.>> "%RESULT_FILE%"

echo ==================================
echo Проверка готовности ОТ-Монитор
echo ==================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo На этом компьютере не найден Python.
  echo На этом компьютере не найден Python.>> "%RESULT_FILE%"
  set "NEXT_STEP=Установите Python 3 и снова запустите Проверить готовность.bat."
  goto :finish
)

set "PYTHON_FOUND=да"
for /f "usebackq delims=" %%I in (`python -c "import sys; print(sys.version.split()[0])" 2^>nul`) do set "PYTHON_VERSION=%%I"
echo Python найден.
echo Версия Python: !PYTHON_VERSION!
echo Python найден: да>> "%RESULT_FILE%"
echo Версия Python: !PYTHON_VERSION!>> "%RESULT_FILE%"
echo.
echo.>> "%RESULT_FILE%"

python -c "import requests, bs4" >nul 2>&1
if errorlevel 1 (
  echo Не найдены библиотеки requests / beautifulsoup4.
  echo Библиотеки requests и beautifulsoup4: не найдены>> "%RESULT_FILE%"
  set "NEXT_STEP=Установите requests и beautifulsoup4, затем повторите проверку."
  goto :finish
)

set "LIBS_FOUND=да"
echo Библиотеки requests и beautifulsoup4 найдены.
echo Библиотеки requests и beautifulsoup4: найдены>> "%RESULT_FILE%"
echo.
echo.>> "%RESULT_FILE%"

call :check_file "server.py"
call :check_file "index.html"
call :check_file "app.js"
call :check_file "style.css"
call :check_file "run_demo_check.py"
call :check_dir "assets"
call :check_dir "data"
call :check_file "data\review_comments.json"

if "%MISSING_FILES%"=="0" (
  set "FILES_STATUS=все основные файлы и папки найдены"
  set "FINAL_STATUS=готово"
  set "NEXT_STEP=Запустите файл Запустить ОТ-Монитор.bat."
  echo Готовность подтверждена.
  echo Можно запускать файл "Запустить ОТ-Монитор.bat".
) else (
  set "FILES_STATUS=есть отсутствующие файлы или папки"
  set "NEXT_STEP=Проверьте состав папки ОТ-Монитор и восстановите отсутствующие элементы."
  echo Обнаружены отсутствующие файлы или папки.
  echo Проверьте состав папки ОТ-Монитор.
)

goto :finish

:check_file
if exist %~1 (
  echo [OK] Файл найден: %~1
  echo [OK] Файл найден: %~1>> "%RESULT_FILE%"
) else (
  echo [X] Не найден файл: %~1
  echo [X] Не найден файл: %~1>> "%RESULT_FILE%"
  set "MISSING_FILES=1"
  if defined MISSING_ITEMS (
    set "MISSING_ITEMS=!MISSING_ITEMS!, %~1"
  ) else (
    set "MISSING_ITEMS=%~1"
  )
)
exit /b 0

:check_dir
if exist %~1 (
  echo [OK] Папка найдена: %~1
  echo [OK] Папка найдена: %~1>> "%RESULT_FILE%"
) else (
  echo [X] Не найдена папка: %~1
  echo [X] Не найдена папка: %~1>> "%RESULT_FILE%"
  set "MISSING_FILES=1"
  if defined MISSING_ITEMS (
    set "MISSING_ITEMS=!MISSING_ITEMS!, %~1"
  ) else (
    set "MISSING_ITEMS=%~1"
  )
)
exit /b 0

:finish
echo.>> "%RESULT_FILE%"
echo Python найден: !PYTHON_FOUND!>> "%RESULT_FILE%"
echo Версия Python: !PYTHON_VERSION!>> "%RESULT_FILE%"
echo Библиотеки requests и beautifulsoup4: !LIBS_FOUND!>> "%RESULT_FILE%"
echo Основные файлы проекта: !FILES_STATUS!>> "%RESULT_FILE%"
if defined MISSING_ITEMS echo Отсутствуют: !MISSING_ITEMS!>> "%RESULT_FILE%"
echo Итог: !FINAL_STATUS!>> "%RESULT_FILE%"
echo Что делать дальше: !NEXT_STEP!>> "%RESULT_FILE%"

echo.
echo Проверка завершена.
echo Результат сохранён в файл:
echo %RESULT_FILE%
echo.
echo Проверка завершена.>> "%RESULT_FILE%"
echo Результат сохранён в файл: %RESULT_FILE%>> "%RESULT_FILE%"
pause
exit /b %MISSING_FILES%