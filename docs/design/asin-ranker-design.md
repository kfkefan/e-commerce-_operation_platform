# ASIN 排名追踪器 - 技术设计方案

**版本**: 1.0  
**创建时间**: 2026-04-12  
**作者**: design-agent

---

## 一、系统架构设计

### 1.1 整体架构图

```mermaid
graph TB
    subgraph 前端层
        A[Vue.js 3 前端] --> B[Element Plus UI]
        A --> C[Axios HTTP 客户端]
    end
    
    subgraph API 网关层
        D[FastAPI 应用] --> E[API 路由]
        D --> F[中间件层]
        F --> G[CORS 中间件]
        F --> H[限流中间件]
        F --> I[异常处理中间件]
    end
    
    subgraph 业务逻辑层
        J[任务管理服务] --> K[任务创建]
        J --> L[任务状态查询]
        J --> M[任务取消]
        
        N[排名爬取服务] --> O[关键词队列]
        N --> P[Playwright 爬虫]
        N --> Q[结果解析器]
    end
    
    subgraph 数据访问层
        R[数据库连接池] --> S[MySQL 8.0]
        T[配置管理器] --> U[配置文件/环境变量]
    end
    
    subgraph 基础设施层
        V[代理池]
        W[UA 轮换器]
        X[信号量控制器]
    end
    
    C --> E
    E --> J
    E --> N
    J --> R
    N --> R
    N --> V
    N --> W
    N --> X
    X --> P
```

### 1.2 架构分层说明

| 层级 | 职责 | 技术选型 |
|------|------|----------|
| 前端层 | 用户界面交互、数据展示 | Vue.js 3 + Element Plus + TypeScript |
| API 网关层 | HTTP 请求处理、路由分发、中间件 | FastAPI + Uvicorn |
| 业务逻辑层 | 核心业务逻辑、任务调度、爬虫控制 | Python asyncio + Playwright |
| 数据访问层 | 数据持久化、连接池管理 | aiomysql + MySQL 8.0 |
| 基础设施层 | 反爬策略、并发控制 | 自定义模块 |

---

## 二、技术栈选型说明

### 2.1 前端技术栈

| 技术 | 版本 | 选型理由 |
|------|------|----------|
| Vue.js | 3.x | 响应式数据绑定、组件化开发、TypeScript 支持完善 |
| Element Plus | 2.x | 丰富的 UI 组件库、与 Vue 3 深度集成、主题定制灵活 |
| TypeScript | 5.x | 类型安全、代码提示、减少运行时错误 |
| Axios | 1.x | Promise-based HTTP 客户端、拦截器支持、取消请求 |
| Vue Router | 4.x | 前端路由管理、导航守卫 |
| Pinia | 2.x | 状态管理、比 Vuex 更简洁的 API |

### 2.2 后端技术栈

| 技术 | 版本 | 选型理由 |
|------|------|----------|
| Python | 3.10+ | 异步编程支持完善、丰富的爬虫生态 |
| FastAPI | 0.100+ | 高性能、自动生成 OpenAPI 文档、类型提示支持 |
| Uvicorn | 0.20+ | ASGI 服务器、支持 asyncio、高性能 |
| Playwright | 1.30+ | 异步 API 支持、多浏览器支持、反爬绕过能力强 |
| aiomysql | 0.2+ | 异步 MySQL 驱动、连接池支持 |
| Pydantic | 2.x | 数据验证、序列化、与 FastAPI 深度集成 |

### 2.3 数据库

| 技术 | 版本 | 选型理由 |
|------|------|----------|
| MySQL | 8.0+ | 成熟稳定、JSON 字段支持、事务支持完善 |

### 2.4 开发工具

| 工具 | 用途 |
|------|------|
| Poetry | Python 依赖管理 |
| npm/pnpm | 前端依赖管理 |
| ESLint + Prettier | 代码规范与格式化 |
| Black + isort | Python 代码格式化 |
| pytest | 单元测试框架 |

---

## 三、模块划分

### 3.1 模块结构

