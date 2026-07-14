@echo off
setlocal EnableExtensions
set "ROOT=%~dp0.."
cd /d "%ROOT%\frontend" || goto :failed
call npm.cmd run dev
if errorlevel 1 goto :failed
exit /b 0

:failed
echo.
echo [ERROR] Windup 2D UI stopped unexpectedly.
pause
exit /b 1
