"""
MySQL 数据库操作模块
提供异步数据库连接池和 CRUD 操作
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

import aiomysql
from aiomysql import Pool

from backend.config import settings
from backend.models.tables import Task, TaskKeyword, TaskResult
from backend.models.schemas import TaskStatus, RankingStatus

logger = logging.getLogger(__name__)


class DatabasePool:
    """数据库连接池管理器"""
    
    def __init__(self):
        self.pool: Optional[Pool] = None
        self._lock = asyncio.Lock()
    
    async def connect(self) -> None:
        """初始化数据库连接池"""
        async with self._lock:
            if self.pool is None:
                try:
                    self.pool = await aiomysql.create_pool(
                        host=settings.DB_HOST,
                        port=settings.DB_PORT,
                        user=settings.DB_USER,
                        password=settings.DB_PASSWORD,
                        db=settings.DB_NAME,
                        minsize=settings.DB_POOL_MINSIZE,
                        maxsize=settings.DB_POOL_MAXSIZE,
                        autocommit=True,
                        charset='utf8mb4',
                        pool_recycle=3600,
                    )
                    logger.info(f"数据库连接池已初始化：{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
                except Exception as e:
                    logger.error(f"数据库连接失败：{e}")
                    raise
    
    async def disconnect(self) -> None:
        """关闭数据库连接池"""
        async with self._lock:
            if self.pool:
                self.pool.close()
                await self.pool.wait_closed()
                self.pool = None
                logger.info("数据库连接池已关闭")
    
    async def acquire(self):
        """获取数据库连接"""
        if self.pool is None:
            raise RuntimeError("数据库未连接")
        return await self.pool.acquire()
    
    def release(self, conn):
        """释放数据库连接"""
        if self.pool and conn:
            self.pool.release(conn)
    
    async def execute(
        self, 
        query: str, 
        params: Optional[tuple] = None,
        fetch: bool = False,
        fetchall: bool = False,
        commit: bool = True
    ) -> Any:
        """执行 SQL 查询
        
        Args:
            query: SQL 查询语句
            params: 查询参数
            fetch: 是否返回单行结果
            fetchall: 是否返回所有结果
            commit: 是否自动提交（用于事务）
        
        Returns:
            查询结果或最后插入 ID
        """
        conn = None
        try:
            conn = await self.acquire()
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, params or ())
                
                if fetch:
                    return await cur.fetchone()
                elif fetchall:
                    return await cur.fetchall()
                elif commit:
                    await conn.commit()
                    return cur.lastrowid
                else:
                    await conn.commit()
                    return None
        except Exception as e:
            logger.error(f"数据库执行错误：{e}, SQL: {query}")
            raise
        finally:
            if conn:
                self.release(conn)
    
    async def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """批量执行 SQL"""
        conn = None
        try:
            conn = await self.acquire()
            async with conn.cursor() as cur:
                await cur.executemany(query, params_list)
                await conn.commit()
        except Exception as e:
            logger.error(f"批量执行错误：{e}")
            raise
        finally:
            if conn:
                self.release(conn)


# 全局数据库池实例
db_pool = DatabasePool()


async def init_database() -> None:
    """初始化数据库连接"""
    await db_pool.connect()


async def close_database() -> None:
    """关闭数据库连接"""
    await db_pool.disconnect()


# ========== 任务相关操作 ==========

async def create_task(
    task_id: str,
    asin: str,
    site: str,
    max_pages: int,
    total_keywords: int
) -> None:
    """创建新任务"""
    query = """
        INSERT INTO tasks (id, asin, site, max_pages, status, total_keywords)
        VALUES (%s, %s, %s, %s, 'pending', %s)
    """
    await db_pool.execute(query, (task_id, asin, site, max_pages, total_keywords))


async def create_keywords(task_id: str, keywords: List[str]) -> None:
    """批量创建任务关键词"""
    if not keywords:
        return
    
    query = """
        INSERT INTO task_keywords (task_id, keyword, priority)
        VALUES (%s, %s, 0)
    """
    params_list = [(task_id, kw) for kw in keywords]
    await db_pool.execute_many(query, params_list)


async def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """获取任务详情"""
    query = """
        SELECT 
            id, asin, site, max_pages, status, total_keywords,
            processed_keywords, created_at, updated_at, completed_at, error_message
        FROM tasks
        WHERE id = %s
    """
    return await db_pool.execute(query, (task_id,), fetch=True)


async def get_task_list(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
) -> Dict[str, Any]:
    """获取任务列表"""
    offset = (page - 1) * page_size
    
    # 构建查询
    where_clause = ""
    params = []
    
    if status:
        where_clause = "WHERE status = %s"
        params.append(status)
    
    # 查询总数
    count_query = f"SELECT COUNT(*) as total FROM tasks {where_clause}"
    count_result = await db_pool.execute(count_query, tuple(params), fetch=True)
    total = count_result['total'] if count_result else 0
    
    # 查询数据
    query = f"""
        SELECT 
            id, asin, site, status, total_keywords, processed_keywords,
            created_at, completed_at
        FROM tasks
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    tasks = await db_pool.execute(query, tuple(params), fetchall=True)
    
    # 计算总页数
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    
    return {
        'tasks': tasks,
        'pagination': {
            'page': page,
            'pageSize': page_size,
            'total': total,
            'totalPages': total_pages
        }
    }


