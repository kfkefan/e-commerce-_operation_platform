# ASIN Ranker 部署指南

本文档提供 ASIN Ranker 项目的完整部署说明，包括本地开发环境、Docker 容器化部署和生产环境部署。

## 目录

- [环境要求](#环境要求)
- [本地开发部署](#本地开发部署)
- [Docker 部署](#docker-部署)
- [生产环境部署](#生产环境部署)
- [环境变量配置](#环境变量配置)
- [常见问题排查](#常见问题排查)

---

## 环境要求

### 最低配置

- **Python**: >= 3.10.0
- **Node.js**: >= 18.0.0
- **MySQL**: >= 8.0.0
- **内存**: 4GB RAM
- **磁盘**: 5GB 可用空间

### 推荐配置

- **Python**: 3.10.x 或 3.11.x
- **Node.js**: 20.x LTS
- **npm**: 10.x
- **MySQL**: 8.0.x
- **内存**: 8GB RAM
- **磁盘**: 10GB 可用空间
- **操作系统**: Linux (Ubuntu 20.04+), macOS, Windows 10+

### Docker 环境 (可选)

- **Docker**: >= 24.0.0
- **Docker Compose**: >= 2.20.0

---

## 本地开发部署

### 1. 克隆项目

```bash
git clone https://github.com/your-org/asin-ranker.git
cd asin-ranker
```

### 2. 配置环境变量

#### 后端环境变量

```bash
cd backend
cp .env.example .env
```

编辑 `backend/.env` 文件，配置数据库连接等参数。

#### 前端环境变量

```bash
cd frontend
cp .env.example .env
```

编辑 `frontend/.env` 文件，配置 API 地址。

#### Docker 环境变量

```bash
cd ..
cp .env.example .env
```

编辑 `.env` 文件，配置 Docker 服务参数。

### 3. 安装后端依赖

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# Linux/Mac:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

### 4. 安装前端依赖

```bash
cd frontend
npm install
```

### 5. 启动 MySQL 数据库

```bash
# 使用 Docker 启动 MySQL
docker run -d \
  --name asin-ranker-mysql \
  -e MYSQL_ROOT_PASSWORD=rootpassword \
  -e MYSQL_DATABASE=asin_ranker \
  -e MYSQL_USER=asinranker \
  -e MYSQL_PASSWORD=asinranker123 \
  -p 3306:3306 \
  mysql:8.0
```

或使用本地安装的 MySQL 服务。

### 6. 启动服务

#### 方式一：使用启动脚本

```bash
# 终端 1 - 启动后端
cd backend
./run.sh dev

# 终端 2 - 启动前端
cd frontend
./run.sh dev
```

#### 方式二：手动启动

```bash
# 终端 1 - 启动后端
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 终端 2 - 启动前端
cd frontend
npm run dev
```

### 7. 访问应用

- 前端：http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/v1/health

---

## Docker 部署

### 1. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，根据需要修改密码和端口。

### 2. 构建并启动服务

```bash
# 构建所有镜像
docker compose build

# 启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f

# 查看服务状态
docker compose ps
```

### 3. 验证服务

```bash
# 检查后端健康
curl http://localhost:8000/api/v1/health

# 检查前端
curl http://localhost/
```

### 4. 停止服务

```bash
# 停止所有服务
docker compose down

# 停止并删除数据卷 (谨慎使用，会删除数据库数据)
docker compose down -v
```

### 5. 服务端口

| 服务 | 容器端口 | 主机端口 | 说明 |
|------|----------|----------|------|
| MySQL | 3306 | 3306 | 数据库 |
| Backend | 8000 | 8000 | FastAPI 后端 |
| Frontend | 80 | 80 | Nginx 前端 |

---

## 生产环境部署

### 方式一：Docker Compose 生产部署 (推荐)

1. 创建生产环境配置：

```bash
cp .env.example .env.prod
```

2. 编辑 `.env.prod`，设置生产环境变量：

```bash
# 强密码
MYSQL_ROOT_PASSWORD=your_secure_root_password
MYSQL_PASSWORD=your_secure_password

# 生产环境标志
DEBUG=false
LOG_LEVEL=WARNING

# 域名配置
VITE_API_BASE_URL=https://api.yourdomain.com
```

3. 启动服务：

```bash
docker compose --env-file .env.prod up -d
```

4. 配置 Nginx 反向代理和 SSL：

```nginx
# /etc/nginx/sites-available/asin-ranker
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 方式二：Systemd 服务部署

1. 安装系统依赖：

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3.10 python3.10-venv nodejs npm mysql-server nginx

# CentOS/RHEL
sudo yum install -y python3 nodejs mysql-server nginx
```

2. 配置 MySQL：

```bash
sudo mysql_secure_installation

sudo mysql -u root -p <<EOF
CREATE DATABASE asin_ranker;
CREATE USER 'asinranker'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON asin_ranker.* TO 'asinranker'@'localhost';
FLUSH PRIVILEGES;
EOF
```

3. 部署后端服务：

```bash
sudo mkdir -p /opt/asin-ranker
sudo chown $USER:$USER /opt/asin-ranker
cd /opt/asin-ranker

# 复制代码
git clone https://github.com/your-org/asin-ranker.git .

# 设置后端
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# 编辑 .env 配置数据库连接
```

4. 创建 systemd 服务文件：

```bash
sudo nano /etc/systemd/system/asin-ranker-backend.service
```

添加以下内容：

```ini
[Unit]
Description=ASIN Ranker Backend Service
After=network.target mysql.service

[Service]
Type=simple
User=deploy
Group=deploy
WorkingDirectory=/opt/asin-ranker/backend
Environment="PATH=/opt/asin-ranker/backend/venv/bin"
ExecStart=/opt/asin-ranker/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

5. 部署前端服务：

```bash
cd /opt/asin-ranker/frontend
npm install
npm run build
```

6. 配置 Nginx：

```bash
sudo nano /etc/nginx/sites-available/asin-ranker
```

添加以下内容：

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        root /opt/asin-ranker/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

7. 启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable asin-ranker-backend
sudo systemctl start asin-ranker-backend
sudo systemctl status asin-ranker-backend

sudo systemctl enable nginx
sudo systemctl restart nginx
```

---

## 环境变量配置

### Docker 环境变量 (.env)

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `MYSQL_ROOT_PASSWORD` | 是 | - | MySQL root 密码 |
| `MYSQL_USER` | 是 | asinranker | MySQL 用户名 |
| `MYSQL_PASSWORD` | 是 | asinranker123 | MySQL 密码 |
| `MYSQL_PORT` | 是 | 3306 | MySQL 端口 |
| `BACKEND_PORT` | 是 | 8000 | 后端服务端口 |
| `FRONTEND_PORT` | 是 | 80 | 前端服务端口 |
| `DEBUG` | 否 | false | 调试模式 |
| `LOG_LEVEL` | 否 | INFO | 日志级别 |
| `MAX_CONCURRENT_BROWSERS` | 否 | 3 | 最大并发浏览器数 |
| `MAX_CONCURRENT_TASKS` | 否 | 5 | 最大并发任务数 |
| `VITE_API_BASE_URL` | 是 | http://localhost:8000/api/v1 | API 地址 |

### 后端环境变量 (backend/.env)

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `DB_HOST` | 是 | localhost | 数据库主机 |
| `DB_PORT` | 是 | 3306 | 数据库端口 |
| `DB_USER` | 是 | root | 数据库用户名 |
| `DB_PASSWORD` | 是 | - | 数据库密码 |
| `DB_NAME` | 是 | asin_ranker | 数据库名 |
| `DEBUG` | 否 | false | 调试模式 |
| `LOG_LEVEL` | 否 | INFO | 日志级别 |
| `MAX_CONCURRENT_BROWSERS` | 否 | 3 | 最大并发浏览器数 |
| `MAX_CONCURRENT_TASKS` | 否 | 5 | 最大并发任务数 |
| `PROXY_POOL_ENABLED` | 否 | false | 代理池开关 |
| `UA_ROTATION_ENABLED` | 否 | true | User-Agent 轮换开关 |

### 前端环境变量 (frontend/.env)

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `VITE_API_BASE_URL` | 是 | http://localhost:8000/api/v1 | API 地址 |

---

## 常见问题排查

### 1. Python 版本错误

**问题**: `Error: Python 3.10 or higher is required`

**解决**:
```bash
# 检查当前版本
python3 --version

# 使用 pyenv 安装正确版本
pyenv install 3.10.13
pyenv global 3.10.13
```

### 2. Node.js 版本错误

**问题**: `Error: Unsupported Node.js version`

**解决**:
```bash
# 检查当前版本
node -v

# 使用 nvm 安装正确版本
nvm install 20
nvm use 20
```

### 3. MySQL 连接失败

**问题**: `Error: Can't connect to MySQL server`

**解决**:
```bash
# 检查 MySQL 是否运行
docker compose ps mysql

# 查看 MySQL 日志
docker compose logs mysql

# 测试连接
mysql -h localhost -P 3306 -u asinranker -p
```

### 4. Playwright 浏览器安装失败

**问题**: `Error: playwright install failed`

**解决**:
```bash
# Linux: 安装系统依赖
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2

# 重新安装浏览器
playwright install chromium
```

### 5. 端口被占用

**问题**: `Error: Address already in use`

**解决**:
```bash
# 查找占用端口的进程
# Linux/Mac:
lsof -i :8000
# Windows:
netstat -ano | findstr :8000

# 杀死进程
# Linux/Mac:
kill -9 <PID>
# Windows:
taskkill /F /PID <PID>

# 或修改端口
export BACKEND_PORT=8001
```

### 6. Docker 构建失败

**问题**: `ERROR: failed to solve: process did not complete successfully`

**解决**:
```bash
# 清理 Docker 缓存
docker builder prune -a

# 重新构建
docker compose build --no-cache

# 查看详细信息
docker compose build --progress=plain
```

### 7. 前端构建失败

**问题**: `Error: ENOSPC: System limit for number of file watchers reached`

**解决**:
```bash
# Linux: 增加文件监控限制
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# 或使用 Docker 构建
docker compose build frontend
```

### 8. 后端健康检查失败

**问题**: 服务启动但健康检查返回 503

**解决**:
```bash
# 查看后端日志
docker compose logs backend

# 手动检查健康端点
curl -v http://localhost:8000/api/v1/health

# 检查数据库连接
docker compose exec backend python -c "from backend.services.database import get_db; print(get_db())"
```

### 9. 跨域问题 (CORS)

**问题**: `Access to fetch at '...' has been blocked by CORS policy`

**解决**:
```bash
# 编辑 backend/.env
CORS_ORIGINS=http://localhost:5173,https://yourdomain.com

# 重启后端服务
docker compose restart backend
```

---

## 监控与维护

### 查看日志

```bash
# Docker 方式
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f mysql

# Systemd 方式
journalctl -u asin-ranker-backend -f
```

### 备份数据库

```bash
# Docker 方式
docker compose exec mysql mysqldump -u root -p asin_ranker > backup-$(date +%Y%m%d).sql

# 恢复数据库
docker compose exec -T mysql mysql -u root -p asin_ranker < backup-20240101.sql
```

### 更新部署

```bash
# 拉取最新代码
git pull origin main

# 重新构建并部署
docker compose build
docker compose up -d

# 清理旧镜像
docker image prune -f
```

### 性能优化

```bash
# 查看容器资源使用
docker stats

# 限制容器资源
# 编辑 docker-compose.yml，添加：
# deploy:
#   resources:
#     limits:
#       cpus: '2'
#       memory: 2G
```

---

## 安全建议

1. **使用强密码**: 生产环境必须使用强密码
2. **使用 HTTPS**: 生产环境必须配置 SSL 证书
3. **限制访问**: 使用防火墙限制数据库和 API 访问
4. **定期更新**: 保持 Python、Node.js 和依赖包更新
5. **监控日志**: 定期检查异常日志
6. **备份数据**: 定期备份数据库
7. **最小权限**: 数据库用户只授予必要权限

---

## 支持

如有问题，请提交 Issue 或联系开发团队。

- GitHub Issues: https://github.com/your-org/asin-ranker/issues
- 文档：https://github.com/your-org/asin-ranker/wiki