```
asin-ranker/
├── frontend/                    # 前端项目
│   ├── src/
│   │   ├── api/                 # API 调用封装
│   │   ├── components/          # 公共组件
│   │   ├── views/               # 页面视图
│   │   ├── stores/              # Pinia 状态管理
│   │   ├── types/               # TypeScript 类型定义
│   │   └── utils/               # 工具函数
│   └── package.json
├── backend/                     # 后端项目
│   ├── app/
│   │   ├── api/                 # API 路由
│   │   │   ├── routes/
│   │   │   │   ├── tasks.py     # 任务相关接口
│   │   │   │   └── health.py    # 健康检查接口
│   │   ├── core/                # 核心配置
│   │   │   ├── config.py        # 配置管理
│   │   │   ├── exceptions.py    # 自定义异常
│   │   │   └── middleware.py    # 中间件
│   │   ├── models/              # 数据模型
│   │   │   ├── task.py          # 任务模型
│   │   │   └── result.py        # 结果模型
│   │   ├── services/            # 业务服务
│   │   │   ├── task_service.py  # 任务管理服务
│   │   │   └── rank_service.py  # 排名爬取服务
│   │   ├── crawlers/            # 爬虫模块
│   │   │   ├── amazon_crawler.py # 亚马逊爬虫
│   │   │   ├── parser.py        # 页面解析器
│   │   │   └── anti_detect.py   # 反检测模块
│   │   ├── db/                  # 数据库模块
│   │   │   ├── connection.py    # 连接池管理
│   │   │   └── repositories/    # 数据访问层
│   │   └── utils/               # 工具函数
│   │       ├── ua_pool.py       # UA 轮换
│   │       ├── proxy_pool.py    # 代理池
│   │       └── semaphore.py     # 信号量管理
│   ├── tests/                   # 测试代码
│   ├── pyproject.toml
│   └── main.py                  # 应用入口
└── docs/                        # 文档
```

### 3.2 模块职责

| 模块 | 职责 |
|------|------|
| `api/routes` | 定义 RESTful API 端点，处理 HTTP 请求/响应 |
| `core` | 应用配置、异常处理、中间件、常量定义 |
| `models` | Pydantic 模型、数据库 ORM 模型 |
| `services` | 业务逻辑实现、任务调度、状态管理 |
| `crawlers` | 网页爬取、数据提取、反爬策略 |
| `db` | 数据库连接池、CRUD 操作 |
| `utils` | 通用工具函数、UA 池、代理池、信号量 |

---

## 四、数据流设计

### 4.1 任务提交流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant A as FastAPI
    participant S as TaskService
    participant D as Database
    participant Q as 任务队列
    
    U->>F: 输入 ASIN/关键词/配置
    F->>F: 表单验证
    F->>A: POST /tasks
    A->>A: 参数验证 (Pydantic)
    A->>S: create_task()
    S->>D: INSERT INTO tasks
    D-->>S: task_id
    S->>D: INSERT INTO task_keywords
    S->>Q:  enqueue task
    S-->>A: TaskResponse
    A-->>F: 201 Created + taskId
    F-->>U: 显示任务提交成功
```

### 4.2 任务执行流程

```mermaid
sequenceDiagram
    participant S as Scheduler
    participant W as Worker
    participant P as Playwright
    participant A as Amazon
    participant D as Database
    
    S->>W: 获取待执行任务
    W->>W: 获取信号量
    W->>P: launch_browser()
    loop 每个关键词
        W->>W: 获取 UA
        W->>W: 获取代理
        W->>P: page.goto(search_url)
        P->>A: HTTP Request
        A-->>P: Search Results HTML
        W->>W: 解析排名数据
        W->>D: INSERT INTO task_results
    end
    W->>P: browser.close()
    W->>S: 释放信号量
    W->>D: UPDATE tasks SET status=completed
```

### 4.3 结果查询流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant A as FastAPI
    participant D as Database
    
    U->>F: 查看任务结果
    F->>A: GET /tasks/{taskId}/results
    A->>D: SELECT FROM task_results
    D-->>A: 结果数据
    A->>A: 格式化响应
    A-->>F: 200 OK + Results
    F-->>U: 展示结果表格
```

---

## 五、并发与速率控制设计

### 5.1 信号量控制

```python
# 全局信号量配置
MAX_CONCURRENT_BROWSERS = 3  # 最大并发浏览器实例数
MAX_CONCURRENT_TASKS = 5     # 最大并发任务数

class SemaphoreManager:
    def __init__(self):
        self.browser_semaphore = asyncio.Semaphore(MAX_CONCURRENT_BROWSERS)
        self.task_semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    
    async def acquire_browser(self):
        await self.browser_semaphore.acquire()
    
    def release_browser(self):
        self.browser_semaphore.release()
```

### 5.2 请求速率控制

| 控制层级 | 策略 | 参数 |
|----------|------|------|
| 浏览器级别 | 信号量限制 | 最多 3 个并发浏览器 |
| 任务级别 | 信号量限制 | 最多 5 个并发任务 |
| 关键词级别 | 随机延迟 | 2-5 秒随机等待 |
| 页面级别 | 指数退避 | 失败重试：1s, 2s, 4s |
| IP 级别 | 代理轮换 | 每 10 次请求切换代理 |

### 5.3 异步任务调度

