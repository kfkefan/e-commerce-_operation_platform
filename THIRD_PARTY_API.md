# 第三方 API 集成指南

本项目支持集成第三方 API 服务，用于绕过亚马逊的反爬虫机制，提供更稳定的数据获取能力。

## 支持的第三方 API

| 提供商 | 特点 | 推荐场景 |
|--------|------|----------|
| **DataForSEO** | 专业 SEO 数据 API，支持 Amazon Rankings | 大规模数据采集，需要历史数据 |
| **SerpApi** | 搜索引擎结果 API，支持 Amazon | 快速集成，结果准确 |
| **ScraperAPI** | 通用网页爬取 API，自动处理反爬 | 灵活定制，支持自定义解析 |

## 快速开始

### 1. 获取 API 密钥

#### DataForSEO
1. 访问 https://dataforseo.com/
2. 注册账号
3. 在 Dashboard 获取 Login 和 Password

#### SerpApi
1. 访问 https://serpapi.com/
2. 注册账号
3. 获取 API Key

#### ScraperAPI
1. 访问 https://www.scraperapi.com/
2. 注册账号
3. 获取 API Key

### 2. 配置环境变量

编辑 `.env` 文件，添加以下配置：

```bash
# ========== 第三方 API 开关 ==========
THIRD_PARTY_API_ENABLED=true
THIRD_PARTY_PROVIDER=serpapi  # dataforseo | serpapi | scraperapi

# DataForSEO 配置
DATAFORSEO_LOGIN=your_email@example.com
DATAFORSEO_PASSWORD=your_password
DATAFORSEO_API_URL=https://api.dataforseo.com/v3

# SerpApi 配置
SERPAPI_API_KEY=your_api_key_here
SERPAPI_API_URL=https://serpapi.com/search

# ScraperAPI 配置
SCRAPERAPI_API_KEY=your_api_key_here
SCRAPERAPI_API_URL=http://api.scraperapi.com

# ========== 使用策略 ==========
USE_THIRD_PARTY_FALLBACK=true  # 本地爬虫失败时回退到第三方 API
THIRD_PARTY_TIMEOUT=30000      # 超时时间（毫秒）
THIRD_PARTY_MAX_RETRIES=2      # 最大重试次数
```

### 3. 重启服务

```bash
docker-compose restart backend
```

## 工作模式

### 模式 1: 仅使用第三方 API
```bash
THIRD_PARTY_API_ENABLED=true
USE_THIRD_PARTY_FALLBACK=false
```
- 所有请求都通过第三方 API
- 速度快，稳定性高
- 需要付费

### 模式 2: 仅使用本地爬虫
```bash
THIRD_PARTY_API_ENABLED=false
```
- 所有请求都使用本地 Playwright
- 免费，但可能被反爬

### 模式 3: 混合模式（推荐）
```bash
THIRD_PARTY_API_ENABLED=true
USE_THIRD_PARTY_FALLBACK=true
```
- 优先使用第三方 API
- 失败时自动回退到本地爬虫
- 平衡成本和稳定性

## API 计费参考

| 提供商 | 免费额度 | 付费计划 | 单价参考 |
|--------|----------|----------|----------|
| DataForSEO | 无 | $50 起 | ~$0.0012/关键词 |
| SerpApi | 100 次/月 | $50 起 | ~$0.0008/关键词 |
| ScraperAPI | 1000 次 | $29 起 | ~$0.0005/请求 |

## 监控和日志

启用第三方 API 后，查看日志确认工作状态：

```bash
docker logs asin-ranker-backend -f
```

正常日志示例：
```
INFO - 使用第三方 API 爬取：pack and play travel crib (provider: serpapi)
INFO - SerpApi 找到自然排名：第 1 页，位置 15
INFO - 第三方 API 成功：pack and play travel crib - found
```

失败回退日志：
```
WARNING - 第三方 API 失败：SerpApi 请求超时
INFO - 第三方 API 失败，回退到本地爬虫：pack and play travel crib
INFO - 使用本地爬虫爬取：pack and play travel crib
```

## 性能优化建议

1. **降低并发**：第三方 API 通常有速率限制
   ```bash
   MAX_CONCURRENT_TASKS=2
   ```

2. **增加超时**：网络请求可能需要更长时间
   ```bash
   THIRD_PARTY_TIMEOUT=60000
   ```

3. **启用重试**：网络波动时自动重试
   ```bash
   THIRD_PARTY_MAX_RETRIES=3
   ```

## 常见问题

### Q: 如何切换第三方 API 提供商？
A: 修改 `THIRD_PARTY_PROVIDER` 变量，重启服务即可。

### Q: 如何查看第三方 API 使用情况？
A: 查看日志中的 "第三方 API" 关键字，或查看提供商的 Dashboard。

### Q: 第三方 API 失败后会怎样？
A: 如果 `USE_THIRD_PARTY_FALLBACK=true`，会自动回退到本地爬虫。

### Q: 可以同时使用多个第三方 API 吗？
A: 当前版本只支持一个提供商，但可以手动切换。

## 安全提示

- **不要将 API 密钥提交到版本控制**
- **定期轮换 API 密钥**
- **监控使用量，避免超额费用**
- **使用环境变量存储敏感信息**
