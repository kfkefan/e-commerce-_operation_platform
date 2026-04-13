"""
排名查找器
协调爬虫和数据库，执行完整的排名查找流程
"""
import asyncio
import logging
from typing import List, Optional
from datetime import datetime

from backend.config import settings
from backend.core.crawler import get_crawler, CrawlResult
from backend.services.database import (
    get_task,
    get_task_keywords,
    update_task_status,
    increment_processed_keywords,
    create_task_result,
)
from backend.models.schemas import TaskStatus, RankingStatus

logger = logging.getLogger(__name__)


class RankFinder:
    """排名查找器"""
    
    def __init__(self):
        self.crawler = get_crawler()
        self._cancelled_tasks = set()
    
    def cancel_task(self, task_id: str) -> None:
        """标记任务为已取消"""
        self._cancelled_tasks.add(task_id)
        logger.info(f"任务已标记取消：{task_id}")
    
    def is_cancelled(self, task_id: str) -> bool:
        """检查任务是否被取消"""
        return task_id in self._cancelled_tasks
    
    def cleanup_task(self, task_id: str) -> None:
        """清理取消的任务"""
        self._cancelled_tasks.discard(task_id)
    
    def _map_status(self, crawl_status: str) -> RankingStatus:
        """映射爬取状态到排名状态"""
        mapping = {
            'found': RankingStatus.FOUND,
            'organic_not_found': RankingStatus.ORGANIC_NOT_FOUND,
            'ad_not_found': RankingStatus.AD_NOT_FOUND,
            'not_found': RankingStatus.NOT_FOUND,
            'error': RankingStatus.ERROR,
            'captcha': RankingStatus.CAPTCHA,
        }
        return mapping.get(crawl_status, RankingStatus.ERROR)
    
    async def process_task_with_config(
        self,
        task_id: str,
        keywords: List[str],
        max_concurrent: int = 3,
        organic_only: bool = False,
        is_retry: bool = False
    ) -> None:
        """
        处理单个任务（支持配置）
        
        Args:
            task_id: 任务 ID
            keywords: 关键词列表
            max_concurrent: 最大并发数
            organic_only: 仅爬取自然结果
            is_retry: 是否为重试任务
        """
        try:
            # 获取任务信息
            task = await get_task(task_id)
            if not task:
                logger.error(f"任务不存在：{task_id}")
                return
            
            asin = task['asin']
            site = task['site']
            max_pages = task['max_pages']
            
            logger.info(f"任务执行配置：并发={max_concurrent}, 仅自然={organic_only}, 重试={is_retry}")
            
            # 分批处理关键词
            batch_size = max_concurrent
            total_keywords = len(keywords)
            
            for i in range(0, total_keywords, batch_size):
                # 检查是否被取消
                if self.is_cancelled(task_id):
                    logger.info(f"任务已取消：{task_id}")
                    await update_task_status(task_id, TaskStatus.CANCELLED, "用户取消")
                    return
                
                batch = keywords[i:i + batch_size]
                logger.info(f"处理关键词批次 {i//batch_size + 1}: {len(batch)} 个关键词")
                
                # 爬取批次
                results = await self.crawler.crawl_keywords_batch_with_config(
                    asin=asin,
                    keywords=batch,
                    site=site,
                    max_pages=max_pages,
                    max_concurrent=batch_size,
                    organic_only=organic_only
                )
                
                # 保存结果
                for result in results:
                    if self.is_cancelled(task_id):
                        break
                    
                    ranking_status = self._map_status(result.status)
                    await create_task_result(
                        task_id=task_id,
                        keyword=result.keyword,
                        organic_page=result.organic_page,
                        organic_position=result.organic_position,
                        ad_page=result.ad_page,
                        ad_position=result.ad_position,
                        status=ranking_status
                    )
                    await increment_processed_keywords(task_id)
                
                # 批次间延迟
                if i + batch_size < total_keywords:
                    await asyncio.sleep(5)
            
            # 完成任务
            await update_task_status(task_id, TaskStatus.COMPLETED)
            logger.info(f"任务完成：{task_id}")
        
        except Exception as e:
            logger.error(f"任务执行失败：{task_id}, 错误：{e}")
            raise  # 抛出异常让 task_service 处理重试
        
        finally:
            # 清理
            self.cleanup_task(task_id)
    
    async def process_task(self, task_id: str) -> None:
        """处理单个任务（向后兼容）"""
        # 获取任务信息
        task = await get_task(task_id)
        if not task:
            logger.error(f"任务不存在：{task_id}")
            return
        
        # 检查任务状态
        if task['status'] not in ['pending', 'running']:
            logger.warning(f"任务状态不允许执行：{task_id}, status={task['status']}")
            return
        
        # 更新为运行中
        await update_task_status(task_id, TaskStatus.RUNNING)
        logger.info(f"任务开始执行：{task_id}")
        
        # 获取关键词
        keywords = await get_task_keywords(task_id)
        if not keywords:
            logger.warning(f"任务没有关键词：{task_id}")
            await update_task_status(task_id, TaskStatus.COMPLETED)
            return
        
        # 使用默认配置执行
        await self.process_task_with_config(
            task_id=task_id,
            keywords=keywords,
            max_concurrent=settings.MAX_CONCURRENT_BROWSERS,
            organic_only=False,
            is_retry=False
        )


# 全局排名查找器实例
rank_finder = RankFinder()


def get_rank_finder() -> RankFinder:
    """获取排名查找器实例"""
    return rank_finder
