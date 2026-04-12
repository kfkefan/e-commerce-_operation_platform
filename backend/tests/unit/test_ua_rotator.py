"""
UA 轮换器测试
测试 UARotator 类的功能
"""
import pytest
from unittest.mock import patch

from backend.core.ua_rotator import UARotator, get_ua_rotator


class TestUARotator:
    """测试 UARotator 类"""
    
    def test_ua_rotator_initialization(self):
        """测试 UA 轮换器初始化"""
        rotator = UARotator()
        
        assert rotator.user_agents is not None
        assert len(rotator.user_agents) > 0
        assert rotator.index == 0
    
    def test_ua_rotator_with_custom_agents(self):
        """测试自定义 UA 列表"""
        custom_agents = [
            "Custom UA 1",
            "Custom UA 2",
            "Custom UA 3"
        ]
        rotator = UARotator(custom_agents=custom_agents)
        
        assert rotator.user_agents == custom_agents
        assert rotator.count == 3
    
    def test_get_next_ua_sequential(self):
        """测试顺序获取 UA"""
        custom_agents = ["UA1", "UA2", "UA3"]
        rotator = UARotator(custom_agents=custom_agents)
        
        assert rotator.get_next_ua() == "UA1"
        assert rotator.get_next_ua() == "UA2"
        assert rotator.get_next_ua() == "UA3"
        # 循环回到第一个
        assert rotator.get_next_ua() == "UA1"
    
    def test_get_random_ua(self):
        """测试随机获取 UA"""
        custom_agents = ["UA1", "UA2", "UA3"]
        rotator = UARotator(custom_agents=custom_agents)
        
        # 多次随机获取应该在列表中
        for _ in range(10):
            ua = rotator.get_random_ua()
            assert ua in custom_agents
    
    def test_get_next_ua_empty_list(self):
        """测试空 UA 列表时获取下一个"""
        rotator = UARotator(custom_agents=[])
        
        ua = rotator.get_next_ua()
        
        assert ua is not None
        assert "Mozilla" in ua
        assert "Chrome" in ua
    
    def test_get_random_ua_empty_list(self):
        """测试空 UA 列表时随机获取"""
        rotator = UARotator(custom_agents=[])
        
        ua = rotator.get_random_ua()
        
        assert ua is not None
        assert "Mozilla" in ua
    
    def test_add_ua(self):
        """测试添加 UA"""
        rotator = UARotator(custom_agents=["UA1"])
        
        rotator.add_ua("UA2")
        
        assert "UA2" in rotator.user_agents
        assert rotator.count == 2
    
    def test_add_duplicate_ua(self):
        """测试添加重复 UA"""
        rotator = UARotator(custom_agents=["UA1"])
        
        rotator.add_ua("UA1")
        
        assert rotator.count == 1  # 不应该重复添加
    
    def test_remove_ua_success(self):
        """测试成功移除 UA"""
        rotator = UARotator(custom_agents=["UA1", "UA2", "UA3"])
        
        result = rotator.remove_ua("UA2")
        
        assert result is True
        assert "UA2" not in rotator.user_agents
        assert rotator.count == 2
    
    def test_remove_ua_not_found(self):
        """测试移除不存在的 UA"""
        rotator = UARotator(custom_agents=["UA1", "UA2"])
        
        result = rotator.remove_ua("UA3")
        
        assert result is False
        assert rotator.count == 2
    
    def test_count_property(self):
        """测试 UA 池大小属性"""
        custom_agents = ["UA1", "UA2", "UA3", "UA4"]
        rotator = UARotator(custom_agents=custom_agents)
        
        assert rotator.count == 4
    
    def test_ua_rotation_does_not_modify_list(self):
        """测试 UA 轮换不修改原始列表"""
        custom_agents = ["UA1", "UA2", "UA3"]
        rotator = UARotator(custom_agents=custom_agents)
        
        # 获取所有 UA
        for _ in range(5):
            rotator.get_next_ua()
        
        # 原始列表应该保持不变
        assert rotator.user_agents == custom_agents
    
    def test_default_ua_format(self):
        """测试默认 UA 格式"""
        rotator = UARotator(custom_agents=[])
        
        ua = rotator._get_default_ua()
        
        assert ua.startswith("Mozilla/5.0")
        assert "Windows NT 10.0" in ua
        assert "Chrome" in ua


class TestGetUaRotator:
    """测试 get_ua_rotator 函数"""
    
    def test_get_ua_rotator_returns_singleton(self):
        """测试获取 UA 轮换器实例"""
        rotator1 = get_ua_rotator()
        rotator2 = get_ua_rotator()
        
        # 应该是同一个实例
        assert rotator1 is rotator2
    
    def test_get_ua_rotator_instance(self):
        """测试 UA 轮换器实例类型"""
        rotator = get_ua_rotator()
        assert isinstance(rotator, UARotator)
    
    def test_get_ua_rotator_has_agents(self):
        """测试 UA 轮换器有 UA 列表"""
        rotator = get_ua_rotator()
        
        assert len(rotator.user_agents) > 0
        assert rotator.count > 0
