import { Router, Request, Response } from 'express';
import { taskService } from '../../services/taskService';
import { asyncHandler, createError } from './middleware/errorHandler';

const router = Router();

/**
 * GET /history - 获取历史记录列表
 */
router.get('/', 
  asyncHandler(async (req: Request, res: Response) => {
    const limit = parseInt(req.query.limit as string) || 10;

    // 验证参数
    if (limit < 1 || limit > 50) {
      throw createError.badRequest('返回数量限制必须在 1-50 之间');
    }

    const history = taskService.getHistory(limit);

    res.json({
      history
    });
  })
);

/**
 * GET /history/:taskId - 获取历史记录详情
 */
router.get('/:taskId', 
  asyncHandler(async (req: Request, res: Response) => {
    const { taskId } = req.params;

    const historyDetail = taskService.getHistoryDetail(taskId);

    if (!historyDetail) {
      throw createError.notFound('历史记录不存在', { taskId });
    }

    res.json(historyDetail);
  })
);

export default router;
