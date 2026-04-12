import dotenv from 'dotenv';
import path from 'path';

// 加载环境变量
dotenv.config();

export interface Config {
  // 应用配置
  nodeEnv: string;
  port: number;
  apiBaseUrl: string;

  // 数据库配置
  databasePath: string;

  // 爬虫配置
  proxyPoolUrl?: string;
  requestDelayMin: number;
  requestDelayMax: number;
  maxRetries: number;
  retryDelay: number;
  maxConcurrentTasks: number;

  // 限流配置
  apiRateLimit: number;
  taskRateLimit: number;

  // 亚马逊站点配置
  defaultSite: string;
  supportedSites: string[];

  // 日志配置
  logLevel: string;
  logFile: string;
}

// 解析环境变量
const parseEnv = {
  nodeEnv: process.env.NODE_ENV || 'development',
  port: parseInt(process.env.PORT || '3000', 10),
  apiBaseUrl: process.env.API_BASE_URL || 'http://localhost:3000',
  
  databasePath: process.env.DATABASE_PATH || path.join(__dirname, '../../data/database.sqlite'),
  
  proxyPoolUrl: process.env.PROXY_POOL_URL || undefined,
  requestDelayMin: parseInt(process.env.REQUEST_DELAY_MIN || '2000', 10),
  requestDelayMax: parseInt(process.env.REQUEST_DELAY_MAX || '5000', 10),
  maxRetries: parseInt(process.env.MAX_RETRIES || '3', 10),
  retryDelay: parseInt(process.env.RETRY_DELAY || '1000', 10),
  maxConcurrentTasks: parseInt(process.env.MAX_CONCURRENT_TASKS || '1', 10),
  
  apiRateLimit: parseInt(process.env.API_RATE_LIMIT || '60', 10),
  taskRateLimit: parseInt(process.env.TASK_RATE_LIMIT || '10', 10),
  
  defaultSite: process.env.DEFAULT_SITE || 'amazon.com',
  supportedSites: (process.env.SUPPORTED_SITES || 'amazon.com,amazon.co.uk,amazon.de,amazon.fr,amazon.co.jp,amazon.cn')
    .split(',')
    .map(s => s.trim()),
  
  logLevel: process.env.LOG_LEVEL || 'info',
  logFile: process.env.LOG_FILE || path.join(__dirname, '../../logs/app.log'),
};

export const config: Config = parseEnv;

// 验证配置
function validateConfig() {
  const errors: string[] = [];

  if (config.port < 1 || config.port > 65535) {
    errors.push('PORT 必须在 1-65535 之间');
  }

  if (config.requestDelayMin < 0 || config.requestDelayMax < 0) {
    errors.push('请求延迟不能为负数');
  }

  if (config.requestDelayMin > config.requestDelayMax) {
    errors.push('REQUEST_DELAY_MIN 不能大于 REQUEST_DELAY_MAX');
  }

  if (config.maxRetries < 0) {
    errors.push('MAX_RETRIES 不能为负数');
  }

  if (config.supportedSites.length === 0) {
    errors.push('至少需要支持一个亚马逊站点');
  }

  if (errors.length > 0) {
    throw new Error(`配置验证失败:\n${errors.join('\n')}`);
  }
}

validateConfig();

export default config;
