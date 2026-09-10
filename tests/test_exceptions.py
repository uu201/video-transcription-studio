"""应用异常单元测试。"""

import pytest
from app.exceptions import (
    AppException,
    MediaNotFoundException,
    FFmpegException,
    ASRDependencyException,
    TaskCancelledException
)


def test_app_exception_basic():
    """测试基础异常。"""
    exc = AppException(
        message="测试错误",
        code="TEST_ERROR",
        retryable=True,
        detail="详细信息"
    )

    assert exc.message == "测试错误"
    assert exc.code == "TEST_ERROR"
    assert exc.retryable is True
    assert exc.detail == "详细信息"


def test_app_exception_to_dict():
    """测试异常转字典。"""
    exc = AppException(
        message="测试错误",
        code="TEST_ERROR",
        retryable=False
    )

    result = exc.to_dict()

    assert result["message"] == "测试错误"
    assert result["code"] == "TEST_ERROR"
    assert result["retryable"] is False


def test_media_not_found_exception():
    """测试媒体文件不存在异常。"""
    exc = MediaNotFoundException("/path/to/video.mp4")

    assert exc.code == "MEDIA_NOT_FOUND"
    assert exc.retryable is False
    assert "/path/to/video.mp4" in exc.message


def test_ffmpeg_exception():
    """测试 FFmpeg 异常。"""
    exc = FFmpegException(
        command="ffmpeg -i input.mp4",
        stderr="Error: invalid file",
        returncode=1
    )

    assert exc.code == "FFMPEG_ERROR"
    assert exc.retryable is True
    assert exc.returncode == 1
    assert "Error: invalid file" in exc.detail


def test_asr_dependency_exception():
    """测试 ASR 依赖异常。"""
    exc = ASRDependencyException("funasr")

    assert exc.code == "ASR_DEPENDENCY_MISSING"
    assert exc.retryable is False
    assert "funasr" in exc.message


def test_task_cancelled_exception():
    """测试任务取消异常。"""
    exc = TaskCancelledException(task_id=123)

    assert exc.code == "TASK_CANCELLED"
    assert exc.retryable is False
    assert "123" in exc.message
