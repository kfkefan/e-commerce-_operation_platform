"""
数据库集成测试
测试数据库操作功能
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import sys
from pathlib import Path

# 添加 backend 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.models.schemas import TaskStatus, RankingStatus
from backend.services.database import (
    DatabasePool,
    create_task,
    create_keywords,
    get_task,
    get_task_list,
    update_task_status,
    increment_processed_keywords,
    get_task_keywords,
    create_task_result,
    get_task_results,
    cancel_task,
    check_database_health,
)


class TestDatabasePool:
    """测试数据库连接池"""
    
    def test_database_pool_initialization(self):
        """测试数据库池初始化"""
        pool = DatabasePool()
        
        assert pool.pool is None
        assert pool._lock is not None
    
    @pytest.mark.asyncio
    async def test_database_pool_connect(self):
        """测试数据库池连接"""
        with patch('backend.services.database.aiomysql.create_pool', new_callable=AsyncMock) as mock_create:
            mock_pool = AsyncMock()
            mock_create.return_value = mock_pool
            
            pool = DatabasePool()
            await pool.connect()
            
            assert pool.pool is not None
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_pool_disconnect(self):
        """测试数据库池断开连接"""
        with patch('backend.services.database.aiomysql.create_pool', new_callable=AsyncMock) as mock_create:
            mock_pool = AsyncMock()
            mock_pool.close = AsyncMock()
            mock_pool.wait_closed = AsyncMock()
            mock_create.return_value = mock_pool
            
            pool = DatabasePool()
            await pool.connect()
            await pool.disconnect()
            
            assert pool.pool is None
            mock_pool.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_pool_execute(self):
        """测试数据库池执行查询"""
        with patch('backend.services.database.aiomysql.create_pool', new_callable=AsyncMock) as mock_create:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            mock_cursor.fetchone = AsyncMock(return_value={'id': 1})
            mock_conn.cursor = MagicMock(return_value=mock_cursor)
            mock_conn.commit = AsyncMock()
            mock_pool.acquire = AsyncMock(return_value=mock_conn)
            mock_pool.release = MagicMock()
            mock_create.return_value = mock_pool
            
            pool = DatabasePool()
            await pool.connect()
            
            result = await pool.execute("SELECT * FROM tasks WHERE id = %s", (1,), fetch=True)
            
            assert result is not None
            mock_cursor.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_database_pool_execute_many(self):
        """测试数据库池批量执行"""
        with patch('backend.services.database.aiomysql.create_pool', new_callable=AsyncMock) as mock_create:
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            mock_conn.cursor = MagicMock(return_value=mock_cursor)
            mock_conn.commit = AsyncMock()
            mock_pool.acquire = AsyncMock(return_value=mock_conn)
            mock_pool.release = MagicMock()
            mock_create.return_value = mock_pool
            
            pool = DatabasePool()
            await pool.connect()
            
            await pool.execute_many(
                "INSERT INTO keywords (task_id, keyword) VALUES (%s, %s)",
                [(1, "kw1"), (1, "kw2")]
            )
            
            mock_cursor.executemany.assert_called_once()


class TestTaskOperations:
    """测试任务数据库操作"""
    
    @pytest.fixture
    def mock_pool(self):
        """模拟数据库池"""
        with patch('backend.services.database.db_pool') as mock:
            mock.execute = AsyncMock()
            mock.execute_many = AsyncMock()
            yield mock
    
    @pytest.mark.asyncio
    async def test_create_task(self, mock_pool):
        """测试创建任务"""
        await create_task(
            task_id="test-uuid",
            asin="B08N5WRWNW",
            site="amazon.com",
            max_pages=5,
            total_keywords=10
        )
        
        mock_pool.execute.assert_called_once()
        call_args = mock_pool.execute.call_args
        assert "INSERT INTO tasks" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_create_keywords(self, mock_pool):
        """测试创建关键词"""
        await create_keywords("test-uuid", ["kw1", "kw2", "kw3"])
        
        mock_pool.execute_many.assert_called_once()
        call_args = mock_pool.execute_many.call_args
        assert len(call_args[0][1]) == 3  # 3 个关键词
    
    @pytest.mark.asyncio
    async def test_create_keywords_empty(self, mock_pool):
        """测试创建空关键词列表"""
        await create_keywords("test-uuid", [])
        
        mock_pool.execute_many.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_task(self, mock_pool):
        """测试获取任务"""
        mock_task = {
            'id': 'test-uuid',
            'asin': 'B08N5WRWNW',
            'status': 'pending',
        }
        mock_pool.execute.return_value = mock_task
        
        result = await get_task("test-uuid")
        
        assert result == mock_task
        mock_pool.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_task_list(self, mock_pool):
        """测试获取任务列表"""
        mock_pool.execute.side_effect = [
            {'total': 2},  # COUNT 查询
            [
                {'id': 'task1', 'status': 'completed'},
                {'id': 'task2', 'status': 'running'},
            ]  # 实际数据查询
        ]
        
        result = await get_task_list(status=None, page=1, page_size=20)
        
        assert 'tasks' in result
        assert 'pagination' in result
        assert result['pagination']['total'] == 2
        assert len(result['tasks']) == 2
    
    @pytest.mark.asyncio
    async def test_get_task_list_with_status(self, mock_pool):
        """测试按状态获取任务列表"""
        mock_pool.execute.side_effect = [
            {'total': 1},
            [{'id': 'task1', 'status': 'running'}]
        ]
        
        result = await get_task_list(status='running', page=1, page_size=20)
        
        assert result['pagination']['total'] == 1
    
    @pytest.mark.asyncio
    async def test_update_task_status(self, mock_pool):
        """测试更新任务状态"""
        await update_task_status("test-uuid", TaskStatus.RUNNING)
        
        mock_pool.execute.assert_called_once()
        call_args = mock_pool.execute.call_args
        assert "UPDATE tasks" in call_args[0][0]
        assert "status = %s" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_update_task_status_completed(self, mock_pool):
        """测试更新任务状态为已完成"""
        await update_task_status("test-uuid", TaskStatus.COMPLETED)
        
        call_args = mock_pool.execute.call_args
        assert "completed_at" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_update_task_status_with_error(self, mock_pool):
        """测试更新任务状态带错误信息"""
        await update_task_status("test-uuid", TaskStatus.FAILED, "Error message")
        
        call_args = mock_pool.execute.call_args
        assert "error_message" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_increment_processed_keywords(self, mock_pool):
        """测试增加已处理关键词计数"""
        await increment_processed_keywords("test-uuid")
        
        mock_pool.execute.assert_called_once()
        call_args = mock_pool.execute.call_args
        assert "processed_keywords = processed_keywords + 1" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_get_task_keywords(self, mock_pool):
        """测试获取任务关键词"""
        mock_pool.execute.return_value = [
            {'keyword': 'kw1'},
            {'keyword': 'kw2'},
            {'keyword': 'kw3'},
        ]
        
        result = await get_task_keywords("test-uuid")
        
        assert len(result) == 3
        assert result[0] == 'kw1'
    
    @pytest.mark.asyncio
    async def test_get_task_keywords_empty(self, mock_pool):
        """测试获取空关键词列表"""
        mock_pool.execute.return_value = None
        
        result = await get_task_keywords("test-uuid")
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_create_task_result(self, mock_pool):
        """测试创建任务结果"""
        await create_task_result(
            task_id="test-uuid",
            keyword="wireless earbuds",
            organic_page=1,
            organic_position=5,
            ad_page=None,
            ad_position=None,
            status=RankingStatus.FOUND
        )
        
        mock_pool.execute.assert_called_once()
        call_args = mock_pool.execute.call_args
        assert "INSERT INTO task_results" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_get_task_results(self, mock_pool):
        """测试获取任务结果"""
        mock_pool.execute.return_value = [
            {
                'keyword': 'kw1',
                'organic_page': 1,
                'organic_position': 5,
                'status': 'found',
                'created_at': '2026-04-12T10:00:00Z',
            }
        ]
        
        result = await get_task_results("test-uuid")
        
        assert len(result) == 1
        assert result[0]['keyword'] == 'kw1'
    
    @pytest.mark.asyncio
    async def test_cancel_task_success(self, mock_pool):
        """测试取消任务成功"""
        mock_pool.execute.return_value = 1  # 影响 1 行
        
        result = await cancel_task("test-uuid")
        
        assert result is True
        call_args = mock_pool.execute.call_args
        assert "status = 'cancelled'" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self, mock_pool):
        """测试取消不存在的任务"""
        mock_pool.execute.return_value = 0  # 没有影响的行
        
        result = await cancel_task("non-existent-uuid")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_database_health_success(self, mock_pool):
        """测试数据库健康检查成功"""
        mock_pool.execute.return_value = None
        
        result = await check_database_health()
        
        assert result is True
        mock_pool.execute.assert_called_with("SELECT 1")
    
    @pytest.mark.asyncio
    async def test_check_database_health_failure(self, mock_pool):
        """测试数据库健康检查失败"""
        mock_pool.execute.side_effect = Exception("Connection error")
        
        result = await check_database_health()
        
        assert result is False


class TestDatabaseTransactions:
    """测试数据库事务"""
    
    @pytest.fixture
    def mock_pool(self):
        """模拟数据库池"""
        with patch('backend.services.database.db_pool') as mock:
            mock.execute = AsyncMock()
            mock.execute_many = AsyncMock()
            mock.acquire = AsyncMock()
            mock.release = MagicMock()
            yield mock
    
    @pytest.mark.asyncio
    async def test_task_creation_transaction(self, mock_pool):
        """测试任务创建事务"""
        # 模拟成功的事务
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()
        mock_pool.acquire.return_value = mock_conn
        
        # 创建任务和关键词
        await create_task("test-uuid", "B08N5WRWNW", "amazon.com", 5, 10)
        await create_keywords("test-uuid", ["kw1", "kw2"])
        
        # 验证提交被调用
        assert mock_conn.commit.called


class TestDatabaseErrorHandling:
    """测试数据库错误处理"""
    
    @pytest.fixture
    def mock_pool_error(self):
        """模拟数据库池错误"""
        with patch('backend.services.database.db_pool') as mock:
            mock.execute = AsyncMock(side_effect=Exception("DB Error"))
            yield mock
    
    @pytest.mark.asyncio
    async def test_get_task_error(self, mock_pool_error):
        """测试获取任务错误处理"""
        with pytest.raises(Exception) as exc_info:
            await get_task("test-uuid")
        
        assert "DB Error" in str(exc_info.value)
