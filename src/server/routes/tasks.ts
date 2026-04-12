import { Router, Request, Response } from 'express';
import { taskService } from '../../services/taskService';
import { asyncHandler, createError, AppError } from './middleware/errorHandler';
import { taskRateLimiter } from './middleware/rateLimiter';
import { z } from 'zod';

const router = Router();

/**
 * 创建任务请求验证 Schema
 */
const createTaskSchema = z.object({
  asin: z.string().regex(/^[A-Z0-9]{10}$/, 'ASIN 格式错误，应为 10 位字母数字组合'),
  keywords: z.array(z.string().min(2).max(100))
    .min(1, '请至少输入一个关键词')
    .max(100, '最多支持 100 个关键词'),
  maxPages: z.number().int().min(1).max(50, '翻页数必须在 1-50 之间'),
  site: z.enum([
    'amazon.com',
    'amazon.co.uk',
    'amazon.de',
    'amazon.fr',
    'amazon.co.jp',
    'amazon.cn'
  ]).optional().default('amazon.com')
});

/**
 * POST /tasks - 创建新任务
 */
router.post('/', 
  taskRateLimiter,
  asyncHandler(async (req: Request, res: Response) => {
    // 验证请求参数
    const validation = createTaskSchema.safeParse(req.body);
    
    if (!validation.success) {
      const errors = validation.error.errors.map(err => ({
        field: err.path.join('.'),
        message: err.message,
        value: req.body[err.path[0]]
      }));
      
      throw createError.badRequest('请求参数错误', { errors });
    }

    const { asin, keywords, maxPages, site } = validation.data;

    // 创建任务
    const task = await taskService.createTask({
      asin,
      keywords,
      maxPages,
      site
    });

    // 异步执行任务（不阻塞响应）
    taskService.executeTask(task.taskId).catch(error => {
      console.error(`任务执行失败：${task.taskId}`, error);
      taskService.updateTaskStatus(task.taskId, 'failed', error.message);
    });

    // 返回 201 Created
    res.status(201).json({
      taskId: task.taskId,
      status: task.status,
      message: '任务创建成功，已开始处理'
    });
  })
);

/**
 * GET /tasks - 获取任务列表
 */
router.get('/', 
  asyncHandler(async (req: Request, res: Response) => {
    const page = parseInt(req.query.page as string) || 1;
    const pageSize = parseInt(req.query.pageSize as string) || 20;
    const status = req.query.status as any || undefined;

    // 验证分页参数
    if (page < 1) {
      throw createError.badRequest('页码必须大于 0');
    }

    if (pageSize < 1 || pageSize > 100) {
      throw createError.badRequest('每页数量必须在 1-100 之间');
    }

    // 验证状态参数
    const validStatuses = ['created', 'running', 'paused', 'completed', 'failed'];
    if (status && !validStatuses.includes(status)) {
      throw createError.badRequest(`无效的状态值：${status}`);
    }

    const result = taskService.getTaskList({
      page,
      pageSize,
      status
    });

    res.json({
      tasks: result.tasks,
      pagination: {
        page,
        pageSize,
        total: result.total,
        totalPages: result.totalPages
      }
    });
  })
);

/**
 * GET /tasks/:taskId - 获取任务详情
 */
router.get('/:taskId', 
  asyncHandler(async (req: Request, res: Response) => {
    const { taskId } = req.params;

    const task = taskService.getTaskDetail(taskId);

    if (!task) {
      throw createError.notFound('任务不存在', { taskId });
    }

    res.json(task);
  })
);

/**
 * POST /tasks/:taskId/pause - 暂停任务
 */
router.post('/:taskId/pause', 
  asyncHandler(async (req: Request, res: Response) => {
    const { taskId } = req.params;

    const task = taskService.getTask(taskId);

    if (!task) {
      throw createError.notFound('任务不存在', { taskId });
    }

    if (task.status !== 'running') {
      throw createError.badRequest('只有运行中的任务可以暂停', {
        currentStatus: task.status
      });
    }

    const success = taskService.pauseTask(taskId);

    if (!success) {
      throw createError.internal('暂停任务失败');
    }

    res.json({
      taskId,
      status: 'paused',
      message: '任务已暂停'
    });
  })
);

/**
 * POST /tasks/:taskId/resume - 继续任务
 */
router.post('/:taskId/resume', 
  asyncHandler(async (req: Request, res: Response) => {
    const { taskId } = req.params;

    const task = taskService.getTask(taskId);

    if (!task) {
      throw createError.notFound('任务不存在', { taskId });
    }

    if (task.status !== 'paused') {
      throw createError.badRequest('只有暂停的任务可以继续', {
        currentStatus: task.status
      });
    }

    const success = taskService.resumeTask(taskId);

    if (!success) {
      throw createError.internal('继续任务失败');
    }

    // 重新启动任务执行
    taskService.executeTask(taskId).catch(error => {
      console.error(`任务执行失败：${taskId}`, error);
      taskService.updateTaskStatus(taskId, 'failed', error.message);
    });

    res.json({
      taskId,
      status: 'running',
      message: '任务已继续'
    });
  })
);

