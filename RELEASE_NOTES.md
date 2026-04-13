# 版本更新说明 v1.1.0

## 发布日期
2026-04-12

## 新增功能

### 前端增强

#### 1. 并发数控制
- **位置**: 任务创建表单
- **默认值**: 3
- **可调范围**: 1-10
- **用途**: 控制同时爬取的关键词数量

#### 2. 仅爬取自然结果
- **位置**: 任务创建表单
- **类型**: 开关选项
- **默认**: 关闭（同时爬取自然和广告结果）
- **用途**: 跳过广告排名，仅获取自然搜索结果

### 后端增强

#### 1. 自动重试机制
- **触发条件**: 任务执行失败且 retry_count < max_retries
- **重试策略**: 指数退避（60s, 120s, 180s...）
- **最大重试次数**: 可配置（默认 2 次）
- **状态流转**: failed → retrying → running → completed/failed
- **断点续爬**: 重试时仅爬取失败的关键词，避免重复

#### 2. 手动重试功能
- **API**: `POST /api/v1/tasks/{task_id}/retry`
- **条件**: 任务状态为 failed 或 cancelled
- **行为**: 创建新任务 ID，保留原任务历史记录
- **参数**: 复用原任务的所有配置

#### 3. 放弃任务功能
- **API**: `POST /api/v1/tasks/{task_id}/abandon`
- **用途**: 主动终止 retrying 状态的任务
- **状态**: retrying/running/pending → cancelled

### 数据库变更

#### tasks 表新增字段
| 字段名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| retry_count | INT | 0 | 当前重试次数 |
| max_retries | INT | 2 | 最大重试次数 |
| fail_reason | TEXT | NULL | 失败原因 |
| next_retry_at | DATETIME | NULL | 下次重试时间 |
| original_task_id | VARCHAR(36) | NULL | 原始任务 ID |
| max_concurrent | INT | 3 | 最大并发数 |
| organic_only | TINYINT | 0 | 仅爬取自然结果 |

#### 新增索引
- `idx_tasks_retry (status, next_retry_at)`: 优化重试查询

## API 变更

### 新增接口

#### 1. 手动重试任务
```http
POST /api/v1/tasks/{task_id}/retry
```

**响应示例**:
```json
{
  "taskId": "new-uuid-here",
  "status": "pending",
  "createdAt": "2026-04-12T10:00:00",
  "totalKeywords": 10,
  "maxPages": 5
}
```

#### 2. 放弃任务
```http
POST /api/v1/tasks/{task_id}/abandon
```

**响应示例**:
```json
{
  "taskId": "task-uuid",
  "status": "cancelled",
  "createdAt": "2026-04-12T10:00:00",
  "totalKeywords": 10,
  "maxPages": 5
}
```

### 任务创建接口增强

```http
POST /api/v1/tasks
```

**新增请求参数**:
```json
{
  "asin": "B0GGBJF4HN",
  "keywords": ["keyword1", "keyword2"],
  "maxPages": 5,
  "site": "amazon.com",
  "maxConcurrent": 3,        // 新增
  "organicOnly": false,      // 新增
  "maxRetries": 2            // 新增
}
```

### 任务详情响应增强

```json
{
  "taskId": "uuid",
  "status": "retrying",
  "retryCount": 1,
  "maxRetries": 2,
  "failReason": "Connection timeout",
  "nextRetryAt": "2026-04-12T10:05:00",
  "canRetry": true,
  "maxConcurrent": 3,
  "organicOnly": false
}
```

## 任务状态机

```
pending → running → completed
              ↓
           failed → retrying → running
              ↓                    ↓
           cancelled ←─────────────┘
```

## 配置示例

### 环境变量 (.env)
```bash
# 爬虫配置
MAX_CONCURRENT_BROWSERS=3
MAX_CONCURRENT_TASKS=5

# 重试配置
DEFAULT_MAX_RETRIES=2
RETRY_BASE_DELAY=60  # 秒
```

## 升级步骤

### 1. 数据库迁移
```bash
docker exec -i asin-ranker-mysql mysql -uroot -pYourPassword asin_ranker < backend/database/migrate_add_retry_fields.sql
```

### 2. 重启服务
```bash
docker-compose restart backend
```

### 3. 验证功能
```bash
# 检查新字段
docker exec asin-ranker-mysql mysql -uroot -pYourPassword -e "DESC asin_ranker.tasks;"

# 测试 API
curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/retry
```

## 已知问题

无

## 后续计划

1. 前端界面更新（并发数滑块、自然结果开关）
2. 重试状态可视化（进度条显示"第 X 次重试"）
3. 失败原因中文提示
4. 任务历史版本对比

## 技术栈

- **后端**: FastAPI + asyncio
- **数据库**: MySQL 8.0
- **爬虫**: Playwright + stealth
- **第三方 API**: DataForSEO, SerpApi, ScraperAPI
