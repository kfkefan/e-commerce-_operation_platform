"""
Playwright 异步爬虫核心
提供亚马逊页面爬取功能，包含反爬策略
"""
import asyncio
import logging
import random
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeout

from backend.config import settings
from backend.core.ua_rotator import get_ua_rotator
from backend.core.proxy_manager import get_proxy_pool

logger = logging.getLogger(__name__)


class CrawlResult:
    """爬取结果"""
    
    def __init__(
        self,
        keyword: str,
        organic_page: Optional[int] = None,
        organic_position: Optional[int] = None,
        ad_page: Optional[int] = None,
        ad_position: Optional[int] = None,
        status: str = "found",
        error: Optional[str] = None
    ):
        self.keyword = keyword
        self.organic_page = organic_page
        self.organic_position = organic_position
        self.ad_page = ad_page
        self.ad_position = ad_position
        self.status = status
        self.error = error
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'keyword': self.keyword,
            'organicPage': self.organic_page,
            'organicPosition': self.organic_position,
            'adPage': self.ad_page,
            'adPosition': self.ad_position,
            'status': self.status,
            'timestamp': self.timestamp,
            'error': self.error
        }


class AmazonCrawler:
    """亚马逊爬虫"""
    
    def __init__(self):
        self.ua_rotator = get_ua_rotator()
        self.proxy_pool = get_proxy_pool()
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
    
    async def random_delay(self, min_seconds: float = None, max_seconds: float = None) -> None:
        """随机延迟"""
        min_delay = min_seconds or settings.REQUEST_DELAY_MIN
        max_delay = max_seconds or settings.REQUEST_DELAY_MAX
        delay = random.uniform(min_delay, max_delay)
        logger.debug(f"延迟 {delay:.2f} 秒")
        await asyncio.sleep(delay)
    
    def _build_search_url(self, site: str, keyword: str, page: int = 1) -> str:
        """构建搜索 URL"""
        from urllib.parse import quote
        base_url = f"https://www.{site}"
        encoded_keyword = quote(keyword)
        return f"{base_url}/s?k={encoded_keyword}&page={page}"
    
    async def _create_browser_context(self, use_proxy: bool = True) -> BrowserContext:
        """创建浏览器上下文"""
        if not self.browser:
            raise RuntimeError("浏览器未初始化")
        
        # 获取 UA
        ua = self.ua_rotator.get_next_ua() if settings.UA_ROTATION_ENABLED else None
        
        # 获取代理
        proxy = None
        if use_proxy and self.proxy_pool.is_enabled:
            proxy = self.proxy_pool.get_proxy()
            if proxy:
                logger.debug(f"使用代理：{proxy}")
        
        # 构建上下文选项
        context_options = {
            'user_agent': ua,
            'viewport': {'width': 1920, 'height': 1080},
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'bypass_csp': True,
            'java_script_enabled': True,
        }
        
        if proxy:
            context_options['proxy'] = {'server': proxy}
        
        return await self.browser.new_context(**context_options)
    
    async def _is_captcha(self, page: Page) -> bool:
        """检测是否遇到验证码"""
        # 检查验证码相关元素
        captcha_indicators = [
            'input[type="captcha"]',
            '[data-a-modal*="captcha"]',
            '.captcha-container',
            'form[action*="captcha"]',
        ]
        
        for selector in captcha_indicators:
            if await page.query_selector(selector):
                return True
        
        # 检查页面文本
        page_text = await page.content()
        if 'captcha' in page_text.lower() or 'verification' in page_text.lower():
            return True
        
        return False
    
    async def _parse_rankings(self, page: Page, asin: str, max_pages: int) -> CrawlResult:
        """解析页面排名"""
        asin_upper = asin.upper()
        
        # 等待搜索结果加载
        try:
            await page.wait_for_selector('[data-component-type="s-search-result"]', timeout=10000)
        except PlaywrightTimeout:
            logger.warning("搜索结果加载超时")
            return CrawlResult(
                keyword="",  # 由调用者设置
                status="error",
                error="搜索结果加载超时"
            )
        
        # 获取所有搜索结果
        results = await page.query_selector_all('[data-component-type="s-search-result"]')
        
        organic_page = None
        organic_position = None
        ad_page = None
        ad_position = None
        
        # 查找自然排名
        for idx, result in enumerate(results):
            try:
                # 获取 ASIN
                asin_attr = await result.get_attribute('data-asin')
                if not asin_attr:
                    # 尝试从链接中提取
                    link = await result.query_selector('a.a-link-normal')
                    if link:
                        href = await link.get_attribute('href')
                        if href and '/dp/' in href:
                            asin_attr = href.split('/dp/')[1].split('/')[0].split('?')[0].upper()
                
                if asin_attr and asin_attr.upper() == asin_upper:
                    # 计算位置（假设每页 48 个结果）
                    organic_position = idx + 1
                    organic_page = 1  # 当前页
                    logger.info(f"找到自然排名：第{organic_page}页，位置{organic_position}")
                    break
            except Exception as e:
                logger.debug(f"解析结果项失败：{e}")
                continue
        
        # 查找广告排名（ Sponsored ）
        try:
            sponsored_results = await page.query_selector_all('[data-component-type="s-search-result"][data-ad-sponsored="true"]')
            for idx, ad in enumerate(sponsored_results):
                asin_attr = await ad.get_attribute('data-asin')
                if asin_attr and asin_attr.upper() == asin_upper:
                    ad_position = idx + 1
                    ad_page = 1
                    logger.info(f"找到广告排名：第{ad_page}页，位置{ad_position}")
                    break
        except Exception as e:
            logger.debug(f"查找广告排名失败：{e}")
        
        # 确定状态
        if organic_page and ad_page:
            status = "found"
        elif organic_page:
            status = "ad_not_found"
        elif ad_page:
            status = "organic_not_found"
        else:
            status = "not_found"
        
        return CrawlResult(
            keyword="",  # 由调用者设置
            organic_page=organic_page,
            organic_position=organic_position,
            ad_page=ad_page,
            ad_position=ad_position,
            status=status
        )
    
    async def crawl_keyword(
        self,
        asin: str,
        keyword: str,
        site: str,
        max_pages: int,
        semaphore: asyncio.Semaphore
    ) -> CrawlResult:
        """
        爬取单个关键词的排名
        
        Args:
            asin: 产品 ASIN
            keyword: 关键词
            site: 亚马逊站点
            max_pages: 最大翻页数
            semaphore: 信号量用于并发控制
        
        Returns:
            爬取结果
        """
        async with semaphore:
            result = CrawlResult(keyword=keyword)
            
            try:
                # 创建浏览器
                async with async_playwright() as p:
                    self.browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            '--disable-blink-features=AutomationControlled',
                            '--no-sandbox',
                            '--disable-dev-shm-usage',
                        ]
                    )
                    
                    context = await self._create_browser_context()
                    
                    try:
                        page = await context.new_page()
                        
                        # 遍历页面
                        for page_num in range(1, max_pages + 1):
                            url = self._build_search_url(site, keyword, page_num)
                            logger.debug(f"爬取：{url}")
                            
                            # 访问页面
                            try:
                                await page.goto(url, wait_until='domcontentloaded', timeout=settings.PAGE_TIMEOUT)
                                await self.random_delay(1, 2)  # 页面加载后延迟
                            except PlaywrightTimeout:
                                logger.warning(f"页面加载超时：{url}")
                                result.status = "error"
                                result.error = "页面加载超时"
                                break
                            
                            # 检查验证码
                            if await self._is_captcha(page):
                                logger.warning(f"检测到验证码：{keyword}")
                                result.status = "captcha"
                                result.error = "检测到验证码"
                                break
                            
                            # 解析排名
                            page_result = await self._parse_rankings(page, asin, max_pages)
                            
                            if page_result.organic_position or page_result.ad_position:
                                # 找到排名
                                result.organic_page = page_result.organic_page
                                result.organic_position = page_result.organic_position
                                result.ad_page = page_result.ad_page
                                result.ad_position = page_result.ad_position
                                result.status = page_result.status
                                break
                            
                            # 随机延迟后继续下一页
                            if page_num < max_pages:
                                await self.random_delay()
                        
                    finally:
                        await context.close()
                        await self.browser.close()
                        self.browser = None
            
            except Exception as e:
                logger.error(f"爬取失败：{keyword}, 错误：{e}")
                result.status = "error"
                result.error = str(e)
            
            return result
    
    async def crawl_keywords_batch(
        self,
        asin: str,
        keywords: list,
        site: str,
        max_pages: int,
        max_concurrent: int = 3
    ) -> list:
        """
        批量爬取多个关键词
        
        Args:
            asin: 产品 ASIN
            keywords: 关键词列表
            site: 亚马逊站点
            max_pages: 最大翻页数
            max_concurrent: 最大并发数
        
        Returns:
            爬取结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        tasks = [
            self.crawl_keyword(asin, keyword, site, max_pages, semaphore)
            for keyword in keywords
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"关键词 {keywords[i]} 处理异常：{result}")
                processed_results.append(CrawlResult(
                    keyword=keywords[i],
                    status="error",
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results


# 全局爬虫实例
crawler = AmazonCrawler()


def get_crawler() -> AmazonCrawler:
    """获取爬虫实例"""
    return crawler
