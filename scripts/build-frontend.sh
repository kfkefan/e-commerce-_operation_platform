#!/bin/bash
set -e

# ASIN Ranker Frontend 构建脚本
# 用法：./scripts/build-frontend.sh [--clean] [--preview]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

CLEAN=false
PREVIEW=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=true
            shift
            ;;
        --preview)
            PREVIEW=true
            shift
            ;;
        -h|--help)
            echo "用法：$0 [选项]"
            echo ""
            echo "选项:"
            echo "  --clean     清理旧的构建文件"
            echo "  --preview   构建后启动预览服务器"
            echo "  -h, --help  显示帮助信息"
            exit 0
            ;;
        *)
            echo "未知选项：$1"
            exit 1
            ;;
    esac
done

echo "🔨 ASIN Ranker 前端构建脚本"
echo "==========================="
echo "前端目录：$FRONTEND_DIR"
echo "清理模式：$CLEAN"
echo "预览模式：$PREVIEW"
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

# 检查 Node.js 版本
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
    
    log_info "Node.js 版本：$NODE_VERSION"
}

# 检查 npm
check_npm() {
    if ! command -v npm &> /dev/null; then
        log_error "npm 未安装"
        exit 1
    fi
    log_info "npm 版本：$(npm -v)"
}

# 清理构建文件
clean_build() {
    log_info "清理旧的构建文件..."
    cd "$FRONTEND_DIR"
    
    rm -rf dist 2>/dev/null || true
    rm -rf build 2>/dev/null || true
    rm -rf node_modules/.vite 2>/dev/null || true
    
    log_info "清理完成"
}

# 安装依赖
install_dependencies() {
    log_info "检查 node_modules..."
    cd "$FRONTEND_DIR"
    
    if [ ! -d "node_modules" ]; then
        log_info "安装前端依赖..."
        npm install
    else
        log_info "依赖已存在，检查是否需要更新..."
        npm install
    fi
    
    log_info "依赖安装完成"
}

# 构建前端
build_frontend() {
    log_info "构建前端项目..."
    cd "$FRONTEND_DIR"
    
    npm run build
    
    log_info "构建完成"
}

# 预览构建结果
preview_build() {
    if [ "$PREVIEW" = false ]; then
        return
    fi
    
    log_info "启动预览服务器..."
    cd "$FRONTEND_DIR"
    
    npm run preview
    
    log_info "预览服务器已启动"
}

# 验证构建
verify_build() {
    log_info "验证构建结果..."
    cd "$FRONTEND_DIR"
    
    if [ -d "dist" ]; then
        DIST_SIZE=$(du -sh dist 2>/dev/null | cut -f1)
        log_info "构建输出目录：dist/ ($DIST_SIZE)"
        
        if [ -f "dist/index.html" ]; then
            log_info "index.html: ✓"
        else
            log_error "dist/index.html 未找到"
            exit 1
        fi
    else
        log_error "dist 目录未找到，构建可能失败"
        exit 1
    fi
    
    log_info "构建验证通过"
}

# 主流程
main() {
    log_info "开始前端构建流程..."
    echo ""
    
    # 清理 (如果需要)
    if [ "$CLEAN" = true ]; then
        clean_build
        echo ""
    fi
    
    # 检查环境
    log_info "步骤 1/3: 检查 Node.js 环境"
    check_node
    check_npm
    echo ""
    
    # 安装依赖
    log_info "步骤 2/3: 安装依赖"
    install_dependencies
    echo ""
    
    # 构建
    log_info "步骤 3/3: 构建前端"
    build_frontend
    echo ""
    
    # 验证
    verify_build
    echo ""
    
    # 预览 (如果需要)
    if [ "$PREVIEW" = true ]; then
        preview_build
    fi
    
    log_info "✅ 前端构建成功完成!"
    echo ""
    echo "构建输出：frontend/dist/"
    echo ""
    echo "部署方式:"
    echo "  - Docker: docker compose up -d"
    echo "  - Nginx: 将 dist/ 内容复制到 Nginx 根目录"
    echo "  - 预览：运行此脚本时添加 --preview 参数"
}

# 执行
main
