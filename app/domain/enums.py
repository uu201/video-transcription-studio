"""领域状态枚举。"""

from enum import Enum


class TaskStatus(str, Enum):
    """处理任务的生命周期状态。"""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class TaskStage(str, Enum):
    """页面展示的处理阶段。"""

    QUEUED = "QUEUED"
    PROBING = "PROBING"
    EXTRACTING = "EXTRACTING"
    TRANSCRIBING = "TRANSCRIBING"
    POST_PROCESSING = "POST_PROCESSING"
    SAVING = "SAVING"
    ANALYZING = "ANALYZING"
    TRANSFERRING = "TRANSFERRING"
    COMPLETED = "COMPLETED"


STAGE_MESSAGES = {
    TaskStage.QUEUED: "等待处理",
    TaskStage.PROBING: "正在读取媒体信息",
    TaskStage.EXTRACTING: "正在提取音频",
    TaskStage.TRANSCRIBING: "正在识别音频，请稍候",
    TaskStage.POST_PROCESSING: "正在整理文案",
    TaskStage.SAVING: "正在保存结果",
    TaskStage.ANALYZING: "正在进行 AI 分析",
    TaskStage.TRANSFERRING: "正在归档文件",
    TaskStage.COMPLETED: "已完成",
}
