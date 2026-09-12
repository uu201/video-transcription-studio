"""AI 分析队列业务服务。"""
from app.db.database import utc_now
from app.repositories.ai_analysis_task import AIAnalysisTaskRepository

class AIAnalysisQueueService:
    TYPES = {
        "SUMMARY": "请生成这段内容的摘要，概括主要事实和主题。",
        "CONCLUSION": "请生成这段内容的总结，提炼最终结论、核心观点和可执行信息。",
    }
    def __init__(self, database, event_hub=None):
        self.database, self.event_hub = database, event_hub
        self.repo = AIAnalysisTaskRepository(database)

    @staticmethod
    def normalize_types(analysis_types) -> list[str]:
        """将历史类型兼容映射到当前仅支持的摘要/总结。"""
        legacy = {'OUTLINE': 'CONCLUSION', 'KEY_POINTS': 'CONCLUSION', 'QUOTES': 'CONCLUSION'}
        normalized = []
        for value in analysis_types or []:
            kind = legacy.get(str(value).upper(), str(value).upper())
            if kind in AIAnalysisQueueService.TYPES and kind not in normalized:
                normalized.append(kind)
        return normalized

    def create(self, transcript_id: int, analysis_types: list[str]):
        transcript = self.database.fetch_one("SELECT id, task_id, clean_text FROM transcript WHERE id=?", (transcript_id,))
        if not transcript: raise ValueError("转录结果不存在")
        created, skipped = [], []
        selected = self.normalize_types(analysis_types)
        if not selected:
            raise ValueError("至少选择一种分析类型")
        now = utc_now()
        with self.database.connection() as conn:
            active = conn.execute("SELECT id FROM ai_analysis_task WHERE transcript_id=? AND analysis_type='FULL' AND status IN ('QUEUED','RUNNING')", (transcript_id,)).fetchone()
            if active:
                skipped = selected
            else:
                cur = conn.execute("INSERT INTO ai_analysis_task(transcript_id,processing_task_id,analysis_type,analysis_types_json,created_at,updated_at) VALUES(?,?,?,?,?,?)", (transcript_id, transcript['task_id'], 'FULL', __import__('json').dumps(selected), now, now))
                created.append(cur.lastrowid)
        for task_id in created:
            self._publish("ai.task.created", task_id, "QUEUED", 0, "等待分析")
        return created, skipped

    def _publish(self, event_type, task_id, status, progress, message, **extra):
        if self.event_hub:
            self.event_hub.publish({"type": event_type, "taskId": task_id, "status": status, "progress": progress, "message": message, "updatedAt": utc_now(), **extra})
