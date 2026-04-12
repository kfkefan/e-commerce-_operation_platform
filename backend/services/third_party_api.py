"""
第三方 API 服务
集成 DataForSEO, SerpApi, ScraperAPI 等外部服务
"""
import asyncio
import logging
import aiohttp
from typing import Dict, Any, Optional, List
from datetime import datetime

from backend.config import settings

logger = logging.getLogger(__name__)


class ThirdPartyAPIResult:
    """第三方 API 爬取结果"""
    
    def __init__(
        self,
        keyword: str,
        organic_page: Optional[int] = None,
        organic_position: Optional[int] = None,
        ad_page: Optional[int] = None,
        ad_position: Optional[int] = None,
        status: str = "found",
        error: Optional[str] = None,
        source: str = "third_party"
    ):
        self.keyword = keyword
        self.organic_page = organic_page
        self.organic_position = organic_position
        self.ad_page = ad_page
        self.ad_position = ad_position
        self.status = status
        self.error = error
        self.timestamp = datetime.utcnow()
        self.source = source  # 标记数据来源
    
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
            'error': self.error,
            'source': self.source
        }


class DataForSEOClient:
    """DataForSEO API 客户端"""
    
    def __init__(self):
        self.login = settings.DATAFORSEO_LOGIN
        self.password = settings.DATAFORSEO_PASSWORD
        self.base_url = settings.DATAFORSEO_API_URL
        self.enabled = bool(self.login and self.password)
    
    async def search_rankings(
        self,
        asin: str,
        keyword: str,
        location: str = "United States",
        language: str = "English",
        device: str = "desktop",
        os: str = "Windows"
    ) -> ThirdPartyAPIResult:
        """
        使用 DataForSEO Amazon Rankings API 查询排名
        
        Args:
            asin: 产品 ASIN
            keyword: 搜索关键词
            location: 地理位置
            language: 语言
            device: 设备类型
            os: 操作系统
        
        Returns:
            排名结果
        """
        if not self.enabled:
            return ThirdPartyAPIResult(
                keyword=keyword,
                status="error",
                error="DataForSEO 未配置"
            )
        
        url = f"{self.base_url}/amazon/rankings/task_post"
        
        payload = {
            "tasks": [
                {
                    "keyword": keyword,
                    "location_code": 2840,  # United States
                    "language_code": "en",
                    "device": device,
                    "os": os,
                    "tag": asin,  # 用 tag 传递 ASIN 便于识别
                    "depth": 100  # 爬取深度
                }
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # 提交任务
                async with session.post(
                    url,
                    json=payload,
                    auth=aiohttp.BasicAuth(self.login, self.password),
                    timeout=aiohttp.ClientTimeout(total=settings.THIRD_PARTY_TIMEOUT / 1000)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"DataForSEO 提交任务失败：{response.status} - {error_text}")
                        return ThirdPartyAPIResult(
                            keyword=keyword,
                            status="error",
                            error=f"API 请求失败：{response.status}"
                        )
                    
                    task_result = await response.json()
                    
                    # DataForSEO 是异步 API，需要等待任务完成
                    # 简化处理：直接返回任务提交成功
                    logger.info(f"DataForSEO 任务已提交：{keyword}")
                    
                    # 实际使用中需要轮询 task_get 端点获取结果
                    # 这里简化处理，返回 pending 状态
                    return ThirdPartyAPIResult(
                        keyword=keyword,
                        status="pending",
                        error="任务已提交，等待异步结果"
                    )
                    
        except asyncio.TimeoutError:
            logger.error(f"DataForSEO 请求超时：{keyword}")
            return ThirdPartyAPIResult(
                keyword=keyword,
                status="error",
                error="请求超时"
            )
        except Exception as e:
            logger.error(f"DataForSEO 请求异常：{e}")
            return ThirdPartyAPIResult(
                keyword=keyword,
                status="error",
                error=str(e)
            )


class SerpApiClient:
    """SerpApi 客户端"""
    
    def __init__(self):
        self.api_key = settings.SERPAPI_API_KEY
        self.base_url = settings.SERPAPI_API_URL
        self.enabled = bool(self.api_key)
    
    async def search_amazon(
        self,
        asin: str,
        keyword: str,
        amazon_domain: str = "amazon.com",
        page: int = 1
    ) -> ThirdPartyAPIResult:
        """
        使用 SerpApi 查询 Amazon 搜索结果
        
        Args:
            asin: 产品 ASIN
            keyword: 搜索关键词
            amazon_domain: 亚马逊站点
            page: 页码
        
        Returns:
            排名结果
        """
        if not self.enabled:
            return ThirdPartyAPIResult(
                keyword=keyword,
                status="error",
                error="SerpApi 未配置"
            )
        
        params = {
            "engine": "amazon",
            "amazon_domain": amazon_domain,
            "search_term": keyword,
            "api_key": self.api_key,
            "page": page
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=settings.THIRD_PARTY_TIMEOUT / 1000)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"SerpApi 请求失败：{response.status} - {error_text}")
                        return ThirdPartyAPIResult(
                            keyword=keyword,
                            status="error",
                            error=f"API 请求失败：{response.status}"
                        )
                    
                    result = await response.json()
                    
                    # 解析搜索结果
                    organic_results = result.get("organic_results", [])
                    sponsored_results = result.get("sponsored_results", [])
                    
                    organic_position = None
                    organic_page = None
                    ad_position = None
                    ad_page = None
                    
                    # 查找自然排名
                    for idx, item in enumerate(organic_results):
                        asin_found = item.get("asin", "")
                        if asin_found.upper() == asin.upper():
                            organic_position = idx + 1
                            organic_page = page
                            logger.info(f"SerpApi 找到自然排名：第{organic_page}页，位置{organic_position}")
                            break
                    
                    # 查找广告排名
                    for idx, item in enumerate(sponsored_results):
                        asin_found = item.get("asin", "")
                        if asin_found and asin_found.upper() == asin.upper():
                            ad_position = idx + 1
                            ad_page = page
                            logger.info(f"SerpApi 找到广告排名：第{ad_page}页，位置{ad_position}")
                            break
                    
                    # 确定状态
                    if organic_position or ad_position:
                        status = "found"
                    else:
                        status = "not_found"
                    
                    return ThirdPartyAPIResult(
                        keyword=keyword,
                        organic_page=organic_page,
                        organic_position=organic_position,
                        ad_page=ad_page,
                        ad_position=ad_position,
                        status=status
                    )
                    
        except asyncio.TimeoutError:
            logger.error(f"SerpApi 请求超时：{keyword}")
            return ThirdPartyAPIResult(
                keyword=keyword,
                status="error",
                error="请求超时"
            )
        except Exception as e:
            logger.error(f"SerpApi 请求异常：{e}")
            return ThirdPartyAPIResult(
                keyword=keyword,
                status="error",
                error=str(e)
            )


class ScraperAPIClient:
    """ScraperAPI 客户端"""
    
    def __init__(self):
        self.api_key = settings.SCRAPERAPI_API_KEY
        self.base_url = settings.SCRAPERAPI_API_URL
        self.enabled = bool(self.api_key)
    
    async def scrape_amazon(
        self,
        asin: str,
        keyword: str,
        amazon_domain: str = "amazon.com",
        page: int = 1
    ) -> ThirdPartyAPIResult:
        """
        使用 ScraperAPI 爬取 Amazon 页面
        
        Args:
            asin: 产品 ASIN
            keyword: 搜索关键词
            amazon_domain: 亚马逊站点
            page: 页码
        
        Returns:
            排名结果
        """
        if not self.enabled:
            return ThirdPartyAPIResult(
                keyword=keyword,
                status="error",
                error="ScraperAPI 未配置"
            )
        
        # 构建 Amazon 搜索 URL
        from urllib.parse import quote
        url = f"https://www.{amazon_domain}/s?k={quote(keyword)}&page={page}"
        
        params = {
            "api_key": self.api_key,
            "url": url,
            "render": "true",  # 启用 JavaScript 渲染
            "country_code": "us",
            "premium": "true"  # 使用高级代理
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.base_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=settings.THIRD_PARTY_TIMEOUT / 1000)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"ScraperAPI 请求失败：{response.status}")
                        return ThirdPartyAPIResult(
                            keyword=keyword,
                            status="error",
                            error=f"API 请求失败：{response.status}"
                        )
                    
                    html_content = await response.text()
                    
                    # 解析 HTML 查找 ASIN
                    organic_position, ad_position = await self._parse_rankings(
                        html_content, asin
                    )
                    
                    if organic_position or ad_position:
                        status = "found"
                    else:
                        status = "not_found"
                    
                    return ThirdPartyAPIResult(
                        keyword=keyword,
                        organic_page=organic_position and page or None,
                        organic_position=organic_position,
                        ad_page=ad_position and page or None,
                        ad_position=ad_position,
                        status=status
                    )
                    
        except asyncio.TimeoutError:
            logger.error(f"ScraperAPI 请求超时：{keyword}")
            return ThirdPartyAPIResult(
                keyword=keyword,
                status="error",
                error="请求超时"
            )
        except Exception as e:
            logger.error(f"ScraperAPI 请求异常：{e}")
            return ThirdPartyAPIResult(
                keyword=keyword,
                status="error",
                error=str(e)
            )
    
    async def _parse_rankings(self, html: str, asin: str) -> tuple:
        """解析 HTML 查找排名位置"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        organic_position = None
        ad_position = None
        
        # 查找所有搜索结果
        results = soup.select('[data-component-type="s-search-result"]')
        
        for idx, result in enumerate(results):
            # 获取 ASIN
            asin_attr = result.get('data-asin', '')
            
            if not asin_attr:
                # 尝试从链接中提取
                link = result.select_one('a.a-link-normal')
                if link and link.get('href'):
                    href = link['href']
                    if '/dp/' in href:
                        asin_attr = href.split('/dp/')[1].split('/')[0].split('?')[0]
            
            if asin_attr.upper() == asin.upper():
                # 检查是否为广告
                is_sponsored = bool(result.select_one('span:contains("Sponsored")'))
                
                if is_sponsored:
                    ad_position = idx + 1
                else:
                    organic_position = idx + 1
                
                break
        
        return organic_position, ad_position


class ThirdPartyAPIService:
    """第三方 API 服务管理器"""
    
    def __init__(self):
        self.enabled = settings.THIRD_PARTY_API_ENABLED
        self.provider = settings.THIRD_PARTY_PROVIDER.lower()
        
        # 初始化客户端
        self.dataforseo = DataForSEOClient()
        self.serpapi = SerpApiClient()
        self.scraperapi = ScraperAPIClient()
        
        logger.info(f"第三方 API 服务已初始化：enabled={self.enabled}, provider={self.provider}")
    
    def _get_client(self):
        """根据配置获取对应的客户端"""
        if self.provider == "dataforseo":
            return self.dataforseo
        elif self.provider == "serpapi":
            return self.serpapi
        elif self.provider == "scraperapi":
            return self.scraperapi
        else:
            logger.warning(f"未知的第三方 API 提供商：{self.provider}")
            return None
    
    async def search_rankings(
        self,
        asin: str,
        keyword: str,
        site: str = "amazon.com",
        max_pages: int = 3
    ) -> ThirdPartyAPIResult:
        """
        使用第三方 API 搜索排名
        
        Args:
            asin: 产品 ASIN
            keyword: 搜索关键词
            site: 亚马逊站点
            max_pages: 最大翻页数
        
        Returns:
            排名结果
        """
        if not self.enabled:
            return ThirdPartyAPIResult(
                keyword=keyword,
                status="error",
                error="第三方 API 未启用"
            )
        
        client = self._get_client()
        if not client:
            return ThirdPartyAPIResult(
                keyword=keyword,
                status="error",
                error="未配置有效的第三方 API"
            )
        
        # 遍历页面查找排名
        for page in range(1, max_pages + 1):
            try:
                if isinstance(client, SerpApiClient):
                    result = await client.search_amazon(asin, keyword, site, page)
                elif isinstance(client, ScraperAPIClient):
                    result = await client.scrape_amazon(asin, keyword, site, page)
                elif isinstance(client, DataForSEOClient):
                    result = await client.search_rankings(asin, keyword)
                else:
                    result = ThirdPartyAPIResult(
                        keyword=keyword,
                        status="error",
                        error="不支持的 API 类型"
                    )
                
                # 如果找到排名或遇到错误，返回结果
                if result.status in ["found", "error", "captcha"]:
                    return result
                
            except Exception as e:
                logger.error(f"第三方 API 搜索失败：{e}")
                continue
        
        # 所有页面都没找到
        return ThirdPartyAPIResult(
            keyword=keyword,
            status="not_found"
        )


# 全局服务实例
third_party_service = ThirdPartyAPIService()


def get_third_party_service() -> ThirdPartyAPIService:
    """获取第三方 API 服务实例"""
    return third_party_service