```python
async def process_task(task_id: str):
    async with semaphore_manager.task_semaphore:
        # 更新任务状态为 running
        await task_service.update_status(task_id, TaskStatus.RUNNING)
        
        # 获取任务关键词列表
        keywords = await task_service.get_keywords(task_id)
        
        # 创建关键词处理协程
        tasks = [
            process_keyword(task_id, kw, semaphore_manager.browser_semaphore)
            for kw in keywords
        ]
        
        # 并发执行（受信号量控制）
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 更新任务状态
        await task_service.complete_task(task_id, results)
```

---

## 六、反爬策略设计

### 6.1 User-Agent 轮换

```python
# UA 池配置
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ... Chrome/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ... Chrome/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # ... 更多 UA
]

class UARotator:
    def __init__(self):
        self.index = 0
    
    def get_next_ua(self) -> str:
        ua = USER_AGENTS[self.index % len(USER_AGENTS)]
        self.index += 1
        return ua
```

### 6.2 代理池管理

```python
# 代理配置
PROXY_LIST = [
    "http://user:pass@proxy1.example.com:8080",
    "http://user:pass@proxy2.example.com:8080",
    # ... 更多代理
]

class ProxyPool:
    def __init__(self):
        self.proxies = PROXY_LIST.copy()
        self.current_index = 0
    
    def get_proxy(self) -> Optional[str]:
        if not self.proxies:
            return None
        proxy = self.proxies[self.current_index % len(self.proxies)]
        self.current_index += 1
        return proxy
    
    def remove_proxy(self, proxy: str):
        """标记代理为失效"""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
```

### 6.3 请求延迟策略

```python
import random

async def random_delay(min_seconds: float = 2.0, max_seconds: float = 5.0):
    """随机延迟"""
    delay = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(delay)

async def exponential_backoff(retry_count: int, base_delay: float = 1.0):
    """指数退避延迟"""
    delay = base_delay * (2 ** retry_count)
    jitter = random.uniform(0, delay * 0.1)  # 添加 10% 抖动
    await asyncio.sleep(delay + jitter)
```

### 6.4 重试机制

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class AmazonCrawler:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError))
    )
    async def fetch_page(self, url: str, browser, context):
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return page
```

### 6.5 反检测措施

| 措施 | 实现方式 |
|------|----------|
| 浏览器指纹 | Playwright 默认隐藏自动化特征 |
| JavaScript 执行 | 启用 JS 渲染，模拟真实浏览器 |
| Cookie 处理 | 自动管理 Cookie，保持会话 |
| 请求头完整 | 设置完整的 Accept、Accept-Language 等头 |
| 鼠标行为 | 随机滚动、随机点击（可选） |
| 验证码检测 | 检测验证码页面，暂停任务并记录 |

### 6.6 异常处理策略

```python
class CrawlException(Exception):
    """爬取异常基类"""
    pass

class CaptchaDetected(CrawlException):
    """检测到验证码"""
    pass

class RateLimited(CrawlException):
    """请求频率受限"""
    pass

