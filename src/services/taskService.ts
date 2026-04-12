import { v4 as uuidv4 } from 'uuid';
import { databaseService } from './database';
import { AmazonCrawler } from '../crawler/amazonCrawler';
import type { RankResult } from '../crawler/amazonCrawler';

/**
 * 任务状态枚举
 */
export type TaskStatus = 'created' | 'running' | 'paused' | 'completed' | 'failed';

/**
 * 任务实体类型
 */
export interface Task {
  taskId: string;
  asin: string;
  site: string;
  maxPages: number;
  status: TaskStatus;
  totalKeywords: number;
  processedKeywords: number;
  errorMessage?: string;
  createdAt: string;
  startedAt?: string;
  pausedAt?: string;
  completedAt?: string;
  updatedAt: string;
}

/**
 * 任务创建参数
 */
export interface CreateTaskParams {
  asin: string;
  keywords: string[];
  maxPages: number;
  site?: string;
}

/**
 * 任务详情（包含进度信息）
 */
export interface TaskDetail extends Task {
  progressPercentage: number;
  estimatedRemainingSeconds?: number;
}

/**
 * 任务管理服务
 * 负责任务的创建、查询、状态更新等操作
 */
export class TaskService {
  private crawler: AmazonCrawler;

  constructor() {
    this.crawler = new AmazonCrawler();
  }

  /**
   * 创建新任务
   */
  async createTask(params: CreateTaskParams): Promise<Task> {
    const db = databaseService.getDb();
    const taskId = uuidv4();
    const now = new Date().toISOString();

    // 使用事务确保数据一致性
    return db.transaction(() => {
      // 1. 创建任务记录
      const insertTask = db.prepare(`
        INSERT INTO tasks (
          task_id, asin, site, max_pages, status, 
          total_keywords, processed_keywords, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'created', ?, 0, ?, ?)
      `);

      insertTask.run(
        taskId,
        params.asin.toUpperCase(),
        params.site || 'amazon.com',
        params.maxPages,
        params.keywords.length,
        now,
        now
      );

      // 2. 批量插入关键词
      const insertKeyword = db.prepare(`
        INSERT INTO task_keywords (task_id, keyword, sort_order, created_at)
        VALUES (?, ?, ?, ?)
      `);

      const insertMany = db.transaction((keywords: string[]) => {
        keywords.forEach((keyword, index) => {
          insertKeyword.run(taskId, keyword.trim(), index, now);
        });
      });

      insertMany(params.keywords);

      // 3. 返回任务信息
      return this.getTask(taskId);
    })();
  }

  /**
   * 获取任务详情
   */
  getTask(taskId: string): Task | null {
    const db = databaseService.getDb();
    
    const stmt = db.prepare(`
      SELECT 
        task_id, asin, site, max_pages, status,
        total_keywords, processed_keywords, error_message,
        created_at, started_at, paused_at, completed_at, updated_at
      FROM tasks
      WHERE task_id = ?
    `);

    const row = stmt.get(taskId) as any;
    if (!row) return null;

    return this.mapTaskRow(row);
  }

  /**
   * 获取任务详情（包含进度计算）
   */
  getTaskDetail(taskId: string): TaskDetail | null {
    const task = this.getTask(taskId);
    if (!task) return null;

    const progressPercentage = task.totalKeywords > 0
      ? (task.processedKeywords / task.totalKeywords) * 100
      : 0;

    // 估算剩余时间（假设每个关键词平均需要 5 秒）
    const remainingKeywords = task.totalKeywords - task.processedKeywords;
    const estimatedRemainingSeconds = task.status === 'running'
      ? Math.ceil(remainingKeywords * 5)
      : undefined;

    return {
      ...task,
      progressPercentage,
      estimatedRemainingSeconds
    };
  }

