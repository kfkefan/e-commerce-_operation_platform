#!/bin/bash
set -e

# ASIN Ranker 构建脚本
# 用法：./scripts/build.sh [--clean] [--skip-frontend]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

CLEAN=false
SKIP_FRONTEND=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=true
            shift
            ;;
        --skip-frontend)
            SKIP_FRONTEND=true
            shift
            ;;
        -h|--help)
            echo "用法：$0 [选项]"
            echo ""
            echo "选项:"
            echo "  --clean          清理旧的构建文件"
            echo "  --skip-frontend  跳过前端构建"
            echo "  -h, --help       显示帮助信息"
            exit 0
            ;;
        *)
            echo "未知选项：$1"
            exit 1
            ;;
    esac
done

echo "🔨 ASIN Ranker 构建脚本"
echo "======================"
echo "项目根目录：$PROJECT_ROOT"
echo "清理模式：$CLEAN"
echo "跳过前端：$SKIP_FRONTEND"
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

# 清理构建文件
clean_build() {
    log_info "清理旧的构建文件..."
    cd "$PROJECT_ROOT"
    rm -rf dist
    rm -rf backend/dist
    rm -rf frontend/dist
    rm -rf frontend/build
    log_info "清理完成"
}

# 检查 Node.js
check_node() {
    if ! command -v node &> /dev/null; then
        log_error "Node.js 未安装"
        exit 1
    fi
    log_info "Node.js: $(node -v)"
}

# 安装依赖
install_deps() {
    log_info "安装依赖..."
    cd "$PROJECT_ROOT"
    
    # 根目录依赖
    if [ -f "package.json" ]; then
        npm ci
    fi
    
    # 后端依赖
    if [ -d "backend" ] && [ -f "backend/package.json" ]; then
        cd backend
        npm ci
        cd ..
    fi
    
    # 前端依赖
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        cd frontend
        npm ci
        cd ..
    fi
    
    log_info "依赖安装完成"
}

# 构建后端
build_backend() {
    log_info "构建后端..."
    cd "$PROJECT_ROOT"
    
    # 检查是否有 backend 目录
    if [ -d "backend" ] && [ -f "backend/package.json" ]; then
        cd backend
        npm run build
        cd ..
    else
        # 直接在根目录构建
        npm run build:server
    fi
    
    log_info "后端构建完成"
}

# 构建前端
build_frontend() {
    if [ "$SKIP_FRONTEND" = true ]; then
        log_warn "跳过前端构建"
        return
    fi
    
    log_info "构建前端..."
    cd "$PROJECT_ROOT"
    
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        cd frontend
        npm run build
        cd ..
        log_info "前端构建完成"
    else
        log_warn "frontend 目录不存在，跳过前端构建"
    fi
}

# 验证构建
verify_build() {
    log_info "验证构建结果..."
    
    # 检查后端构建输出
    if [ -d "backend/dist" ] || [ -d "dist/server" ]; then
        log_info "后端构建输出：✓"
    else
        log_error "后端构建输出未找到"
        exit 1
    fi
    
    # 检查前端构建输出 (如果未跳过)
    if [ "$SKIP_FRONTEND" = false ]; then
        if [ -d "frontend/dist" ] || [ -d "frontend/build" ]; then
            log_info "前端构建输出：✓"
        else
            log_warn "前端构建输出未找到"
        fi
    fi
    
    log_info "构建验证通过"
}

# 主流程
main() {
    log_info "开始构建流程..."
    echo ""
    
    # 清理 (如果需要)
    if [ "$CLEAN" = true ]; then
        clean_build
        echo ""
    fi
    
    # 检查环境
    log_info "步骤 1/4: 检查环境"
    check_node
    echo ""
    
    # 安装依赖
    log_info "步骤 2/4: 安装依赖"
    install_deps
    echo ""
    
    # 构建后端
    log_info "步骤 3/4: 构建后端"
    build_backend
    echo ""
    
    # 构建前端
    log_info "步骤 4/4: 构建前端"
    build_frontend
    echo ""
    
    # 验证
    verify_build
    
    echo ""
    log_info "✅ 构建成功完成!"
}

# 执行
main
