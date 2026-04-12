import rateLimit from 'express-rate-limit';
import { Request, Response } from 'express';
import { config } from '../../config';
import { createError } from './errorHandler';

/**
 * API 限流中间件
 * 限制每个 IP 的请求频率
 */
export const apiRateLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 分钟
  max: config.apiRateLimit, // 每分钟最大请求数
  message: {
    errorCode: 'RATE_LIMIT_EXCEEDED',
    message: '请求频率超限，请稍后重试',
    details: {
      retryAfter: 60
    }
  } as any,
  standardHeaders: true, // 在响应头中返回限流信息
  legacyHeaders: false,
  keyGenerator: (req: Request) => {
    // 使用 IP 地址作为限流键
    return req.ip || req.socket.remoteAddress || 'unknown';
  },
  handler: (req: Request, res: Response) => {
    res.status(429).json({
      errorCode: 'RATE_LIMIT_EXCEEDED',
      message: '请求频率超限，请稍后重试',
      details: {
        retryAfter: 60,
        limit: config.apiRateLimit,
        windowMs: 60000
      }
    });
  }
});

/**
 * 任务创建限流中间件
 * 限制每个用户的任务创建频率
 */
export const taskRateLimiter = rateLimit({
  windowMs: 60 * 60 * 1000, // 1 小时
  max: config.taskRateLimit, // 每小时最大任务创建数
  message: {
    errorCode: 'TASK_RATE_LIMIT_EXCEEDED',
    message: '任务创建频率超限，请稍后重试',
    details: {
      retryAfter: 3600
    }
  } as any,
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req: Request) => {
    // 使用 IP 地址作为限流键
    return req.ip || req.socket.remoteAddress || 'unknown';
  },
  handler: (req: Request, res: Response) => {
    res.status(429).json({
      errorCode: 'TASK_RATE_LIMIT_EXCEEDED',
      message: `任务创建频率超限，每小时最多创建 ${config.taskRateLimit} 个任务`,
      details: {
        retryAfter: 3600,
        limit: config.taskRateLimit,
        windowMs: 3600000
      }
    });
  }
});

/**
 * 严格限流中间件
 * 用于特别敏感的接口（如登录、注册等）
 */
export const strictRateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 分钟
  max: 10, // 15 分钟内最多 10 次请求
  message: {
    errorCode: 'STRICT_RATE_LIMIT_EXCEEDED',
    message: '操作过于频繁，请 15 分钟后再试',
    details: {
      retryAfter: 900
    }
  } as any,
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req: Request) => {
    return req.ip || req.socket.remoteAddress || 'unknown';
  }
});

/**
 * 自定义限流配置
 * @param windowMs 时间窗口（毫秒）
 * @param max 最大请求数
 * @param message 错误消息
 */
export const createRateLimiter = (
  windowMs: number,
  max: number,
  errorCode: string = 'RATE_LIMIT_EXCEEDED',
  message?: string
) => {
  return rateLimit({
    windowMs,
    max,
    message: {
      errorCode,
      message: message || '请求频率超限，请稍后重试',
      details: {
        retryAfter: Math.ceil(windowMs / 1000),
        limit: max,
        windowMs
      }
    } as any,
    standardHeaders: true,
    legacyHeaders: false,
    keyGenerator: (req: Request) => {
      return req.ip || req.socket.remoteAddress || 'unknown';
    },
    handler: (req: Request, res: Response) => {
      res.status(429).json({
        errorCode,
        message: message || '请求频率超限，请稍后重试',
        details: {
          retryAfter: Math.ceil(windowMs / 1000),
          limit: max,
          windowMs
        }
      });
    }
  });
};

/**
 * 检查限流状态的中间件
 * 在响应头中添加限流信息
 */
export const rateLimitInfo = (req: Request, res: Response, next: () => void) => {
  // 这个中间件会在响应头中添加限流信息
  // 实际的限流计数由 express-rate-limit 处理
  next();
};
