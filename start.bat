@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title Windup 2D Studio Launcher
cd /d "%~dp0"

echo.
echo  W I N D U P   2 D   S T U D I O
echo  高清人物与动作资产工作台
echo  =============================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] 未找到 Python。请安装 Python 3.11 或更高版本。
  pause
  exit /b 1
)
where node >nul 2>&1
if errorlevel 1 (
  echo [ERROR] 未找到 Node.js。请安装 Node.js 22 LTS。
  pause
  exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
  echo [ERROR] 未找到 npm，请重新安装 Node.js。
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] 创建 Python 虚拟环境...
  python -m venv .venv
  if errorlevel 1 goto :failed
)

echo [2/5] 同步后端依赖...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -q -r backend\requirements.txt
if errorlevel 1 goto :failed

echo [3/5] 同步前端依赖...
pushd frontend
if exist package-lock.json (
  call npm ci --silent
) else (
  call npm install --silent
)
if errorlevel 1 (
  popd
  goto :failed
)
popd

echo [4/5] 启动 FastAPI 与 React...
start "Windup 2D API" cmd /k "cd /d ""%~dp0backend"" && ""%~dp0.venv\Scripts\python.exe"" -m uvicorn app.main:app --host 127.0.0.1 --port 8002"
start "Windup 2D UI" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo [5/5] 等待服务就绪...
set /a retries=0
:wait_api
powershell -NoProfile -Command "try { $r=Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:8002/api/v1/health; if($r.StatusCode -eq 200){exit 0}else{exit 1} } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
  set /a retries+=1
  if !retries! geq 45 (
    echo [ERROR] 后端在 45 秒内未就绪，请查看 Windup 2D API 窗口。
    pause
    exit /b 1
  )
  ping -n 2 127.0.0.1 >nul
  goto :wait_api
)

echo.
echo  =============================================
echo  工作台已启动: http://127.0.0.1:5175
echo  API 文档:     http://127.0.0.1:8002/docs
echo  =============================================
echo.
start "" http://127.0.0.1:5175
timeout /t 3 >nul
exit /b 0

:failed
echo.
echo [ERROR] 依赖安装失败，请检查上方错误信息与网络连接。
pause
exit /b 1
