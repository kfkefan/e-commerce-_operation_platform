import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import request from 'supertest';
import express from 'express';
import tasksRouter from '../../../src/server/routes/tasks';
import { databaseService } from '../../../src/services/database';

// 创建测试 Express 应用
function createTestApp() {
  const app = express();
  app.use(express.json());
  app.use('/api/tasks', tasksRouter);
  return app;
}

describe('Tasks API Integration', () => {
  let app: express.Express;
  let testTaskId: string;

  beforeEach(() => {
    app = createTestApp();
    testTaskId = '';
  });

  afterEach(async () => {
    // 清理测试数据
    if (testTaskId) {
      const db = databaseService.getDb();
      db.prepare('DELETE FROM task_results WHERE task_id = ?').run(testTaskId);
      db.prepare('DELETE FROM task_keywords WHERE task_id = ?').run(testTaskId);
      db.prepare('DELETE FROM tasks WHERE task_id = ?').run(testTaskId);
    }
  });

  describe('POST /api/tasks - 创建任务', () => {
    it('应该成功创建任务', async () => {
      const response = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'B08N5WRWNW',
          keywords: ['wireless earbuds', 'bluetooth headphones'],
          maxPages: 5
        });

      expect(response.status).toBe(201);
      expect(response.body.taskId).toBeDefined();
      expect(response.body.status).toBe('created');
      expect(response.body.message).toBe('任务创建成功，已开始处理');

      testTaskId = response.body.taskId;
    });

    it('应该返回 400 当 ASIN 格式错误', async () => {
      const response = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'B08N5WRW', // 只有 8 位
          keywords: ['test'],
          maxPages: 5
        });

      expect(response.status).toBe(400);
      expect(response.body.errorCode).toBeDefined();
      expect(response.body.message).toContain('ASIN');
    });

    it('应该返回 400 当关键词为空', async () => {
      const response = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'B08N5WRWNW',
          keywords: [],
          maxPages: 5
        });

      expect(response.status).toBe(400);
      expect(response.body.message).toContain('关键词');
    });

    it('应该返回 400 当关键词超过 100 个', async () => {
      const response = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'B08N5WRWNW',
          keywords: Array(101).fill('test'),
          maxPages: 5
        });

      expect(response.status).toBe(400);
      expect(response.body.message).toContain('100');
    });

    it('应该返回 400 当翻页数超出范围', async () => {
      const response = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'B08N5WRWNW',
          keywords: ['test'],
          maxPages: 100 // 超出 1-50 范围
        });

      expect(response.status).toBe(400);
      expect(response.body.message).toContain('翻页数');
    });

    it('应该返回 400 当翻页数小于 1', async () => {
      const response = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'B08N5WRWNW',
          keywords: ['test'],
          maxPages: 0
        });

      expect(response.status).toBe(400);
    });

    it('应该接受有效的站点参数', async () => {
      const response = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'B08N5WRWNW',
          keywords: ['test'],
          maxPages: 5,
          site: 'amazon.co.uk'
        });

      expect(response.status).toBe(201);
      testTaskId = response.body.taskId;
    });

    it('应该返回 400 当站点参数无效', async () => {
      const response = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'B08N5WRWNW',
          keywords: ['test'],
          maxPages: 5,
          site: 'amazon.invalid'
        });

      expect(response.status).toBe(400);
    });

    it('应该处理关键词前后空格', async () => {
      const response = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'B08N5WRWNW',
          keywords: ['  test keyword  '],
          maxPages: 5
        });

      expect(response.status).toBe(201);
      testTaskId = response.body.taskId;
    });
  });

  describe('GET /api/tasks - 获取任务列表', () => {
    it('应该获取任务列表', async () => {
      // 先创建一些任务
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = createResponse.body.taskId;

      const response = await request(app).get('/api/tasks');

      expect(response.status).toBe(200);
      expect(response.body.tasks).toBeDefined();
      expect(response.body.pagination).toBeDefined();
      expect(Array.isArray(response.body.tasks)).toBe(true);
    });

    it('应该支持分页参数', async () => {
      const response = await request(app)
        .get('/api/tasks')
        .query({ page: 1, pageSize: 10 });

      expect(response.status).toBe(200);
      expect(response.body.pagination.page).toBe(1);
      expect(response.body.pagination.pageSize).toBe(10);
    });

    it('应该支持状态筛选', async () => {
      const response = await request(app)
        .get('/api/tasks')
        .query({ status: 'created' });

      expect(response.status).toBe(200);
    });

    it('应该返回 400 当页码小于 1', async () => {
      const response = await request(app)
        .get('/api/tasks')
        .query({ page: 0 });

      expect(response.status).toBe(400);
    });

    it('应该返回 400 当 pageSize 超出范围', async () => {
      const response = await request(app)
        .get('/api/tasks')
        .query({ pageSize: 200 });

      expect(response.status).toBe(400);
    });

    it('应该返回 400 当状态参数无效', async () => {
      const response = await request(app)
        .get('/api/tasks')
        .query({ status: 'invalid_status' });

      expect(response.status).toBe(400);
    });
  });

  describe('GET /api/tasks/:taskId - 获取任务详情', () => {
    it('应该获取任务详情', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 5 });
      testTaskId = createResponse.body.taskId;

      const response = await request(app).get(`/api/tasks/${testTaskId}`);

      expect(response.status).toBe(200);
      expect(response.body.taskId).toBe(testTaskId);
      expect(response.body.asin).toBe('B08N5WRWNW');
      expect(response.body.progressPercentage).toBeDefined();
    });

    it('应该返回 404 当任务不存在', async () => {
      const response = await request(app).get('/api/tasks/non-existent-id');

      expect(response.status).toBe(404);
      expect(response.body.errorCode).toBeDefined();
    });
  });

  describe('POST /api/tasks/:taskId/pause - 暂停任务', () => {
    it('应该暂停运行中的任务', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = createResponse.body.taskId;

      // 先设置为运行状态
      const db = databaseService.getDb();
      db.prepare("UPDATE tasks SET status = 'running' WHERE task_id = ?").run(testTaskId);

      const response = await request(app).post(`/api/tasks/${testTaskId}/pause`);

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('paused');
    });

    it('应该返回 400 当任务不是运行状态', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = createResponse.body.taskId;

      const response = await request(app).post(`/api/tasks/${testTaskId}/pause`);

      expect(response.status).toBe(400);
      expect(response.body.message).toContain('运行中');
    });

    it('应该返回 404 当任务不存在', async () => {
      const response = await request(app).post('/api/tasks/non-existent-id/pause');

      expect(response.status).toBe(404);
    });
  });

  describe('POST /api/tasks/:taskId/resume - 继续任务', () => {
    it('应该继续暂停的任务', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = createResponse.body.taskId;

      // 先设置为暂停状态
      const db = databaseService.getDb();
      db.prepare("UPDATE tasks SET status = 'paused' WHERE task_id = ?").run(testTaskId);

      const response = await request(app).post(`/api/tasks/${testTaskId}/resume`);

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('running');
    });

    it('应该返回 400 当任务不是暂停状态', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = createResponse.body.taskId;

      const response = await request(app).post(`/api/tasks/${testTaskId}/resume`);

      expect(response.status).toBe(400);
      expect(response.body.message).toContain('暂停');
    });

    it('应该返回 404 当任务不存在', async () => {
      const response = await request(app).post('/api/tasks/non-existent-id/resume');

      expect(response.status).toBe(404);
    });
  });

  describe('POST /api/tasks/:taskId/cancel - 取消任务', () => {
    it('应该取消运行中的任务', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = createResponse.body.taskId;

      // 先设置为运行状态
      const db = databaseService.getDb();
      db.prepare("UPDATE tasks SET status = 'running' WHERE task_id = ?").run(testTaskId);

      const response = await request(app).post(`/api/tasks/${testTaskId}/cancel`);

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('failed');
      expect(response.body.message).toBe('任务已取消');
    });

    it('应该取消暂停的任务', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = createResponse.body.taskId;

      const db = databaseService.getDb();
      db.prepare("UPDATE tasks SET status = 'paused' WHERE task_id = ?").run(testTaskId);

      const response = await request(app).post(`/api/tasks/${testTaskId}/cancel`);

      expect(response.status).toBe(200);
    });

    it('应该返回 400 当任务已完成', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = createResponse.body.taskId;

      const db = databaseService.getDb();
      db.prepare("UPDATE tasks SET status = 'completed' WHERE task_id = ?").run(testTaskId);

      const response = await request(app).post(`/api/tasks/${testTaskId}/cancel`);

      expect(response.status).toBe(400);
    });

    it('应该返回 404 当任务不存在', async () => {
      const response = await request(app).post('/api/tasks/non-existent-id/cancel');

      expect(response.status).toBe(404);
    });
  });

  describe('GET /api/tasks/:taskId/results - 获取任务结果', () => {
    it('应该获取任务结果', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = createResponse.body.taskId;

      const response = await request(app).get(`/api/tasks/${testTaskId}/results`);

      expect(response.status).toBe(200);
      expect(response.body.results).toBeDefined();
      expect(response.body.pagination).toBeDefined();
    });

    it('应该支持分页参数', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = createResponse.body.taskId;

      const response = await request(app)
        .get(`/api/tasks/${testTaskId}/results`)
        .query({ page: 1, pageSize: 20 });

      expect(response.status).toBe(200);
      expect(response.body.pagination.page).toBe(1);
      expect(response.body.pagination.pageSize).toBe(20);
    });

    it('应该支持状态筛选', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = createResponse.body.taskId;

      const response = await request(app)
        .get(`/api/tasks/${testTaskId}/results`)
        .query({ status: 'not_found' });

      expect(response.status).toBe(200);
    });

    it('应该支持排序参数', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = createResponse.body.taskId;

      const response = await request(app)
        .get(`/api/tasks/${testTaskId}/results`)
        .query({ sortBy: 'keyword', sortOrder: 'asc' });

      expect(response.status).toBe(200);
    });

    it('应该返回 404 当任务不存在', async () => {
      const response = await request(app).get('/api/tasks/non-existent-id/results');

      expect(response.status).toBe(404);
    });

    it('应该返回 400 当排序字段无效', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = createResponse.body.taskId;

      const response = await request(app)
        .get(`/api/tasks/${testTaskId}/results`)
        .query({ sortBy: 'invalid_field' });

      expect(response.status).toBe(400);
    });
  });

  describe('GET /api/tasks/:taskId/export - 导出数据', () => {
    it('应该返回 400 当任务未完成', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = createResponse.body.taskId;

      const response = await request(app).get(`/api/tasks/${testTaskId}/export`);

      expect(response.status).toBe(400);
      expect(response.body.message).toContain('未完成');
    });

    it('应该返回 404 当任务不存在', async () => {
      const response = await request(app).get('/api/tasks/non-existent-id/export');

      expect(response.status).toBe(404);
    });

    it('应该支持 CSV 格式参数', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({ asin: 'B08N5WRWNW', keywords: ['test'], maxPages: 1 });
      testTaskId = createResponse.body.taskId;

      // 先设置为完成状态
      const db = databaseService.getDb();
      db.prepare("UPDATE tasks SET status = 'completed' WHERE task_id = ?").run(testTaskId);

      const response = await request(app)
        .get(`/api/tasks/${testTaskId}/export`)
        .query({ format: 'csv' });

      expect(response.status).toBe(200);
      expect(response.headers['content-type']).toContain('text/csv');
    });
  });
});
