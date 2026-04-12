import { vi } from 'vitest';
import path from 'path';
import fs from 'fs';

// 设置测试环境变量
process.env.NODE_ENV = 'test';
process.env.DATABASE_PATH = path.join(__dirname, 'test-database.sqlite');

// 清理测试数据库
const dbPath = process.env.DATABASE_PATH;
if (fs.existsSync(dbPath)) {
  fs.unlinkSync(dbPath);
}

// Mock 全局 console 以减少测试输出噪音
vi.spyOn(console, 'log').mockImplementation(() => {});
vi.spyOn(console, 'error').mockImplementation(() => {});
vi.spyOn(console, 'warn').mockImplementation(() => {});

// 清理函数
afterAll(() => {
  // 清理测试数据库
  if (fs.existsSync(dbPath)) {
    fs.unlinkSync(dbPath);
  }
});
