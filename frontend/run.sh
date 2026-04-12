#!/bin/bash
set -e

# ASIN Ranker Frontend 启动脚本
# 用法：./run.sh [mode]
# mode: dev, build, preview (默认：dev)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:-dev}"

echo "🚀 ASIN Ranker 前端服务"
echo "======================"
echo "模式：$MODE"
echo "目录：$SCRIPT_DIR"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Node.js
check_node() {
    if ! command -v node &> /dev/null; then
        log_error "Node.js 未安装，请先安装 Node.js >= 18.0.0"
        exit 1
    fi
    
    NODE_VERSION=$(node -v)
    NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d'v' -f1 | cut -d'.' -f1)
    
    if [ "$NODE_MAJOR" -lt 18 ]; then
        log_error "Node.js 版本过低 (当前：$NODE_VERSION)，需要 >= 18.0.0"
        exit 1
    fi
    
    log_info "Node.js: $NODE_VERSION"
    log_info "npm: $(npm -v)"
}

# 安装依赖
install_deps() {
    log_info "检查依赖..."
    
    if [ ! -d "node_modules" ]; then
        log_info "安装前端依赖..."
        npm install
    else
        log_info "依赖已存在"
    fi
}

# 启动开发模式
start_dev() {
    log_info "启动开发服务器..."
    log_info "访问地址：http://localhost:5173"
    log_info "API 地址：http://localhost:8000/api/v1"
    echo ""
    
    npm run dev
}

# 构建生产版本
start_build() {
    log_info "构建生产版本..."
    
    npm run build
    
    log_info "构建完成!"
    log_info "输出目录：dist/"
    
    if [ -d "dist" ]; then
        DIST_SIZE=$(du -sh dist 2>/dev/null | cut -f1)
        log_info "构建大小：$DIST_SIZE"
    fi
}

# 预览生产版本
start_preview() {
    log_info "预览生产版本..."
    
    if [ ! -d "dist" ]; then
        log_warn "未找到 dist 目录，先执行构建..."
        start_build
    fi
    
    log_info "启动预览服务器..."
    log_info "访问地址：http://localhost:4173"
    echo ""
    
    npm run preview
}

# 主流程
main() {
    # 检查环境
    check_node
    echo ""
    
    # 安装依赖
    install_deps
    echo ""
    
    # 启动服务
    case $MODE in
        dev|development)
            start_dev
            ;;
        build)
            start_build
            ;;
        preview)
            start_preview
            ;;
        *)
            log_error "未知模式：$MODE"
            echo ""
            echo "可用模式:"
            echo "  dev     - 开发模式 (Vite 热重载)"
            echo "  build   - 构建生产版本"
            echo "  preview - 预览生产版本"
            exit 1
            ;;
    esac
}

# 执行
main
