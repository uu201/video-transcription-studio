"""AI 分析队列任务仓储。"""
from app.db.database import Database, utc_now

class AIAnalysisTaskRepository:
    def __init__(self, database: Database):
        self.database = database

    def get(self, task_id: int):
        return self.database.fetch_one("""SELECT a.*, t.task_id AS transcription_task_id,
            p.status AS transcription_status, m.file_name
            FROM ai_analysis_task a JOIN transcript t ON t.id=a.transcript_id
            LEFT JOIN processing_task p ON p.id=t.task_id
            LEFT JOIN media_file m ON m.id=p.media_file_id WHERE a.id=?""", (task_id,))

    def list(self, status: str | None = None):
        sql = """SELECT a.*, t.task_id AS transcription_task_id, m.file_name
            FROM ai_analysis_task a JOIN transcript t ON t.id=a.transcript_id
            JOIN processing_task p ON p.id=t.task_id JOIN media_file m ON m.id=p.media_file_id"""
        params = []
        if status:
            sql += " WHERE a.status=?"; params.append(status)
        sql += " ORDER BY a.created_at DESC"
        return self.database.fetch_all(sql, tuple(params))

    def active(self, transcript_id: int, analysis_type: str):
        return self.database.fetch_one("SELECT * FROM ai_analysis_task WHERE transcript_id=? AND analysis_type=? AND status IN ('QUEUED','RUNNING') ORDER BY id DESC LIMIT 1", (transcript_id, analysis_type))

    def claim_next(self, worker_id: str):
        now = utc_now()
        with self.database.connection() as conn:
            row = conn.execute("SELECT id FROM ai_analysis_task WHERE status='QUEUED' AND cancel_requested=0 AND pause_requested=0 ORDER BY created_at LIMIT 1").fetchone()
            if not row: return None
            changed = conn.execute("UPDATE ai_analysis_task SET status='RUNNING', progress=1, message='开始分析', worker_id=?, started_at=COALESCE(started_at,?), heartbeat_at=?, updated_at=? WHERE id=? AND status='QUEUED'", (worker_id, now, now, now, row['id'])).rowcount
            return int(row['id']) if changed else None

    def update(self, task_id: int, **fields):
        if not fields: return
        fields['updated_at'] = utc_now()
        sql = "UPDATE ai_analysis_task SET " + ", ".join(f"{k}=?" for k in fields) + " WHERE id=?"
        self.database.execute(sql, tuple(fields.values()) + (task_id,))
