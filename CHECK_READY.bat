@echo off
cd /d "%~dp0"
setlocal EnableDelayedExpansion

set "RESULT_FILE=CHECK_READY_RESULT.txt"
set "PYTHON_FOUND=NO"
set "PYTHON_VERSION=NOT_FOUND"
set "REQUESTS_FOUND=NO"
set "BS4_FOUND=NO"
set "PROJECT_READY=NO"
set "NEXT_STEP=Install Python or contact technical support."
set "MISSING_ITEMS="
set "HAS_ERRORS=0"

break > "%RESULT_FILE%"
echo ==================================>> "%RESULT_FILE%"
echo OT-Monitor readiness check>> "%RESULT_FILE%"
echo ==================================>> "%RESULT_FILE%"
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "Get-Date -Format 'yyyy-MM-dd HH:mm:ss'"`) do set "CHECK_TIME=%%I"
echo Check time: !CHECK_TIME!>> "%RESULT_FILE%"
echo.>> "%RESULT_FILE%"

echo ==================================
echo OT-Monitor readiness check
echo ==================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo Python: NOT FOUND
  echo Python: NOT FOUND>> "%RESULT_FILE%"
  set "NEXT_STEP=Install Python 3 for Windows and run this file again."
  goto finish
)

set "PYTHON_FOUND=YES"
for /f "usebackq delims=" %%I in (`python -c "import sys; print(sys.version.split()[0])" 2^>nul`) do set "PYTHON_VERSION=%%I"
echo Python: FOUND
echo Python version: !PYTHON_VERSION!
echo Python: FOUND>> "%RESULT_FILE%"
echo Python version: !PYTHON_VERSION!>> "%RESULT_FILE%"
echo.>> "%RESULT_FILE%"
echo.

python -c "import requests" >nul 2>&1
if errorlevel 1 (
  echo requests: NOT FOUND
  echo requests: NOT FOUND>> "%RESULT_FILE%"
  set "NEXT_STEP=Install requests and run this file again."
  set "HAS_ERRORS=1"
) else (
  set "REQUESTS_FOUND=YES"
  echo requests: FOUND
  echo requests: FOUND>> "%RESULT_FILE%"
)

python -c "import bs4" >nul 2>&1
if errorlevel 1 (
  echo bs4: NOT FOUND
  echo bs4: NOT FOUND>> "%RESULT_FILE%"
  set "NEXT_STEP=Install beautifulsoup4 and run this file again."
  set "HAS_ERRORS=1"
) else (
  set "BS4_FOUND=YES"
  echo bs4: FOUND
  echo bs4: FOUND>> "%RESULT_FILE%"
)

echo.>> "%RESULT_FILE%"
echo.

call :check_file "server.py"
call :check_file "index.html"
call :check_file "app.js"
call :check_file "style.css"
call :check_file "run_demo_check.py"
call :check_dir "data"
call :check_file "data\review_comments.json"
call :check_dir "assets"

if "%HAS_ERRORS%"=="0" (
  set "PROJECT_READY=YES"
  set "NEXT_STEP=Next step: Run START_OT_MONITOR.bat if it exists, or use the Russian launch file."
  echo Ready: YES
) else (
  echo Ready: NO
  if not defined MISSING_ITEMS (
    set "NEXT_STEP=Check missing libraries or project files."
  ) else (
    set "NEXT_STEP=Restore missing project files and run this file again."
  )
)

goto finish

:check_file
if exist %~1 (
  echo [OK] File found: %~1
  echo [OK] File found: %~1>> "%RESULT_FILE%"
) else (
  echo [X] File missing: %~1
  echo [X] File missing: %~1>> "%RESULT_FILE%"
  set "HAS_ERRORS=1"
  if defined MISSING_ITEMS (
    set "MISSING_ITEMS=!MISSING_ITEMS!, %~1"
  ) else (
    set "MISSING_ITEMS=%~1"
  )
)
exit /b 0

:check_dir
if exist %~1 (
  echo [OK] Folder found: %~1
  echo [OK] Folder found: %~1>> "%RESULT_FILE%"
) else (
  echo [X] Folder missing: %~1
  echo [X] Folder missing: %~1>> "%RESULT_FILE%"
  set "HAS_ERRORS=1"
  if defined MISSING_ITEMS (
    set "MISSING_ITEMS=!MISSING_ITEMS!, %~1"
  ) else (
    set "MISSING_ITEMS=%~1"
  )
)
exit /b 0

:finish
echo.>> "%RESULT_FILE%"
echo Summary>> "%RESULT_FILE%"
echo Python found: !PYTHON_FOUND!>> "%RESULT_FILE%"
echo Python version: !PYTHON_VERSION!>> "%RESULT_FILE%"
echo requests found: !REQUESTS_FOUND!>> "%RESULT_FILE%"
echo bs4 found: !BS4_FOUND!>> "%RESULT_FILE%"
echo Project ready: !PROJECT_READY!>> "%RESULT_FILE%"
if defined MISSING_ITEMS echo Missing items: !MISSING_ITEMS!>> "%RESULT_FILE%"
echo Next step: !NEXT_STEP!>> "%RESULT_FILE%"

echo.
echo Check complete.
echo Result file: %RESULT_FILE%
echo.
pause
exit /b %HAS_ERRORS%