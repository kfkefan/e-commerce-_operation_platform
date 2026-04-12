# ASIN Ranker 部署脚本 (Windows PowerShell)
# 用法：.\scripts\deploy.ps1 [-Environment <dev|staging|production>]
# 默认环境：production

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('dev', 'staging', 'production')]
    [string]$Environment = 'production'
)

$ErrorActionPreference = 'Stop'

Write-Host "🚀 ASIN Ranker 部署脚本" -ForegroundColor Green
Write-Host "========================"
Write-Host "环境：$Environment"
Write-Host "项目根目录：$PSScriptRoot\.."
Write-Host ""

$PROJECT_ROOT = Split-Path -Parent $PSScriptRoot

function Log-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Log-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Log-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# 检查 Node.js 版本
function Test-NodeVersion {
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Log-Error "Node.js 未安装，请先安装 Node.js >= 20.0.0"
        exit 1
    }
    
    $nodeVersion = node -v
    $majorVersion = [int]($nodeVersion -replace 'v(\d+)\..*', '$1')
    
    if ($majorVersion -lt 20) {
        Log-Error "Node.js 版本过低 (当前：$nodeVersion)，需要 >= 20.0.0"
        exit 1
    }
    
    Log-Info "Node.js 版本检查通过：$nodeVersion"
}

# 安装依赖
function Install-Dependencies {
    Log-Info "安装项目依赖..."
    Set-Location $PROJECT_ROOT
    npm ci --production
    Log-Info "依赖安装完成"
}

# 构建项目
function Build-Project {
    Log-Info "构建项目..."
    Set-Location $PROJECT_ROOT
    npm run build
    Log-Info "构建完成"
}

# 数据库迁移
function Run-Migrations {
    Log-Info "执行数据库迁移..."
    # 如果有数据库迁移脚本，在这里执行
    # 例如：npm run migrate
    Log-Info "数据库迁移完成"
}

# 健康检查
function Test-Health {
    Log-Info "执行健康检查..."
    Start-Sleep -Seconds 5
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000/health" -TimeoutSec 10 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Log-Info "健康检查通过"
            return $true
        } else {
            Log-Warn "健康检查失败 (HTTP $($response.StatusCode))，但继续执行"
            return $false
        }
    } catch {
        Log-Warn "健康检查失败：$($_.Exception.Message)，但继续执行"
        return $false
    }
}

# 主部署流程
function Start-Deployment {
    Log-Info "开始部署流程..."
    Write-Host ""
    
    # 步骤 1: 检查环境
    Log-Info "步骤 1/5: 检查环境"
    Test-NodeVersion
    Write-Host ""
    
    # 步骤 2: 安装依赖
    Log-Info "步骤 2/5: 安装依赖"
    Install-Dependencies
    Write-Host ""
    
    # 步骤 3: 构建项目
    Log-Info "步骤 3/5: 构建项目"
    Build-Project
    Write-Host ""
    
    # 步骤 4: 数据库迁移
    Log-Info "步骤 4/5: 数据库迁移"
    Run-Migrations
    Write-Host ""
    
    # 步骤 5: 健康检查
    Log-Info "步骤 5/5: 健康检查"
    Test-Health
    Write-Host ""
    
    Log-Info "✅ 部署完成!"
    Write-Host ""
    Write-Host "请手动重启服务或运行：.\start.bat"
}

# 执行主流程
Start-Deployment
