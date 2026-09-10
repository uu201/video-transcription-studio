"""全局异常处理器。"""

from __future__ import annotations

import logging
from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions import AppException

LOGGER = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """处理应用业务异常。"""
    LOGGER.warning(
        f"业务异常: {exc.code} - {exc.message}",
        extra={
            "code": exc.code,
            "retryable": exc.retryable,
            "path": request.url.path,
            "detail": exc.detail
        }
    )

    return JSONResponse(
        status_code=400,
        content={
            "error": exc.to_dict()
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未预期的异常。"""
    LOGGER.error(
        f"未处理异常: {type(exc).__name__} - {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method
        }
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "服务器内部错误",
                "code": "INTERNAL_SERVER_ERROR",
                "retryable": True,
                "detail": str(exc) if LOGGER.level <= logging.DEBUG else None
            }
        }
    )
