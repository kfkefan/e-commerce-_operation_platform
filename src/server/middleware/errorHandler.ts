import { Request, Response, NextFunction } from 'express';

/**
 * 自定义错误类
 */
export class AppError extends Error {
  statusCode: number;
  errorCode: string;
  details?: any;

  constructor(
    statusCode: number,
    errorCode: string,
    message: string,
    details?: any
  ) {
    super(message);
    this.statusCode = statusCode;
    this.errorCode = errorCode;
    this.details = details;
    this.name = 'AppError';
  }
}

/**
 * 错误响应接口
 */
export interface ErrorResponse {
  errorCode: string;
  message: string;
  details?: any;
}

/**
 * 全局错误处理中间件
 * 捕获所有未处理的错误并返回统一的错误响应格式
 */
export const errorHandler = (
  err: Error | AppError,
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  // 如果是 AppError，直接返回
  if (err instanceof AppError) {
    const response: ErrorResponse = {
      errorCode: err.errorCode,
      message: err.message,
      details: err.details
    };

    res.status(err.statusCode).json(response);
    return;
  }

  // 如果是其他错误，根据类型处理
  console.error('未处理的错误:', err);

  // 默认错误响应
  const statusCode = (err as any).statusCode || 500;
  const errorCode = (err as any).errorCode || 'INTERNAL_SERVER_ERROR';
  const message = process.env.NODE_ENV === 'production' 
    ? '服务器内部错误' 
    : err.message;

  const response: ErrorResponse = {
    errorCode,
    message,
    details: process.env.NODE_ENV === 'development' ? {
      stack: err.stack,
      name: err.name
    } : undefined
  };

  res.status(statusCode).json(response);
};

/**
 * 404 错误处理中间件
 * 处理未找到的路由
 */
export const notFoundHandler = (
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  const error = new AppError(
    404,
    'ROUTE_NOT_FOUND',
    `未找到的路由：${req.method} ${req.path}`
  );
  next(error);
};

/**
 * 异步错误包装器
 * 用于包装异步路由处理器，避免需要手动调用 next()
 */
export const asyncHandler = (
  fn: (req: Request, res: Response, next: NextFunction) => Promise<any>
) => {
  return (req: Request, res: Response, next: NextFunction): void => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};

/**
 * 创建 AppError 的辅助函数
 */
export const createError = {
  badRequest: (message: string, details?: any) => 
    new AppError(400, 'BAD_REQUEST', message, details),
  
  unauthorized: (message: string, details?: any) => 
    new AppError(401, 'UNAUTHORIZED', message, details),
  
  forbidden: (message: string, details?: any) => 
    new AppError(403, 'FORBIDDEN', message, details),
  
  notFound: (message: string, details?: any) => 
    new AppError(404, 'NOT_FOUND', message, details),
  
  conflict: (message: string, details?: any) => 
    new AppError(409, 'CONFLICT', message, details),
  
  tooManyRequests: (message: string, details?: any) => 
    new AppError(429, 'TOO_MANY_REQUESTS', message, details),
  
  internal: (message: string, details?: any) => 
    new AppError(500, 'INTERNAL_SERVER_ERROR', message, details)
};
