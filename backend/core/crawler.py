"""
Playwright 异步爬虫核心 - 增强反爬版本
提供亚马逊页面爬取功能，集成 stealth 反检测和第三方 API 支持
"""
import asyncio
import logging
import random
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, ElementHandle, TimeoutError as PlaywrightTimeout
from playwright_stealth import stealth_async
from playwright.async_api import Error as PlaywrightError # 导入 Playwright 错误类型

from backend.config import settings
from backend.core.ua_rotator import get_ua_rotator
from backend.core.proxy_manager import get_proxy_pool
from backend.services.third_party_api import get_third_party_service, ThirdPartyAPIResult

logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO)
# 3. 创建 Handler (例如输出到控制台)
handler = logging.StreamHandler()  
handler.setLevel(logging.INFO) # Handler 的级别也要 >= INFO

# 4. 设置格式并添加 Handler
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


# --- 新增：地址信息库 (建议提取到 config.py 或单独的文件中) ---
# 格式: 邮编: {城市, 州, 纬度, 经度, 时区}
US_LOCATIONS = {
    "19701": {"city": "Newark", "state": "DE", "lat": 39.6837, "lon": -75.7497, "tz": "America/New_York"},    # 特拉华 (免税)
    "97201": {"city": "Portland", "state": "OR", "lat": 45.5152, "lon": -122.6784, "tz": "America/Los_Angeles"}, # 俄勒冈 (免税)
    "10001": {"city": "New York", "state": "NY", "lat": 40.7506, "lon": -73.9971, "tz": "America/New_York"},    # 纽约
    "90001": {"city": "Los Angeles", "state": "CA", "lat": 33.9731, "lon": -118.2479, "tz": "America/Los_Angeles"}, # 洛杉矶
    "60601": {"city": "Chicago", "state": "IL", "lat": 41.8857, "lon": -87.6182, "tz": "America/Chicago"},       # 芝加哥
}


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
        from urllib.parse import quote_plus
        base_url = f"https://www.{site}"
        encoded_keyword = quote_plus(keyword)
        url = f"{base_url}/s?k={encoded_keyword}&page={page}"
        return url
    
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
    
    def _get_random_location_data(self):
        """随机获取一组地理位置信息"""
        zip_code = random.choice(list(US_LOCATIONS.keys()))
        loc_data = US_LOCATIONS[zip_code]
        return {
            "zip_code": zip_code,
            "geolocation": {'latitude': loc_data['lat'], 'longitude': loc_data['lon']},
            "timezone_id": loc_data['tz'],
            "locale": "en-US"
        }
    
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
            logger.warning(f"模拟人类行为失败：{e}")
    
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
    
    async def _parse_rankings(self, page: Page, asin: str, current_page: int, max_pages: int) -> CrawlResult:
        """解析页面排名 - 增强版本"""
        logger.info(f"解析页面排名：ASIN={asin}, 当前页={current_page}, 最大页数={max_pages}") 
        asin_upper = asin.upper()
        
        # 等待搜索结果加载
        try:
            await page.wait_for_selector('[data-component-type="s-search-result"]', timeout=20000)
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
            # 随机延迟
            await self.random_delay(5, 10)
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
                logger.info(f"解析第 {index + 1} 个搜索结果")
                logger.info(f"产品属性: ASIN: {await product.get_attribute('data-asin')}, 索引: {await product.get_attribute('data-index')}")
                # 获取 ASIN
                asin_attr = await product.get_attribute("data-asin")
                if not asin_attr:
                    # 先查找链接元素
                    link = await product.query_selector('a.a-link-normal')
                    if link:
                        href = await link.get_attribute('href')
                        # 匹配 /dp/ASIN 或 /gp/product/ASIN
                        match = re.search(r'/dp/([A-Z0-9]{10})', href)
                        if match:
                            asin_attr = match.group(1)
                        elif '/dp/' in href:
                        # 兜底：如果没有匹配到正则，尝试简单的字符串分割（保留你的原逻辑）
                        # 但要注意处理索引错误
                            try:
                                asin_attr = href.split('/dp/')[1].split('/')[0].split('?')[0].upper()
                            except IndexError:
                                pass # 分割失败，忽略

                # 2. 校验 ASIN

                if not asin_attr or not (asin_attr.upper().startswith("B0") or asin_attr.upper().startswith("B9")):
                    logger.info(f"跳过无效 ASIN: {asin_attr}")
                    continue # 格式不对直接跳过，无需打日志（除非调试）
                
                current_asin = asin_attr.upper()
                logger.info(f"当前搜索结果 ASIN: {current_asin}，目标结果ASIN: {asin_upper}")

                # 4. 计算排名
                visual_position = index + 1
                is_sponsored = False
                if current_asin == asin_upper:
                    logger.info(f"✓ 找到匹配 ASIN: {current_asin}，视觉位置: {visual_position}")
                    
                    # 3. 判定是否为广告
                    is_sponsored =  await self._is_sponsored_product(product)
                    logger.info(f"ASIN {current_asin} - 广告属性检测: {'是广告' if is_sponsored else '非广告'}")
                
                    if is_sponsored:
                        # 广告通常只记录视觉位置（即第几个看到的）
                        if ad_position is None:
                            ad_position = visual_position
                            ad_page = current_page
                            logger.info(f"✓ 找到广告排名：第{ad_page}页，位置{ad_position}")
                    else:
                        # 自然排名：优先使用 data-index 属性值
                        data_index_str = await product.get_attribute('data-index')
                        if data_index_str and data_index_str.isdigit():
                            natural_rank_on_page = int(data_index_str)
                            if organic_position is None:
                                # 如果你只想要“它在页面上的第几个位置”，直接用 visual_position
                                organic_position = natural_rank_on_page
                                organic_page = current_page
                                logger.info(f"✓ 找到自然排名：第{organic_page}页，位置{organic_position}")
                        else:
                            # 如果没有 data-index，退回到视觉位置（不太准确，但有时是唯一选择）
                            logger.warning(f"警告：ASIN {current_asin} 被识别为自然排名，但未找到 data-index 属性！使用视觉位置代替。")
                            if organic_position is None:
                                organic_position = visual_position
                                organic_page = current_page
                                logger.info(f"✓ 找到自然排名（使用视觉位置）：第{organic_page}页，位置{organic_position}")
                    # 如果都找到了，提前退出
                    if (organic_position is not None) and (ad_position is not None):
                        logger.info("已找到目标自然排名和广告排名，停止解析当前页面")
                        break
                        
            except Exception as e:
                logger.debug(f"解析产品项失败：{e}")
                continue

        
        return CrawlResult(
            keyword="",
            organic_page=organic_page,
            organic_position=organic_position,
            ad_page=ad_page,
            ad_position=ad_position,
            status=""
        )

    async def _is_sponsored_product(self, product:ElementHandle) -> bool:
        """
        综合判断商品是否为广告
        """
        try: 
            # 确保 product 是有效的 ElementHandle
            if not isinstance(product, ElementHandle):
                logger.error(f"传入的 product 不是 ElementHandle 类型: {type(product)}")
                return False
             
            # 2. 检查内部子元素是否有广告属性 (最高优先级)
            if await product.get_attribute('data-ad-price'):
                logger.info("检测到广告属性：容器自身有 data-ad-price")
                return True
            
            #   - 再检查内部子元素
            inner_ad_price_element = await product.query_selector(':scope [data-ad-price]')
            if inner_ad_price_element:
                logger.info("检测到广告属性：子元素有 data-ad-price")
                return True

            # 3. 检查 "Sponsored" 文本 (兜底方案)
            # 亚马逊通常会在标题上方或角落放一个 span 写着 "Sponsored"
            # 使用 :has-text 或 text 选择器
       
            # 查找包含 "Sponsored" 或 "广告" 的 span 标签
            # 注意：这里用 text="Sponsored" 或 :has-text 都可以，取决于你的 Playwright 版本
            sponsored_locator = await product.query_selector('span:has-text("Sponsored"), span:has-text("广告")')
            if sponsored_locator:
                logger.info("检测到广告属性：Sponsored")
                return True
            
        except Exception as e: # 捕获其他非预期错误
            logger.error(f"检测 'Sponsored' 文本时发生未知错误: {e}")
            # 一般不建议在此处 return False，因为错误不代表不是广告
            return False

        logger.info("未检测到广告属性")
        return False    
    
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
            logger.info(f"使用本地爬虫爬取：{keyword} (站点：{site}, 重试：{retry_count}, 最大页数：{max_pages})")
            result = await self._crawl_with_playwright(asin, keyword, site, max_pages, retry_count)
            
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
    # 核心入口。负责初始化浏览器环境、配置反爬参数、管理页面生命周期。
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
                # 1. 获取随机地理位置信息
                location_info = self._get_random_location_data()
                logger.info(f"地理位置信息：语言={location_info['locale']}, 时区={location_info['timezone_id']}, 经纬度={location_info['geolocation']}")
                # 2. 启动浏览器 - 增强反爬参数
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-infobars',
                        '--window-position=0,0',
                        '--ignore-certifcate-errors',
                        '--ignore-certifcate-errors-spki-list',
                        '--no-first-run',
                        '--no-zygote',
                        '--disable-gpu',
                    ]
                )
                
                # 3. 创建上下文 - 增强版随机指纹
                viewport = self._get_random_viewport()
                ua = self.ua_rotator.get_random_ua()
                
                context = await browser.new_context(
                    viewport=viewport, 
                    user_agent=ua,
                    device_scale_factor=1, # 固定缩放比例（非 Retina 屏）
                    is_mobile=False, # 固定为桌面端
                    has_touch=False, # 关闭触摸支持
                    locale=location_info['locale'],           # 语言
                    timezone_id=location_info['timezone_id'], # 时区 (关键)
                    geolocation=location_info['geolocation'], # 经纬度 (关键)
                    permissions=['geolocation'],              # 授予定位权限
                    proxy={"server": self.proxy_pool.get_proxy()} if self.proxy_pool.is_enabled else None,
                    color_scheme='light',
                    extra_http_headers={
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    },
                )
                
                # 4. 增强反爬脚本
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                    
                    // 新增：欺骗 Permissions API
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                    );


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
                
                logger.info(f"浏览器指纹：UA={ua[:50]}..., 分辨率={viewport['width']}x{viewport['height']}, 时区={location_info['timezone_id']}")
                
                logger.info(f"开始爬取：{keyword} (ASIN: {asin})")
                
                organic_position = None
                organic_page = None
                ad_page = None  
                ad_position = None
                found_organic = False # 引入标志位，更清晰地追踪状态
                found_ad = False                

                # 4. 遍历页面
                should_continue = True
                for page_num in range(1, max_pages + 1):
                    if not should_continue: # 提前终止检查
                        break

                    url = self._build_search_url(site, keyword, page_num)
                    logger.info(f"爬取：{url}")
                    
                    try:
                        #让浏览器页面跳转到指定网址，等待其 HTML 完全加载并构建完 DOM 树（不等待图片等外部资源），最多等待 60 秒，如果超时则报错。
                        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                        logger.info(f"页面加载成功：{url}")  

                        # 等待搜索结果加载出来（即商品卡片出现）
                        await page.wait_for_selector('[data-component-type="s-search-result"]', timeout=5000)
                        logger.info("搜索结果加载成功")
                        # 随机延迟
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
                        logger.info(f"开始识别验证码：{keyword}")
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

                    page_result = await self._parse_rankings(page, asin, page_num, max_pages)

                    if page_result.status == "error":
                        result.status = "error"
                        result.error = page_result.error
                        break
                    

                     # 更新找到的排名
                    if not found_organic and page_result.organic_position is not None:
                        organic_position = page_result.organic_position
                        organic_page = page_result.organic_page
                        found_organic = True # 标记已找到
                        logger.info(f"找到自然排名：第{organic_page}页，位置{organic_position}")

                    if not found_ad and page_result.ad_position is not None:
                        ad_position = page_result.ad_position
                        ad_page = page_result.ad_page
                        found_ad = True # 标记已找到
                        logger.info(f"找到广告排名：第{ad_page}页，位置{ad_position}")

                    # 检查是否全部找到，提前终止
                    if found_organic and found_ad:
                        logger.info("自然排名和广告排名均已找到，停止搜索。")
                        should_continue = False # 设置标志，准备跳出循环
                        break # 立即跳出

                    # 页面间延迟
                    if page_num < max_pages:
                        await self.random_delay(3, 6)

                # 整理查询的结果        
                result.organic_page = organic_page
                result.organic_position = organic_position
                result.ad_page = ad_page
                result.ad_position = ad_position

                # 根据最终找到的情况设置状态
                if found_organic and found_ad:
                    result.status = "found"
                elif found_organic and not found_ad:
                    result.status = "ad_not_found" # 找到了自然，没找到广告
                elif not found_organic and found_ad:
                    result.status = "organic_not_found" # 没找到自然，找到了广告
                else: # 两个都没找到
                    result.status = "not_found"
        
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
                logger.info(f"关键词 {keywords[i]} 处理异常：{result}")
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
