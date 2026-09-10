"""媒体文件仓储。"""

from app.db.database import Database


class MediaFileRepository:
    """封装媒体文件查询。"""

    def __init__(self, database: Database):
        self.database = database

    def get(self, media_id: int):
        """读取媒体文件。"""
        return self.database.fetch_one("SELECT * FROM media_file WHERE id=?", (media_id,))
