"""扫描本地目录并创建去重媒体记录与任务。"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path

from app.db.database import Database, utc_now
from app.domain.schemas import ScanResult


class Scanner:
    """递归发现支持的音视频文件。"""

    MEDIA_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v", ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".weba", ".wma"}

    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def fingerprint(path: Path, stat: os.stat_result) -> str:
        """使用大小、修改时间和文件头生成稳定指纹，避免重复读取大文件。"""
        digest = hashlib.sha256()
        digest.update(f"{stat.st_size}:{stat.st_mtime_ns}".encode())
        with path.open("rb") as handle:
            digest.update(handle.read(1024 * 1024))
        return digest.hexdigest()

    @staticmethod
    def is_stable(path: Path, wait_seconds: int) -> bool:
        """通过两次大小和修改时间采样，跳过仍在复制的文件。"""
        if wait_seconds <= 0:
            return True
        try:
            first = path.stat()
            time.sleep(min(wait_seconds, 5))
            second = path.stat()
            return first.st_size == second.st_size and first.st_mtime_ns == second.st_mtime_ns
        except OSError:
            return False

    def scan(self, source_id: int) -> ScanResult:
        """扫描指定源并为新版本创建排队任务。"""
        source = self.database.fetch_one("SELECT * FROM scan_source WHERE id = ?", (source_id,))
        if not source:
            raise ValueError("扫描源不存在")
        root = Path(source["root_path"])
        result = ScanResult()
        if not root.is_dir():
            result.errors.append(f"目录不存在或不可读：{root}")
            result.failed = 1
            return result
        iterator = root.rglob("*") if source["recursive"] else root.glob("*")
        for path in iterator:
            if not path.is_file() or path.suffix.lower() not in self.MEDIA_EXTENSIONS:
                continue
            result.discovered += 1
            try:
                stat = path.stat()
                if not self.is_stable(path, int(source["stable_wait_seconds"])):
                    result.skipped += 1
                    continue
                stat = path.stat()
                fingerprint = self.fingerprint(path, stat)
                existing = self.database.fetch_one("SELECT id FROM media_file WHERE scan_source_id = ? AND path = ? AND fingerprint = ?", (source_id, str(path), fingerprint))
                if existing:
                    result.skipped += 1
                    continue
                now = utc_now()
                media_id = self.database.execute("INSERT INTO media_file (scan_source_id, path, file_name, extension, size_bytes, modified_at, fingerprint, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (source_id, str(path), path.name, path.suffix.lower(), stat.st_size, str(stat.st_mtime), fingerprint, now, now))
                self.database.execute("INSERT INTO processing_task (media_file_id, created_at, updated_at) VALUES (?, ?, ?)", (media_id, now, now))
                result.created += 1
            except (OSError, ValueError) as exc:
                result.failed += 1
                result.errors.append(f"{path.name}: {exc}")
        return result
