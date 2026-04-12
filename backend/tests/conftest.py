"""
Pytest 配置和共享 fixtures
"""
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import sys
from pathlib import Path

# 添加 backend 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.schemas import TaskStatus, RankingStatus


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_asin() -> str:
    """返回有效的 ASIN"""
    return "B08N5WRWNW"


@pytest.fixture
def mock_keywords() -> list:
    """返回测试关键词列表"""
    return [
        "wireless earbuds",
        "bluetooth headphones",
        "noise cancelling earbuds"
    ]


@pytest.fixture
def mock_task_id() -> str:
    """返回模拟任务 ID"""
    return str(uuid.uuid4())


@pytest.fixture
def mock_task_data(mock_asin, mock_task_id) -> dict:
    """返回模拟任务数据"""
    return {
        'id': mock_task_id,
        'asin': mock_asin,
        'site': 'amazon.com',
        'max_pages': 5,
        'status': TaskStatus.PENDING.value,
        'total_keywords': 3,
        'processed_keywords': 0,
        'created_at': '2026-04-12T10:00:00Z',
        'updated_at': '2026-04-12T10:00:00Z',
        'completed_at': None,
        'error_message': None,
    }


@pytest.fixture
def mock_crawl_result() -> dict:
    """返回模拟爬取结果"""
    return {
        'keyword': 'wireless earbuds',
        'organic_page': 3,
        'organic_position': 12,
        'ad_page': 1,
        'ad_position': 4,
        'status': 'found',
        'error': None,
        'timestamp': '2026-04-12T10:02:00Z',
    }


@pytest.fixture
def mock_db_pool():
    """模拟数据库连接池"""
    with patch('backend.services.database.db_pool') as mock_pool:
        mock_pool.execute = AsyncMock()
        mock_pool.execute_many = AsyncMock()
        mock_pool.acquire = AsyncMock()
        mock_pool.release = MagicMock()
        yield mock_pool


@pytest.fixture
def mock_rank_finder():
    """模拟排名查找器"""
    with patch('backend.services.task_service.get_rank_finder') as mock_factory:
        mock_finder = MagicMock()
        mock_finder.process_task = AsyncMock()
        mock_finder.cancel_task = MagicMock()
        mock_factory.return_value = mock_finder
        yield mock_finder


@pytest.fixture
def mock_crawler():
    """模拟爬虫"""
    with patch('backend.core.rank_finder.get_crawler') as mock_factory:
        mock_crawler_instance = MagicMock()
        mock_crawler_instance.crawl_keywords_batch = AsyncMock()
        mock_factory.return_value = mock_crawler_instance
        yield mock_crawler_instance


@pytest.fixture
def mock_ua_rotator():
    """模拟 UA 轮换器"""
    with patch('backend.core.ua_rotator.get_ua_rotator') as mock_factory:
        mock_rotator = MagicMock()
        mock_rotator.get_next_ua = MagicMock(return_value="Mozilla/5.0 Chrome/120.0.0.0")
        mock_rotator.get_random_ua = MagicMock(return_value="Mozilla/5.0 Firefox/121.0")
        mock_rotator.user_agents = [
            "Mozilla/5.0 Chrome/120.0.0.0",
            "Mozilla/5.0 Firefox/121.0",
        ]
        mock_factory.return_value = mock_rotator
        yield mock_rotator


@pytest.fixture
def mock_proxy_pool():
    """模拟代理池"""
    with patch('backend.core.crawler.get_proxy_pool') as mock_factory:
        mock_pool = MagicMock()
        mock_pool.is_enabled = False
        mock_pool.get_proxy = MagicMock(return_value=None)
        mock_factory.return_value = mock_pool
        yield mock_pool


@pytest_asyncio.fixture
async def mock_task_service(mock_rank_finder):
    """模拟任务服务"""
    from backend.services.task_service import TaskService
    service = TaskService()
    yield service
