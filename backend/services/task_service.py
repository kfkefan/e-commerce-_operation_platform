"""
任务管理服务
提供任务创建、查询、取消等业务逻辑
"""
import asyncio
import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from backend.models.schemas import TaskCreateRequest, TaskStatus
from backend.services.database import (
    create_task,
    create_keywords,
    get_task,
    get_task_list,
    get_task_keywords,
    get_task_results,
    update_task_status,
    cancel_task as db_cancel_task,
)
from backend.core.rank_finder import get_rank_finder

logger = logging.getLogger(__name__)


class TaskService:
    """任务管理服务"""
    
    def __init__(self):
        self.rank_finder = get_rank_finder()
        self._active_tasks: Dict[str, asyncio.Task] = {}
    
    async def create_task(self, request: TaskCreateRequest) -> str:
        """
        创建新任务
        
        Args:
            request: 创建任务请求
        
        Returns:
            任务 ID
        """
        task_id = str(uuid.uuid4())
        
        # 创建任务记录
        await create_task(
            task_id=task_id,
            asin=request.asin,
            site=request.site,
            max_pages=request.maxPages,
            total_keywords=len(request.keywords)
        )
        
        # 创建关键词
        await create_keywords(task_id, request.keywords)
        
        logger.info(f"任务创建成功：{task_id}, ASIN: {request.asin}, 关键词数：{len(request.keywords)}")
        
        # 异步启动任务
        asyncio.create_task(self._execute_task(task_id))
        
        return task_id
    
    async def _execute_task(self, task_id: str) -> None:
        """
        执行任务
        
        Args:
            task_id: 任务 ID
        """
        try:
            # 创建异步任务
            task = asyncio.create_task(self.rank_finder.process_task(task_id))
            self._active_tasks[task_id] = task
            
            # 等待任务完成
            await task
        
        except Exception as e:
            logger.error(f"任务执行异常：{task_id}, 错误：{e}")
            await update_task_status(task_id, TaskStatus.FAILED, str(e))
        
        finally:
            # 从活跃任务中移除
            self._active_tasks.pop(task_id, None)
    
    async def get_task_detail(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务详情
        
        Args:
            task_id: 任务 ID
        
        Returns:
            任务详情字典
        """
        task = await get_task(task_id)
        if not task:
            return None
        
        # 计算进度
        total = task['total_keywords']
        processed = task['processed_keywords']
        progress = int((processed / total) * 100) if total > 0 else 0
        
        return {
            'taskId': task['id'],
            'status': task['status'],
            'createdAt': task['created_at'],
            'updatedAt': task['updated_at'],
            'asin': task['asin'],
            'site': task['site'],
            'maxPages': task['max_pages'],
            'totalKeywords': total,
            'processedKeywords': processed,
            'progress': progress,
            'errorMessage': task.get('error_message'),
        }
    
    async def get_task_list_paginated(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取分页任务列表
        
        Args:
            status: 状态筛选
            page: 页码
            page_size: 每页数量
        
        Returns:
            任务列表和分页信息
        """
        result = await get_task_list(status, page, page_size)
        
        # 转换格式
        tasks = []
        for task in result['tasks']:
            tasks.append({
                'taskId': task['id'],
                'status': task['status'],
                'createdAt': task['created_at'],
                'completedAt': task.get('completed_at'),
                'totalKeywords': task['total_keywords'],
                'processedKeywords': task['processed_keywords'],
            })
        
        return {
            'tasks': tasks,
            'pagination': result['pagination']
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务 ID
        
        Returns:
            是否成功取消
        """
        # 检查任务是否存在
        task = await get_task(task_id)
        if not task:
            return False
        
        # 检查任务状态
        if task['status'] not in ['pending', 'running']:
            logger.warning(f"任务无法取消：{task_id}, 当前状态：{task['status']}")
            return False
        
        # 标记取消
        self.rank_finder.cancel_task(task_id)
        
        # 如果在活跃任务中，等待其自然结束
        if task_id in self._active_tasks:
            logger.info(f"等待任务停止：{task_id}")
            # 不强制取消，让 rank_finder 自行检测取消标志
        
        # 更新数据库状态
        success = await db_cancel_task(task_id)
        
        if success:
            logger.info(f"任务已取消：{task_id}")
        
        return success
    
    async def get_task_results(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务结果
        
        Args:
            task_id: 任务 ID
        
        Returns:
            任务结果
        """
        task = await get_task(task_id)
        if not task:
            return None
        
        results = await get_task_results(task_id)
        
        # 转换格式
        formatted_results = []
        for r in results:
            formatted_results.append({
                'keyword': r['keyword'],
                'organicPage': r['organic_page'],
                'organicPosition': r['organic_position'],
                'adPage': r['ad_page'],
                'adPosition': r['ad_position'],
                'status': r['status'],
                'timestamp': r['created_at'],
            })
        
        return {
            'taskId': task['id'],
            'asin': task['asin'],
            'site': task['site'],
            'completedAt': task.get('completed_at'),
            'results': formatted_results,
        }
    
    def get_active_task_count(self) -> int:
        """获取活跃任务数"""
        return len(self._active_tasks)


# 全局任务服务实例
task_service = TaskService()


def get_task_service() -> TaskService:
    """获取任务服务实例"""
    return task_service
