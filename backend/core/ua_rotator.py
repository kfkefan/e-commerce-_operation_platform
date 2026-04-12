"""
User-Agent 轮换器
提供 UA 池管理和轮换功能
"""
import random
from typing import List
from backend.config import settings


class UARotator:
    """User-Agent 轮换器"""
    
    def __init__(self, custom_agents: List[str] = None):
        """
        初始化 UA 轮换器
        
        Args:
            custom_agents: 自定义 UA 列表，如果为 None 则使用默认配置
        """
        self.user_agents = custom_agents or settings.user_agents
        self.index = 0
        self._lock = False
    
    def get_next_ua(self) -> str:
        """
        获取下一个 User-Agent（顺序轮换）
        
        Returns:
            User-Agent 字符串
        """
        if not self.user_agents:
            return self._get_default_ua()
        
        ua = self.user_agents[self.index % len(self.user_agents)]
        self.index += 1
        return ua
    
    def get_random_ua(self) -> str:
        """
        获取随机 User-Agent
        
        Returns:
            User-Agent 字符串
        """
        if not self.user_agents:
            return self._get_default_ua()
        
        return random.choice(self.user_agents)
    
    def _get_default_ua(self) -> str:
        """默认 UA"""
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    
    def add_ua(self, ua: str) -> None:
        """
        添加新的 User-Agent 到池中
        
        Args:
            ua: User-Agent 字符串
        """
        if ua and ua not in self.user_agents:
            self.user_agents.append(ua)
    
    def remove_ua(self, ua: str) -> bool:
        """
        从池中移除 User-Agent
        
        Args:
            ua: User-Agent 字符串
        
        Returns:
            是否成功移除
        """
        if ua in self.user_agents:
            self.user_agents.remove(ua)
            return True
        return False
    
    @property
    def count(self) -> int:
        """UA 池大小"""
        return len(self.user_agents)


# 全局 UA 轮换器实例
ua_rotator = UARotator()


def get_ua_rotator() -> UARotator:
    """获取 UA 轮换器实例"""
    return ua_rotator
