-- ASIN Ranker Database Initialization Script
-- MySQL 8.0+

-- 创建数据库
CREATE DATABASE IF NOT EXISTS asin_ranker
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE asin_ranker;

-- 创建 tasks 表（任务主表）
CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(36) PRIMARY KEY COMMENT '任务 ID (UUID)',
    asin VARCHAR(10) NOT NULL COMMENT '产品 ASIN',
    site VARCHAR(50) NOT NULL DEFAULT 'amazon.com' COMMENT '亚马逊站点',
    max_pages INT NOT NULL DEFAULT 5 COMMENT '最大翻页数 (1-50)',
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT '任务状态',
    total_keywords INT NOT NULL COMMENT '关键词总数',
    processed_keywords INT NOT NULL DEFAULT 0 COMMENT '已处理关键词数',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    completed_at DATETIME NULL COMMENT '完成时间',
    error_message TEXT NULL COMMENT '错误信息',
    
    INDEX idx_tasks_status (status),
    INDEX idx_tasks_created_at (created_at DESC),
    INDEX idx_tasks_status_created (status, created_at DESC),
    INDEX idx_tasks_asin (asin)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务主表';

-- 创建 task_keywords 表（任务关键词表）
CREATE TABLE IF NOT EXISTS task_keywords (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增 ID',
    task_id VARCHAR(36) NOT NULL COMMENT '关联任务 ID',
    keyword VARCHAR(200) NOT NULL COMMENT '关键词文本',
    priority INT NOT NULL DEFAULT 0 COMMENT '处理优先级',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    
    CONSTRAINT fk_task_keywords_task
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    
    INDEX idx_task_keywords_task_id (task_id),
    INDEX idx_task_keywords_task_priority (task_id, priority ASC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务关键词表';

-- 创建 task_results 表（任务结果表）
CREATE TABLE IF NOT EXISTS task_results (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增 ID',
    task_id VARCHAR(36) NOT NULL COMMENT '关联任务 ID',
    keyword VARCHAR(200) NOT NULL COMMENT '关键词文本',
    organic_page INT NULL COMMENT '自然排名页码',
    organic_position INT NULL COMMENT '自然排名页内位置',
    ad_page INT NULL COMMENT '广告排名页码',
    ad_position INT NULL COMMENT '广告排名页内位置',
    status VARCHAR(30) NOT NULL COMMENT '结果状态',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '爬取时间',
    
    CONSTRAINT fk_task_results_task
        FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    
    INDEX idx_task_results_task_id (task_id),
    INDEX idx_task_results_task_keyword (task_id, keyword),
    INDEX idx_task_results_task_status (task_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务结果表';

-- 创建 config 表（系统配置表）
CREATE TABLE IF NOT EXISTS config (
    `key` VARCHAR(100) PRIMARY KEY COMMENT '配置键',
    value TEXT NOT NULL COMMENT '配置值 (JSON 格式)',
    description VARCHAR(500) NULL COMMENT '配置描述',
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- 初始化配置数据
INSERT INTO config (`key`, value, description) VALUES
    ('crawler.max_concurrent_browsers', '3', '最大并发浏览器实例数'),
    ('crawler.max_concurrent_tasks', '5', '最大并发任务数'),
    ('crawler.request_delay_min', '2', '请求最小延迟（秒）'),
    ('crawler.request_delay_max', '5', '请求最大延迟（秒）'),
    ('crawler.max_retries', '3', '最大重试次数'),
    ('crawler.proxy_list', '[]', '代理列表（JSON 数组）'),
    ('crawler.user_agents', '[]', 'User-Agent 列表（JSON 数组）'),
    ('sites.supported', '["amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr", "amazon.co.jp", "amazon.ca", "amazon.com.au"]', '支持的亚马逊站点列表')
ON DUPLICATE KEY UPDATE value=VALUES(value);
