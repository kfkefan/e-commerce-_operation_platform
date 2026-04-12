#!/bin/bash
set -e

# ASIN Ranker Backend 启动脚本
# 用法：./run.sh [mode]
# mode: dev, production (默认：dev)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODE="${1:-dev}"

echo "🚀 ASIN Ranker 后端服务"
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

# 检查 Python
check_python() {
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        log_error "Python 未安装，请先安装 Python >= 3.10"
        exit 1
    fi
    
    PYTHON_CMD=$(command -v python3 || command -v python)
    log_info "Python: $($PYTHON_CMD --version)"
}

# 设置虚拟环境
setup_venv() {
    if [ ! -d "venv" ]; then
        log_info "创建 Python 虚拟环境..."
        python3 -m venv venv || python -m venv venv
    fi
    
    log_info "激活虚拟环境..."
    source venv/bin/activate
}

# 安装依赖
install_deps() {
    log_info "检查依赖..."
    
    if [ ! -f "venv/bin/uvicorn" ]; then
        log_info "安装 Python 依赖..."
        pip install --upgrade pip
        pip install -r requirements.txt
    fi
}

# 安装 Playwright 浏览器
install_playwright() {
    log_info "检查 Playwright 浏览器..."
    
    if ! playwright install chromium 2>/dev/null; then
        log_info "安装 Playwright Chromium..."
        playwright install chromium
        playwright install-deps chromium
    fi
}

# 创建日志目录
setup_logs() {
    if [ ! -d "logs" ]; then
        mkdir -p logs
        log_info "创建日志目录：logs/"
    fi
}

# 启动开发模式
start_dev() {
    log_info "启动开发服务器 (热重载)..."
    log_info "API 文档：http://localhost:8000/docs"
    log_info "健康检查：http://localhost:8000/api/v1/health"
    echo ""
    
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
}

# 启动生产模式
start_production() {
    log_info "启动生产服务器..."
    log_info "API 文档：http://localhost:8000/docs"
    log_info "健康检查：http://localhost:8000/api/v1/health"
    echo ""
    
    # 生产环境使用多 worker
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
}

# 主流程
main() {
    # 检查环境
    check_python
    echo ""
    
    # 设置虚拟环境
    setup_venv
    echo ""
    
    # 安装依赖
    install_deps
    echo ""
    
    # 安装 Playwright
    install_playwright
    echo ""
    
    # 设置日志目录
    setup_logs
    echo ""
    
    # 启动服务
    case $MODE in
        dev|development)
            start_dev
            ;;
        production|prod)
            start_production
            ;;
        *)
            log_error "未知模式：$MODE"
            echo ""
            echo "可用模式:"
            echo "  dev       - 开发模式 (热重载)"
            echo "  production - 生产模式 (多 worker)"
            exit 1
            ;;
    esac
}

# 执行
main
