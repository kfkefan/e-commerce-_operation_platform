@echo off
REM ASIN Ranker 快速启动脚本 (Windows)
REM 用法：start.bat [mode]
REM mode: dev, build, production (默认：dev)

setlocal enabledelayedexpansion

cd /d "%~dp0"

set MODE=%1
if "%MODE%"=="" set MODE=dev

echo.
echo 🚀 ASIN Ranker 启动脚本
echo ======================
echo 模式：%MODE%
echo.

if "%MODE%"=="dev" (
    echo 启动开发模式...
    call npm run dev
    goto :end
)

if "%MODE%"=="build" (
    echo 构建项目...
    call npm run build
    goto :end
)

if "%MODE%"=="production" (
    goto :production
)

if "%MODE%"=="start" (
    goto :production
)

if "%MODE%"=="docker" (
    goto :docker
)

if "%MODE%"=="stop" (
    goto :stop
)

if "%MODE%"=="logs" (
    goto :logs
)

echo 未知模式：%MODE%
echo.
echo 可用模式:
echo   dev       - 开发模式 ^(默认^)
echo   build     - 构建项目
echo   production - 生产模式
echo   docker    - Docker 启动
echo   stop      - 停止服务
echo   logs      - 查看日志
exit /b 1

:production
echo 启动生产模式...
REM 检查是否已构建
if not exist "dist" (
    echo 未找到构建文件，先执行构建...
    call npm run build
)
call npm start
goto :end

:docker
echo 使用 Docker 启动...
docker compose --version >nul 2>&1
if errorlevel 1 (
    echo 错误：Docker 未安装
    exit /b 1
)
call docker compose up -d
echo.
echo 服务已启动：
echo   - 前端：http://localhost
echo   - API: http://localhost:3000
echo.
echo 查看日志：docker compose logs -f
echo 停止服务：docker compose down
goto :end

:stop
echo 停止服务...
docker compose --version >nul 2>&1
if not errorlevel 1 (
    if exist "docker-compose.yml" (
        call docker compose down
        goto :end
    )
)
REM 尝试杀死 Node 进程
taskkill /F /IM node.exe >nul 2>&1 || echo 未找到运行的 Node 进程
echo 服务已停止
goto :end

:logs
echo 查看日志...
docker compose --version >nul 2>&1
if not errorlevel 1 (
    if exist "docker-compose.yml" (
        call docker compose logs -f
        goto :end
    )
)
echo Docker 未使用，请手动查看日志文件
goto :end

:end
echo.
endlocal
