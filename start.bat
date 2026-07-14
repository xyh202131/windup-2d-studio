@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Windup 2D Studio Launcher

set "ROOT=%~dp0"
set "NO_BROWSER=0"
if /I "%~1"=="--no-browser" set "NO_BROWSER=1"

cd /d "%ROOT%" || goto :path_failed

echo.
echo  W I N D U P   2 D   S T U D I O
echo  HD character and action asset workspace
echo  ==================================================
echo.

set "SYSTEM_PYTHON="
for /f "delims=" %%I in ('where python.exe 2^>nul') do if not defined SYSTEM_PYTHON set "SYSTEM_PYTHON=%%I"
if not defined SYSTEM_PYTHON (
  echo [ERROR] Python was not found in PATH.
  echo         Install Python 3.11 or newer and try again.
  goto :failed
)

"%SYSTEM_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python 3.11 or newer is required.
  goto :failed
)

where node.exe >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Node.js was not found in PATH.
  echo         Install Node.js 22 LTS and try again.
  goto :failed
)

node.exe -e "process.exit(parseInt(process.versions.node, 10) < 22 ? 1 : 0)" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Node.js 22 LTS or newer is required.
  goto :failed
)

set "NPM_CMD="
for /f "delims=" %%I in ('where npm.cmd 2^>nul') do if not defined NPM_CMD set "NPM_CMD=%%I"
if not defined NPM_CMD (
  echo [ERROR] npm.cmd was not found in PATH.
  goto :failed
)

set "PYTHON=%ROOT%.venv\Scripts\python.exe"
set "HEALTH_PYTHON=%SYSTEM_PYTHON%"
if exist "%PYTHON%" set "HEALTH_PYTHON=%PYTHON%"

call :check_api
if not errorlevel 1 (
  set "API_RUNNING=1"
) else (
  set "API_RUNNING=0"
)

call :check_ui
if not errorlevel 1 (
  set "UI_RUNNING=1"
) else (
  set "UI_RUNNING=0"
)

if "%API_RUNNING%"=="0" (
  if not exist "%PYTHON%" (
    echo [1/5] Creating Python virtual environment...
    "%SYSTEM_PYTHON%" -m venv "%ROOT%.venv"
    if errorlevel 1 goto :dependency_failed
  ) else (
    echo [1/5] Python virtual environment is ready.
  )
  set "HEALTH_PYTHON=%PYTHON%"
  echo [2/5] Synchronizing backend dependencies...
  "%PYTHON%" -m pip install --disable-pip-version-check --quiet -r "%ROOT%backend\requirements.txt"
  if errorlevel 1 goto :dependency_failed
) else (
  echo [1/5] Backend is already running on port 8002.
  echo [2/5] Backend dependency sync is not needed.
)

if "%UI_RUNNING%"=="0" (
  echo [3/5] Synchronizing frontend dependencies...
  pushd "%ROOT%frontend" || goto :path_failed
  call "%NPM_CMD%" install --silent
  set "NPM_EXIT=!errorlevel!"
  popd
  if not "!NPM_EXIT!"=="0" goto :dependency_failed
) else (
  echo [3/5] Frontend is already running on port 5175.
)

if "%API_RUNNING%"=="0" (
  call :port_open 8002
  if not errorlevel 1 (
    echo [ERROR] Port 8002 is occupied by another application.
    goto :failed
  )
  echo [4/5] Starting FastAPI backend...
  start "Windup 2D API" /D "%ROOT%backend" "%ROOT%tools\run-api.bat"
) else (
  echo [4/5] Reusing the running FastAPI backend.
)

if "%UI_RUNNING%"=="0" (
  call :port_open 5175
  if not errorlevel 1 (
    echo [ERROR] Port 5175 is occupied by another application.
    goto :failed
  )
  echo       Starting React frontend...
  start "Windup 2D UI" /D "%ROOT%frontend" "%ROOT%tools\run-ui.bat"
) else (
  echo       Reusing the running React frontend.
)

echo [5/5] Waiting for both services...
set /a RETRIES=0

:wait_services
call :check_api
set "API_STATUS=!errorlevel!"
call :check_ui
set "UI_STATUS=!errorlevel!"
if "!API_STATUS!"=="0" if "!UI_STATUS!"=="0" goto :ready

set /a RETRIES+=1
if !RETRIES! geq 60 goto :start_failed
ping 127.0.0.1 -n 2 >nul
goto :wait_services

:ready
echo.
echo  ==================================================
echo  Studio:   http://127.0.0.1:5175
echo  API docs: http://127.0.0.1:8002/docs
echo  ==================================================
echo.
if "%NO_BROWSER%"=="0" start "" "http://127.0.0.1:5175"
exit /b 0

:check_api
"%HEALTH_PYTHON%" -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8002/api/v1/health', timeout=2); raise SystemExit(0 if r.status == 200 else 1)" >nul 2>&1
exit /b %errorlevel%

:check_ui
"%HEALTH_PYTHON%" -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:5175/', timeout=2); raise SystemExit(0 if r.status == 200 else 1)" >nul 2>&1
exit /b %errorlevel%

:port_open
netstat -ano -p TCP | findstr /C:":%~1" | findstr /C:"LISTENING" >nul 2>&1
exit /b %errorlevel%

:dependency_failed
echo.
echo [ERROR] Dependency installation failed.
echo         Check the messages above and your network connection.
goto :failed

:start_failed
echo.
echo [ERROR] The services did not become ready within 60 seconds.
echo         Check the Windup 2D API and Windup 2D UI windows.
goto :failed

:path_failed
echo.
echo [ERROR] The project directory could not be opened:
echo         %ROOT%

:failed
if not defined WINDUP_NO_PAUSE pause
exit /b 1
