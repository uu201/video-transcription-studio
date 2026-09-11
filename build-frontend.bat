@echo off
REM 前端构建脚本

echo ========================================
echo 构建前端生产版本
echo ========================================
echo.

cd /d "%~dp0frontend"

echo [1/3] 安装依赖...
call npm install

echo.
echo [2/3] 构建前端...
call npm run build

echo.
echo [3/3] 构建完成！
echo.
echo 构建产物已输出到: app\static\dist
echo.
echo 现在可以运行: start.bat
echo 访问: http://localhost:8000
echo.
echo ========================================

pause
