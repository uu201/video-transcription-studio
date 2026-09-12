"""领域状态枚举。"""

from enum import Enum


class TaskStatus(str, Enum):
    """处理任务的生命周期状态。"""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"
    PAUSED = "PAUSED"


TASK_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.QUEUED: frozenset({TaskStatus.RUNNING, TaskStatus.PAUSED, TaskStatus.CANCELED}),
    TaskStatus.RUNNING: frozenset({TaskStatus.PAUSED, TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELED}),
    TaskStatus.PAUSED: frozenset({TaskStatus.QUEUED, TaskStatus.CANCELED}),
    TaskStatus.FAILED: frozenset({TaskStatus.QUEUED}),
    TaskStatus.CANCELED: frozenset({TaskStatus.QUEUED}),
    TaskStatus.SUCCEEDED: frozenset(),
}


def can_transition(current: str | TaskStatus, target: str | TaskStatus) -> bool:
    """Return whether a task lifecycle transition is allowed."""
    current_status = TaskStatus(current)
    target_status = TaskStatus(target)
    return target_status in TASK_TRANSITIONS[current_status]


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
