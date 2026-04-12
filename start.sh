#!/bin/bash
set -e

# ASIN Ranker 快速启动脚本 (Linux/Mac)
# 用法：./start.sh [mode]
# mode: dev, build, production (默认：dev)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:-dev}"

echo "🚀 ASIN Ranker 启动脚本"
echo "======================"
echo "模式：$MODE"
echo ""

case $MODE in
    dev)
        echo "启动开发模式..."
        npm run dev
        ;;
    build)
        echo "构建项目..."
        npm run build
        ;;
    production|start)
        echo "启动生产模式..."
        # 检查是否已构建
        if [ ! -d "dist" ]; then
            echo "未找到构建文件，先执行构建..."
            npm run build
        fi
        npm start
        ;;
    docker)
        echo "使用 Docker 启动..."
        if ! command -v docker &> /dev/null; then
            echo "错误：Docker 未安装"
            exit 1
        fi
        docker compose up -d
        echo "服务已启动："
        echo "  - 前端：http://localhost"
        echo "  - API: http://localhost:3000"
        echo ""
        echo "查看日志：docker compose logs -f"
        echo "停止服务：docker compose down"
        ;;
    stop)
        echo "停止服务..."
        if command -v docker &> /dev/null && [ -f "docker-compose.yml" ]; then
            docker compose down
        else
            # 尝试杀死 Node 进程
            pkill -f "node.*dist/server" || true
        fi
        echo "服务已停止"
        ;;
    logs)
        echo "查看日志..."
        if command -v docker &> /dev/null && [ -f "docker-compose.yml" ]; then
            docker compose logs -f
        else
            echo "Docker 未使用，请手动查看日志文件"
        fi
        ;;
    *)
        echo "未知模式：$MODE"
        echo ""
        echo "可用模式:"
        echo "  dev       - 开发模式 (默认)"
        echo "  build     - 构建项目"
        echo "  production - 生产模式"
        echo "  docker    - Docker 启动"
        echo "  stop      - 停止服务"
        echo "  logs      - 查看日志"
        exit 1
        ;;
esac
