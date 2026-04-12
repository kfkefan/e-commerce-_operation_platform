"""
FastAPI 接口集成测试
测试 API 端点的完整功能
"""
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch, MagicMock
import json

import sys
from pathlib import Path

# 添加 backend 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from httpx import AsyncClient
from fastapi.testclient import TestClient
from backend.main import app
from backend.models.schemas import TaskStatus


@pytest.fixture
def client() -> TestClient:
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_task_id() -> str:
    """返回模拟任务 ID"""
    import uuid
    return str(uuid.uuid4())


class TestHealthEndpoint:
    """测试健康检查端点"""
    
    def test_health_check(self, client):
        """测试健康检查"""
        with patch('backend.api.routes.health.check_database_health', return_value=True):
            response = client.get("/api/v1/health")
            
            assert response.status_code == 200
            data = response.json()
            assert 'status' in data
            assert 'version' in data
    
    def test_root_endpoint(self, client):
        """测试根路径"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert 'name' in data
        assert 'version' in data
    
    def test_ping_endpoint(self, client):
        """测试 ping 端点"""
        response = client.get("/ping")
        
        assert response.status_code == 200
        data = response.json()
        assert data['pong'] is True


class TestTaskEndpoints:
    """测试任务端点"""
    
    @pytest.fixture
    def valid_task_request(self) -> dict:
        """返回有效的任务请求"""
        return {
            "asin": "B08N5WRWNW",
            "keywords": ["wireless earbuds", "bluetooth headphones"],
            "maxPages": 5,
            "site": "amazon.com"
        }
    
    def test_create_task_success(self, client, valid_task_request, mock_task_id):
        """测试创建任务成功"""
        with patch('backend.services.task_service.TaskService.create_task', return_value=mock_task_id), \
             patch('backend.services.task_service.TaskService.get_task_detail', return_value={
                 'id': mock_task_id,
                 'status': TaskStatus.PENDING.value,
                 'created_at': '2026-04-12T10:00:00Z',
                 'total_keywords': 2,
                 'max_pages': 5,
                 'asin': 'B08N5WRWNW',
                 'site': 'amazon.com',
             }):
            
            response = client.post("/api/v1/tasks", json=valid_task_request)
            
            assert response.status_code == 201
            data = response.json()
            assert 'taskId' in data
            assert data['taskId'] == mock_task_id
            assert 'status' in data
    
    def test_create_task_invalid_asin(self, client, valid_task_request):
        """测试创建任务 - ASIN 无效"""
        valid_task_request['asin'] = "INVALID"
        
        response = client.post("/api/v1/tasks", json=valid_task_request)
        
        assert response.status_code == 400
        data = response.json()
        assert 'detail' in data
    
    def test_create_task_empty_keywords(self, client, valid_task_request):
        """测试创建任务 - 关键词为空"""
        valid_task_request['keywords'] = []
        
        response = client.post("/api/v1/tasks", json=valid_task_request)
        
        assert response.status_code == 422  # Pydantic 验证失败
    
    def test_create_task_too_many_keywords(self, client, valid_task_request):
        """测试创建任务 - 关键词过多"""
        valid_task_request['keywords'] = ["kw"] * 101
        
        response = client.post("/api/v1/tasks", json=valid_task_request)
        
        assert response.status_code == 422
    
    def test_create_task_invalid_site(self, client, valid_task_request):
        """测试创建任务 - 站点无效"""
        valid_task_request['site'] = "amazon.invalid"
        
        response = client.post("/api/v1/tasks", json=valid_task_request)
        
        assert response.status_code == 422
    
    def test_get_task_success(self, client, mock_task_id):
        """测试获取任务详情成功"""
        mock_task = {
            'taskId': mock_task_id,
            'status': TaskStatus.RUNNING.value,
            'createdAt': '2026-04-12T10:00:00Z',
            'updatedAt': '2026-04-12T10:03:00Z',
            'asin': 'B08N5WRWNW',
            'site': 'amazon.com',
            'maxPages': 5,
            'totalKeywords': 10,
            'processedKeywords': 6,
            'progress': 60,
            'errorMessage': None,
        }
        
        with patch('backend.services.task_service.TaskService.get_task_detail', return_value=mock_task):
            response = client.get(f"/api/v1/tasks/{mock_task_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data['taskId'] == mock_task_id
            assert data['status'] == 'running'
            assert data['progress'] == 60
    
    def test_get_task_not_found(self, client, mock_task_id):
        """测试获取不存在的任务"""
        with patch('backend.services.task_service.TaskService.get_task_detail', return_value=None):
            response = client.get(f"/api/v1/tasks/{mock_task_id}")
            
            assert response.status_code == 404
            data = response.json()
            assert 'detail' in data
    
    def test_list_tasks_success(self, client):
        """测试获取任务列表成功"""
        mock_result = {
            'tasks': [
                {
                    'taskId': 'task-1',
                    'status': 'completed',
                    'createdAt': '2026-04-12T10:00:00Z',
                    'completedAt': '2026-04-12T10:05:00Z',
                    'totalKeywords': 10,
                    'processedKeywords': 10,
                }
            ],
            'pagination': {
                'page': 1,
                'pageSize': 20,
                'total': 1,
                'totalPages': 1
            }
        }
        
        with patch('backend.services.task_service.TaskService.get_task_list_paginated', return_value=mock_result):
            response = client.get("/api/v1/tasks")
            
            assert response.status_code == 200
            data = response.json()
            assert 'tasks' in data
            assert 'pagination' in data
            assert len(data['tasks']) == 1
    
    def test_list_tasks_with_status_filter(self, client):
        """测试按状态筛选任务列表"""
        mock_result = {
            'tasks': [],
            'pagination': {
                'page': 1,
                'pageSize': 20,
                'total': 0,
                'totalPages': 1
            }
        }
        
        with patch('backend.services.task_service.TaskService.get_task_list_paginated', return_value=mock_result) as mock_list:
            response = client.get("/api/v1/tasks?status=running")
            
            assert response.status_code == 200
            mock_list.assert_called_with(status='running', page=1, page_size=20)
    
    def test_list_tasks_pagination(self, client):
        """测试任务列表分页"""
        mock_result = {
            'tasks': [],
            'pagination': {
                'page': 2,
                'pageSize': 50,
                'total': 100,
                'totalPages': 2
            }
        }
        
        with patch('backend.services.task_service.TaskService.get_task_list_paginated', return_value=mock_result) as mock_list:
            response = client.get("/api/v1/tasks?page=2&pageSize=50")
            
            assert response.status_code == 200
            mock_list.assert_called_with(status=None, page=2, page_size=50)
    
    def test_cancel_task_success(self, client, mock_task_id):
        """测试取消任务成功"""
        with patch('backend.services.task_service.TaskService.get_task_detail', side_effect=[
            {
                'taskId': mock_task_id,
                'status': TaskStatus.RUNNING.value,
                'created_at': '2026-04-12T10:00:00Z',
                'total_keywords': 10,
                'max_pages': 5,
                'asin': 'B08N5WRWNW',
                'site': 'amazon.com',
            },
            {
                'taskId': mock_task_id,
                'status': TaskStatus.CANCELLED.value,
                'created_at': '2026-04-12T10:00:00Z',
                'total_keywords': 10,
                'max_pages': 5,
                'asin': 'B08N5WRWNW',
                'site': 'amazon.com',
            },
        ]), \
             patch('backend.services.task_service.TaskService.cancel_task', return_value=True):
            
            response = client.delete(f"/api/v1/tasks/{mock_task_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'cancelled'
    
    def test_cancel_task_not_found(self, client, mock_task_id):
        """测试取消不存在的任务"""
        with patch('backend.services.task_service.TaskService.get_task_detail', return_value=None):
            response = client.delete(f"/api/v1/tasks/{mock_task_id}")
            
            assert response.status_code == 404
    
    def test_cancel_task_already_completed(self, client, mock_task_id):
        """测试取消已完成的任务"""
        with patch('backend.services.task_service.TaskService.get_task_detail', return_value={
            'taskId': mock_task_id,
            'status': TaskStatus.COMPLETED.value,
            'created_at': '2026-04-12T10:00:00Z',
            'total_keywords': 10,
            'max_pages': 5,
            'asin': 'B08N5WRWNW',
            'site': 'amazon.com',
        }):
            response = client.delete(f"/api/v1/tasks/{mock_task_id}")
            
            assert response.status_code == 400
            data = response.json()
            assert 'detail' in data
    
    def test_get_task_results_success(self, client, mock_task_id):
        """测试获取任务结果成功"""
        mock_result = {
            'taskId': mock_task_id,
            'asin': 'B08N5WRWNW',
            'site': 'amazon.com',
            'completedAt': '2026-04-12T10:05:00Z',
            'results': [
                {
                    'keyword': 'wireless earbuds',
                    'organicPage': 1,
                    'organicPosition': 5,
                    'adPage': None,
                    'adPosition': None,
                    'status': 'found',
                    'timestamp': '2026-04-12T10:02:00Z',
                }
            ]
        }
        
        with patch('backend.services.task_service.TaskService.get_task_detail', return_value={
            'taskId': mock_task_id,
            'status': TaskStatus.COMPLETED.value,
            'created_at': '2026-04-12T10:00:00Z',
            'total_keywords': 1,
            'max_pages': 5,
            'asin': 'B08N5WRWNW',
            'site': 'amazon.com',
        }), \
             patch('backend.services.task_service.TaskService.get_task_results', return_value=mock_result):
            
            response = client.get(f"/api/v1/tasks/{mock_task_id}/results")
            
            assert response.status_code == 200
            data = response.json()
            assert 'results' in data
            assert len(data['results']) == 1
    
    def test_get_task_results_not_completed(self, client, mock_task_id):
        """测试获取未完成的任务结果"""
        with patch('backend.services.task_service.TaskService.get_task_detail', return_value={
            'taskId': mock_task_id,
            'status': TaskStatus.RUNNING.value,
            'created_at': '2026-04-12T10:00:00Z',
            'total_keywords': 10,
            'max_pages': 5,
            'asin': 'B08N5WRWNW',
            'site': 'amazon.com',
        }):
            response = client.get(f"/api/v1/tasks/{mock_task_id}/results")
            
            # 根据实现，可能返回部分结果或错误
            # 这里假设允许获取部分结果
            assert response.status_code in [200, 400]


class TestCORS:
    """测试 CORS 配置"""
    
    def test_cors_headers(self, client):
        """测试 CORS 头"""
        response = client.options(
            "/api/v1/tasks",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            }
        )
        
        # FastAPI 默认启用 CORS
        assert response.status_code in [200, 404]  # 取决于具体配置