  /**
   * 获取任务列表（支持分页和筛选）
   */
  getTaskList(options?: {
    page?: number;
    pageSize?: number;
    status?: TaskStatus;
  }): { tasks: Task[]; total: number; totalPages: number } {
    const db = databaseService.getDb();
    const page = options?.page || 1;
    const pageSize = options?.pageSize || 20;
    const offset = (page - 1) * pageSize;

    // 构建查询条件
    let whereClause = '';
    const params: any[] = [];
    
    if (options?.status) {
      whereClause = 'WHERE status = ?';
      params.push(options.status);
    }

    // 查询总数
    const countStmt = db.prepare(`
      SELECT COUNT(*) as total FROM tasks ${whereClause}
    `);
    const countResult = countStmt.get(...params) as any;
    const total = countResult.total;

    // 查询任务列表
    const selectStmt = db.prepare(`
      SELECT 
        task_id, asin, site, max_pages, status,
        total_keywords, processed_keywords, error_message,
        created_at, started_at, paused_at, completed_at, updated_at
      FROM tasks
      ${whereClause}
      ORDER BY created_at DESC
      LIMIT ? OFFSET ?
    `);

    const rows = selectStmt.all(...params, pageSize, offset) as any[];
    const tasks = rows.map(row => this.mapTaskRow(row));

    return {
      tasks,
      total,
      totalPages: Math.ceil(total / pageSize)
    };
  }

  /**
   * 更新任务状态
   */
  updateTaskStatus(taskId: string, status: TaskStatus, errorMessage?: string): boolean {
    const db = databaseService.getDb();
    const now = new Date().toISOString();

    const updates: string[] = ['status = ?', 'updated_at = ?'];
    const params: any[] = [status, now];

    // 根据状态设置对应的时间字段
    if (status === 'running' && !errorMessage) {
      updates.push('started_at = ?');
      params.push(now);
    } else if (status === 'paused') {
      updates.push('paused_at = ?');
      params.push(now);
    } else if (status === 'completed') {
      updates.push('completed_at = ?');
      params.push(now);
    } else if (status === 'failed') {
      updates.push('completed_at = ?', 'error_message = ?');
      params.push(now, errorMessage);
    }

    const stmt = db.prepare(`
      UPDATE tasks SET ${updates.join(', ')} WHERE task_id = ?
    `);

    const result = stmt.run(...params, taskId);
    return result.changes > 0;
  }

  /**
   * 更新任务进度
   */
  updateTaskProgress(taskId: string, processedKeywords: number): boolean {
    const db = databaseService.getDb();
    const now = new Date().toISOString();

    const stmt = db.prepare(`
      UPDATE tasks 
      SET processed_keywords = ?, updated_at = ?
      WHERE task_id = ?
    `);

    const result = stmt.run(processedKeywords, now, taskId);
    return result.changes > 0;
  }

  /**
   * 暂停任务
   */
  pauseTask(taskId: string): boolean {
    const task = this.getTask(taskId);
    if (!task || task.status !== 'running') {
      return false;
    }
    return this.updateTaskStatus(taskId, 'paused');
  }

  /**
   * 继续任务
   */
  resumeTask(taskId: string): boolean {
    const task = this.getTask(taskId);
    if (!task || task.status !== 'paused') {
      return false;
    }
    return this.updateTaskStatus(taskId, 'running');
  }

  /**
   * 取消任务
   */
  cancelTask(taskId: string): boolean {
    const task = this.getTask(taskId);
    if (!task || (task.status !== 'running' && task.status !== 'paused')) {
      return false;
    }
    return this.updateTaskStatus(taskId, 'failed', '用户取消任务');
  }

