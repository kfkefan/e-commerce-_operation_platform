"""
任务管理服务
提供任务创建、查询、取消、重试等业务逻辑
"""
import asyncio
import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

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
    set_task_retrying,
    get_retryable_tasks,
    get_failed_keywords,
    check_result_exists,
    increment_processed_keywords,
)
from backend.core.rank_finder import get_rank_finder

logger = logging.getLogger(__name__)


class TaskService:
    """任务管理服务"""
    
    def __init__(self):
        self.rank_finder = get_rank_finder()
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._retry_scheduler = None
    
    async def start_retry_scheduler(self):
        """启动重试调度器（后台任务）"""
        logger.info("启动重试调度器...")
        while True:
            try:
                await asyncio.sleep(10)  # 每 10 秒检查一次
                await self._process_retry_queue()
            except Exception as e:
                logger.error(f"重试调度器异常：{e}")
    
    async def _process_retry_queue(self):
        """处理重试队列"""
        try:
            retryable_tasks = await get_retryable_tasks()
            
            for task in retryable_tasks:
                task_id = task['id']
                retry_count = task['retry_count']
                
                logger.info(f"执行自动重试：{task_id} (第 {retry_count + 1} 次)")
                
                # 启动重试任务
                asyncio.create_task(self._execute_task(task_id, is_retry=True))
                
        except Exception as e:
            logger.error(f"处理重试队列失败：{e}")
    
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
            total_keywords=len(request.keywords),
            max_concurrent=request.maxConcurrent,
            organic_only=request.organicOnly,
            max_retries=request.maxRetries,
            original_task_id=None
        )
        
        # 创建关键词
        await create_keywords(task_id, request.keywords)
        
        logger.info(f"任务创建成功：{task_id}, ASIN: {request.asin}, 关键词数：{len(request.keywords)}")
        
        # ✅ 新增：立即通知前端任务状态为 PENDING
        await self.notify_task_status_change(task_id, TaskStatus.PENDING)
        
        # 异步启动任务
        asyncio.create_task(self._execute_task(task_id))
        
        return task_id
    
    async def retry_task(self, task_id: str) -> str:
        """
        手动重试任务（生成新任务 ID）
        
        Args:
            task_id: 原任务 ID
        
        Returns:
            新任务 ID
        """
        # 获取原任务信息
        original_task = await get_task(task_id)
        if not original_task:
            raise ValueError(f"任务不存在：{task_id}")
        
        if original_task['status'] not in ['failed', 'cancelled']:
            raise ValueError(f"任务状态不允许重试：{original_task['status']}")
        
        # 创建新任务
        new_task_id = str(uuid.uuid4())
        
        await create_task(
            task_id=new_task_id,
            asin=original_task['asin'],
            site=original_task['site'],
            max_pages=original_task['max_pages'],
            total_keywords=original_task['total_keywords'],
            max_concurrent=original_task.get('max_concurrent', 3),
            organic_only=bool(original_task.get('organic_only', 0)),
            max_retries=original_task.get('max_retries', 2),
            original_task_id=task_id  # 关联原任务
        )
        
        # 复制关键词
        keywords = await get_task_keywords(task_id)
        if keywords:
            await create_keywords(new_task_id, keywords)
        
        logger.info(f"手动重试任务：{task_id} -> {new_task_id}")
        
        # 启动新任务
        asyncio.create_task(self._execute_task(new_task_id))
        
        return new_task_id
    
    async def _execute_task(self, task_id: str, is_retry: bool = False) -> None:
        """
        执行任务（支持重试）
        
        Args:
            task_id: 任务 ID
            is_retry: 是否为重试任务
        """
        try:
            # 获取任务信息
            task = await get_task(task_id)
            if not task:
                logger.error(f"任务不存在：{task_id}")
                return
            
            # 检查任务状态
            if task['status'] not in ['pending', 'running', 'retrying']:
                logger.warning(f"任务状态不允许执行：{task_id}, status={task['status']}")
                return
            
            # 更新为运行中
            await update_task_status(task_id, TaskStatus.RUNNING)
            logger.info(f"任务开始执行：{task_id} (retry={is_retry})")
            
            # 获取任务配置
            max_concurrent = task.get('max_concurrent', 3)
            organic_only = bool(task.get('organic_only', 0))
            
            # 获取关键词（重试时只获取未成功的）
            if is_retry:
                failed_keywords = await get_failed_keywords(task_id)
                if not failed_keywords:
                    logger.info(f"没有失败的关键词，任务完成：{task_id}")
                    await update_task_status(task_id, TaskStatus.COMPLETED)
                    return
                
                # 只爬取失败的关键词
                keywords_to_process = failed_keywords
                logger.info(f"重试任务，需处理 {len(failed_keywords)} 个失败关键词")
            else:
                keywords = await get_task_keywords(task_id)
                keywords_to_process = keywords
            
            # 执行爬虫任务
            await self.rank_finder.process_task_with_config(
                task_id=task_id,
                keywords=keywords_to_process,
                max_concurrent=max_concurrent,
                organic_only=organic_only,
                is_retry=is_retry
            )
        
        except Exception as e:
            logger.error(f"任务执行异常：{task_id}, 错误：{e}")
            
            # 获取任务当前重试次数
            task = await get_task(task_id)
            if task:
                retry_count = task.get('retry_count', 0)
                max_retries = task.get('max_retries', 2)
                
                if retry_count < max_retries:
                    # 安排自动重试
                    next_retry_delay = 60 * (retry_count + 1)  # 指数退避：60s, 120s, 180s...
                    next_retry_at = datetime.utcnow() + timedelta(seconds=next_retry_delay)
                    
                    await set_task_retrying(
                        task_id=task_id,
                        fail_reason=str(e),
                        next_retry_at=next_retry_at,
                        retry_count=retry_count + 1
                    )
                    
                    logger.info(f"任务失败，安排第 {retry_count + 1} 次重试：{task_id}, {next_retry_at}")
                else:
                    # 重试次数耗尽，标记为失败
                    await update_task_status(task_id, TaskStatus.FAILED, str(e))
                    logger.warning(f"任务重试次数耗尽，标记为失败：{task_id}")
        
        finally:
            # 从活跃任务中移除
            self._active_tasks.pop(task_id, None)
    
    async def get_task_detail(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务详情"""
        task = await get_task(task_id)
        if not task:
            return None
        
        # 计算进度
        total = task['total_keywords']
        processed = task['processed_keywords']
        progress = int((processed / total) * 100) if total > 0 else 0
        
        # 判断是否可以手动重试
        can_retry = (
            task['status'] in ['failed', 'cancelled'] and 
            task.get('retry_count', 0) < task.get('max_retries', 2)
        )
        
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
            'retryCount': task.get('retry_count', 0),
            'maxRetries': task.get('max_retries', 2),
            'failReason': task.get('fail_reason'),
            'nextRetryAt': task.get('next_retry_at'),
            'canRetry': can_retry,
            'maxConcurrent': task.get('max_concurrent', 3),
            'organicOnly': bool(task.get('organic_only', 0)),
        }
    
    async def get_task_list_paginated(
        self,
        status: Optional[str] = None,
        asin: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """获取分页任务列表"""
        result = await get_task_list(status, asin, page, page_size)
        
        # 转换格式
        tasks = []
        for task in result['tasks']:
            can_retry = (
                task['status'] in ['failed', 'cancelled'] and 
                task.get('retry_count', 0) < 2
            )
            
            tasks.append({
                'taskId': task['id'],
                'asin': task['asin'],  # ✅ 添加 ASIN 字段
                'site': task['site'],  # ✅ 添加站点字段
                'status': task['status'],
                'createdAt': task['created_at'],
                'completedAt': task.get('completed_at'),
                'totalKeywords': task['total_keywords'],
                'processedKeywords': task['processed_keywords'],
                'retryCount': task.get('retry_count', 0),
                'canRetry': can_retry,
            })
        
        return {
            'tasks': tasks,
            'pagination': result['pagination']
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = await get_task(task_id)
        if not task:
            return False
        
        if task['status'] not in ['pending', 'running', 'retrying']:
            logger.warning(f"任务无法取消：{task_id}, 当前状态：{task['status']}")
            return False
        
        # 标记取消
        self.rank_finder.cancel_task(task_id)
        
        # 如果在活跃任务中，等待其自然结束
        if task_id in self._active_tasks:
            logger.info(f"等待任务停止：{task_id}")
        
        # 更新数据库状态
        success = await db_cancel_task(task_id)
        
        if success:
            logger.info(f"任务已取消：{task_id}")
        
        return success
    
    async def get_task_results(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
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
    
    async def notify_task_status_change(self, task_id: str, status: TaskStatus):
        """
        通知前端任务状态变化（通过 WebSocket 推送）
        """
        from backend.routers.websocket import push_to_all_clients
        
        # 获取当前任务进度信息
        task = await get_task(task_id)
        
        message = {
            "type": "task_status_update",
            "task_id": task_id,
            "status": status.value
        }
        
        # 如果有任务信息，添加进度数据
        if task:
            message["processed_keywords"] = task.get('processed_keywords', 0)
            message["total_keywords"] = task.get('total_keywords', 0)
        
        # 推送到所有连接的客户端
        await push_to_all_clients(message)
        
        logger.info(f"WebSocket 消息已发送 - task_id: {task_id}, status: {status.value}")
        
    def get_active_task_count(self) -> int:
        """获取活跃任务数"""
        return len(self._active_tasks)


# 全局任务服务实例
task_service = TaskService()


def get_task_service() -> TaskService:
    """获取任务服务实例"""
    return task_service
