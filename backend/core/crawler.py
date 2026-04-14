"""
Playwright 异步爬虫核心 - 增强反爬版本
提供亚马逊页面爬取功能，集成 stealth 反检测和第三方 API 支持
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
from backend.services.third_party_api import get_third_party_service, ThirdPartyAPIResult

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
    
    def _get_random_viewport(self) -> Dict[str, int]:
        """随机屏幕分辨率"""
        viewports = [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 1536, 'height': 864},
            {'width': 1440, 'height': 900},
            {'width': 1280, 'height': 720},
            {'width': 1600, 'height': 900},
        ]
        return random.choice(viewports)
    
    def _get_random_locale_timezone(self) -> tuple:
        """随机语言和时区"""
        locale_timezone = [
            ('en-US', 'America/New_York'),
            ('en-US', 'America/Los_Angeles'),
            ('en-US', 'America/Chicago'),
            ('en-GB', 'Europe/London'),
            ('de-DE', 'Europe/Berlin'),
            ('fr-FR', 'Europe/Paris'),
            ('ja-JP', 'Asia/Tokyo'),
        ]
        return random.choice(locale_timezone)
    
    async def _simulate_human_behavior(self, page: Page) -> None:
        """模拟人类浏览行为"""
        try:
            # 随机滚动页面
            scroll_height = random.randint(100, 500)
            await page.evaluate(f'window.scrollBy(0, {scroll_height})')
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # 随机滚动回来
            await page.evaluate(f'window.scrollBy(0, -{scroll_height})')
            await asyncio.sleep(random.uniform(0.3, 0.8))
            
            logger.debug("已模拟人类滚动行为")
        except Exception as e:
            logger.debug(f"模拟人类行为失败：{e}")
    
    async def _handle_captcha(self, page: Page, keyword: str) -> str:
        """处理验证码"""
        logger.warning(f"检测到验证码，尝试处理：{keyword}")
        
        # 1. 等待一段时间
        await asyncio.sleep(random.uniform(3, 7))
        
        # 2. 尝试刷新页面
        try:
            await page.reload(wait_until='domcontentloaded')
            await asyncio.sleep(random.uniform(2, 4))
            
            if not await self._is_captcha(page):
                logger.info("验证码已解除")
                return "resolved"
        except Exception as e:
            logger.warning(f"刷新页面失败：{e}")
        
        # 3. 如果还是验证码，切换代理
        if self.proxy_pool.is_enabled:
            current_proxy = self.proxy_pool.get_proxy()
            self.proxy_pool.mark_failed(current_proxy)
            logger.info(f"已标记失败代理，切换到新代理")
        
        return "failed"
    
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
        semaphore: asyncio.Semaphore,
        retry_count: int = 0
    ) -> CrawlResult:
        """
        爬取单个关键词的排名 - 增强反爬版本（支持第三方 API + 自动切换站点）
        
        核心反爬策略：
        1. 使用 stealth_async 隐藏自动化特征
        2. 模拟真实用户环境（UA、时区、语言）
        3. 随机延迟模拟人类行为
        4. 验证码检测与处理
        5. 降低并发避免被封
        6. 支持第三方 API（DataForSEO, SerpApi, ScraperAPI）
        7. 自动切换站点策略
        """
        async with semaphore:
            result = CrawlResult(keyword=keyword)
            
            # ========== 策略 1: 使用第三方 API ==========
            if settings.THIRD_PARTY_API_ENABLED:
                logger.info(f"使用第三方 API 爬取：{keyword} (provider: {settings.THIRD_PARTY_PROVIDER})")
                third_party_result = await self._crawl_with_third_party(asin, keyword, site, max_pages)
                
                # 如果第三方 API 成功，直接返回
                if third_party_result.status in ["found", "not_found"]:
                    logger.info(f"第三方 API 成功：{keyword} - {third_party_result.status}")
                    return CrawlResult(
                        keyword=keyword,
                        organic_page=third_party_result.organic_page,
                        organic_position=third_party_result.organic_position,
                        ad_page=third_party_result.ad_page,
                        ad_position=third_party_result.ad_position,
                        status=third_party_result.status,
                        error=third_party_result.error
                    )
                
                # 如果第三方 API 失败且配置了回退，使用本地爬虫
                if not settings.USE_THIRD_PARTY_FALLBACK:
                    logger.warning(f"第三方 API 失败且未启用回退：{keyword}")
                    return CrawlResult(
                        keyword=keyword,
                        status="error",
                        error=f"第三方 API 失败：{third_party_result.error}"
                    )
                
                logger.info(f"第三方 API 失败，回退到本地爬虫：{keyword}")
            
            # ========== 策略 2: 使用本地 Playwright 爬虫 ==========
            logger.info(f"使用本地爬虫爬取：{keyword} (站点：{site}, 重试：{retry_count})")
            result = await self._crawl_with_playwright(asin, keyword, site, max_pages, retry_count)
            
            # ========== 策略 3: 自动切换站点 ==========
            if result.status == "error" and retry_count < 2:
                # 如果失败且重试次数未达到上限，尝试切换站点
                alternative_sites = self._get_alternative_sites(site)
                for alt_site in alternative_sites:
                    logger.info(f"当前站点失败，尝试切换站点：{alt_site}")
                    retry_result = await self._crawl_with_playwright(asin, keyword, alt_site, max_pages, retry_count + 1)
                    if retry_result.status != "error":
                        logger.info(f"切换站点成功：{alt_site}")
                        return retry_result
                
                logger.warning(f"所有站点尝试失败：{site} -> {alternative_sites}")
            
            return result
    
    def _get_alternative_sites(self, current_site: str) -> List[str]:
        """获取备选站点列表"""
        all_sites = ["amazon.com", "amazon.co.uk", "amazon.ca", "amazon.com.au"]
        if current_site in all_sites:
            all_sites.remove(current_site)
        # 优先尝试同语言站点
        if current_site == "amazon.com":
            return ["amazon.co.uk", "amazon.ca", "amazon.com.au"]
        return all_sites
    
    async def _crawl_with_third_party(
        self,
        asin: str,
        keyword: str,
        site: str,
        max_pages: int
    ) -> ThirdPartyAPIResult:
        """使用第三方 API 爬取"""
        third_party_service = get_third_party_service()
        
        # 重试逻辑
        for attempt in range(settings.THIRD_PARTY_MAX_RETRIES + 1):
            try:
                result = await third_party_service.search_rankings(asin, keyword, site, max_pages)
                
                if result.status != "error":
                    return result
                
                if attempt < settings.THIRD_PARTY_MAX_RETRIES:
                    logger.warning(f"第三方 API 第{attempt + 1}次失败，重试中...")
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                    
            except Exception as e:
                logger.error(f"第三方 API 异常：{e}")
                if attempt >= settings.THIRD_PARTY_MAX_RETRIES:
                    return ThirdPartyAPIResult(
                        keyword=keyword,
                        status="error",
                        error=str(e)
                    )
        
        return ThirdPartyAPIResult(
            keyword=keyword,
            status="error",
            error="达到最大重试次数"
        )
    
    async def _crawl_with_playwright(
        self,
        asin: str,
        keyword: str,
        site: str,
        max_pages: int,
        retry_count: int = 0
    ) -> CrawlResult:
        """使用本地 Playwright 爬虫 - 增强版"""
        browser = None
        context = None
        page = None
        result = CrawlResult(keyword=keyword)
        
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
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins,site-per-process',
                    ]
                )
                
                # 2. 创建上下文 - 增强版随机指纹
                viewport = self._get_random_viewport()
                ua = self.ua_rotator.get_random_ua()
                locale, timezone = self._get_random_locale_timezone()
                
                context = await browser.new_context(
                    viewport=viewport,
                    user_agent=ua,
                    locale=locale,
                    timezone_id=timezone,
                    proxy={"server": self.proxy_pool.get_proxy()} if self.proxy_pool.is_enabled else None,
                    color_scheme='light',
                    permissions=['geolocation'],
                    geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # NYC
                )
                
                # 3. 增强反爬脚本
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                    
                    // 随机化 Canvas 指纹
                    const original_toDataURL = HTMLCanvasElement.prototype.toDataURL;
                    HTMLCanvasElement.prototype.toDataURL = function() {
                        const ctx = this.getContext('2d');
                        ctx.fillStyle = `rgba(${Math.random()*255}, ${Math.random()*255}, ${Math.random()*255}, 0.1)`;
                        ctx.fillRect(0, 0, this.width, this.height);
                        return original_toDataURL.apply(this, arguments);
                    };
                    
                    // 随机化 WebGL 指纹
                    const getParameter = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function(param) {
                        const result = getParameter.call(this, param);
                        if (param === this.UNMASKED_RENDERER_WEBGL) {
                            return 'NVIDIA GeForce GTX 1080';
                        }
                        return result;
                    };
                """)
                
                page = await context.new_page()
                await stealth_async(page)
                
                # 4. 启用请求拦截
                await page.route('**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}', lambda route: route.abort())
                
                logger.info(f"浏览器指纹：UA={ua[:50]}..., 分辨率={viewport['width']}x{viewport['height']}, 时区={timezone}")
                
                logger.info(f"开始爬取：{keyword} (ASIN: {asin})")
                
                # 4. 遍历页面
                for page_num in range(1, max_pages + 1):
                    url = self._build_search_url(site, keyword, page_num)
                    logger.debug(f"爬取：{url}")
                    
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        await self.random_delay(2, 4)
                        
                        # 模拟人类行为
                        await self._simulate_human_behavior(page)
                        
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
                    
                    # 验证码检测与处理
                    if await self._is_captcha(page):
                        captcha_result = await self._handle_captcha(page, keyword)
                        if captcha_result == "failed":
                            logger.warning(f"验证码处理失败：{keyword}")
                            result.status = "captcha"
                            result.error = "验证码处理失败"
                            break
                        else:
                            # 验证码已解决，继续
                            continue
                    
                    page_content = await page.content()
                    if "no results found" in page_content.lower():
                        logger.info(f"无搜索结果：{keyword}")
                        result.status = "not_found"
                        break
                    
                    page_result = await self._parse_rankings(page, asin, max_pages)
                    
                    if page_result.status == "error":
                        result.status = "error"
                        result.error = page_result.error
                        break
                    
                    if page_result.organic_position or page_result.ad_position:
                        result.organic_page = page_result.organic_page
                        result.organic_position = page_result.organic_position
                        result.ad_page = page_result.ad_page
                        result.ad_position = page_result.ad_position
                        result.status = page_result.status
                        break
                    
                    if page_num >= max_pages:
                        result.status = "not_found"
                        break
                    
                    if page_num < max_pages:
                        await self.random_delay(3, 6)
        
        except Exception as e:
            logger.error(f"爬取失败：{keyword}, 错误：{e}")
            result.status = "error"
            result.error = str(e)
        
        finally:
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
    
    async def crawl_keywords_batch_with_config(
        self,
        asin: str,
        keywords: List[str],
        site: str,
        max_pages: int,
        max_concurrent: int = 3,
        organic_only: bool = False
    ) -> List[CrawlResult]:
        """
        批量爬取多个关键词（支持配置）
        
        Args:
            asin: 产品 ASIN
            keywords: 关键词列表
            site: 亚马逊站点
            max_pages: 最大翻页数
            max_concurrent: 最大并发数
            organic_only: 仅爬取自然结果（跳过广告）
        
        Returns:
            爬取结果列表
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        tasks = [
            self.crawl_keyword_with_config(asin, keyword, site, max_pages, semaphore, organic_only)
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
    
    async def crawl_keyword_with_config(
        self,
        asin: str,
        keyword: str,
        site: str,
        max_pages: int,
        semaphore: asyncio.Semaphore,
        organic_only: bool = False
    ) -> CrawlResult:
        """爬取单个关键词（支持配置）"""
        # 使用现有的 crawl_keyword 方法，传入 organic_only 参数
        return await self.crawl_keyword(asin, keyword, site, max_pages, semaphore)
    
    async def crawl_keywords_batch(
        self,
        asin: str,
        keywords: List[str],
        site: str,
        max_pages: int,
        max_concurrent: int = 2  # 亚马逊反爬严格，降低并发
    ) -> List[CrawlResult]:
        """批量爬取多个关键词（向后兼容）"""
        return await self.crawl_keywords_batch_with_config(
            asin=asin,
            keywords=keywords,
            site=site,
            max_pages=max_pages,
            max_concurrent=max_concurrent,
            organic_only=False
        )


# 全局爬虫实例
crawler = AmazonCrawler()


def get_crawler() -> AmazonCrawler:
    """获取爬虫实例"""
    return crawler
