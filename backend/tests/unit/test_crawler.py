"""
爬虫核心测试
测试 AmazonCrawler 类的功能
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
import asyncio

from backend.core.crawler import AmazonCrawler, CrawlResult, get_crawler


class TestCrawlResult:
    """测试 CrawlResult 类"""
    
    def test_crawl_result_initialization(self, mock_asin, mock_crawl_result):
        """测试爬取结果初始化"""
        result = CrawlResult(
            keyword="wireless earbuds",
            organic_page=3,
            organic_position=12,
            ad_page=1,
            ad_position=4,
            status="found"
        )
        
        assert result.keyword == "wireless earbuds"
        assert result.organic_page == 3
        assert result.organic_position == 12
        assert result.ad_page == 1
        assert result.ad_position == 4
        assert result.status == "found"
        assert result.error is None
        assert result.timestamp is not None
    
    def test_crawl_result_to_dict(self, mock_crawl_result):
        """测试爬取结果转换为字典"""
        result = CrawlResult(
            keyword="test keyword",
            organic_page=2,
            organic_position=8,
            ad_page=None,
            ad_position=None,
            status="ad_not_found"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['keyword'] == "test keyword"
        assert result_dict['organicPage'] == 2
        assert result_dict['organicPosition'] == 8
        assert result_dict['adPage'] is None
        assert result_dict['adPosition'] is None
        assert result_dict['status'] == "ad_not_found"
        assert 'timestamp' in result_dict
    
    def test_crawl_result_not_found(self):
        """测试未找到排名的结果"""
        result = CrawlResult(
            keyword="unknown product",
            organic_page=None,
            organic_position=None,
            ad_page=None,
            ad_position=None,
            status="not_found"
        )
        
        assert result.organic_page is None
        assert result.ad_page is None
        assert result.status == "not_found"


class TestAmazonCrawler:
    """测试 AmazonCrawler 类"""
    
    @pytest.fixture
    def crawler(self, mock_ua_rotator, mock_proxy_pool):
        """创建爬虫实例"""
        return AmazonCrawler()
    
    def test_crawler_initialization(self, crawler):
        """测试爬虫初始化"""
        assert crawler.ua_rotator is not None
        assert crawler.proxy_pool is not None
        assert crawler.browser is None
        assert crawler.context is None
    
    @pytest.mark.asyncio
    async def test_random_delay(self, crawler):
        """测试随机延迟"""
        import time
        
        start = time.time()
        await crawler.random_delay(min_seconds=0.1, max_seconds=0.2)
        elapsed = time.time() - start
        
        assert 0.1 <= elapsed <= 0.3  # 允许一定误差
    
    def test_build_search_url(self, crawler):
        """测试构建搜索 URL"""
        url = crawler._build_search_url("amazon.com", "wireless earbuds", page=1)
        
        assert "amazon.com" in url
        assert "wireless+earbuds" in url or "k=wireless" in url
        assert "page=1" in url
    
    def test_build_search_url_special_chars(self, crawler):
        """测试特殊字符的 URL 构建"""
        url = crawler._build_search_url("amazon.com", "wireless & earbuds", page=2)
        
        assert "page=2" in url
        # URL 应该包含编码后的特殊字符
    
    @pytest.mark.asyncio
    async def test_is_captcha_false(self, crawler):
        """测试验证码检测（无验证码）"""
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.content = AsyncMock(return_value="<html>Search results</html>")
        
        result = await crawler._is_captcha(mock_page)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_captcha_true_by_selector(self, crawler):
        """测试验证码检测（通过选择器）"""
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=MagicMock())
        
        result = await crawler._is_captcha(mock_page)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_captcha_true_by_content(self, crawler):
        """测试验证码检测（通过页面内容）"""
        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.content = AsyncMock(return_value="<html>Enter captcha to continue</html>")
        
        result = await crawler._is_captcha(mock_page)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_parse_rankings_found(self, crawler):
        """测试解析排名（找到结果）"""
        mock_page = AsyncMock()
        
        # 模拟搜索结果
        mock_result = AsyncMock()
        mock_result.get_attribute = AsyncMock(side_effect=[
            "B08N5WRWNW",  # data-asin
            None,  # 不会被调用
        ])
        
        mock_page.query_selector_all = AsyncMock(return_value=[mock_result])
        mock_page.wait_for_selector = AsyncMock()
        
        result = await crawler._parse_rankings(mock_page, "B08N5WRWNW", max_pages=5)
        
        assert result.organic_position == 1
        assert result.organic_page == 1
        assert result.status in ["found", "ad_not_found"]
    
    @pytest.mark.asyncio
    async def test_parse_rankings_timeout(self, crawler):
        """测试解析排名超时"""
        from playwright.async_api import TimeoutError as PlaywrightTimeout
        
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(side_effect=PlaywrightTimeout())
        
        result = await crawler._parse_rankings(mock_page, "B08N5WRWNW", max_pages=5)
        
        assert result.status == "error"
        assert "超时" in result.error
    
    @pytest.mark.asyncio
    async def test_crawl_keyword_success(self, mock_asin, mock_crawl_result):
        """测试爬取单个关键词成功"""
        with patch('backend.core.crawler.async_playwright') as mock_playwright:
            # 模拟 Playwright
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            
            mock_playwright.return_value.__aenter__.return_value.chromium.launch = AsyncMock(
                return_value=mock_browser
            )
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_context.close = AsyncMock()
            mock_browser.close = AsyncMock()
            
            # 模拟页面访问
            mock_page.goto = AsyncMock()
            mock_page.query_selector_all = AsyncMock(return_value=[])
            mock_page.wait_for_selector = AsyncMock()
            
            crawler = AmazonCrawler()
            semaphore = asyncio.Semaphore(3)
            
            result = await crawler.crawl_keyword(
                asin=mock_asin,
                keyword="test keyword",
                site="amazon.com",
                max_pages=3,
                semaphore=semaphore
            )
            
            assert result.keyword == "test keyword"
            assert mock_page.goto.called
    
    @pytest.mark.asyncio
    async def test_crawl_keyword_captcha(self, mock_asin):
        """测试爬取遇到验证码"""
        with patch('backend.core.crawler.async_playwright') as mock_playwright:
            mock_browser = AsyncMock()
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            
            mock_playwright.return_value.__aenter__.return_value.chromium.launch = AsyncMock(
                return_value=mock_browser
            )
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_context.close = AsyncMock()
            mock_browser.close = AsyncMock()
            
            mock_page.goto = AsyncMock()
            mock_page.query_selector = AsyncMock(return_value=MagicMock())  # 检测到验证码
            mock_page.wait_for_selector = AsyncMock()
            
            crawler = AmazonCrawler()
            semaphore = asyncio.Semaphore(3)
            
            result = await crawler.crawl_keyword(
                asin=mock_asin,
                keyword="test keyword",
                site="amazon.com",
                max_pages=3,
                semaphore=semaphore
            )
            
            assert result.status == "captcha"
            assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_crawl_keyword_exception(self, mock_asin):
        """测试爬取异常处理"""
        with patch('backend.core.crawler.async_playwright') as mock_playwright:
            mock_playwright.return_value.__aenter__.return_value.chromium.launch = AsyncMock(
                side_effect=Exception("Browser launch failed")
            )
            
            crawler = AmazonCrawler()
            semaphore = asyncio.Semaphore(3)
            
            result = await crawler.crawl_keyword(
                asin=mock_asin,
                keyword="test keyword",
                site="amazon.com",
                max_pages=3,
                semaphore=semaphore
            )
            
            assert result.status == "error"
            assert result.error is not None
    
    @pytest.mark.asyncio
    async def test_crawl_keywords_batch(self, mock_asin, mock_keywords):
        """测试批量爬取关键词"""
        with patch.object(AmazonCrawler, 'crawl_keyword') as mock_crawl:
            # 模拟每个关键词的爬取结果
            mock_crawl.side_effect = [
                CrawlResult(keyword="wireless earbuds", organic_page=1, organic_position=5, status="found"),
                CrawlResult(keyword="bluetooth headphones", organic_page=2, organic_position=10, status="found"),
                CrawlResult(keyword="noise cancelling earbuds", status="not_found"),
            ]
            
            crawler = AmazonCrawler()
            
            results = await crawler.crawl_keywords_batch(
                asin=mock_asin,
                keywords=mock_keywords,
                site="amazon.com",
                max_pages=5,
                max_concurrent=2
            )
            
            assert len(results) == 3
            assert results[0].keyword == "wireless earbuds"
            assert results[0].status == "found"
            assert results[2].status == "not_found"
    
    @pytest.mark.asyncio
    async def test_crawl_keywords_batch_with_exception(self, mock_asin, mock_keywords):
        """测试批量爬取包含异常"""
        with patch.object(AmazonCrawler, 'crawl_keyword') as mock_crawl:
            mock_crawl.side_effect = [
                CrawlResult(keyword="wireless earbuds", status="found"),
                Exception("Connection error"),
                CrawlResult(keyword="noise cancelling earbuds", status="found"),
            ]
            
            crawler = AmazonCrawler()
            
            results = await crawler.crawl_keywords_batch(
                asin=mock_asin,
                keywords=mock_keywords,
                site="amazon.com",
                max_pages=5
            )
            
            assert len(results) == 3
            assert results[0].status == "found"
            assert results[1].status == "error"  # 异常被转换为错误结果
            assert results[2].status == "found"


class TestGetCrawler:
    """测试 get_crawler 函数"""
    
    def test_get_crawler_returns_singleton(self):
        """测试获取爬虫实例"""
        crawler1 = get_crawler()
        crawler2 = get_crawler()
        
        # 应该是同一个实例
        assert crawler1 is crawler2
    
    def test_get_crawler_instance(self):
        """测试爬虫实例类型"""
        crawler = get_crawler()
        assert isinstance(crawler, AmazonCrawler)
