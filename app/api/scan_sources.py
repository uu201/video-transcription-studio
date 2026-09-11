"""扫描源 API。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.api.dependencies import database, scanner
from app.db.database import Database, utc_now
from app.services.scanner import Scanner

router = APIRouter(prefix="/api/scan-sources", tags=["扫描源"])


class ScanSourceInput(BaseModel):
    """扫描源表单参数。"""

    name: str = Field(min_length=1, max_length=120)
    rootPath: str
    recursive: bool = True
    stableWaitSeconds: int = Field(default=3, ge=0, le=3600)
    autoScan: bool = False
    resultDir: str | None = None
    transferPolicy: str = "keep"


def _item(row) -> dict:
    """将数据库行转换为前端 camelCase。"""
    return {"id": row["id"], "name": row["name"], "rootPath": row["root_path"], "recursive": bool(row["recursive"]), "stableWaitSeconds": row["stable_wait_seconds"], "autoScan": bool(row["auto_scan"]), "resultDir": row["result_dir"], "transferPolicy": row["transfer_policy"], "createdAt": row["created_at"], "updatedAt": row["updated_at"]}


@router.get("")
def list_sources(response: Response, db: Database = Depends(database)) -> list[dict]:
    """列出全部扫描源。"""
    response.headers["Cache-Control"] = "public, max-age=30"
    return [_item(row) for row in db.fetch_all("SELECT * FROM scan_source ORDER BY id DESC")]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_source(payload: ScanSourceInput, db: Database = Depends(database)) -> dict:
    """保存一个扫描目录。"""
    root = Path(payload.rootPath).expanduser().resolve()
    if not root.is_dir():
        raise HTTPException(400, "输入目录不存在或不可读")
    now = utc_now()
    try:
        source_id = db.execute("INSERT INTO scan_source (name, root_path, recursive, stable_wait_seconds, auto_scan, result_dir, transfer_policy, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (payload.name, str(root), int(payload.recursive), payload.stableWaitSeconds, int(payload.autoScan), payload.resultDir, payload.transferPolicy, now, now))
    except Exception as exc:
        raise HTTPException(409, "该输入目录已经配置") from exc
    row = db.fetch_one("SELECT * FROM scan_source WHERE id = ?", (source_id,))
    return _item(row)


@router.put("/{source_id}")
def update_source(source_id: int, payload: ScanSourceInput, db: Database = Depends(database)) -> dict:
    """更新扫描源设置。"""
    root = Path(payload.rootPath).expanduser().resolve()
    if not root.is_dir():
        raise HTTPException(400, "输入目录不存在或不可读")
    now = utc_now()
    changed = db.execute("UPDATE scan_source SET name=?, root_path=?, recursive=?, stable_wait_seconds=?, auto_scan=?, result_dir=?, transfer_policy=?, updated_at=? WHERE id=?", (payload.name, str(root), int(payload.recursive), payload.stableWaitSeconds, int(payload.autoScan), payload.resultDir, payload.transferPolicy, now, source_id))
    if changed == 0:
        raise HTTPException(404, "扫描源不存在")
    return _item(db.fetch_one("SELECT * FROM scan_source WHERE id = ?", (source_id,)))


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_source(source_id: int, db: Database = Depends(database)) -> None:
    """删除扫描源及其媒体记录。"""
    if db.execute("DELETE FROM scan_source WHERE id = ?", (source_id,)) == 0:
        raise HTTPException(404, "扫描源不存在")


@router.post("/{source_id}/validate")
def validate_source(source_id: int, db: Database = Depends(database)) -> dict:
    """验证扫描目录。"""
    row = db.fetch_one("SELECT root_path FROM scan_source WHERE id = ?", (source_id,))
    if not row:
        raise HTTPException(404, "扫描源不存在")
    root = Path(row["root_path"])
    return {"valid": root.is_dir(), "path": str(root), "readable": root.is_dir() and root.exists()}


@router.post("/{source_id}/scan")
def scan_source(source_id: int, db: Database = Depends(database), scan_service: Scanner = Depends(scanner)) -> dict:
    """扫描目录并返回可供用户勾选的媒体文件。"""
    if not db.fetch_one("SELECT id FROM scan_source WHERE id = ?", (source_id,)):
        raise HTTPException(404, "扫描源不存在")

    # 执行扫描
    result = scan_service.scan(source_id)

    # 获取该扫描源的所有媒体文件（包括已处理的）
    sql = """
        SELECT m.id, m.file_name, m.path, m.extension, m.size_bytes, m.modified_at,
               (SELECT COUNT(*) FROM processing_task t WHERE t.media_file_id = m.id) AS task_count,
               (SELECT t.status FROM processing_task t WHERE t.media_file_id = m.id ORDER BY t.id DESC LIMIT 1) AS latest_status
        FROM media_file m
        WHERE m.scan_source_id = ?
        ORDER BY m.updated_at DESC, m.id DESC
    """
    rows = db.fetch_all(sql, (source_id,))

    # 格式化文件信息
    files = []
    for row in rows:
        # 格式化文件大小
        size_bytes = row["size_bytes"]
        if size_bytes < 1024:
            size_display = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_display = f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            size_display = f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            size_display = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

        # 判断文件是否可选（未处理或处理失败的可以重新处理）
        task_count = row["task_count"] or 0
        latest_status = row["latest_status"]
        is_new = row["id"] in result.media_ids
        can_select = is_new or latest_status in (None, 'failed', 'cancelled')

        files.append({
            "id": row["id"],
            "file_name": row["file_name"],
            "path": row["path"],
            "extension": row["extension"],
            "size_bytes": size_bytes,
            "size_display": size_display,
            "modified_at": row["modified_at"],
            "task_count": task_count,
            "latest_status": latest_status,
            "is_new": is_new,
            "can_select": can_select
        })

    return {
        "discovered": result.discovered,
        "created": result.created,
        "skipped": result.skipped,
        "failed": result.failed,
        "errors": result.errors,
        "newMediaIds": result.media_ids,
        "files": files
    }


@router.get("/{source_id}/media")
def list_source_media(source_id: int, available_only: bool = True, db: Database = Depends(database)) -> list[dict]:
    """列出扫描源媒体，默认只返回尚未创建任务的文件。"""
    if not db.fetch_one("SELECT id FROM scan_source WHERE id = ?", (source_id,)):
        raise HTTPException(404, "扫描源不存在")
    sql = """
        SELECT m.*,
               (SELECT COUNT(*) FROM processing_task t WHERE t.media_file_id = m.id) AS task_count,
               (SELECT t.status FROM processing_task t WHERE t.media_file_id = m.id ORDER BY t.id DESC LIMIT 1) AS latest_task_status
        FROM media_file m
        WHERE m.scan_source_id = ?
    """
    if available_only:
        sql += " AND NOT EXISTS (SELECT 1 FROM processing_task t WHERE t.media_file_id = m.id)"
    sql += " ORDER BY m.updated_at DESC, m.id DESC"
    rows = db.fetch_all(sql, (source_id,))
    return [
        {
            "id": row["id"],
            "fileName": row["file_name"],
            "path": row["path"],
            "extension": row["extension"],
            "sizeBytes": row["size_bytes"],
            "modifiedAt": row["modified_at"],
            "status": row["status"],
            "taskCount": row["task_count"],
            "latestTaskStatus": row["latest_task_status"],
        }
        for row in rows
    ]
