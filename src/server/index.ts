import express, { Express } from 'express';
import cors from 'cors';
import compression from 'compression';
import path from 'path';
import { config } from '../config';
import { databaseService } from '../services/database';
import { errorHandler, notFoundHandler } from './middleware/errorHandler';
import { apiRateLimiter } from './middleware/rateLimiter';
import tasksRouter from './routes/tasks';
import historyRouter from './routes/history';

/**
 * 创建并配置 Express 应用
 */
export function createApp(): Express {
  const app = express();

  // ============================================
  // 中间件配置
  // ============================================

  // 启用 CORS
  app.use(cors({
    origin: process.env.NODE_ENV === 'production' 
      ? false  // 生产环境禁止所有 CORS（应配置具体域名）
      : true,   // 开发环境允许所有来源
    credentials: true,
    exposedHeaders: ['X-RateLimit-Limit', 'X-RateLimit-Remaining']
  }));

  // 启用 Gzip 压缩
  app.use(compression());

  // 解析 JSON 请求体
  app.use(express.json({ limit: '10mb' }));

  // 解析 URL-encoded 请求体
  app.use(express.urlencoded({ extended: true, limit: '10mb' }));

  // ============================================
  // 全局限流
  // ============================================
  app.use(apiRateLimiter);

  // ============================================
  // 路由配置
  // ============================================

  // API 版本前缀
  const apiPrefix = '/api/v1';

  // 健康检查
  app.get('/health', (req, res) => {
    res.json({
      status: 'ok',
      timestamp: new Date().toISOString(),
      version: '1.0.0'
    });
  });

  // API 路由
  app.use(`${apiPrefix}/tasks`, tasksRouter);
  app.use(`${apiPrefix}/history`, historyRouter);

  // API 根路径
  app.get(apiPrefix, (req, res) => {
    res.json({
      name: 'ASIN Ranker API',
      version: '1.0.0',
      endpoints: {
        tasks: `${apiPrefix}/tasks`,
        history: `${apiPrefix}/history`
      }
    });
  });

  // ============================================
  // 前端静态文件服务（生产环境）
  // ============================================
  if (process.env.NODE_ENV === 'production') {
    const frontendPath = path.join(__dirname, '../../frontend/dist');
    app.use(express.static(frontendPath));
    
    // SPA 路由支持：所有未知路由返回 index.html
    app.get('*', (req, res) => {
      res.sendFile(path.join(frontendPath, 'index.html'));
    });
  }

  // ============================================
  // 错误处理
  // ============================================

  // 404 处理
  app.use(notFoundHandler);

  // 全局错误处理
  app.use(errorHandler);

  return app;
}

/**
 * 启动服务器
 */
export async function startServer(): Promise<void> {
  // 初始化数据库
  databaseService.connect();

  // 创建 Express 应用
  const app = createApp();

  // 启动 HTTP 服务器
  return new Promise((resolve, reject) => {
    const server = app.listen(config.port, () => {
      console.log(`
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ASIN 关键词排名追踪器 - 服务器已启动                      ║
║                                                           ║
║   环境：${config.nodeEnv.padEnd(12)} 端口：${config.port.toString().padEnd(5)}                     ║
║   地址：http://localhost:${config.port}                            ║
║   文档：http://localhost:${config.port}/api/v1                     ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
      `.trim());
      resolve();
    });

    // 优雅关闭
    const gracefulShutdown = (signal: string) => {
      console.log(`\n收到信号 ${signal}，正在关闭服务器...`);
      
      server.close(() => {
        console.log('HTTP 服务器已关闭');
        databaseService.close();
        console.log('数据库连接已关闭');
        process.exit(0);
      });

      // 如果 10 秒后还没关闭，强制退出
      setTimeout(() => {
        console.error('未能优雅关闭，强制退出');
        process.exit(1);
      }, 10000);
    };

    process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
    process.on('SIGINT', () => gracefulShutdown('SIGINT'));

    // 处理未捕获的异常
    process.on('uncaughtException', (error) => {
      console.error('未捕获的异常:', error);
      gracefulShutdown('uncaughtException');
    });

    process.on('unhandledRejection', (reason, promise) => {
      console.error('未处理的 Promise 拒绝:', reason);
      gracefulShutdown('unhandledRejection');
    });
  });
}

// ============================================
// 主程序入口
// ============================================
if (require.main === module) {
  startServer().catch((error) => {
    console.error('服务器启动失败:', error);
    process.exit(1);
  });
}
