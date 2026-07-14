@echo off
setlocal EnableExtensions
set "ROOT=%~dp0.."
cd /d "%ROOT%\backend" || goto :failed
"%ROOT%\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8002
if errorlevel 1 goto :failed
exit /b 0

:failed
echo.
echo [ERROR] Windup 2D API stopped unexpectedly.
pause
exit /b 1
