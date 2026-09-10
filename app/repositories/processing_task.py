"""处理任务仓储，供服务层复用。"""

from app.db.database import Database


class ProcessingTaskRepository:
    """封装任务读取，避免业务代码拼接跨表查询。"""

    def __init__(self, database: Database):
        self.database = database

    def get(self, task_id: int):
        """读取任务和媒体路径。"""
        return self.database.fetch_one("SELECT t.*, m.file_name, m.path FROM processing_task t JOIN media_file m ON m.id=t.media_file_id WHERE t.id=?", (task_id,))

    def list(self, limit: int = 100):
        """按创建时间倒序读取任务。"""
        return self.database.fetch_all("SELECT t.*, m.file_name, m.path FROM processing_task t JOIN media_file m ON m.id=t.media_file_id ORDER BY t.created_at DESC LIMIT ?", (limit,))
