"""云端转录单表同步服务。"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import httpx

from app.db.database import Database, utc_now

LOGGER = logging.getLogger(__name__)


def _as_bool(value: Any, default: bool = False) -> bool:
    """将 JSON、环境变量常见写法统一转换为布尔值。"""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _json_object(response: httpx.Response, operation: str) -> dict[str, Any]:
    """Parse a cloud response and turn empty/non-JSON bodies into useful errors."""
    try:
        body = response.json()
    except ValueError as exc:
        content_type = response.headers.get("content-type", "")
        detail = f"HTTP {response.status_code}"
        if content_type:
            detail += f"，Content-Type: {content_type.split(';', 1)[0]}"
        detail += "，响应为空" if not response.text.strip() else "，响应不是 JSON"
        raise RuntimeError(f"{operation}：{detail}，请检查云端地址和接口版本") from exc
    if not isinstance(body, dict):
        raise RuntimeError(f"{operation}：云端返回的数据格式不正确，请检查接口版本")
    return body


class CloudSyncService:
    """将本地转录和 AI 结果幂等上传到云端。"""

    def __init__(self, database: Database):
        """创建同步服务并绑定本地数据库。"""
        self.database = database

    def config(self) -> dict[str, Any]:
        """读取并规范化云端同步配置。"""
        row = self.database.fetch_one("SELECT value_json FROM app_setting WHERE key='system_settings'")
        saved: dict[str, Any] = {}
        if row:
            try:
                saved = json.loads(row["value_json"] or "{}")
            except (TypeError, ValueError):
                saved = {}
        value = saved.get("cloudSync") or {}
        return {
            "enabled": _as_bool(value.get("enabled")),
            "autoSync": _as_bool(value.get("autoSync")),
            "baseUrl": str(value.get("baseUrl", "")).strip().rstrip("/"),
            "token": str(value.get("token", "")).strip(),
            "timeoutSeconds": max(3, min(int(value.get("timeoutSeconds", 30) or 30), 300)),
            "retryCount": max(0, min(int(value.get("retryCount", 2) or 2), 5)),
        }

    def test(self) -> dict[str, Any]:
        """使用同步列表接口测试云端地址和秘钥。"""
        config = self.config()
        if not config["baseUrl"] or not config["token"]:
            return {"available": False, "message": "请填写云端地址和同步秘钥"}
        try:
            response = httpx.get(
                f'{config["baseUrl"]}/ops/transcriptions/sync/list',
                headers={"X-Archive-Token": config["token"]},
                params={"limit": 1},
                timeout=config["timeoutSeconds"],
                trust_env=False,
            )
            response.raise_for_status()
            body = _json_object(response, "云端响应无效")
            if body.get("code", 200) != 200:
                return {"available": False, "message": body.get("msg") or "云端鉴权失败"}
            return {"available": True, "message": "云端连接正常"}
        except (httpx.HTTPError, RuntimeError) as exc:
            return {"available": False, "message": f"云端连接失败：{exc}"}

    def sync_task(self, task_id: int, *, force: bool = False) -> dict[str, Any]:
        """组装任务、分段和 AI 结果，并幂等上传一条云端记录。"""
        config = self.config()
        if not config["enabled"] and not force:
            raise RuntimeError("云端同步未启用")
        if not config["baseUrl"] or not config["token"]:
            raise RuntimeError("请先配置云端地址和同步秘钥")

        row = self.database.fetch_one(
            """SELECT t.id, t.status, t.language, t.finished_at, m.file_name, m.path, m.extension,
                      m.modified_at, m.fingerprint, tr.id AS transcript_id, tr.raw_text,
                      tr.clean_text, tr.version, tr.updated_at AS transcribed_at
               FROM processing_task t JOIN media_file m ON m.id=t.media_file_id
               JOIN transcript tr ON tr.task_id=t.id WHERE t.id=?""", (task_id,)
        )
        if not row:
            raise RuntimeError("任务或转录结果不存在")
        if row["status"] != "SUCCEEDED":
            raise RuntimeError("仅支持同步已完成的转录任务")

        segments = self.database.fetch_all(
            "SELECT sequence,start_seconds,end_seconds,text,speaker,confidence FROM transcript_segment WHERE transcript_id=? ORDER BY sequence",
            (row["transcript_id"],),
        )
        analyses = self.database.fetch_all(
            "SELECT analysis_type,content FROM ai_analysis WHERE task_id=? AND status='SUCCEEDED' ORDER BY id",
            (task_id,),
        )
        ai_results = {str(item["analysis_type"]): item["content"] for item in analyses}
        source_slug = hashlib.sha256(f'{row["path"]}|{row["fingerprint"]}'.encode("utf-8")).hexdigest()
        payload = {
            "sourceSlug": source_slug,
            "localTaskId": task_id,
            "fileName": row["file_name"],
            "filePath": row["path"],
            "fileExtension": row["extension"],
            "language": row["language"],
            "rawText": row["raw_text"],
            "cleanText": row["clean_text"],
            "segments": [dict(item) for item in segments],
            "aiSummary": ai_results.get("SUMMARY"),
            "aiConclusion": ai_results.get("CONCLUSION"),
            "aiResults": ai_results,
            "transcriptVersion": row["version"],
            "sourceModifiedAt": row["modified_at"],
            "transcribedAt": row["transcribed_at"] or row["finished_at"],
            "syncHash": hashlib.sha256(json.dumps({"text": row["clean_text"], "analyses": ai_results}, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
        }
        url = f'{config["baseUrl"]}/ops/transcriptions/sync'
        attempts = config["retryCount"] + 1
        last_error: Exception | None = None
        for _ in range(attempts):
            try:
                response = httpx.post(url, json=payload, headers={"X-Archive-Token": config["token"]}, timeout=config["timeoutSeconds"], trust_env=False)
                response.raise_for_status()
                result = _json_object(response, "云端响应无效")
                if result.get("code", 200) != 200:
                    raise RuntimeError(result.get("msg") or "云端接口返回失败")
                remote_id = (result.get("data") or {}).get("id") or result.get("id")
                self._record(task_id, url, payload["syncHash"], "SUCCEEDED", str(remote_id or ""))
                return {"taskId": task_id, "remoteId": remote_id, "status": "SUCCEEDED", "syncHash": payload["syncHash"]}
            except (httpx.HTTPError, ValueError, RuntimeError) as exc:
                last_error = exc
        self._record(task_id, url, payload["syncHash"], "FAILED", str(last_error))
        raise RuntimeError(f"云端同步失败：{last_error}") from last_error

    def _record(self, task_id: int, target: str, source_hash: str, status: str, error: str = "") -> None:
        """将一次同步尝试写入本地文件转移历史。"""
        now = utc_now()
        self.database.execute(
            "INSERT INTO file_transfer(task_id,operation,source_path,target_path,source_hash,status,error_message,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (task_id, "CLOUD_SYNC", str(task_id), target, source_hash, status, error if status == "FAILED" else None, now, now),
        )


def auto_sync_task(database: Database, task_id: int) -> None:
    """自动同步失败只记录日志，不影响本地任务状态。"""
    service = CloudSyncService(database)
    if not service.config()["autoSync"]:
        return
    try:
        service.sync_task(task_id)
    except Exception:
        LOGGER.exception("任务 #%s 自动同步云端失败", task_id)
