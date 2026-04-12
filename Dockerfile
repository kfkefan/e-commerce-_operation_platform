# ASIN Ranker 后端 Dockerfile
# 多阶段构建，优化镜像大小

# =====================
# 阶段 1: 构建阶段
# =====================
FROM node:20-alpine AS builder

WORKDIR /app

# 安装构建依赖
RUN apk add --no-cache python3 make g++

# 复制 package 文件
COPY package*.json ./
COPY backend/package*.json ./backend/ 2>/dev/null || true
COPY frontend/package*.json ./frontend/ 2>/dev/null || true

# 安装所有依赖 (包括 devDependencies)
RUN npm ci

# 复制源代码
COPY . .

# 构建项目
RUN npm run build

# =====================
# 阶段 2: 生产阶段
# =====================
FROM node:20-alpine AS production

WORKDIR /app

# 安装运行时依赖
RUN apk add --no-cache sqlite-libs

# 创建非 root 用户
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# 复制 package 文件
COPY package*.json ./

# 仅安装生产依赖
RUN npm ci --production && npm cache clean --force

# 复制构建产物
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/src/database/init.sql ./database/init.sql 2>/dev/null || true

# 复制静态文件 (如果需要)
COPY --from=builder /app/frontend/dist ./frontend/dist 2>/dev/null || true

# 设置权限
RUN chown -R nodejs:nodejs /app

# 切换到非 root 用户
USER nodejs

# 暴露端口
EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

# 环境变量
ENV NODE_ENV=production
ENV PORT=3000

# 启动命令
CMD ["node", "dist/server/index.js"]
