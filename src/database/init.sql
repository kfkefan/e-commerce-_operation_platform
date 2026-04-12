-- ASIN 关键词排名追踪器 - 数据库初始化脚本
-- 版本：v1.0
-- 创建日期：2026-04-11

-- 启用外键约束
PRAGMA foreign_keys = ON;

-- ============================================
-- 任务表 (tasks)
-- 存储任务基本信息和状态
-- ============================================
CREATE TABLE IF NOT EXISTS tasks (
    task_id VARCHAR(36) PRIMARY KEY,
    asin VARCHAR(10) NOT NULL,
    site VARCHAR(50) NOT NULL DEFAULT 'amazon.com',
    max_pages INTEGER NOT NULL DEFAULT 5,
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    total_keywords INTEGER NOT NULL,
    processed_keywords INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    paused_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 任务表索引
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tasks_asin ON tasks(asin);

-- ============================================
-- 任务关键词表 (task_keywords)
-- 存储任务的关键词列表
-- ============================================
CREATE TABLE IF NOT EXISTS task_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(36) NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    sort_order INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);

-- 关键词表索引
CREATE INDEX IF NOT EXISTS idx_keywords_task_id ON task_keywords(task_id);
CREATE INDEX IF NOT EXISTS idx_keywords_task_sort ON task_keywords(task_id, sort_order);

-- ============================================
-- 任务结果表 (task_results)
-- 存储爬取结果数据
-- ============================================
CREATE TABLE IF NOT EXISTS task_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(36) NOT NULL,
    keyword_id INTEGER NOT NULL,
    keyword VARCHAR(100) NOT NULL,
    organic_page INTEGER,
    organic_position INTEGER,
    ad_page INTEGER,
    ad_position INTEGER,
    status VARCHAR(20) NOT NULL,
    raw_html TEXT,
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY (keyword_id) REFERENCES task_keywords(id) ON DELETE CASCADE
);

-- 结果表索引
CREATE INDEX IF NOT EXISTS idx_results_task_id ON task_results(task_id);
CREATE INDEX IF NOT EXISTS idx_results_task_keyword ON task_results(task_id, keyword);
CREATE INDEX IF NOT EXISTS idx_results_status ON task_results(status);

-- ============================================
-- 历史记录表 (history)
-- 存储历史记录摘要（最近 10 条）
-- ============================================
CREATE TABLE IF NOT EXISTS history (
    task_id VARCHAR(36) PRIMARY KEY,
    asin VARCHAR(10) NOT NULL,
    keyword_count INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);

-- 历史记录表索引
CREATE INDEX IF NOT EXISTS idx_history_created_at ON history(created_at DESC);

-- ============================================
-- 历史快照表 (history_snapshots)
-- 存储历史任务的完整快照（JSON 格式）
-- ============================================
CREATE TABLE IF NOT EXISTS history_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id VARCHAR(36) NOT NULL,
    snapshot_data TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES history(task_id) ON DELETE CASCADE
);

-- ============================================
-- 配置表 (config)
-- 存储系统配置
-- ============================================
CREATE TABLE IF NOT EXISTS config (
    key VARCHAR(50) PRIMARY KEY,
    value TEXT NOT NULL,
    type VARCHAR(20) NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认配置
INSERT OR REPLACE INTO config (key, value, type) VALUES
    ('request_delay_min', '2000', 'number'),
    ('request_delay_max', '5000', 'number'),
    ('max_retries', '3', 'number'),
    ('supported_sites', '["amazon.com","amazon.co.uk","amazon.de","amazon.fr","amazon.co.jp","amazon.cn"]', 'json');

-- ============================================
-- 触发器：自动更新 updated_at 字段
-- ============================================
CREATE TRIGGER IF NOT EXISTS update_tasks_timestamp 
AFTER UPDATE ON tasks
BEGIN
    UPDATE tasks SET updated_at = CURRENT_TIMESTAMP WHERE task_id = NEW.task_id;
END;

-- ============================================
-- 视图：任务进度统计
-- ============================================
CREATE VIEW IF NOT EXISTS task_progress AS
SELECT 
    task_id,
    status,
    total_keywords,
    processed_keywords,
    ROUND(processed_keywords * 100.0 / total_keywords, 2) AS progress_percentage,
    created_at,
    started_at,
    completed_at
FROM tasks;

-- ============================================
-- 视图：结果统计
-- ============================================
CREATE VIEW IF NOT EXISTS result_stats AS
SELECT 
    task_id,
    COUNT(*) AS total_results,
    SUM(CASE WHEN status = 'found' THEN 1 ELSE 0 END) AS found_count,
    SUM(CASE WHEN status = 'ad_only' THEN 1 ELSE 0 END) AS ad_only_count,
    SUM(CASE WHEN status = 'organic_only' THEN 1 ELSE 0 END) AS organic_only_count,
    SUM(CASE WHEN status = 'not_found' THEN 1 ELSE 0 END) AS not_found_count
FROM task_results
GROUP BY task_id;
