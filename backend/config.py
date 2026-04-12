"""
应用配置模块
从环境变量加载配置，提供默认值
"""
import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""
    
    # ========== 应用基础配置 ==========
    APP_NAME: str = Field(default="ASIN Ranker", description="应用名称")
    APP_VERSION: str = Field(default="1.0.0", description="应用版本")
    DEBUG: bool = Field(default=False, description="调试模式")
    
    # ========== 服务器配置 ==========
    HOST: str = Field(default="0.0.0.0", description="服务器监听地址")
    PORT: int = Field(default=8000, description="服务器端口")
    
    # ========== 数据库配置 ==========
    DB_HOST: str = Field(default="localhost", description="MySQL 主机")
    DB_PORT: int = Field(default=3306, description="MySQL 端口")
    DB_USER: str = Field(default="root", description="MySQL 用户名")
    DB_PASSWORD: str = Field(default="", description="MySQL 密码")
    DB_NAME: str = Field(default="asin_ranker", description="数据库名称")
    DB_POOL_MINSIZE: int = Field(default=5, description="数据库连接池最小连接数")
    DB_POOL_MAXSIZE: int = Field(default=20, description="数据库连接池最大连接数")
    
    # ========== 爬虫配置 ==========
    MAX_CONCURRENT_BROWSERS: int = Field(default=3, description="最大并发浏览器实例数")
    MAX_CONCURRENT_TASKS: int = Field(default=5, description="最大并发任务数")
    REQUEST_DELAY_MIN: float = Field(default=2.0, description="请求最小延迟（秒）")
    REQUEST_DELAY_MAX: float = Field(default=5.0, description="请求最大延迟（秒）")
    MAX_RETRIES: int = Field(default=3, description="最大重试次数")
    PAGE_TIMEOUT: int = Field(default=30000, description="页面加载超时（毫秒）")
    
    # ========== 代理配置 ==========
    PROXY_POOL_ENABLED: bool = Field(default=False, description="是否启用代理池")
    PROXY_LIST: List[str] = Field(default_factory=list, description="代理列表")
    
    # ========== User-Agent 配置 ==========
    UA_ROTATION_ENABLED: bool = Field(default=True, description="是否启用 UA 轮换")
    
    # ========== 第三方 API 配置 ==========
    THIRD_PARTY_API_ENABLED: bool = Field(default=False, description="是否启用第三方 API（如 DataForSEO, SerpApi）")
    THIRD_PARTY_PROVIDER: str = Field(default="dataforseo", description="第三方 API 提供商：dataforseo|serpapi|scraperapi")
    
    # DataForSEO 配置
    DATAFORSEO_LOGIN: str = Field(default="", description="DataForSEO 登录邮箱")
    DATAFORSEO_PASSWORD: str = Field(default="", description="DataForSEO API 密码")
    DATAFORSEO_API_URL: str = Field(default="https://api.dataforseo.com/v3", description="DataForSEO API 基础 URL")
    
    # SerpApi 配置
    SERPAPI_API_KEY: str = Field(default="", description="SerpApi API 密钥")
    SERPAPI_API_URL: str = Field(default="https://serpapi.com/search", description="SerpApi API 基础 URL")
    
    # ScraperAPI 配置
    SCRAPERAPI_API_KEY: str = Field(default="", description="ScraperAPI API 密钥")
    SCRAPERAPI_API_URL: str = Field(default="http://api.scraperapi.com", description="ScraperAPI API 基础 URL")
    
    # 第三方 API 使用策略
    USE_THIRD_PARTY_FALLBACK: bool = Field(default=True, description="本地爬虫失败时是否回退到第三方 API")
    THIRD_PARTY_TIMEOUT: int = Field(default=30000, description="第三方 API 请求超时（毫秒）")
    THIRD_PARTY_MAX_RETRIES: int = Field(default=2, description="第三方 API 最大重试次数")
    
    # ========== 日志配置 ==========
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FILE: str = Field(default="logs/app.log", description="日志文件路径")
    LOG_MAX_BYTES: int = Field(default=10 * 1024 * 1024, description="日志文件最大大小（字节）")
    LOG_BACKUP_COUNT: int = Field(default=5, description="日志备份文件数量")
    
    # ========== CORS 配置 ==========
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173", "http://localhost", "http://localhost:80", "*"],
        description="允许的 CORS 源"
    )
    
    @property
    def database_url(self) -> str:
        """构建数据库连接 URL"""
        return f"mysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def user_agents(self) -> List[str]:
        """User-Agent 池"""
        return [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            # Firefox on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        ]
    
    @property
    def amazon_sites(self) -> dict:
        """支持的亚马逊站点配置"""
        return {
            "amazon.com": {"domain": "amazon.com", "tld": "com", "language": "en_US"},
            "amazon.co.uk": {"domain": "amazon.co.uk", "tld": "co.uk", "language": "en_GB"},
            "amazon.de": {"domain": "amazon.de", "tld": "de", "language": "de_DE"},
            "amazon.fr": {"domain": "amazon.fr", "tld": "fr", "language": "fr_FR"},
            "amazon.co.jp": {"domain": "amazon.co.jp", "tld": "co.jp", "language": "ja_JP"},
            "amazon.ca": {"domain": "amazon.ca", "tld": "ca", "language": "en_CA"},
            "amazon.com.au": {"domain": "amazon.com.au", "tld": "com.au", "language": "en_AU"},
        }
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例（用于依赖注入）"""
    return settings
