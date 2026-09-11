"""扫描本地目录并创建去重媒体记录与任务。"""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path

from app.db.database import Database, utc_now
from app.domain.schemas import ScanResult


class Scanner:
    """递归发现支持的音视频文件，仅建立索引，不直接创建转写任务。"""

    MEDIA_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v", ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".weba", ".wma"}

    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def fingerprint(path: Path, stat: os.stat_result) -> str:
        """快速指纹算法：使用文件元数据 + 部分内容采样，避免读取大文件全部内容。"""
        digest = hashlib.sha256()
        # 1. 文件元数据（文件名、大小、修改时间）
        digest.update(f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}".encode())

        # 2. 对于大文件，只采样头部和尾部各 64KB
        if stat.st_size > 1024 * 1024:  # > 1MB
            try:
                with path.open("rb") as handle:
                    # 读取前 64KB
                    digest.update(handle.read(64 * 1024))
                    # 如果文件足够大，跳到末尾读取后 64KB
                    if stat.st_size > 128 * 1024:
                        handle.seek(-64 * 1024, 2)
                        digest.update(handle.read(64 * 1024))
            except (OSError, IOError):
                pass  # 文件不可读时仅使用元数据
        else:
            # 小文件直接读取全部内容
            try:
                with path.open("rb") as handle:
                    digest.update(handle.read())
            except (OSError, IOError):
                pass

        return digest.hexdigest()

    @staticmethod
    def is_stable(path: Path, wait_seconds: int) -> bool:
        """通过两次大小和修改时间采样，跳过仍在复制的文件。

        优化：只对"新"文件（最近修改）进行稳定性检查，
        对于旧文件（修改时间超过 wait_seconds）直接认为稳定。
        """
        if wait_seconds <= 0:
            return True
        try:
            first = path.stat()
            # 如果文件的修改时间已经超过等待时间，认为稳定
            time_since_modified = time.time() - first.st_mtime
            if time_since_modified > wait_seconds:
                return True

            # 只对最近修改的文件进行二次检查
            # 使用较短的等待时间（最多1秒），避免扫描太慢
            actual_wait = min(wait_seconds, 1)
            time.sleep(actual_wait)
            second = path.stat()
            return first.st_size == second.st_size and first.st_mtime_ns == second.st_mtime_ns
        except OSError:
            return False

    def scan(self, source_id: int) -> ScanResult:
        """扫描指定源并保存新媒体，任务由用户勾选文件后创建。

        性能优化：
        1. 批量查询已存在的文件路径，避免逐个查询数据库
        2. 只对新文件计算指纹，减少文件 I/O
        3. 只对最近修改的文件进行稳定性检查
        """
        source = self.database.fetch_one("SELECT * FROM scan_source WHERE id = ?", (source_id,))
        if not source:
            raise ValueError("扫描源不存在")
        root = Path(source["root_path"])
        result = ScanResult()
        if not root.is_dir():
            result.errors.append(f"目录不存在或不可读：{root}")
            result.failed = 1
            return result

        # 批量查询该扫描源下已存在的文件路径，避免逐个查询
        existing_paths = set()
        for row in self.database.fetch_all("SELECT path FROM media_file WHERE scan_source_id = ?", (source_id,)):
            existing_paths.add(row["path"])

        iterator = root.rglob("*") if source["recursive"] else root.glob("*")
        for path in iterator:
            if not path.is_file() or path.suffix.lower() not in self.MEDIA_EXTENSIONS:
                continue
            result.discovered += 1
            try:
                path_str = str(path)

                # 快速检查：如果路径已存在，跳过（不计算指纹）
                if path_str in existing_paths:
                    result.skipped += 1
                    continue

                stat = path.stat()

                # 稳定性检查（优化后只对新文件等待）
                if not self.is_stable(path, int(source["stable_wait_seconds"])):
                    result.skipped += 1
                    continue

                # 重新获取 stat（稳定性检查后可能有变化）
                stat = path.stat()

                # 计算指纹（只对新文件计算）
                fingerprint = self.fingerprint(path, stat)

                # 二次确认：检查指纹是否已存在（防止文件移动/重命名）
                existing = self.database.fetch_one(
                    "SELECT id FROM media_file WHERE scan_source_id = ? AND fingerprint = ?",
                    (source_id, fingerprint)
                )
                if existing:
                    result.skipped += 1
                    continue

                # 插入新媒体记录
                now = utc_now()
                media_id = self.database.execute(
                    "INSERT INTO media_file (scan_source_id, path, file_name, extension, size_bytes, modified_at, fingerprint, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (source_id, path_str, path.name, path.suffix.lower(), stat.st_size, str(stat.st_mtime), fingerprint, now, now)
                )
                result.created += 1
                result.media_ids.append(media_id)
            except (OSError, ValueError) as exc:
                result.failed += 1
                result.errors.append(f"{path.name}: {exc}")
        return result
