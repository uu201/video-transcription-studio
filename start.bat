@echo off
REM 一键启动脚本 - 生产模式

echo ========================================
echo 启动视频转文案工作台
echo ========================================
echo.

REM 检查前端是否已构建
if not exist "app\static\dist\index.html" (
    echo [警告] 前端未构建，正在构建...
    echo.
    call build-frontend.bat
    echo.
)

echo [启动] 启动后端服务...
echo.
set "PROJECT_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PROJECT_PYTHON%" (
    echo [错误] 未找到项目虚拟环境：%PROJECT_PYTHON%
    echo 请先执行：py -3.11 -m venv .venv
    echo 再执行：%~dp0.venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)
"%PROJECT_PYTHON%" "%~dp0start.py"
