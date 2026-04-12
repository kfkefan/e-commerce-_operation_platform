import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';
import { config } from '../config';

/**
 * SQLite 数据库操作类
 * 负责数据库连接、初始化和基础操作
 */
export class DatabaseService {
  private db: Database.Database | null = null;
  private dbPath: string;

  constructor(dbPath?: string) {
    this.dbPath = dbPath || config.databasePath;
  }

  /**
   * 初始化数据库连接
   */
  connect(): Database.Database {
    // 确保数据库目录存在
    const dbDir = path.dirname(this.dbPath);
    if (!fs.existsSync(dbDir)) {
      fs.mkdirSync(dbDir, { recursive: true });
    }

    // 创建数据库连接
    this.db = new Database(this.dbPath);
    
    // 启用外键约束
    this.db.pragma('foreign_keys = ON');
    
    // 设置 WAL 模式以提高并发性能
    this.db.pragma('journal_mode = WAL');
    
    // 初始化数据库表
    this.initializeTables();

    console.log(`数据库连接成功：${this.dbPath}`);
    return this.db;
  }

  /**
   * 初始化数据库表
   */
  private initializeTables(): void {
    if (!this.db) {
      throw new Error('数据库未连接');
    }

    // 读取并执行初始化 SQL 脚本
    const initSqlPath = path.join(__dirname, '../database/init.sql');
    
    if (fs.existsSync(initSqlPath)) {
      const initSql = fs.readFileSync(initSqlPath, 'utf-8');
      this.db.exec(initSql);
      console.log('数据库表初始化完成');
    } else {
      console.warn('警告：未找到数据库初始化脚本，使用默认建表语句');
      this.createTablesFallback();
    }
  }

  /**
   * 备用建表语句（当 init.sql 不存在时使用）
   */
  private createTablesFallback(): void {
    if (!this.db) return;

    // 创建 tasks 表
    this.db.exec(`
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

    // 创建 task_keywords 表
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS task_keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id VARCHAR(36) NOT NULL,
        keyword VARCHAR(100) NOT NULL,
        sort_order INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
      )
    `);

    // 创建 task_results 表
    this.db.exec(`
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

    // 创建 history 表
    this.db.exec(`
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

    console.log('数据库表创建完成（备用模式）');
  }

  /**
   * 获取数据库实例
   */
  getDb(): Database.Database {
    if (!this.db) {
      throw new Error('数据库未连接，请先调用 connect()');
    }
    return this.db;
  }

  /**
   * 关闭数据库连接
   */
  close(): void {
    if (this.db) {
      this.db.close();
      this.db = null;
      console.log('数据库连接已关闭');
    }
  }

  /**
   * 执行事务
   */
  transaction<T>(fn: () => T): T {
    if (!this.db) {
      throw new Error('数据库未连接');
    }
    
    const transaction = this.db.transaction(fn);
    return transaction();
  }

  /**
   * 清理过期数据（可选的维护功能）
   */
  cleanupOldData(days: number = 30): void {
    if (!this.db) return;

    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - days);

    // 清理旧的任务结果原始 HTML
    this.db.prepare(`
      UPDATE task_results 
      SET raw_html = NULL 
      WHERE processed_at < ?
    `).run(cutoffDate.toISOString());

    console.log(`已清理 ${days} 天前的原始 HTML 数据`);
  }
}

// 导出单例实例
export const databaseService = new DatabaseService();
