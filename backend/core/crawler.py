"""
Playwright 异步爬虫核心 - 增强反爬版本
提供亚马逊页面爬取功能，集成 stealth 反检测
"""
import asyncio
import logging
import random
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeout
from playwright_stealth import stealth_async

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
    """亚马逊爬虫 - 增强反爬版本"""
    
    def __init__(self):
        self.ua_rotator = get_ua_rotator()
        self.proxy_pool = get_proxy_pool()
    
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
    
    async def _is_captcha(self, page: Page) -> bool:
        """检测是否遇到验证码"""
        try:
            content = await page.content()
            content_lower = content.lower()
            
            # 检查验证码关键词
            captcha_indicators = [
                'captcha',
                'type the characters',
                'enter the characters',
                'verification',
                'security check',
            ]
            
            for indicator in captcha_indicators:
                if indicator in content_lower:
                    logger.warning(f"检测到验证码关键词：{indicator}")
                    return True
            
            # 检查验证码相关元素
            captcha_selectors = [
                'input[type="captcha"]',
                '[data-a-modal*="captcha"]',
                '.captcha-container',
                'form[action*="captcha"]',
                '#captchadiv',
            ]
            
            for selector in captcha_selectors:
                if await page.query_selector(selector):
                    logger.warning(f"检测到验证码元素：{selector}")
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"验证码检测异常：{e}")
            return False
    
    async def _parse_rankings(self, page: Page, asin: str, max_pages: int) -> CrawlResult:
        """解析页面排名 - 增强版本"""
        asin_upper = asin.upper()
        
        # 等待搜索结果加载
        try:
            await page.wait_for_selector('[data-component-type="s-search-result"]', timeout=10000)
        except PlaywrightTimeout:
            logger.warning("搜索结果加载超时")
            return CrawlResult(keyword="", status="error", error="搜索结果加载超时")
        
        # 检查是否被重定向到验证码页面
        current_url = page.url
        if 'captcha' in current_url.lower() or 'validation' in current_url.lower():
            logger.warning("检测到验证码重定向")
            return CrawlResult(keyword="", status="captcha", error="检测到验证码")
        
        # 获取所有搜索结果
        try:
            products = await page.query_selector_all('[data-component-type="s-search-result"]')
            logger.info(f"找到 {len(products)} 个搜索结果")
        except Exception as e:
            logger.warning(f"获取搜索结果失败：{e}")
            return CrawlResult(keyword="", status="error", error="无法获取搜索结果")
        
        organic_page = None
        organic_position = None
        ad_page = None
        ad_position = None
        
        # 遍历所有产品
        for index, product in enumerate(products):
            try:
                # 获取 ASIN
                asin_attr = await product.get_attribute("data-asin")
                if not asin_attr:
                    # 尝试从链接中提取
                    link = await product.query_selector('a.a-link-normal')
                    if link:
                        href = await link.get_attribute('href')
                        if href and '/dp/' in href:
                            asin_attr = href.split('/dp/')[1].split('/')[0].split('?')[0].upper()
                
                if not asin_attr:
                    continue
                
                # 亚马逊 ASIN 格式检查 (B0xxxxxx 或 B9xxxxxx)
                if not (asin_attr.upper().startswith("B0") or asin_attr.upper().startswith("B9")):
                    continue
                
                current_asin = asin_attr.upper()
                
                # 判定是否为广告
                is_sponsored = False
                try:
                    sponsored_text = await product.query_selector('span:has-text("Sponsored")')
                    if sponsored_text:
                        is_sponsored = True
                except:
                    pass
                
                # 检查是否匹配目标 ASIN
                if current_asin == asin_upper:
                    position = index + 1
                    
                    if is_sponsored:
                        if ad_position is None:
                            ad_position = position
                            ad_page = 1
                            logger.info(f"✓ 找到广告排名：第{ad_page}页，位置{ad_position}")
                    else:
                        if organic_position is None:
                            organic_position = position
                            organic_page = 1
                            logger.info(f"✓ 找到自然排名：第{organic_page}页，位置{organic_position}")
                    
                    # 如果都找到了，提前退出
                    if organic_position and ad_position:
                        break
                        
            except Exception as e:
                logger.debug(f"解析产品项失败：{e}")
                continue
        
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
            keyword="",
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
        爬取单个关键词的排名 - 增强反爬版本
        
        核心反爬策略：
        1. 使用 stealth_async 隐藏自动化特征
        2. 模拟真实用户环境（UA、时区、语言）
        3. 随机延迟模拟人类行为
        4. 验证码检测与处理
        5. 降低并发避免被封
        """
        async with semaphore:
            result = CrawlResult(keyword=keyword)
            browser = None
            context = None
            page = None
            
            try:
                async with async_playwright() as p:
                    # 1. 启动浏览器 - 增强反爬参数
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-setuid-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-accelerated-2d-canvas',
                            '--no-first-run',
                            '--no-zygote',
                            '--disable-gpu',
                            '--disable-blink-features=AutomationControlled',
                        ]
                    )
                    
                    # 2. 创建上下文 - 模拟真实用户环境
                    context = await browser.new_context(
                        viewport={'width': 1920, 'height': 1080},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        locale='en-US',
                        timezone_id='America/New_York',  # 美国时区
                        proxy={"server": self.proxy_pool.get_proxy()} if self.proxy_pool.is_enabled else None,
                    )
                    
                    page = await context.new_page()
                    
                    # 3. 【关键步骤】应用 Stealth 插件
                    # 自动处理 navigator.webdriver, WebGL, Chrome Runtime 等指纹
                    await stealth_async(page)
                    
                    logger.info(f"开始爬取：{keyword} (ASIN: {asin})")
                    
                    # 4. 遍历页面
                    for page_num in range(1, max_pages + 1):
                        url = self._build_search_url(site, keyword, page_num)
                        logger.debug(f"爬取：{url}")
                        
                        # 访问页面
                        try:
                            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                            await self.random_delay(2, 4)  # 页面加载后随机延迟
                        except PlaywrightTimeout:
                            logger.warning(f"页面加载超时：{url}")
                            result.status = "error"
                            result.error = "页面加载超时"
                            break
                        except Exception as e:
                            logger.error(f"页面访问失败：{e}")
                            result.status = "error"
                            result.error = str(e)
                            break
                        
                        # 5. 验证码检测
                        if await self._is_captcha(page):
                            logger.warning(f"检测到验证码：{keyword}")
                            result.status = "captcha"
                            result.error = "检测到验证码"
                            break
                        
                        # 检查是否返回了 "No results found"
                        page_content = await page.content()
                        if "no results found" in page_content.lower():
                            logger.info(f"无搜索结果：{keyword}")
                            result.status = "not_found"
                            break
                        
                        # 6. 解析排名
                        page_result = await self._parse_rankings(page, asin, max_pages)
                        
                        # 检查是否有错误
                        if page_result.status == "error":
                            result.status = "error"
                            result.error = page_result.error
                            break
                        
                        # 检查是否找到排名
                        if page_result.organic_position or page_result.ad_position:
                            result.organic_page = page_result.organic_page
                            result.organic_position = page_result.organic_position
                            result.ad_page = page_result.ad_page
                            result.ad_position = page_result.ad_position
                            result.status = page_result.status
                            break
                        
                        # 如果已经是最后一页且没找到
                        if page_num >= max_pages:
                            result.status = "not_found"
                            break
                        
                        # 翻页前的随机延迟，模拟人类行为
                        if page_num < max_pages:
                            await self.random_delay(3, 6)
                
            except Exception as e:
                logger.error(f"爬取失败：{keyword}, 错误：{e}")
                result.status = "error"
                result.error = str(e)
            
            finally:
                # 清理资源
                try:
                    if page:
                        await page.close()
                    if context:
                        await context.close()
                    if browser:
                        await browser.close()
                except Exception:
                    pass
            
            return result
    
    async def crawl_keywords_batch(
        self,
        asin: str,
        keywords: List[str],
        site: str,
        max_pages: int,
        max_concurrent: int = 2  # 亚马逊反爬严格，降低并发
    ) -> List[CrawlResult]:
        """
        批量爬取多个关键词
        
        Args:
            asin: 产品 ASIN
            keywords: 关键词列表
            site: 亚马逊站点
            max_pages: 最大翻页数
            max_concurrent: 最大并发数（建议 2-3）
        
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