/**
 * POST /tasks/:taskId/cancel - 取消任务
 */
router.post('/:taskId/cancel', 
  asyncHandler(async (req: Request, res: Response) => {
    const { taskId } = req.params;

    const task = taskService.getTask(taskId);

    if (!task) {
      throw createError.notFound('任务不存在', { taskId });
    }

    if (task.status !== 'running' && task.status !== 'paused') {
      throw createError.badRequest('只有运行中或暂停的任务可以取消', {
        currentStatus: task.status
      });
    }

    const success = taskService.cancelTask(taskId);

    if (!success) {
      throw createError.internal('取消任务失败');
    }

    res.json({
      taskId,
      status: 'failed',
      message: '任务已取消'
    });
  })
);

/**
 * GET /tasks/:taskId/results - 获取任务结果
 */
router.get('/:taskId/results', 
  asyncHandler(async (req: Request, res: Response) => {
    const { taskId } = req.params;
    
    // 验证任务是否存在
    const task = taskService.getTask(taskId);
    if (!task) {
      throw createError.notFound('任务不存在', { taskId });
    }

    const page = parseInt(req.query.page as string) || 1;
    const pageSize = parseInt(req.query.pageSize as string) || 50;
    const status = req.query.status as string || undefined;
    const sortBy = req.query.sortBy as string || 'keyword';
    const sortOrder = (req.query.sortOrder as 'asc' | 'desc') || 'asc';

    // 验证分页参数
    if (page < 1) {
      throw createError.badRequest('页码必须大于 0');
    }

    if (pageSize < 1 || pageSize > 100) {
      throw createError.badRequest('每页数量必须在 1-100 之间');
    }

    // 验证排序参数
    const validSortBy = ['keyword', 'organic_page', 'ad_page', 'status', 'processed_at'];
    if (sortBy && !validSortBy.includes(sortBy)) {
      throw createError.badRequest(`无效的排序字段：${sortBy}`);
    }

    if (sortOrder !== 'asc' && sortOrder !== 'desc') {
      throw createError.badRequest('排序方向必须是 asc 或 desc');
    }

    // 验证状态参数
    const validStatuses = ['found', 'ad_only', 'organic_only', 'not_found'];
    if (status && !validStatuses.includes(status)) {
      throw createError.badRequest(`无效的状态值：${status}`);
    }

    const result = taskService.getTaskResults(taskId, {
      page,
      pageSize,
      status,
      sortBy,
      sortOrder
    });

    res.json({
      results: result.results,
      pagination: {
        page,
        pageSize,
        total: result.total,
        totalPages: result.totalPages
      }
    });
  })
);

/**
 * GET /tasks/:taskId/export - 导出数据
 */
router.get('/:taskId/export', 
  asyncHandler(async (req: Request, res: Response) => {
    const { taskId } = req.params;
    const format = (req.query.format as 'csv' | 'xlsx') || 'csv';

    // 验证任务是否存在
    const task = taskService.getTask(taskId);
    if (!task) {
      throw createError.notFound('任务不存在', { taskId });
    }

    // 检查任务是否完成
    if (task.status !== 'completed') {
      throw createError.badRequest('任务未完成，无法导出', {
        currentStatus: task.status
      });
    }

    // 获取所有结果
    const allResults: any[] = [];
    let page = 1;
    const pageSize = 100;

    while (true) {
      const result = taskService.getTaskResults(taskId, { page, pageSize });
      allResults.push(...result.results);
      
      if (page >= result.totalPages) break;
      page++;
    }

    // 生成文件名
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    const filename = `asin-rank-${task.asin}-${timestamp}`;

    if (format === 'csv') {
      // 生成 CSV
      const csv = generateCSV(allResults, task);
      
      res.setHeader('Content-Type', 'text/csv; charset=utf-8');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}.csv"`);
      res.send(csv);
    } else if (format === 'xlsx') {
      // 生成 Excel（需要安装 xlsx 库）
      throw createError.badRequest('Excel 导出功能暂未实现，请使用 CSV 格式');
    }
  })
);

/**
 * 生成 CSV 文件内容
 */
function generateCSV(results: any[], task: any): string {
  // CSV 头部
  const headers = [
    '关键词',
    '自然排名页码',
    '自然排名位置',
    '广告排名页码',
    '广告排名位置',
    '状态',
    '处理时间'
  ];

  // CSV 内容
  const rows = results.map(r => [
    `"${r.keyword}"`,
    r.organic_page || '',
    r.organic_position || '',
    r.ad_page || '',
    r.ad_position || '',
    r.status,
    r.processed_at
  ]);

  // 合并为 CSV 字符串
  return [
    headers.join(','),
    ...rows.map(row => row.join(','))
  ].join('\n');
}

export default router;
