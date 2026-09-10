"""扫描源仓储。"""

from app.db.database import Database


class ScanSourceRepository:
    """封装扫描源读写。"""

    def __init__(self, database: Database):
        self.database = database

    def get(self, source_id: int):
        """读取一个扫描源。"""
        return self.database.fetch_one("SELECT * FROM scan_source WHERE id=?", (source_id,))

    def list(self):
        """读取全部扫描源。"""
        return self.database.fetch_all("SELECT * FROM scan_source ORDER BY id DESC")
