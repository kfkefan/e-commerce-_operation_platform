import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { TaskService } from '../../../src/services/taskService';
import { databaseService, DatabaseService } from '../../../src/services/database';
import type { Task } from '../../../src/services/taskService';
import Database from 'better-sqlite3';

// 使用内存数据库进行测试
vi.mock('../../../src/services/database', async () => {
  const actual = await vi.importActual('../../../src/services/database');
  const memDb = new Database(':memory:');
  
  // 初始化表结构
  memDb.exec(`
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
    )
  `);

  memDb.exec(`
    CREATE TABLE IF NOT EXISTS task_keywords (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      task_id VARCHAR(36) NOT NULL,
      keyword VARCHAR(100) NOT NULL,
      sort_order INTEGER NOT NULL,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
    )
  `);

  memDb.exec(`
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
    )
  `);

  memDb.exec(`
    CREATE TABLE IF NOT EXISTS history (
      task_id VARCHAR(36) PRIMARY KEY,
      asin VARCHAR(10) NOT NULL,
      keyword_count INTEGER NOT NULL,
      status VARCHAR(20) NOT NULL,
      created_at TIMESTAMP NOT NULL,
      completed_at TIMESTAMP,
      FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
    )
  `);

  memDb.exec(`
    CREATE TABLE IF NOT EXISTS history_snapshots (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      task_id VARCHAR(36) NOT NULL,
      snapshot_data TEXT,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
    )
  `);

  const mockService = {
    connect: vi.fn().mockReturnValue(memDb),
    getDb: vi.fn().mockReturnValue(memDb),
    close: vi.fn(),
    transaction: vi.fn((fn) => fn())
  };

  return {
    ...actual,
    databaseService: mockService,
    DatabaseService: vi.fn().mockImplementation(() => mockService)
  };
});

