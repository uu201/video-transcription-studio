"""云端转录同步配置与操作 API。"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import database
from app.db.database import Database
from app.services.cloud_sync import CloudSyncService

router = APIRouter(prefix="/api/cloud-sync", tags=["云端同步"])


def _as_bool(value: object, default: bool = False) -> bool:
    """兼容前端表单提交的布尔值字符串。"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@router.get("/config")
def get_config(db: Database = Depends(database)) -> dict:
    """返回当前云端同步配置。"""
    return CloudSyncService(db).config()


@router.put("/config")
def save_config(payload: dict, db: Database = Depends(database)) -> dict:
    """保存云端同步配置并保留其它系统设置。"""
    service = CloudSyncService(db)
    current = service.config()
    value = {
        "enabled": _as_bool(payload.get("enabled"), current["enabled"]),
        "autoSync": _as_bool(payload.get("autoSync"), current["autoSync"]),
        "baseUrl": str(payload.get("baseUrl", current["baseUrl"])).strip().rstrip("/"),
        "token": str(payload.get("token", current["token"])).strip(),
        "timeoutSeconds": max(3, min(int(payload.get("timeoutSeconds", current["timeoutSeconds"])), 300)),
        "retryCount": max(0, min(int(payload.get("retryCount", current["retryCount"])), 5)),
    }
    row = db.fetch_one("SELECT value_json FROM app_setting WHERE key='system_settings'")
    import json
    saved = json.loads(row["value_json"] or "{}") if row else {}
    saved["cloudSync"] = value
    db.execute("INSERT INTO app_setting(key,value_json,updated_at) VALUES('system_settings',?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at", (json.dumps(saved, ensure_ascii=False), __import__('app.db.database', fromlist=['utc_now']).utc_now()))
    return value


@router.post("/test")
def test_connection(db: Database = Depends(database)) -> dict:
    """测试云端同步接口连通性。"""
    return CloudSyncService(db).test()


@router.post("/tasks/{task_id}")
def sync_task(task_id: int, db: Database = Depends(database)) -> dict:
    """手动同步一个已完成任务。"""
    try:
        return CloudSyncService(db).sync_task(task_id, force=True)
    except RuntimeError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/tasks/{task_id}/history")
def sync_history(task_id: int, db: Database = Depends(database)) -> list[dict]:
    """返回任务的云端同步历史。"""
    return [dict(row) for row in db.fetch_all("SELECT * FROM file_transfer WHERE task_id=? AND operation='CLOUD_SYNC' ORDER BY id DESC", (task_id,))]
