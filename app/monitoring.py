"""性能监控工具。"""

from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Callable, Any

LOGGER = logging.getLogger(__name__)


def monitor_performance(func: Callable) -> Callable:
    """性能监控装饰器：记录函数执行时间。"""

    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> Any:
        start = time.time()
        error_occurred = False

        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            error_occurred = True
            raise
        finally:
            duration_ms = (time.time() - start) * 1000

            log_data = {
                "function": func.__name__,
                "module": func.__module__,
                "duration_ms": f"{duration_ms:.2f}",
                "error": error_occurred
            }

            # 根据执行时间选择日志级别
            if error_occurred:
                LOGGER.warning(f"性能监控: {func.__name__} 执行失败", extra=log_data)
            elif duration_ms > 5000:
                LOGGER.warning(f"性能监控: {func.__name__} 执行缓慢 ({duration_ms:.0f}ms)", extra=log_data)
            elif duration_ms > 1000:
                LOGGER.info(f"性能监控: {func.__name__} 执行完成 ({duration_ms:.0f}ms)", extra=log_data)
            else:
                LOGGER.debug(f"性能监控: {func.__name__} 执行完成 ({duration_ms:.0f}ms)", extra=log_data)

    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> Any:
        start = time.time()
        error_occurred = False

        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            error_occurred = True
            raise
        finally:
            duration_ms = (time.time() - start) * 1000

            log_data = {
                "function": func.__name__,
                "module": func.__module__,
                "duration_ms": f"{duration_ms:.2f}",
                "error": error_occurred
            }

            if error_occurred:
                LOGGER.warning(f"性能监控: {func.__name__} 执行失败", extra=log_data)
            elif duration_ms > 5000:
                LOGGER.warning(f"性能监控: {func.__name__} 执行缓慢 ({duration_ms:.0f}ms)", extra=log_data)
            elif duration_ms > 1000:
                LOGGER.info(f"性能监控: {func.__name__} 执行完成 ({duration_ms:.0f}ms)", extra=log_data)
            else:
                LOGGER.debug(f"性能监控: {func.__name__} 执行完成 ({duration_ms:.0f}ms)", extra=log_data)

    # 根据函数类型返回对应的包装器
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


class PerformanceTimer:
    """性能计时器上下文管理器。"""

    def __init__(self, name: str, logger: logging.Logger = None):
        self.name = name
        self.logger = logger or LOGGER
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration_ms = (self.end_time - self.start_time) * 1000

        if exc_type:
            self.logger.warning(f"{self.name} 执行失败 ({duration_ms:.0f}ms)")
        elif duration_ms > 1000:
            self.logger.info(f"{self.name} 执行完成 ({duration_ms:.0f}ms)")
        else:
            self.logger.debug(f"{self.name} 执行完成 ({duration_ms:.0f}ms)")

    @property
    def duration_ms(self) -> float:
        """获取执行时长（毫秒）。"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


# 使用示例:
#
# @monitor_performance
# def process_task(task_id: int):
#     # 任务处理逻辑
#     pass
#
# with PerformanceTimer("扫描文件"):
#     scan_directory(path)