describe('TaskService', () => {
  let taskService: TaskService;
  let testTaskId: string;

  beforeEach(() => {
    taskService = new TaskService();
    testTaskId = '';
  });

  afterEach(() => {
    // 清理测试数据
    if (testTaskId) {
      const db = databaseService.getDb();
      try {
        db.prepare('DELETE FROM task_results WHERE task_id = ?').run(testTaskId);
        db.prepare('DELETE FROM task_keywords WHERE task_id = ?').run(testTaskId);
        db.prepare('DELETE FROM tasks WHERE task_id = ?').run(testTaskId);
      } catch (e) {
        // 忽略清理错误
      }
    }
  });

  describe('createTask', () => {
    it('应该成功创建任务', async () => {
      const params = {
        asin: 'B08N5WRWNW',
        keywords: ['wireless earbuds', 'bluetooth headphones'],
        maxPages: 5,
        site: 'amazon.com'
      };

      const task = await taskService.createTask(params);

      expect(task).toBeDefined();
      expect(task.taskId).toBeDefined();
      expect(task.asin).toBe('B08N5WRWNW');
      expect(task.site).toBe('amazon.com');
      expect(task.maxPages).toBe(5);
      expect(task.totalKeywords).toBe(2);
      expect(task.processedKeywords).toBe(0);
      expect(task.status).toBe('created');

      testTaskId = task.taskId;
    });

    it('应该将 ASIN 转换为大写', async () => {
      const params = {
        asin: 'b08n5wrwnw',
        keywords: ['test keyword'],
        maxPages: 3
      };

      const task = await taskService.createTask(params);
      expect(task.asin).toBe('B08N5WRWNW');
      testTaskId = task.taskId;
    });

    it('应该使用默认站点当未指定', async () => {
      const params = {
        asin: 'B08N5WRWNW',
        keywords: ['test'],
        maxPages: 1
      };

      const task = await taskService.createTask(params);
      expect(task.site).toBe('amazon.com');
      testTaskId = task.taskId;
    });

    it('应该处理单个关键词', async () => {
      const params = {
        asin: 'B08N5WRWNW',
        keywords: ['single keyword'],
        maxPages: 1
      };

      const task = await taskService.createTask(params);
      expect(task.totalKeywords).toBe(1);
      testTaskId = task.taskId;
    });

    it('应该处理大量关键词', async () => {
      const keywords = Array.from({ length: 100 }, (_, i) => `keyword ${i}`);
      const params = {
        asin: 'B08N5WRWNW',
        keywords,
        maxPages: 1
      };

      const task = await taskService.createTask(params);
      expect(task.totalKeywords).toBe(100);
      testTaskId = task.taskId;
    });

    it('应该去除关键词前后空格', async () => {
      const params = {
        asin: 'B08N5WRWNW',
        keywords: ['  keyword with spaces  ', 'normal keyword'],
        maxPages: 1
      };

      const task = await taskService.createTask(params);
      testTaskId = task.taskId;
      
      const db = databaseService.getDb();
      const keywords = db.prepare('SELECT keyword FROM task_keywords WHERE task_id = ? ORDER BY sort_order').all(testTaskId);
      expect(keywords[0].keyword).toBe('keyword with spaces');
    });

    it('应该生成唯一的 taskId', async () => {
      const params1 = { asin: 'B08N5WRWNW', keywords: ['test1'], maxPages: 1 };
      const params2 = { asin: 'B08N5WRWNW', keywords: ['test2'], maxPages: 1 };

      const task1 = await taskService.createTask(params1);
      const task2 = await taskService.createTask(params2);

      expect(task1.taskId).not.toBe(task2.taskId);
      testTaskId = task1.taskId;
    });

    it('应该设置正确的时间戳', async () => {
      const beforeCreate = new Date().getTime();
      const task = await taskService.createTask({
        asin: 'B08N5WRWNW',
        keywords: ['test'],
        maxPages: 1
      });
      const afterCreate = new Date().getTime();

      const taskCreatedAt = new Date(task.createdAt).getTime();
      expect(taskCreatedAt).toBeGreaterThanOrEqual(beforeCreate);
      expect(taskCreatedAt).toBeLessThanOrEqual(afterCreate);
      testTaskId = task.taskId;
    });
  });

  describe('getTask', () => {
    it('应该获取存在的任务', async () => {
      const createParams = { asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 };
      const createdTask = await taskService.createTask(createParams);
      testTaskId = createdTask.taskId;

      const task = taskService.getTask(testTaskId);

      expect(task).toBeDefined();
      expect(task?.taskId).toBe(testTaskId);
      expect(task?.asin).toBe('B08N5WRWNW');
    });

    it('应该返回 null 当任务不存在', () => {
      const task = taskService.getTask('non-existent-id');
      expect(task).toBeNull();
    });
  });

  describe('getTaskDetail', () => {
    it('应该获取任务详情包含进度信息', async () => {
      const createParams = { asin: 'B08N5WRWNW', keywords: ['test1', 'test2'], maxPages: 1 };
      const createdTask = await taskService.createTask(createParams);
      testTaskId = createdTask.taskId;

      const detail = taskService.getTaskDetail(testTaskId);

      expect(detail).toBeDefined();
      expect(detail?.progressPercentage).toBe(0);
      expect(detail?.totalKeywords).toBe(2);
    });

    it('应该计算正确的进度百分比', async () => {
      const createParams = { asin: 'B08N5WRWNW', keywords: Array(10).fill('test'), maxPages: 1 };
      const createdTask = await taskService.createTask(createParams);
      testTaskId = createdTask.taskId;

      taskService.updateTaskProgress(testTaskId, 5);

      const detail = taskService.getTaskDetail(testTaskId);
      expect(detail?.progressPercentage).toBe(50);
    });

    it('应该返回 null 当任务不存在', () => {
      const detail = taskService.getTaskDetail('non-existent-id');
      expect(detail).toBeNull();
    });

    it('应该估算剩余时间', async () => {
      const createParams = { asin: 'B08N5WRWNW', keywords: Array(10).fill('test'), maxPages: 1 };
      const createdTask = await taskService.createTask(createParams);
      testTaskId = createdTask.taskId;

      taskService.updateTaskStatus(testTaskId, 'running');
      taskService.updateTaskProgress(testTaskId, 5);

      const detail = taskService.getTaskDetail(testTaskId);
      expect(detail?.estimatedRemainingSeconds).toBeDefined();
      expect(detail?.estimatedRemainingSeconds).toBeGreaterThan(0);
    });
  });

  describe('getTaskList', () => {
    it('应该获取任务列表', async () => {
      await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test1'], maxPages: 1 });
      await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test2'], maxPages: 1 });

      const result = taskService.getTaskList();

      expect(result.tasks.length).toBeGreaterThanOrEqual(2);
      expect(result.total).toBeGreaterThanOrEqual(2);
      expect(result.totalPages).toBeGreaterThanOrEqual(1);
    });

    it('应该支持分页', async () => {
      for (let i = 0; i < 5; i++) {
        await taskService.createTask({ asin: 'B08N5WRWNW', keywords: [`test${i}`], maxPages: 1 });
      }

      const page1 = taskService.getTaskList({ page: 1, pageSize: 2 });
      const page2 = taskService.getTaskList({ page: 2, pageSize: 2 });

      expect(page1.tasks.length).toBe(2);
      expect(page2.tasks.length).toBe(2);
      expect(page1.tasks[0].taskId).not.toBe(page2.tasks[0].taskId);
    });

    it('应该支持状态筛选', async () => {
      const task1 = await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test1'], maxPages: 1 });
      const task2 = await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test2'], maxPages: 1 });
      
      taskService.updateTaskStatus(task2.taskId, 'completed');

      const createdTasks = taskService.getTaskList({ status: 'created' });
      const completedTasks = taskService.getTaskList({ status: 'completed' });

      expect(createdTasks.tasks.some(t => t.taskId === task1.taskId)).toBe(true);
      expect(completedTasks.tasks.some(t => t.taskId === task2.taskId)).toBe(true);
    });
  });

  describe('updateTaskStatus', () => {
    it('应该更新任务状态', async () => {
      const task = await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = task.taskId;

      const success = taskService.updateTaskStatus(testTaskId, 'running');
      expect(success).toBe(true);

      const updatedTask = taskService.getTask(testTaskId);
      expect(updatedTask?.status).toBe('running');
    });

    it('应该设置 startedAt 当状态变为 running', async () => {
      const task = await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = task.taskId;

      taskService.updateTaskStatus(testTaskId, 'running');

      const updatedTask = taskService.getTask(testTaskId);
      expect(updatedTask?.startedAt).toBeDefined();
    });

    it('应该设置 completedAt 当状态变为 completed', async () => {
      const task = await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = task.taskId;

      taskService.updateTaskStatus(testTaskId, 'completed');

      const updatedTask = taskService.getTask(testTaskId);
      expect(updatedTask?.completedAt).toBeDefined();
    });

    it('应该设置 errorMessage 当状态变为 failed', async () => {
      const task = await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = task.taskId;

      taskService.updateTaskStatus(testTaskId, 'failed', 'Test error message');

      const updatedTask = taskService.getTask(testTaskId);
      expect(updatedTask?.status).toBe('failed');
      expect(updatedTask?.errorMessage).toBe('Test error message');
    });

    it('应该返回 false 当任务不存在', () => {
      const success = taskService.updateTaskStatus('non-existent-id', 'running');
      expect(success).toBe(false);
    });
  });

  describe('updateTaskProgress', () => {
    it('应该更新任务进度', async () => {
      const task = await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = task.taskId;

      const success = taskService.updateTaskProgress(testTaskId, 1);
      expect(success).toBe(true);

      const updatedTask = taskService.getTask(testTaskId);
      expect(updatedTask?.processedKeywords).toBe(1);
    });

    it('应该返回 false 当任务不存在', () => {
      const success = taskService.updateTaskProgress('non-existent-id', 1);
      expect(success).toBe(false);
    });
  });

  describe('pauseTask', () => {
    it('应该暂停运行中的任务', async () => {
      const task = await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = task.taskId;

      taskService.updateTaskStatus(testTaskId, 'running');

      const success = taskService.pauseTask(testTaskId);
      expect(success).toBe(true);

      const updatedTask = taskService.getTask(testTaskId);
      expect(updatedTask?.status).toBe('paused');
    });

    it('应该返回 false 当任务不是运行状态', async () => {
      const task = await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = task.taskId;

      const success = taskService.pauseTask(testTaskId);
      expect(success).toBe(false);
    });

    it('应该返回 false 当任务不存在', () => {
      const success = taskService.pauseTask('non-existent-id');
      expect(success).toBe(false);
    });
  });

  describe('resumeTask', () => {
    it('应该继续暂停的任务', async () => {
      const task = await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = task.taskId;

      taskService.updateTaskStatus(testTaskId, 'running');
      taskService.pauseTask(testTaskId);

      const success = taskService.resumeTask(testTaskId);
      expect(success).toBe(true);

      const updatedTask = taskService.getTask(testTaskId);
      expect(updatedTask?.status).toBe('running');
    });

    it('应该返回 false 当任务不是暂停状态', async () => {
      const task = await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = task.taskId;

      const success = taskService.resumeTask(testTaskId);
      expect(success).toBe(false);
    });

    it('应该返回 false 当任务不存在', () => {
      const success = taskService.resumeTask('non-existent-id');
      expect(success).toBe(false);
    });
  });

  describe('cancelTask', () => {
    it('应该取消运行中的任务', async () => {
      const task = await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = task.taskId;

      taskService.updateTaskStatus(testTaskId, 'running');

      const success = taskService.cancelTask(testTaskId);
      expect(success).toBe(true);

      const updatedTask = taskService.getTask(testTaskId);
      expect(updatedTask?.status).toBe('failed');
      expect(updatedTask?.errorMessage).toBe('用户取消任务');
    });

    it('应该取消暂停的任务', async () => {
      const task = await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = task.taskId;

      taskService.updateTaskStatus(testTaskId, 'running');
      taskService.pauseTask(testTaskId);

      const success = taskService.cancelTask(testTaskId);
      expect(success).toBe(true);
    });

    it('应该返回 false 当任务已完成', async () => {
      const task = await taskService.createTask({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = task.taskId;

      taskService.updateTaskStatus(testTaskId, 'completed');

      const success = taskService.cancelTask(testTaskId);
      expect(success).toBe(false);
    });

    it('应该返回 false 当任务不存在', () => {
      const success = taskService.cancelTask('non-existent-id');
      expect(success).toBe(false);
    });
  });

  describe('边界条件测试', () => {
    it('应该处理空关键词列表', async () => {
      const params = {
        asin: 'B08N5WRWNW',
        keywords: [],
        maxPages: 1
      };

      const task = await taskService.createTask(params);
      expect(task.totalKeywords).toBe(0);
      testTaskId = task.taskId;
    });

    it('应该处理超长关键词', async () => {
      const longKeyword = 'a'.repeat(100);
      const params = {
        asin: 'B08N5WRWNW',
        keywords: [longKeyword],
        maxPages: 1
      };

      const task = await taskService.createTask(params);
      expect(task.totalKeywords).toBe(1);
      testTaskId = task.taskId;
    });

    it('应该处理最大翻页数', async () => {
      const params = {
        asin: 'B08N5WRWNW',
        keywords: ['test'],
        maxPages: 50
      };

      const task = await taskService.createTask(params);
      expect(task.maxPages).toBe(50);
      testTaskId = task.taskId;
    });

    it('应该处理特殊字符 ASIN', async () => {
      const params = {
        asin: 'B08N5WRWNW',
        keywords: ['test & special <chars>'],
        maxPages: 1
      };

      const task = await taskService.createTask(params);
      testTaskId = task.taskId;
      
      const db = databaseService.getDb();
      const keywords = db.prepare('SELECT keyword FROM task_keywords WHERE task_id = ?').all(testTaskId);
      expect(keywords[0].keyword).toBe('test & special <chars>');
    });
  });
});