async def update_task_status(
    task_id: str,
    status: TaskStatus,
    error_message: Optional[str] = None
) -> None:
    """更新任务状态"""
    updates = ["status = %s", "updated_at = %s"]
    params = [status.value, datetime.utcnow()]
    
    if status == TaskStatus.COMPLETED:
        updates.append("completed_at = %s")
        params.append(datetime.utcnow())
    
    if error_message:
        updates.append("error_message = %s")
        params.append(error_message)
    
    query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = %s"
    params.append(task_id)
    
    await db_pool.execute(query, tuple(params))


async def increment_processed_keywords(task_id: str) -> None:
    """增加已处理关键词计数"""
    query = """
        UPDATE tasks 
        SET processed_keywords = processed_keywords + 1, updated_at = %s
        WHERE id = %s
    """
    await db_pool.execute(query, (datetime.utcnow(), task_id))


async def get_task_keywords(task_id: str) -> List[str]:
    """获取任务的关键词列表"""
    query = """
        SELECT keyword FROM task_keywords
        WHERE task_id = %s
        ORDER BY priority ASC, id ASC
    """
    results = await db_pool.execute(query, (task_id,), fetchall=True)
    return [row['keyword'] for row in results] if results else []


async def create_task_result(
    task_id: str,
    keyword: str,
    organic_page: Optional[int],
    organic_position: Optional[int],
    ad_page: Optional[int],
    ad_position: Optional[int],
    status: RankingStatus
) -> None:
    """创建任务结果"""
    query = """
        INSERT INTO task_results 
        (task_id, keyword, organic_page, organic_position, ad_page, ad_position, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    await db_pool.execute(
        query,
        (task_id, keyword, organic_page, organic_position, ad_page, ad_position, status.value)
    )


async def get_task_results(task_id: str) -> List[Dict[str, Any]]:
    """获取任务结果"""
    query = """
        SELECT 
            keyword, organic_page, organic_position,
            ad_page, ad_position, status, created_at
        FROM task_results
        WHERE task_id = %s
        ORDER BY keyword
    """
    return await db_pool.execute(query, (task_id,), fetchall=True) or []


async def cancel_task(task_id: str) -> bool:
    """取消任务（仅支持 pending 或 running 状态）"""
    query = """
        UPDATE tasks 
        SET status = 'cancelled', updated_at = %s, completed_at = %s
        WHERE id = %s AND status IN ('pending', 'running')
    """
    now = datetime.utcnow()
    result = await db_pool.execute(query, (now, now, task_id))
    return result > 0


async def check_database_health() -> bool:
    """检查数据库健康状态"""
    try:
        query = "SELECT 1"
        await db_pool.execute(query)
        return True
    except Exception as e:
        logger.error(f"数据库健康检查失败：{e}")
        return False