  /**
   * 保存任务结果
   */
  saveTaskResults(taskId: string, results: Array<{
    keywordId: number;
    keyword: string;
    result: RankResult;
  }>): void {
    const db = databaseService.getDb();

    const insertResult = db.prepare(`
      INSERT INTO task_results (
        task_id, keyword_id, keyword,
        organic_page, organic_position,
        ad_page, ad_position,
        status, raw_html, processed_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    const insertMany = db.transaction((results: any[]) => {
      results.forEach(({ keywordId, keyword, result }) => {
        insertResult.run(
          taskId,
          keywordId,
          keyword,
          result.organicPage || null,
          result.organicPosition || null,
          result.adPage || null,
          result.adPosition || null,
          result.status,
          result.rawHtml || null,
          new Date().toISOString()
        );
      });
    });

    insertMany(results);
  }

  /**
   * 获取任务结果（支持分页和筛选）
   */
  getTaskResults(taskId: string, options?: {
    page?: number;
    pageSize?: number;
    status?: string;
    sortBy?: string;
    sortOrder?: 'asc' | 'desc';
  }): { results: any[]; total: number; totalPages: number } {
    const db = databaseService.getDb();
    const page = options?.page || 1;
    const pageSize = options?.pageSize || 50;
    const offset = (page - 1) * pageSize;

    // 构建查询条件
    const whereClauses: string[] = ['task_id = ?'];
    const params: any[] = [taskId];

    if (options?.status) {
      whereClauses.push('status = ?');
      params.push(options.status);
    }

    const whereClause = whereClauses.join(' AND ');

    // 查询总数
    const countStmt = db.prepare(`
      SELECT COUNT(*) as total FROM task_results WHERE ${whereClause}
    `);
    const countResult = countStmt.get(...params) as any;
    const total = countResult.total;

    // 构建排序子句
    const sortBy = options?.sortBy || 'keyword';
    const sortOrder = options?.sortOrder || 'asc';
    const orderColumn = this.getOrderColumn(sortBy);
    const orderDirection = sortOrder.toUpperCase();

    // 查询结果列表
    const selectStmt = db.prepare(`
      SELECT 
        keyword, organic_page, organic_position,
        ad_page, ad_position, status, processed_at
      FROM task_results
      WHERE ${whereClause}
      ORDER BY ${orderColumn} ${orderDirection}
      LIMIT ? OFFSET ?
    `);

    const rows = selectStmt.all(...params, pageSize, offset);

    return {
      results: rows,
      total,
      totalPages: Math.ceil(total / pageSize)
    };
  }

  /**
   * 获取历史记录（最近 N 条）
   */
  getHistory(limit: number = 10): any[] {
    const db = databaseService.getDb();

    const stmt = db.prepare(`
      SELECT 
        h.task_id, h.asin, h.keyword_count, h.status,
        h.created_at, h.completed_at
      FROM history h
      ORDER BY h.created_at DESC
      LIMIT ?
    `);

    return stmt.all(limit);
  }

  /**
   * 获取历史记录详情
   */
  getHistoryDetail(taskId: string): any | null {
    const db = databaseService.getDb();

    // 获取历史记录
    const historyStmt = db.prepare(`
      SELECT * FROM history WHERE task_id = ?
    `);
    const history = historyStmt.get(taskId);

    if (!history) return null;

    // 获取结果列表
    const resultsStmt = db.prepare(`
      SELECT 
        keyword, organic_page, organic_position,
        ad_page, ad_position, status, processed_at
      FROM task_results
      WHERE task_id = ?
    `);
    const results = resultsStmt.all(taskId);

    return {
      ...history,
      results
    };
  }

  /**
   * 添加到历史记录
   */
  addToHistory(task: Task): void {
    const db = databaseService.getDb();
    const now = new Date().toISOString();

    // 插入历史记录
    const insertHistory = db.prepare(`
      INSERT OR REPLACE INTO history (
        task_id, asin, keyword_count, status, created_at, completed_at
      ) VALUES (?, ?, ?, ?, ?, ?)
    `);

    insertHistory.run(
      task.taskId,
      task.asin,
      task.totalKeywords,
      task.status,
      task.createdAt,
      task.completedAt || now
    );

    // 创建快照数据
    const snapshotData = JSON.stringify({
      task: this.getTaskDetail(task.taskId),
      timestamp: now
    });

    const insertSnapshot = db.prepare(`
      INSERT INTO history_snapshots (task_id, snapshot_data, created_at)
      VALUES (?, ?, ?)
    `);

    insertSnapshot.run(task.taskId, snapshotData, now);

    // 清理旧的历史记录，只保留最近 100 条
    db.prepare(`
      DELETE FROM history WHERE task_id IN (
        SELECT task_id FROM history 
        ORDER BY created_at DESC 
        LIMIT -1 OFFSET 100
      )
    `).run();
  }

  /**
   * 执行任务（爬虫入口）
   */
  async executeTask(taskId: string): Promise<void> {
    const task = this.getTask(taskId);
    if (!task) {
      throw new Error(`任务不存在：${taskId}`);
    }

    // 更新状态为运行中
    this.updateTaskStatus(taskId, 'running');

    try {
      const db = databaseService.getDb();

      // 获取任务关键词
      const keywordsStmt = db.prepare(`
        SELECT id, keyword FROM task_keywords 
        WHERE task_id = ? 
        ORDER BY sort_order
      `);
      const keywords = keywordsStmt.all(taskId) as Array<{ id: number; keyword: string }>;

      // 逐个处理关键词
      for (let i = 0; i < keywords.length; i++) {
        // 检查任务是否被暂停或取消
        const currentTask = this.getTask(taskId);
        if (currentTask?.status !== 'running') {
          console.log(`任务 ${taskId} 已${currentTask?.status}，停止执行`);
          break;
        }

        const { id: keywordId, keyword } = keywords[i];

        try {
          // 执行爬虫
          const result = await this.crawler.searchAndExtractRank(
            keyword,
            task.asin,
            task.maxPages,
            task.site
          );

          // 保存结果
          this.saveTaskResults(taskId, [{
            keywordId,
            keyword,
            result
          }]);

          // 更新进度
          this.updateTaskProgress(taskId, i + 1);

          console.log(`任务 ${taskId}: 关键词 "${keyword}" 处理完成，状态：${result.status}`);
        } catch (error) {
          console.error(`任务 ${taskId}: 关键词 "${keyword}" 处理失败`, error);
          // 继续处理下一个关键词
        }
      }

      // 检查是否所有关键词都处理完成
      const finalTask = this.getTask(taskId);
      if (finalTask && finalTask.status === 'running') {
        this.updateTaskStatus(taskId, 'completed');
        
        // 添加到历史记录
        const completedTask = this.getTask(taskId);
        if (completedTask) {
          this.addToHistory(completedTask);
        }
      }
    } catch (error) {
      console.error(`任务 ${taskId} 执行失败`, error);
      this.updateTaskStatus(taskId, 'failed', (error as Error).message);
      throw error;
    }
  }

  /**
   * 将数据库行映射为 Task 对象
   */
  private mapTaskRow(row: any): Task {
    return {
      taskId: row.task_id,
      asin: row.asin,
      site: row.site,
      maxPages: row.max_pages,
      status: row.status as TaskStatus,
      totalKeywords: row.total_keywords,
      processedKeywords: row.processed_keywords,
      errorMessage: row.error_message || undefined,
      createdAt: row.created_at,
      startedAt: row.started_at || undefined,
      pausedAt: row.paused_at || undefined,
      completedAt: row.completed_at || undefined,
      updatedAt: row.updated_at
    };
  }

  /**
   * 获取排序字段名
   */
  private getOrderColumn(sortBy: string): string {
    const columnMap: Record<string, string> = {
      keyword: 'keyword',
      organic_page: 'organic_page',
      ad_page: 'ad_page',
      status: 'status',
      processed_at: 'processed_at'
    };
    return columnMap[sortBy] || 'keyword';
  }
}

// 导出单例实例
export const taskService = new TaskService();
