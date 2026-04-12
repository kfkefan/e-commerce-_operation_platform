"""
任务服务测试
测试 TaskService 类的功能
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
import uuid

from backend.services.task_service import TaskService, get_task_service
from backend.models.schemas import TaskCreateRequest, TaskStatus


class TestTaskService:
    """测试 TaskService 类"""
    
    @pytest.fixture
    def task_service(self, mock_rank_finder):
        """创建任务服务实例"""
        return TaskService()
    
    def test_task_service_initialization(self, task_service):
        """测试任务服务初始化"""
        assert task_service.rank_finder is not None
        assert task_service._active_tasks == {}
    
    @pytest.mark.asyncio
    async def test_create_task_success(
        self, 
        task_service, 
        mock_rank_finder,
        mock_task_id
    ):
        """测试创建任务成功"""
        request = TaskCreateRequest(
            asin="B08N5WRWNW",
            keywords=["wireless earbuds", "bluetooth headphones"],
            maxPages=5,
            site="amazon.com"
        )
        
        with patch('backend.services.task_service.create_task', new_callable=AsyncMock) as mock_create, \
             patch('backend.services.task_service.create_keywords', new_callable=AsyncMock) as mock_create_kw, \
             patch('backend.services.task_service.get_task', return_value={
                 'id': mock_task_id,
                 'status': TaskStatus.PENDING.value,
                 'total_keywords': 2,
                 'processed_keywords': 0,
                 'created_at': '2026-04-12T10:00:00Z',
                 'updated_at': '2026-04-12T10:00:00Z',
                 'asin': 'B08N5WRWNW',
                 'site': 'amazon.com',
                 'max_pages': 5,
             }):
            
            task_id = await task_service.create_task(request)
            
            assert task_id is not None
            assert len(task_id) == 36  # UUID 长度
            mock_create.assert_called_once()
            mock_create_kw.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_task_validates_asin(self, task_service):
        """测试 ASIN 验证"""
        # 无效 ASIN（长度不对）
        with pytest.raises(ValueError) as exc_info:
            TaskCreateRequest(
                asin="INVALID",
                keywords=["test"],
                maxPages=5
            )
        
        assert "10 位" in str(exc_info.value) or "10" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_task_validates_keywords_empty(self, task_service):
        """测试关键词空列表验证"""
        with pytest.raises(ValueError) as exc_info:
            TaskCreateRequest(
                asin="B08N5WRWNW",
                keywords=[],
                maxPages=5
            )
        
        assert "至少" in str(exc_info.value) or "空" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_task_validates_keywords_too_many(self, task_service):
        """测试关键词数量超限验证"""
        with pytest.raises(ValueError) as exc_info:
            TaskCreateRequest(
                asin="B08N5WRWNW",
                keywords=["kw"] * 101,
                maxPages=5
            )
        
        assert "100" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_task_validates_site(self, task_service):
        """测试站点验证"""
        with pytest.raises(ValueError) as exc_info:
            TaskCreateRequest(
                asin="B08N5WRWNW",
                keywords=["test"],
                site="amazon.invalid"
            )
        
        assert "不支持" in str(exc_info.value) or "站点" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_task_detail_success(self, task_service, mock_task_id):
        """测试获取任务详情成功"""
        mock_task_data = {
            'id': mock_task_id,
            'status': TaskStatus.RUNNING.value,
            'asin': 'B08N5WRWNW',
            'site': 'amazon.com',
            'max_pages': 5,
            'total_keywords': 10,
            'processed_keywords': 6,
            'created_at': '2026-04-12T10:00:00Z',
            'updated_at': '2026-04-12T10:03:00Z',
            'error_message': None,
        }
        
        with patch('backend.services.task_service.get_task', return_value=mock_task_data):
            result = await task_service.get_task_detail(mock_task_id)
            
            assert result is not None
            assert result['taskId'] == mock_task_id
            assert result['status'] == TaskStatus.RUNNING.value
            assert result['progress'] == 60  # 6/10 = 60%
            assert result['totalKeywords'] == 10
            assert result['processedKeywords'] == 6
    
    @pytest.mark.asyncio
    async def test_get_task_detail_not_found(self, task_service, mock_task_id):
        """测试获取不存在的任务"""
        with patch('backend.services.task_service.get_task', return_value=None):
            result = await task_service.get_task_detail(mock_task_id)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_task_list_paginated(self, task_service, mock_task_id):
        """测试获取分页任务列表"""
        mock_result = {
            'tasks': [
                {
                    'id': mock_task_id,
                    'status': 'completed',
                    'created_at': '2026-04-12T10:00:00Z',
                    'completed_at': '2026-04-12T10:05:00Z',
                    'total_keywords': 10,
                    'processed_keywords': 10,
                }
            ],
            'pagination': {
                'page': 1,
                'pageSize': 20,
                'total': 1,
                'totalPages': 1
            }
        }
        
        with patch('backend.services.task_service.get_task_list', return_value=mock_result):
            result = await task_service.get_task_list_paginated(
                status='completed',
                page=1,
                page_size=20
            )
            
            assert 'tasks' in result
            assert 'pagination' in result
            assert len(result['tasks']) == 1
            assert result['tasks'][0]['taskId'] == mock_task_id
    
    @pytest.mark.asyncio
    async def test_cancel_task_success(self, task_service, mock_task_id):
        """测试取消任务成功"""
        mock_task_data = {
            'id': mock_task_id,
            'status': TaskStatus.RUNNING.value,
            'total_keywords': 10,
            'processed_keywords': 5,
        }
        
        with patch('backend.services.task_service.get_task', return_value=mock_task_data), \
             patch('backend.services.task_service.db_cancel_task', return_value=True) as mock_cancel:
            
            result = await task_service.cancel_task(mock_task_id)
            
            assert result is True
            mock_cancel.assert_called_once_with(mock_task_id)
    
    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self, task_service, mock_task_id):
        """测试取消不存在的任务"""
        with patch('backend.services.task_service.get_task', return_value=None):
            result = await task_service.cancel_task(mock_task_id)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_cancel_task_already_completed(self, task_service, mock_task_id):
        """测试取消已完成的任务"""
        mock_task_data = {
            'id': mock_task_id,
            'status': TaskStatus.COMPLETED.value,
        }
        
        with patch('backend.services.task_service.get_task', return_value=mock_task_data), \
             patch('backend.services.task_service.db_cancel_task', return_value=False) as mock_cancel:
            
            result = await task_service.cancel_task(mock_task_id)
            
            assert result is False
            mock_cancel.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_task_results_success(self, task_service, mock_task_id):
        """测试获取任务结果成功"""
        mock_task_data = {
            'id': mock_task_id,
            'asin': 'B08N5WRWNW',
            'site': 'amazon.com',
            'completed_at': '2026-04-12T10:05:00Z',
        }
        
        mock_results = [
            {
                'keyword': 'wireless earbuds',
                'organic_page': 1,
                'organic_position': 5,
                'ad_page': None,
                'ad_position': None,
                'status': 'found',
                'created_at': '2026-04-12T10:02:00Z',
            }
        ]
        
        with patch('backend.services.task_service.get_task', return_value=mock_task_data), \
             patch('backend.services.task_service.get_task_results', return_value=mock_results):
            
            result = await task_service.get_task_results(mock_task_id)
            
            assert result is not None
            assert result['taskId'] == mock_task_id
            assert len(result['results']) == 1
            assert result['results'][0]['keyword'] == 'wireless earbuds'
    
    @pytest.mark.asyncio
    async def test_get_active_task_count(self, task_service):
        """测试获取活跃任务数"""
        task_service._active_tasks = {
            'task1': MagicMock(),
            'task2': MagicMock(),
            'task3': MagicMock(),
        }
        
        count = task_service.get_active_task_count()
        
        assert count == 3
    
    @pytest.mark.asyncio
    async def test_execute_task_exception(self, task_service, mock_task_id):
        """测试任务执行异常处理"""
        with patch.object(task_service.rank_finder, 'process_task', side_effect=Exception("Test error")), \
             patch('backend.services.task_service.update_task_status', new_callable=AsyncMock) as mock_update:
            
            # _execute_task 是私有方法，但我们可以测试它
            try:
                await task_service._execute_task(mock_task_id)
            except:
                pass  # 异常应该被内部捕获
            
            # 验证错误状态被更新
            mock_update.assert_called()


class TestTaskCreateRequest:
    """测试 TaskCreateRequest 模型"""
    
    def test_valid_request(self):
        """测试有效的请求"""
        request = TaskCreateRequest(
            asin="B08N5WRWNW",
            keywords=["test keyword"],
            maxPages=5,
            site="amazon.com"
        )
        
        assert request.asin == "B08N5WRWNW"
        assert request.keywords == ["test keyword"]
        assert request.maxPages == 5
        assert request.site == "amazon.com"
    
    def test_asin_uppercase_conversion(self):
        """测试 ASIN 自动转大写"""
        request = TaskCreateRequest(
            asin="b08n5wrwnw",
            keywords=["test"]
        )
        
        assert request.asin == "B08N5WRWNW"
    
    def test_default_values(self):
        """测试默认值"""
        request = TaskCreateRequest(
            asin="B08N5WRWNW",
            keywords=["test"]
        )
        
        assert request.maxPages == 5
        assert request.site == "amazon.com"


class TestGetTaskService:
    """测试 get_task_service 函数"""
    
    def test_get_task_service_returns_singleton(self):
        """测试获取任务服务实例"""
        service1 = get_task_service()
        service2 = get_task_service()
        
        # 应该是同一个实例
        assert service1 is service2
    
    def test_get_task_service_instance(self):
        """测试任务服务实例类型"""
        service = get_task_service()
        assert isinstance(service, TaskService)
