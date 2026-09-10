"""AI 分析结果仓储。"""

from app.db.database import Database


class AnalysisRepository:
    """读取 AI 分析结果。"""

    def __init__(self, database: Database):
        self.database = database

    def list_for_task(self, task_id: int):
        """读取任务的分析历史。"""
        return self.database.fetch_all("SELECT * FROM ai_analysis WHERE task_id=? ORDER BY id", (task_id,))
