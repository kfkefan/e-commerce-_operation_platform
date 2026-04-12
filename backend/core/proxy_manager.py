"""
代理管理器
提供代理池管理和健康检查功能
"""
import logging
from typing import List, Optional
from backend.config import settings

logger = logging.getLogger(__name__)


class ProxyPool:
    """代理池管理器"""
    
    def __init__(self, proxies: List[str] = None):
        """
        初始化代理池
        
        Args:
            proxies: 代理列表，格式如 "http://user:pass@proxy:8080"
        """
        self.proxies = proxies or settings.PROXY_LIST
        self.current_index = 0
        self.failed_proxies = set()
        self._lock = False
    
    def get_proxy(self) -> Optional[str]:
        """
        获取下一个可用代理
        
        Returns:
            代理地址，如果没有可用代理则返回 None
        """
        if not self.proxies:
            return None
        
        # 过滤掉失败的代理
        available_proxies = [p for p in self.proxies if p not in self.failed_proxies]
        
        if not available_proxies:
            logger.warning("所有代理都已失败，重置失败列表")
            self.failed_proxies.clear()
            available_proxies = self.proxies
        
        proxy = available_proxies[self.current_index % len(available_proxies)]
        self.current_index += 1
        return proxy
    
    def mark_failed(self, proxy: str) -> None:
        """
        标记代理为失败
        
        Args:
            proxy: 代理地址
        """
        if proxy:
            self.failed_proxies.add(proxy)
            logger.warning(f"代理标记为失败：{proxy}")
    
    def mark_success(self, proxy: str) -> None:
        """
        标记代理为成功（从失败列表中移除）
        
        Args:
            proxy: 代理地址
        """
        if proxy in self.failed_proxies:
            self.failed_proxies.remove(proxy)
            logger.info(f"代理恢复成功：{proxy}")
    
    def add_proxy(self, proxy: str) -> None:
        """
        添加新代理到池中
        
        Args:
            proxy: 代理地址
        """
        if proxy and proxy not in self.proxies:
            self.proxies.append(proxy)
            logger.info(f"添加新代理：{proxy}")
    
    def remove_proxy(self, proxy: str) -> bool:
        """
        从池中移除代理
        
        Args:
            proxy: 代理地址
        
        Returns:
            是否成功移除
        """
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            self.failed_proxies.discard(proxy)
            logger.info(f"移除代理：{proxy}")
            return True
        return False
    
    def clear_failed(self) -> None:
        """清空失败代理列表"""
        self.failed_proxies.clear()
        logger.info("已清空失败代理列表")
    
    @property
    def total_count(self) -> int:
        """代理总数"""
        return len(self.proxies)
    
    @property
    def available_count(self) -> int:
        """可用代理数"""
        return len(self.proxies) - len(self.failed_proxies)
    
    @property
    def is_enabled(self) -> bool:
        """代理池是否启用"""
        return settings.PROXY_POOL_ENABLED and len(self.proxies) > 0


# 全局代理池实例
proxy_pool = ProxyPool()


def get_proxy_pool() -> ProxyPool:
    """获取代理池实例"""
    return proxy_pool
