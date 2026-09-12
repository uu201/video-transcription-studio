"""AI 分析队列业务服务。"""
from app.db.database import utc_now
from app.repositories.ai_analysis_task import AIAnalysisTaskRepository

class AIAnalysisQueueService:
    TYPES = {"SUMMARY": "请总结以下内容：", "OUTLINE": "请提炼以下内容的结构提纲：", "KEY_POINTS": "请提炼以下内容的核心观点：", "QUOTES": "请提取以下内容中的精彩金句："}
    def __init__(self, database, event_hub=None):
        self.database, self.event_hub = database, event_hub
        self.repo = AIAnalysisTaskRepository(database)

    def create(self, transcript_id: int, analysis_types: list[str]):
        transcript = self.database.fetch_one("SELECT id, task_id, clean_text FROM transcript WHERE id=?", (transcript_id,))
        if not transcript: raise ValueError("转录结果不存在")
        created, skipped = [], []
        now = utc_now()
        with self.database.connection() as conn:
            for kind in dict.fromkeys(analysis_types):
                kind = kind.upper()
                if kind not in self.TYPES: continue
                active = conn.execute("SELECT id FROM ai_analysis_task WHERE transcript_id=? AND analysis_type=? AND status IN ('QUEUED','RUNNING')", (transcript_id, kind)).fetchone()
                if active: skipped.append(kind); continue
                cur = conn.execute("INSERT INTO ai_analysis_task(transcript_id,processing_task_id,analysis_type,created_at,updated_at) VALUES(?,?,?,?,?)", (transcript_id, transcript['task_id'], kind, now, now))
                created.append(cur.lastrowid)
        for task_id in created:
            self._publish("ai.task.created", task_id, "QUEUED", 0, "等待分析")
        return created, skipped

    def _publish(self, event_type, task_id, status, progress, message, **extra):
        if self.event_hub:
            self.event_hub.publish({"type": event_type, "taskId": task_id, "status": status, "progress": progress, "message": message, "updatedAt": utc_now(), **extra})
