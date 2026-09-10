"""环境检测缓存单元测试。"""

import pytest
from datetime import datetime, timedelta
from app.services.environment import EnvironmentCache


def test_environment_cache_empty_by_default():
    """测试缓存默认为空。"""
    EnvironmentCache.clear()
    result = EnvironmentCache.get()
    assert result is None


def test_environment_cache_stores_data():
    """测试缓存存储数据。"""
    EnvironmentCache.clear()

    test_data = {"overall": "ok", "items": []}
    EnvironmentCache.set(test_data)

    cached = EnvironmentCache.get()
    assert cached == test_data


def test_environment_cache_expiry():
    """测试缓存过期。"""
    EnvironmentCache.clear()

    test_data = {"overall": "ok", "items": []}
    EnvironmentCache.set(test_data)

    # 立即获取应该有效
    assert EnvironmentCache.get(ttl_seconds=1) == test_data

    # 手动设置过期时间
    EnvironmentCache._cached_at = datetime.now() - timedelta(seconds=10)

    # 过期后应该返回 None
    assert EnvironmentCache.get(ttl_seconds=1) is None


def test_environment_cache_clear():
    """测试清除缓存。"""
    EnvironmentCache.clear()

    test_data = {"overall": "ok", "items": []}
    EnvironmentCache.set(test_data)

    assert EnvironmentCache.get() is not None

    EnvironmentCache.clear()
    assert EnvironmentCache.get() is None
