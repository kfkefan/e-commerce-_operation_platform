import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import request from 'supertest';
import express from 'express';
import tasksRouter from '../../../src/server/routes/tasks';
import { databaseService } from '../../../src/services/database';
import { TaskService } from '../../../src/services/taskService';

// 创建测试 Express 应用
function createTestApp() {
  const app = express();
  app.use(express.json());
  app.use('/api/tasks', tasksRouter);
  return app;
}

describe('E2E Flow Test', () => {
  let app: express.Express;
  let taskService: TaskService;
  let testTaskId: string;

  beforeEach(() => {
    app = createTestApp();
    taskService = new TaskService();
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

  describe('完整流程：提交任务 → 查询状态 → 获取结果', () => {
    it('应该完成完整的任务流程', async () => {
      // 步骤 1: 提交任务
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'B08N5WRWNW',
          keywords: ['wireless earbuds', 'bluetooth headphones', 'noise cancelling earbuds'],
          maxPages: 5,
          site: 'amazon.com'
        });

      expect(createResponse.status).toBe(201);
      expect(createResponse.body.taskId).toBeDefined();
      expect(createResponse.body.status).toBe('created');

      testTaskId = createResponse.body.taskId;

      // 步骤 2: 查询任务状态
      const statusResponse = await request(app)
        .get(`/api/tasks/${testTaskId}`);

      expect(statusResponse.status).toBe(200);
      expect(statusResponse.body.taskId).toBe(testTaskId);
      expect(statusResponse.body.asin).toBe('B08N5WRWNW');
      expect(statusResponse.body.totalKeywords).toBe(3);
      expect(statusResponse.body.status).toBeDefined();
      expect(statusResponse.body.progressPercentage).toBeDefined();

      // 步骤 3: 获取任务结果（初始应为空）
      const resultsResponse = await request(app)
        .get(`/api/tasks/${testTaskId}/results`);

      expect(resultsResponse.status).toBe(200);
      expect(resultsResponse.body.results).toBeDefined();
      expect(resultsResponse.body.pagination).toBeDefined();

      // 步骤 4: 手动更新任务状态模拟处理完成
      taskService.updateTaskStatus(testTaskId, 'completed');
      taskService.updateTaskProgress(testTaskId, 3);

      // 保存模拟结果
      const db = databaseService.getDb();
      const insertResult = db.prepare(`
        INSERT INTO task_results (
          task_id, keyword_id, keyword,
          organic_page, organic_position,
          ad_page, ad_position,
          status, processed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      `);

      insertResult.run(
        testTaskId, 1, 'wireless earbuds',
        1, 5, null, null, 'organic_only',
        new Date().toISOString()
      );

      insertResult.run(
        testTaskId, 2, 'bluetooth headphones',
        2, 3, 1, 2, 'found',
        new Date().toISOString()
      );

      insertResult.run(
        testTaskId, 3, 'noise cancelling earbuds',
        null, null, null, null, 'not_found',
        new Date().toISOString()
      );

      // 步骤 5: 再次查询任务状态（应为完成）
      const finalStatusResponse = await request(app)
        .get(`/api/tasks/${testTaskId}`);

      expect(finalStatusResponse.status).toBe(200);
      expect(finalStatusResponse.body.status).toBe('completed');
      expect(finalStatusResponse.body.processedKeywords).toBe(3);
      expect(finalStatusResponse.body.progressPercentage).toBe(100);

      // 步骤 6: 获取最终结果
      const finalResultsResponse = await request(app)
        .get(`/api/tasks/${testTaskId}/results`);

      expect(finalResultsResponse.status).toBe(200);
      expect(finalResultsResponse.body.results.length).toBe(3);
      expect(finalResultsResponse.body.results[0].keyword).toBe('wireless earbuds');
      expect(finalResultsResponse.body.results[0].organic_page).toBe(1);
      expect(finalResultsResponse.body.results[0].organic_position).toBe(5);
      expect(finalResultsResponse.body.results[0].status).toBe('organic_only');

      // 步骤 7: 筛选结果
      const filteredResponse = await request(app)
        .get(`/api/tasks/${testTaskId}/results`)
        .query({ status: 'found' });

      expect(filteredResponse.status).toBe(200);
      expect(filteredResponse.body.results.length).toBe(1);
      expect(filteredResponse.body.results[0].keyword).toBe('bluetooth headphones');

      // 步骤 8: 排序结果
      const sortedResponse = await request(app)
        .get(`/api/tasks/${testTaskId}/results`)
        .query({ sortBy: 'organic_page', sortOrder: 'asc' });

      expect(sortedResponse.status).toBe(200);
      expect(sortedResponse.body.results[0].keyword).toBe('wireless earbuds'); // organic_page=1

      // 步骤 9: 尝试导出（应该成功因为任务已完成）
      const exportResponse = await request(app)
        .get(`/api/tasks/${testTaskId}/export`)
        .query({ format: 'csv' });

      expect(exportResponse.status).toBe(200);
      expect(exportResponse.headers['content-type']).toContain('text/csv');
      expect(exportResponse.text).toContain('关键词');
    });

    it('应该处理任务暂停和继续流程', async () => {
      // 步骤 1: 创建任务
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'B08N5WRWNW',
          keywords: ['test keyword 1', 'test keyword 2'],
          maxPages: 3
        });

      expect(createResponse.status).toBe(201);
      testTaskId = createResponse.body.taskId;

      // 步骤 2: 设置为运行状态
      taskService.updateTaskStatus(testTaskId, 'running');

      // 步骤 3: 暂停任务
      const pauseResponse = await request(app)
        .post(`/api/tasks/${testTaskId}/pause`);

      expect(pauseResponse.status).toBe(200);
      expect(pauseResponse.body.status).toBe('paused');

      // 步骤 4: 验证暂停状态
      const pausedStatusResponse = await request(app)
        .get(`/api/tasks/${testTaskId}`);

      expect(pausedStatusResponse.body.status).toBe('paused');

      // 步骤 5: 继续任务
      const resumeResponse = await request(app)
        .post(`/api/tasks/${testTaskId}/resume`);

      expect(resumeResponse.status).toBe(200);
      expect(resumeResponse.body.status).toBe('running');

      // 步骤 6: 验证运行状态
      const resumedStatusResponse = await request(app)
        .get(`/api/tasks/${testTaskId}`);

      expect(resumedStatusResponse.body.status).toBe('running');
    });

    it('应该处理任务取消流程', async () => {
      // 步骤 1: 创建任务
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'B08N5WRWNW',
          keywords: ['test keyword'],
          maxPages: 1
        });

      expect(createResponse.status).toBe(201);
      testTaskId = createResponse.body.taskId;

      // 步骤 2: 设置为运行状态
      taskService.updateTaskStatus(testTaskId, 'running');

      // 步骤 3: 取消任务
      const cancelResponse = await request(app)
        .post(`/api/tasks/${testTaskId}/cancel`);

      expect(cancelResponse.status).toBe(200);
      expect(cancelResponse.body.status).toBe('failed');
      expect(cancelResponse.body.message).toBe('任务已取消');

      // 步骤 4: 验证取消状态
      const cancelledStatusResponse = await request(app)
        .get(`/api/tasks/${testTaskId}`);

      expect(cancelledStatusResponse.body.status).toBe('failed');
      expect(cancelledStatusResponse.body.errorMessage).toBe('用户取消任务');
    });

    it('应该处理任务列表分页', async () => {
      // 创建多个任务
      const taskIds: string[] = [];
      for (let i = 0; i < 5; i++) {
        const createResponse = await request(app)
          .post('/api/tasks')
          .send({
            asin: 'B08N5WRWNW',
            keywords: [`test keyword ${i}`],
            maxPages: 1
          });
        taskIds.push(createResponse.body.taskId);
      }

      // 测试分页
      const page1Response = await request(app)
        .get('/api/tasks')
        .query({ page: 1, pageSize: 2 });

      expect(page1Response.status).toBe(200);
      expect(page1Response.body.tasks.length).toBe(2);
      expect(page1Response.body.pagination.page).toBe(1);
      expect(page1Response.body.pagination.pageSize).toBe(2);
      expect(page1Response.body.pagination.total).toBeGreaterThanOrEqual(5);

      const page2Response = await request(app)
        .get('/api/tasks')
        .query({ page: 2, pageSize: 2 });

      expect(page2Response.status).toBe(200);
      expect(page2Response.body.tasks.length).toBe(2);
      expect(page2Response.body.pagination.page).toBe(2);

      // 验证不同页的任务不同
      expect(page1Response.body.tasks[0].taskId)
        .not.toBe(page2Response.body.tasks[0].taskId);
    });

    it('应该处理并发任务', async () => {
      // 并发创建多个任务
      const createPromises = Array.from({ length: 3 }, (_, i) =>
        request(app)
          .post('/api/tasks')
          .send({
            asin: 'B08N5WRWNW',
            keywords: [`concurrent test ${i}`],
            maxPages: 1
          })
      );

      const responses = await Promise.all(createPromises);

      responses.forEach(response => {
        expect(response.status).toBe(201);
        expect(response.body.taskId).toBeDefined();
      });

      // 验证所有任务都已创建
      const listResponse = await request(app).get('/api/tasks');
      expect(listResponse.body.tasks.length).toBeGreaterThanOrEqual(3);
    });
  });

  describe('错误处理流程', () => {
    it('应该处理无效 ASIN 格式', async () => {
      const response = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'INVALID', // 不是 10 位
          keywords: ['test'],
          maxPages: 1
        });

      expect(response.status).toBe(400);
      expect(response.body.errorCode).toBeDefined();
    });

    it('应该处理不存在任务的操作', async () => {
      const fakeTaskId = '00000000-0000-0000-0000-000000000000';

      const getResponse = await request(app).get(`/api/tasks/${fakeTaskId}`);
      expect(getResponse.status).toBe(404);

      const pauseResponse = await request(app).post(`/api/tasks/${fakeTaskId}/pause`);
      expect(pauseResponse.status).toBe(404);

      const cancelResponse = await request(app).post(`/api/tasks/${fakeTaskId}/cancel`);
      expect(cancelResponse.status).toBe(404);
    });

    it('应该处理无效状态转换', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'B08N5WRWNW',
          keywords: ['test'],
          maxPages: 1
        });

      testTaskId = createResponse.body.taskId;

      // 尝试暂停 created 状态的任务（应该失败）
      const pauseResponse = await request(app)
        .post(`/api/tasks/${testTaskId}/pause`);

      expect(pauseResponse.status).toBe(400);
      expect(pauseResponse.body.message).toContain('运行中');

      // 尝试继续 created 状态的任务（应该失败）
      const resumeResponse = await request(app)
        .post(`/api/tasks/${testTaskId}/resume`);

      expect(resumeResponse.status).toBe(400);
      expect(resumeResponse.body.message).toContain('暂停');
    });

    it('应该处理无效分页参数', async () => {
      const response = await request(app)
        .get('/api/tasks')
        .query({ page: -1, pageSize: 0 });

      expect(response.status).toBe(400);
    });
  });

  describe('数据一致性测试', () => {
    it('应该保持任务状态一致性', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'B08N5WRWNW',
          keywords: ['test'],
          maxPages: 1
        });

      testTaskId = createResponse.body.taskId;

      // 获取任务详情
      const detailResponse = await request(app).get(`/api/tasks/${testTaskId}`);
      const detailBody = detailResponse.body;

      // 验证任务列表中的任务与详情一致
      const listResponse = await request(app)
        .get('/api/tasks')
        .query({ pageSize: 100 });

      const taskInList = listResponse.body.tasks.find(
        (t: any) => t.taskId === testTaskId
      );

      expect(taskInList).toBeDefined();
      expect(taskInList.asin).toBe(detailBody.asin);
      expect(taskInList.status).toBe(detailBody.status);
    });

    it('应该保持结果计数一致性', async () => {
      const createResponse = await request(app)
        .post('/api/tasks')
        .send({
          asin: 'B08N5WRWNW',
          keywords: ['test1', 'test2', 'test3'],
          maxPages: 1
        });

      testTaskId = createResponse.body.taskId;

      // 手动添加结果
      const db = databaseService.getDb();
      const insertResult = db.prepare(`
        INSERT INTO task_results (
          task_id, keyword_id, keyword, status, processed_at
        ) VALUES (?, ?, ?, ?, ?)
      `);

      for (let i = 0; i < 3; i++) {
        insertResult.run(
          testTaskId, i + 1, `test${i + 1}`, 'not_found', new Date().toISOString()
        );
      }

      // 验证结果数量
      const resultsResponse = await request(app)
        .get(`/api/tasks/${testTaskId}/results`)
        .query({ pageSize: 100 });

      expect(resultsResponse.body.results.length).toBe(3);
      expect(resultsResponse.body.pagination.total).toBe(3);
    });
  });
});
