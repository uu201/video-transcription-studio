"""文件转移记录仓储。"""

from app.db.database import Database


class FileTransferRepository:
    """读取文件归档历史。"""

    def __init__(self, database: Database):
        self.database = database

    def list_for_task(self, task_id: int):
        """读取任务的转移记录。"""
        return self.database.fetch_all("SELECT * FROM file_transfer WHERE task_id=? ORDER BY id", (task_id,))
