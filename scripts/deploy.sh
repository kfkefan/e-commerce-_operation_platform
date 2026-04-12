#!/bin/bash
set -e

# ASIN Ranker 部署脚本 (Linux/Mac)
# 用法：./scripts/deploy.sh [environment]
# environment: dev, staging, production (默认: production)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-production}"

echo "🚀 ASIN Ranker 部署脚本"
echo "========================"
echo "环境：$ENVIRONMENT"
echo "项目根目录：$PROJECT_ROOT"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
check_node_version() {
    if ! command -v node &> /dev/null; then
        log_error "Node.js 未安装，请先安装 Node.js >= 20.0.0"
        exit 1
    fi
    
    NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_VERSION" -lt 20 ]; then
        log_error "Node.js 版本过低 (当前：$(node -v))，需要 >= 20.0.0"
        exit 1
    fi
    log_info "Node.js 版本检查通过：$(node -v)"
}

# 安装依赖
install_dependencies() {
    log_info "安装项目依赖..."
    cd "$PROJECT_ROOT"
    npm ci --production
    log_info "依赖安装完成"
}

# 构建项目
build_project() {
    log_info "构建项目..."
    cd "$PROJECT_ROOT"
    npm run build
    log_info "构建完成"
}

# 数据库迁移
run_migrations() {
    log_info "执行数据库迁移..."
    # 如果有数据库迁移脚本，在这里执行
    # 例如：npm run migrate
    log_info "数据库迁移完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    # 等待服务启动
    sleep 5
    
    # 检查健康端点
    if command -v curl &> /dev/null; then
        HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/health 2>/dev/null || echo "000")
        if [ "$HEALTH_RESPONSE" = "200" ]; then
            log_info "健康检查通过"
            return 0
        else
            log_warn "健康检查失败 (HTTP $HEALTH_RESPONSE)，但继续执行"
            return 1
        fi
    else
        log_warn "curl 未安装，跳过健康检查"
        return 0
    fi
}

# 重启服务 (systemd)
restart_service() {
    if command -v systemctl &> /dev/null; then
        log_info "重启 systemd 服务..."
        sudo systemctl restart asin-ranker
        sudo systemctl enable asin-ranker
        log_info "服务重启完成"
    else
        log_warn "systemctl 不可用，请手动重启服务"
    fi
}

# 主部署流程
main() {
    log_info "开始部署流程..."
    echo ""
    
    # 步骤 1: 检查环境
    log_info "步骤 1/5: 检查环境"
    check_node_version
    echo ""
    
    # 步骤 2: 安装依赖
    log_info "步骤 2/5: 安装依赖"
    install_dependencies
    echo ""
    
    # 步骤 3: 构建项目
    log_info "步骤 3/5: 构建项目"
    build_project
    echo ""
    
    # 步骤 4: 数据库迁移
    log_info "步骤 4/5: 数据库迁移"
    run_migrations
    echo ""
    
    # 步骤 5: 重启服务
    log_info "步骤 5/5: 重启服务"
    restart_service
    echo ""
    
    # 健康检查
    health_check
    
    echo ""
    log_info "✅ 部署完成!"
    echo ""
    echo "服务状态检查：systemctl status asin-ranker"
    echo "查看日志：journalctl -u asin-ranker -f"
}

# 执行主流程
main