async def safe_crawl(keyword: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            result = await crawl_keyword(keyword)
            return result
        except CaptchaDetected:
            # 记录验证码，跳过该关键词
            log.warning(f"Captcha detected for keyword: {keyword}")
            return {"status": "captcha", "keyword": keyword}
        except RateLimited:
            # 延长等待时间后重试
            await asyncio.sleep(60 * (attempt + 1))
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await exponential_backoff(attempt)
```

---

## 七、性能优化设计

### 7.1 数据库连接池

```python
from aiomysql import create_pool

class DatabasePool:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool = None
    
    async def connect(self):
        self.pool = await create_pool(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            db=self.config.database,
            minsize=5,
            maxsize=20,
            autocommit=True
        )
    
    async def disconnect(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
    
    def acquire(self):
        return self.pool.acquire()
```

### 7.2 批量插入优化

```python
async def batch_insert_results(conn, task_id: str, results: list):
    """批量插入结果，减少数据库交互次数"""
    async with conn.acquire() as conn:
        async with conn.cursor() as cur:
            # 使用多值 INSERT
            values = []
            for r in results:
                values.append((
                    task_id, r['keyword'], r['organic_page'],
                    r['organic_position'], r['ad_page'], r['ad_position'],
                    r['status'], r['timestamp']
                ))
            
            await cur.executemany(
                """INSERT INTO task_results 
                   (task_id, keyword, organic_page, organic_position, 
                    ad_page, ad_position, status, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                values
            )
```

### 7.3 前端性能优化

| 优化项 | 措施 |
|--------|------|
| 代码分割 | 按路由懒加载组件 |
| 静态资源 | CDN 加速、Gzip 压缩 |
| 表格渲染 | 虚拟滚动（>100 行时） |
| API 请求 | 防抖节流、请求缓存 |
| 状态管理 | Pinia 持久化、按需订阅 |

---

## 八、监控与日志

### 8.1 日志配置

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    logger = logging.getLogger("asin_ranker")
    logger.setLevel(logging.INFO)
    
    # 文件处理器（轮转）
    file_handler = RotatingFileHandler(
        "logs/app.log", maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(levelname)s - %(message)s")
    )
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
```

### 8.2 关键指标监控

| 指标 | 监控方式 | 告警阈值 |
|------|----------|----------|
| 任务成功率 | 数据库统计 | < 90% |
| 平均处理时间 | 日志分析 | > 60s/关键词 |
| API 响应时间 | 中间件记录 | > 500ms |
| 数据库连接数 | 连接池监控 | > 80% 容量 |
| 浏览器实例数 | 信号量监控 | 达到上限 |

---

## 九、部署架构

### 9.1 单机部署

```
┌─────────────────────────────────────┐
│           Docker Container          │
│  ┌─────────────┐  ┌───────────────┐ │
│  │   Uvicorn   │  │    MySQL 8    │ │
│  │  (FastAPI)  │  │   (本地)      │ │
│  └─────────────┘  └───────────────┘ │
└─────────────────────────────────────┘
```

### 9.2 生产环境部署

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Nginx     │────▶│   Uvicorn   │────▶│   MySQL 8   │
│  (反向代理) │     │  (多实例)   │     │  (主从)     │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌─────────────┐
                    │   Redis     │
                    │  (可选缓存) │
                    └─────────────┘
```

### 9.3 环境变量配置

```bash
# .env
DATABASE_URL=mysql://user:pass@localhost:3306/asin_ranker
MAX_CONCURRENT_BROWSERS=3
MAX_CONCURRENT_TASKS=5
PROXY_POOL_ENABLED=true
UA_ROTATION_ENABLED=true
LOG_LEVEL=INFO
```

---

## 十、安全设计

### 10.1 API 安全

| 措施 | 实现 |
|------|------|
| CORS | 限制允许的来源域名 |
| 限流 | 每 IP 每分钟最多 60 次请求 |
| 输入验证 | Pydantic 模型严格验证 |
| SQL 注入防护 | 参数化查询 |
| XSS 防护 | 前端输入输出转义 |

### 10.2 数据安全

| 措施 | 实现 |
|------|------|
| 敏感配置 | 环境变量存储，不提交代码 |
| 代理凭证 | 加密存储（可选） |
| 日志脱敏 | 不记录完整 URL 和 Cookie |

---

## 十一、扩展性设计

### 11.1 多站点支持

```python
SITE_CONFIGS = {
    "amazon.com": {"domain": "amazon.com", "tld": "com", "language": "en_US"},
    "amazon.co.uk": {"domain": "amazon.co.uk", "tld": "co.uk", "language": "en_GB"},
    "amazon.de": {"domain": "amazon.de", "tld": "de", "language": "de_DE"},
    "amazon.co.jp": {"domain": "amazon.co.jp", "tld": "co.jp", "language": "ja_JP"},
}

def build_search_url(site: str, keyword: str, page: int) -> str:
    config = SITE_CONFIGS.get(site, SITE_CONFIGS["amazon.com"])
    return f"https://www.{config['domain']}/s?k={quote(keyword)}&page={page}"
```

### 11.2 多平台扩展

```python
# 抽象爬虫基类
class BaseCrawler(ABC):
    @abstractmethod
    async def search(self, keyword: str, page: int) -> SearchResults:
        pass
    
    @abstractmethod
    def parse_ranking(self, html: str, asin: str) -> RankingResult:
        pass

class AmazonCrawler(BaseCrawler):
    # 亚马逊实现
    pass

class eBayCrawler(BaseCrawler):
    # eBay 实现（未来扩展）
    pass
```

---

## 十二、验收标准对照

| PRD 要求 | 技术方案对应 |
|----------|--------------|
| 异步架构 | FastAPI + asyncio + Playwright 异步 API |
| 信号量控制 | asyncio.Semaphore 限制并发浏览器数 |
| Playwright | 使用 async_playwright 进行页面爬取 |
| 连接池 | aiomysql 连接池，minsize=5, maxsize=20 |
| UA 轮换 | UARotator 类，从预定义池轮换 |
| 代理池 | ProxyPool 类，支持代理列表轮换 |
| 随机延迟 | random.uniform(2, 5) 秒延迟 |
| 指数退避 | tenacity 库实现重试机制 |

---

**文档结束**
