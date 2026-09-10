"""文件复制/移动与哈希校验服务。"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from app.domain.schemas import AppError


class FileTransferService:
    """执行归档策略，只有校验目标后才删除源文件。"""

    @staticmethod
    def sha256(path: Path) -> str:
        """计算文件 SHA-256。"""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def execute(self, source: Path, target: Path, operation: str) -> str:
        """复制或移动文件，并返回目标哈希。"""
        if operation not in {"copy", "move"}:
            return self.sha256(source)
        if not source.is_file():
            raise AppError("TRANSFER_SOURCE_MISSING", "归档源文件不存在", str(source), True, "确认源目录未被外部程序移动")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise AppError("TRANSFER_CONFLICT", "归档目标文件已存在", str(target), False, "修改冲突策略或清理目标文件")
        source_hash = self.sha256(source)
        shutil.copy2(source, target)
        target_hash = self.sha256(target)
        if source_hash != target_hash:
            target.unlink(missing_ok=True)
            raise AppError("TRANSFER_VERIFY_FAILED", "归档校验失败", str(target), True, "检查磁盘空间后重试")
        if operation == "move":
            source.unlink()
        return target_hash
