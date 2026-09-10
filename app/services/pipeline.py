"""任务流水线编排。"""

from __future__ import annotations

import json
import logging
import traceback
from pathlib import Path
from typing import Callable

from app.config import Settings
from app.db.database import Database, utc_now
from app.domain.enums import TaskStage, TaskStatus, STAGE_MESSAGES
from app.domain.schemas import AppError
from app.services.asr.sensevoice_provider import SenseVoiceProvider
from app.services.audio_extractor import AudioExtractor
from app.services.exporter import Exporter
from app.services.media_probe import MediaProbe
from app.services.media_toolchain import MediaToolchain
from app.services.text_processor import TextProcessor

LOGGER = logging.getLogger(__name__)


class PipelineService:
    """按阶段更新任务并保存完整转写结果。"""

    def __init__(self, settings: Settings, database: Database):
        self.settings = settings
        self.database = database
        self.toolchain = MediaToolchain.from_app_root(settings)
        self.probe = MediaProbe(self.toolchain)
        self.extractor = AudioExtractor(self.toolchain, settings.cache_dir)
        self.provider = SenseVoiceProvider(settings)
        self.processor = TextProcessor()
        self.exporter = Exporter(settings)

    def _update(self, task_id: int, stage: TaskStage, progress: int, message: str | None = None) -> None:
        """提交阶段状态与任务事件，保持事务短小。"""
        now = utc_now()
        text = message or STAGE_MESSAGES[stage]
        with self.database.connection() as connection:
            connection.execute("UPDATE processing_task SET current_stage = ?, progress = ?, message = ?, heartbeat_at = ?, updated_at = ? WHERE id = ?", (stage.value, progress, text, now, now, task_id))
            connection.execute("INSERT INTO task_event (task_id, stage, level, message, created_at) VALUES (?, ?, 'INFO', ?, ?)", (task_id, stage.value, text, now))

    def _cancelled(self, task_id: int) -> bool:
        """检查 Web 请求的取消标记。"""
        row = self.database.fetch_one("SELECT cancel_requested FROM processing_task WHERE id = ?", (task_id,))
        return bool(row and row["cancel_requested"])

    def process(self, task_id: int) -> None:
        """执行单个任务，统一分类异常并清理临时目录。"""
        task = self.database.fetch_one("SELECT t.*, m.path, m.file_name, m.extension FROM processing_task t JOIN media_file m ON m.id = t.media_file_id WHERE t.id = ?", (task_id,))
        if not task:
            return
        media_path = Path(task["path"])
        try:
            self._update(task_id, TaskStage.PROBING, 5)
            media_info = self.probe.inspect(media_path)
            if self._cancelled(task_id):
                raise AppError("TASK_CANCELED", "任务已取消", retryable=False)
            self.database.execute("UPDATE media_file SET media_info_json = ?, updated_at = ? WHERE id = ?", (json.dumps(media_info.__dict__, ensure_ascii=False), utc_now(), task["media_file_id"]))
            self._update(task_id, TaskStage.EXTRACTING, 20)
            audio_path = self.extractor.prepare(media_path, task_id)
            if self._cancelled(task_id):
                raise AppError("TASK_CANCELED", "任务已取消", retryable=False)
            self._update(task_id, TaskStage.TRANSCRIBING, 70)
            options = json.loads(task["asr_options_json"] or "{}")
            asr_result = self.provider.transcribe(audio_path, task["language"], options)
            self._update(task_id, TaskStage.POST_PROCESSING, 80)
            clean_text = self.processor.process(asr_result)
            self._update(task_id, TaskStage.SAVING, 85)
            self._save_transcript(task_id, asr_result, clean_text)
            paths = self.exporter.export(task_id, asr_result, clean_text)
            now = utc_now()
            with self.database.connection() as connection:
                for export_type, path in paths.items():
                    connection.execute("INSERT INTO export_record (task_id, export_type, file_path, created_at) VALUES (?, ?, ?, ?)", (task_id, export_type, str(path), now))
                connection.execute("UPDATE processing_task SET status = 'SUCCEEDED', current_stage = 'COMPLETED', progress = 100, message = '已完成', finished_at = ?, heartbeat_at = ?, updated_at = ? WHERE id = ?", (now, now, now, task_id))
                connection.execute("INSERT INTO task_event (task_id, stage, level, message, created_at) VALUES (?, 'COMPLETED', 'SUCCESS', '处理完成', ?)", (task_id, now))
            LOGGER.info("任务 #%s | 处理完成：%d 段 | %d 字符", task_id, len(asr_result.segments), len(clean_text))
        except AppError as exc:
            self._fail(task_id, exc)
        except Exception as exc:  # pragma: no cover - 防止后台线程静默退出
            LOGGER.exception("任务 #%s | 未处理异常", task_id)
            self._fail(task_id, AppError("INTERNAL_ERROR", "任务处理失败", traceback.format_exc(), True, "查看日志后重试"))
        finally:
            self.extractor.cleanup(task_id)

    def _save_transcript(self, task_id: int, result, clean_text: str) -> None:
        """以一个事务保存转写正文和分段。"""
        now = utc_now()
        with self.database.connection() as connection:
            connection.execute("INSERT INTO transcript (task_id, language, raw_text, clean_text, raw_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(task_id) DO UPDATE SET language=excluded.language, raw_text=excluded.raw_text, clean_text=excluded.clean_text, raw_json=excluded.raw_json, version=transcript.version + 1, updated_at=excluded.updated_at", (task_id, result.language, result.text, clean_text, json.dumps(result.raw_result, ensure_ascii=False), now, now))
            transcript = connection.execute("SELECT id FROM transcript WHERE task_id = ?", (task_id,)).fetchone()
            connection.execute("DELETE FROM transcript_segment WHERE transcript_id = ?", (transcript["id"],))
            connection.executemany("INSERT INTO transcript_segment (transcript_id, sequence, start_seconds, end_seconds, text, speaker, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)", [(transcript["id"], segment.sequence, segment.start, segment.end, segment.text, segment.speaker, segment.confidence) for segment in result.segments])

    def _fail(self, task_id: int, error: AppError) -> None:
        """保存面向用户的失败状态和事件。"""
        status = TaskStatus.CANCELED.value if error.code == "TASK_CANCELED" else TaskStatus.FAILED.value
        now = utc_now()
        with self.database.connection() as connection:
            connection.execute("UPDATE processing_task SET status = ?, error_code = ?, error_message = ?, error_detail = ?, retryable = ?, message = ?, finished_at = ?, updated_at = ? WHERE id = ?", (status, error.code, error.user_message, error.detail, int(error.retryable), error.user_message, now, now, task_id))
            connection.execute("INSERT INTO task_event (task_id, stage, level, message, detail, created_at) VALUES (?, ?, 'ERROR', ?, ?, ?)", (task_id, TaskStage.COMPLETED.value, error.user_message, error.user_action, now))
