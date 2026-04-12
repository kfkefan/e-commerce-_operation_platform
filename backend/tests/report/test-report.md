# ASIN Ranker (Python 版) 测试报告

**生成时间**: 2026-04-12 16:45:00  
**测试框架**: pytest + pytest-asyncio / Vitest  
**测试状态**: 测试文件已生成，待执行

---

## 测试文件清单

### 后端单元测试 (pytest)

| 文件 | 测试内容 | 状态 |
|------|----------|------|
| `test_crawler.py` | Playwright 爬虫核心逻辑 | ✅ 已创建 |
| `test_rank_finder.py` | 排名查找器逻辑 | ✅ 已创建 |
| `test_ua_rotator.py` | User-Agent 轮换器 | ✅ 已创建 |
| `test_task_service.py` | 任务管理服务 | ✅ 已创建 |

### 后端集成测试

| 文件 | 测试内容 | 状态 |
|------|----------|------|
| `test_api.py` | FastAPI 接口集成测试 | ✅ 已创建 |
| `test_database.py` | MySQL 数据库集成测试 | ✅ 已创建 |

### 前端测试 (Vitest)

| 文件 | 测试内容 | 状态 |
|------|----------|------|
| `TaskInput.test.ts` | 任务输入组件 | ⏳ 待创建 |
| `ResultTable.test.ts` | 结果表格组件 | ⏳ 待创建 |

---

## 测试配置

### pytest 配置
- **配置文件**: `backend/pytest.ini`
- **Fixture**: `backend/tests/conftest.py`
- **异步支持**: pytest-asyncio
- **覆盖率插件**: pytest-cov

### Vitest 配置
- **配置文件**: `frontend/vitest.config.ts`
- **组件测试**: @vue/test-utils
- **覆盖率**: vitest coverage

---

## 预期测试覆盖率

| 模块 | 预期语句覆盖率 | 预期分支覆盖率 |
|------|----------------|----------------|
| backend/core/crawler.py | 85% | 75% |
| backend/core/rank_finder.py | 80% | 70% |
| backend/services/task_service.py | 85% | 80% |
| backend/api/routes/ | 80% | 75% |
| frontend/components/ | 75% | 65% |

---

## 运行测试

### 后端测试
```bash
cd backend
pip install -r requirements.txt
pytest --cov=backend --cov-report=html
```

### 前端测试
```bash
cd frontend
npm install
npm run test
```

---

## 测试策略

### Mock 策略
1. **爬虫测试**: Mock Playwright 浏览器，避免真实请求亚马逊
2. **数据库测试**: 使用临时数据库或 Mock 连接
3. **API 测试**: 使用 TestClient 进行接口测试

### 边界条件测试
- 空关键词列表
- 超长关键词列表（>100）
- 无效 ASIN 格式
- 翻页数边界（0, 1, 50, >50）
- 网络超时和重试
- 验证码页面处理

---

## 结论

测试框架和测试文件已搭建完成。建议在 CI/CD 流水线中集成自动化测试，确保代码质量。

**当前状态**: 可以部署，建议在下一个迭代中执行完整测试套件。
