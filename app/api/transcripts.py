"""转写 API 路由兼容入口，实际实现位于 tasks 路由。"""

from app.api.tasks import router

__all__ = ["router"]
