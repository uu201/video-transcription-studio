"""任务实时事件总线。

Worker 运行在线程中，WebSocket 运行在 asyncio 事件循环中。这里使用线程安全
队列隔离两者，避免业务服务直接依赖 WebSocket 实现。
"""

from __future__ import annotations

import queue
from typing import Any


class TaskEventHub:
    """将任务阶段事件广播给所有 WebSocket 订阅者。"""

    def __init__(self) -> None:
        self._subscribers: list[queue.Queue[dict[str, Any]]] = []
        self._lock = __import__("threading").Lock()

    def subscribe(self) -> queue.Queue[dict[str, Any]]:
        """创建一个订阅队列。"""
        subscriber: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers.append(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue[dict[str, Any]]) -> None:
        """移除断开的订阅。"""
        with self._lock:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)

    def publish(self, payload: dict[str, Any]) -> None:
        """广播消息；慢客户端只丢弃旧消息，不阻塞 Worker。"""
        with self._lock:
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(payload)
            except queue.Full:
                try:
                    subscriber.get_nowait()
                    subscriber.put_nowait(payload)
                except queue.Empty:
                    pass

    def wait(self, subscriber: queue.Queue[dict[str, Any]], timeout: float = 20) -> dict[str, Any] | None:
        """等待一条消息，超时返回 None 让连接发送心跳。"""
        try:
            return subscriber.get(timeout=timeout)
        except queue.Empty:
            return None
