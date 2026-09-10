"""转写结果仓储。"""

from app.db.database import Database


class TranscriptRepository:
    """封装转写结果查询。"""

    def __init__(self, database: Database):
        self.database = database

    def get(self, task_id: int):
        """读取正文。"""
        return self.database.fetch_one("SELECT * FROM transcript WHERE task_id=?", (task_id,))

    def segments(self, task_id: int):
        """读取时间戳分段。"""
        return self.database.fetch_all("SELECT s.* FROM transcript_segment s JOIN transcript t ON t.id=s.transcript_id WHERE t.task_id=? ORDER BY s.sequence", (task_id,))
