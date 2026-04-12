# ASIN 排名追踪器

亚马逊 ASIN 关键词排名追踪工具，支持多站点、多关键词批量查询。

## 功能特性

- ✅ 支持 7 个亚马逊站点（美国、英国、德国、法国、日本、加拿大、澳大利亚）
- ✅ 批量关键词查询（最多 100 个）
- ✅ 自然排名和广告排名追踪
- ✅ 实时任务进度监控
- ✅ 反爬策略（UA 轮换、代理池、请求延迟、重试机制）
- ✅ 并发控制（信号量限制）
- ✅ 结果导出 CSV

## 技术栈

### 后端
- Python 3.10+
- FastAPI
- Playwright（异步爬虫）
- MySQL 8.0
- aiomysql（异步数据库）

### 前端
- Vue.js 3
- Element Plus
- TypeScript
- Vite

## 快速开始

### 方式一：Docker Compose（推荐）

1. 克隆项目
```bash
git clone <repository-url>
cd asin-ranker
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，修改数据库密码等配置
```

3. 启动服务
```bash
docker-compose up -d
```

4. 访问应用
- 前端：http://localhost
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 方式二：本地开发

#### 后端

1. 创建虚拟环境
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 安装依赖
```bash
pip install -r requirements.txt
playwright install chromium
```

3. 初始化数据库
```bash
mysql -u root -p < database/init.sql
```

4. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件
```

5. 启动服务
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端

1. 安装依赖
```bash
cd frontend
npm install
```

2. 启动开发服务器
```bash
npm run dev
```

3. 访问 http://localhost:5173

## 项目结构

```
asin-ranker/
├── backend/                    # 后端代码
│   ├── api/
│   │   └── routes/            # API 路由
│   ├── core/                  # 核心模块（爬虫、UA、代理）
│   ├── services/              # 业务服务
│   ├── models/                # 数据模型
│   ├── database/              # 数据库脚本
│   ├── config.py              # 配置管理
│   ├── main.py                # 应用入口
│   └── requirements.txt       # Python 依赖
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── api/               # API 调用
│   │   ├── components/        # 组件
│   │   ├── views/             # 页面
│   │   ├── types/             # TypeScript 类型
│   │   └── router/            # 路由
│   ├── index.html
│   └── package.json
├── docker-compose.yml          # Docker 编排
├── Dockerfile.backend          # 后端镜像
├── Dockerfile.frontend         # 前端镜像
└── README.md
```

## API 使用示例

### 创建任务
```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "asin": "B08N5WRWNW",
    "keywords": ["wireless earbuds", "bluetooth headphones"],
    "maxPages": 5,
    "site": "amazon.com"
  }'
```

### 查询任务状态
```bash
curl http://localhost:8000/api/v1/tasks/{taskId}
```

### 获取任务结果
```bash
curl http://localhost:8000/api/v1/tasks/{taskId}/results
```

### 健康检查
```bash
curl http://localhost:8000/api/v1/health
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| DB_HOST | MySQL 主机 | localhost |
| DB_PORT | MySQL 端口 | 3306 |
| DB_USER | MySQL 用户名 | root |
| DB_PASSWORD | MySQL 密码 | - |
| DB_NAME | 数据库名 | asin_ranker |
| MAX_CONCURRENT_BROWSERS | 最大并发浏览器数 | 3 |
| MAX_CONCURRENT_TASKS | 最大并发任务数 | 5 |
| REQUEST_DELAY_MIN | 请求最小延迟（秒） | 2 |
| REQUEST_DELAY_MAX | 请求最大延迟（秒） | 5 |
| PROXY_POOL_ENABLED | 是否启用代理池 | false |
| UA_ROTATION_ENABLED | 是否启用 UA 轮换 | true |

### 反爬策略

1. **User-Agent 轮换**: 每次请求使用不同的 UA
2. **代理池**: 支持 HTTP 代理轮换（需自行配置）
3. **请求延迟**: 2-5 秒随机延迟
4. **重试机制**: 失败请求指数退避重试
5. **并发控制**: Semaphore 限制并发浏览器实例数

## 注意事项

⚠️ **合法使用**: 请遵守亚马逊网站的使用条款，合理使用本工具，避免过度频繁请求。

⚠️ **代理配置**: 如需大量查询，建议配置代理池以避免 IP 被封。

⚠️ **验证码**: 遇到验证码时任务会暂停并记录，需要手动处理。

## 开发计划

- [ ] 支持更多亚马逊站点
- [ ] 历史排名趋势图表
- [ ] 定时任务自动追踪
- [ ] 邮件/ webhook 通知
- [ ] 多用户支持

## License

MIT
