-- Database migration: Add retry fields to tasks table
ALTER TABLE tasks ADD COLUMN retry_count INT NOT NULL DEFAULT 0 AFTER error_message;
ALTER TABLE tasks ADD COLUMN max_retries INT NOT NULL DEFAULT 2 AFTER retry_count;
ALTER TABLE tasks ADD COLUMN fail_reason TEXT NULL AFTER max_retries;
ALTER TABLE tasks ADD COLUMN next_retry_at DATETIME NULL AFTER fail_reason;
ALTER TABLE tasks ADD COLUMN original_task_id VARCHAR(36) NULL AFTER next_retry_at;
ALTER TABLE tasks ADD COLUMN max_concurrent INT NOT NULL DEFAULT 3 AFTER original_task_id;
ALTER TABLE tasks ADD COLUMN organic_only TINYINT NOT NULL DEFAULT 0 AFTER max_concurrent;
ALTER TABLE tasks ADD INDEX idx_tasks_retry (status, next_retry_at);
DESC tasks;
