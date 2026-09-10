"""SQLite 连接、迁移和常用读写封装。"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def utc_now() -> str:
    """返回统一格式的 UTC 时间。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    """为每次操作创建短生命周期 SQLite 连接。"""

    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """打开启用外键和 WAL 的连接，并在异常时回滚。"""
        connection = sqlite3.connect(self.path, timeout=5, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def migrate(self) -> None:
        """执行内置的幂等初始迁移。"""
        schema = (Path(__file__).parent / "migrations" / "001_initial_schema.sql").read_text(encoding="utf-8")
        with self.connection() as connection:
            connection.executescript(schema)

    def fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        """查询多行数据。"""
        with self.connection() as connection:
            return list(connection.execute(sql, params).fetchall())

    def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        """查询一行数据。"""
        with self.connection() as connection:
            return connection.execute(sql, params).fetchone()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        """执行写入并返回自增主键或受影响行数。"""
        with self.connection() as connection:
            cursor = connection.execute(sql, params)
            return cursor.lastrowid or cursor.rowcount
