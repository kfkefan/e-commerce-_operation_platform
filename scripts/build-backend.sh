#!/bin/bash
set -e

# ASIN Ranker Backend 构建脚本
# 用法：./scripts/build-backend.sh [--clean] [--install]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

CLEAN=false
INSTALL=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=true
            shift
            ;;
        --install)
            INSTALL=true
            shift
            ;;
        -h|--help)
            echo "用法：$0 [选项]"
            echo ""
            echo "选项:"
            echo "  --clean     清理旧的构建文件和缓存"
            echo "  --install   安装 Python 依赖"
            echo "  -h, --help  显示帮助信息"
            exit 0
            ;;
        *)
            echo "未知选项：$1"
            exit 1
            ;;
    esac
done

echo "🔨 ASIN Ranker 后端构建脚本"
echo "==========================="
echo "后端目录：$BACKEND_DIR"
echo "清理模式：$CLEAN"
echo "安装依赖：$INSTALL"
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

# 检查 Python 版本
check_python() {
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        log_error "Python 未安装，请先安装 Python >= 3.10"
        exit 1
    fi
    
    PYTHON_CMD=$(command -v python3 || command -v python)
    PYTHON_VERSION=$("$PYTHON_CMD" --version 2>&1 | cut -d' ' -f2)
    log_info "Python 版本：$PYTHON_VERSION"
    
    # 检查版本 >= 3.10
    MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
    MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)
    
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
        log_error "Python 版本过低，需要 >= 3.10"
        exit 1
    fi
}

# 创建虚拟环境
setup_venv() {
    log_info "检查虚拟环境..."
    
    if [ ! -d "$BACKEND_DIR/venv" ]; then
        log_info "创建 Python 虚拟环境..."
        cd "$BACKEND_DIR"
        python3 -m venv venv || python -m venv venv
        log_info "虚拟环境创建完成"
    else
        log_info "虚拟环境已存在"
    fi
}

# 安装依赖
install_dependencies() {
    if [ "$INSTALL" = false ]; then
        log_warn "跳过依赖安装 (使用 --install 参数来安装)"
        return
    fi
    
    log_info "安装 Python 依赖..."
    cd "$BACKEND_DIR"
    
    # 激活虚拟环境
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # 升级 pip
    pip install --upgrade pip
    
    # 安装依赖
    pip install -r requirements.txt
    
    # 安装 Playwright 浏览器
    log_info "安装 Playwright 浏览器..."
    playwright install chromium
    
    log_info "依赖安装完成"
}

# 清理构建文件
clean_build() {
    log_info "清理构建文件和缓存..."
    cd "$BACKEND_DIR"
    
    # 清理 Python 缓存
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    
    # 清理 pytest 缓存
    rm -rf .pytest_cache 2>/dev/null || true
    rm -rf .coverage 2>/dev/null || true
    rm -rf htmlcov 2>/dev/null || true
    
    # 清理日志
    rm -rf logs/*.log 2>/dev/null || true
    
    log_info "清理完成"
}

# 运行测试
run_tests() {
    log_info "运行后端测试..."
    cd "$BACKEND_DIR"
    
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    pytest tests/ -v --tb=short
    
    log_info "测试完成"
}

# 验证构建
verify_build() {
    log_info "验证后端配置..."
    cd "$BACKEND_DIR"
    
    if [ -f "requirements.txt" ]; then
        log_info "requirements.txt: ✓"
    else
        log_error "requirements.txt 未找到"
        exit 1
    fi
    
    if [ -f "main.py" ]; then
        log_info "main.py: ✓"
    else
        log_error "main.py 未找到"
        exit 1
    fi
    
    log_info "验证通过"
}

# 主流程
main() {
    log_info "开始后端构建流程..."
    echo ""
    
    # 清理 (如果需要)
    if [ "$CLEAN" = true ]; then
        clean_build
        echo ""
    fi
    
    # 检查环境
    log_info "步骤 1/3: 检查 Python 环境"
    check_python
    echo ""
    
    # 设置虚拟环境
    log_info "步骤 2/3: 设置虚拟环境"
    setup_venv
    echo ""
    
    # 安装依赖 (如果需要)
    if [ "$INSTALL" = true ]; then
        log_info "步骤 3/3: 安装依赖"
        install_dependencies
        echo ""
    fi
    
    # 验证
    verify_build
    
    echo ""
    log_info "✅ 后端构建准备完成!"
    echo ""
    echo "启动后端服务:"
    echo "  cd backend"
    echo "  source venv/bin/activate  # Linux/Mac"
    echo "  uvicorn main:app --reload"
}

# 执行
main
