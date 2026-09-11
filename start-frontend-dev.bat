@echo off
REM 前端开发模式启动脚本

echo ========================================
echo 启动前端开发服务器
echo ========================================
echo.
echo 前端将运行在: http://localhost:5173
echo API 代理到: http://localhost:8000
echo.
echo 请确保后端已在另一个终端启动:
echo   .venv\Scripts\python.exe start.py
echo.
echo ========================================

cd /d "%~dp0frontend"
npm run dev
