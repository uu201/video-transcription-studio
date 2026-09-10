"""应用异常定义和错误处理。"""

from __future__ import annotations


class AppException(Exception):
    """应用基础异常，所有业务异常都应继承此类。"""

    def __init__(self, message: str, code: str, retryable: bool = False, detail: str | None = None):
        self.message = message
        self.code = code
        self.retryable = retryable
        self.detail = detail
        super().__init__(message)

    def to_dict(self) -> dict:
        """转换为 API 响应格式。"""
        return {
            "message": self.message,
            "code": self.code,
            "retryable": self.retryable,
            "detail": self.detail
        }


# ==================== 媒体文件相关异常 ====================

class MediaNotFoundException(AppException):
    """媒体文件不存在。"""

    def __init__(self, file_path: str):
        super().__init__(
            message=f"媒体文件不存在: {file_path}",
            code="MEDIA_NOT_FOUND",
            retryable=False,
            detail=f"找不到文件: {file_path}"
        )


class MediaReadException(AppException):
    """媒体文件读取失败。"""

    def __init__(self, file_path: str, reason: str):
        super().__init__(
            message=f"无法读取媒体文件: {file_path}",
            code="MEDIA_READ_ERROR",
            retryable=True,
            detail=reason
        )


# ==================== FFmpeg 相关异常 ====================

class FFmpegNotFoundException(AppException):
    """FFmpeg 未找到。"""

    def __init__(self):
        super().__init__(
            message="FFmpeg 未安装或未配置",
            code="FFMPEG_NOT_FOUND",
            retryable=False,
            detail="请安装 FFmpeg 或设置 VIDEO_TEXT_FFMPEG_DIR 环境变量"
        )


class FFmpegException(AppException):
    """FFmpeg 执行失败。"""

    def __init__(self, command: str, stderr: str, returncode: int):
        super().__init__(
            message="FFmpeg 执行失败",
            code="FFMPEG_ERROR",
            retryable=True,
            detail=f"命令: {command}\n返回码: {returncode}\n错误输出: {stderr}"
        )
        self.stderr = stderr
        self.returncode = returncode


# ==================== ASR 相关异常 ====================

class ASRDependencyException(AppException):
    """ASR 依赖缺失。"""

    def __init__(self, missing_package: str):
        super().__init__(
            message=f"ASR 依赖缺失: {missing_package}",
            code="ASR_DEPENDENCY_MISSING",
            retryable=False,
            detail=f"请运行: pip install {missing_package}"
        )


class ASRModelNotFoundException(AppException):
    """ASR 模型未找到。"""

    def __init__(self, model_name: str):
        super().__init__(
            message=f"ASR 模型未下载: {model_name}",
            code="ASR_MODEL_NOT_FOUND",
            retryable=True,
            detail=f"首次运行时将自动下载模型: {model_name}"
        )


class ASRInferenceException(AppException):
    """ASR 推理失败。"""

    def __init__(self, reason: str):
        super().__init__(
            message="语音识别失败",
            code="ASR_INFERENCE_ERROR",
            retryable=True,
            detail=reason
        )


# ==================== 数据库相关异常 ====================

class DatabaseException(AppException):
    """数据库操作失败。"""

    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"数据库操作失败: {operation}",
            code="DATABASE_ERROR",
            retryable=True,
            detail=reason
        )


class RecordNotFoundException(AppException):
    """数据库记录不存在。"""

    def __init__(self, record_type: str, record_id: int | str):
        super().__init__(
            message=f"{record_type} 不存在: {record_id}",
            code="RECORD_NOT_FOUND",
            retryable=False,
            detail=f"找不到 {record_type} 记录: {record_id}"
        )


# ==================== 任务相关异常 ====================

class TaskCancelledException(AppException):
    """任务已被取消。"""

    def __init__(self, task_id: int):
        super().__init__(
            message=f"任务已被取消: {task_id}",
            code="TASK_CANCELLED",
            retryable=False,
            detail=f"任务 {task_id} 在处理过程中被取消"
        )


class TaskTimeoutException(AppException):
    """任务超时。"""

    def __init__(self, task_id: int, timeout_seconds: int):
        super().__init__(
            message=f"任务超时: {task_id}",
            code="TASK_TIMEOUT",
            retryable=True,
            detail=f"任务 {task_id} 执行超过 {timeout_seconds} 秒"
        )


# ==================== 扫描相关异常 ====================

class ScanSourceException(AppException):
    """扫描源异常。"""

    def __init__(self, source_path: str, reason: str):
        super().__init__(
            message=f"扫描源访问失败: {source_path}",
            code="SCAN_SOURCE_ERROR",
            retryable=True,
            detail=reason
        )


class InvalidPathException(AppException):
    """路径无效。"""

    def __init__(self, path: str, reason: str = "路径不存在或无法访问"):
        super().__init__(
            message=f"无效路径: {path}",
            code="INVALID_PATH",
            retryable=False,
            detail=reason
        )


# ==================== 配置相关异常 ====================

class ConfigurationException(AppException):
    """配置错误。"""

    def __init__(self, config_key: str, reason: str):
        super().__init__(
            message=f"配置错误: {config_key}",
            code="CONFIGURATION_ERROR",
            retryable=False,
            detail=reason
        )
