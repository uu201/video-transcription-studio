"""独立 AI 分析 Worker。"""
from __future__ import annotations
import logging, threading, uuid, json
from app.db.database import utc_now
from app.repositories.ai_analysis_task import AIAnalysisTaskRepository
from app.services.ai_analysis_queue import AIAnalysisQueueService
from app.services.llm.factory import create_provider

LOGGER = logging.getLogger(__name__)

class AIWorkerPool:
    def __init__(self, settings, database, event_hub=None, worker_count=1):
        self.settings, self.database, self.event_hub = settings, database, event_hub
        self.worker_count = worker_count or 1; self.stop_event = threading.Event(); self.threads=[]
        self.repo = AIAnalysisTaskRepository(database)
    def start(self):
        if self.threads: return
        for _ in range(self.worker_count):
            t=threading.Thread(target=self._run, args=(f"ai-{uuid.uuid4().hex[:8]}",), daemon=True); t.start(); self.threads.append(t)
    def stop(self):
        self.stop_event.set()
        for t in self.threads: t.join(timeout=3)
        self.threads=[]
    def notify_new_task(self): pass
    def _run(self, worker_id):
        while not self.stop_event.is_set():
            task_id=self.repo.claim_next(worker_id)
            if not task_id:
                self.stop_event.wait(getattr(self.settings,'ai_poll_interval_seconds',2)); continue
            try: self._process(task_id)
            except Exception as exc:
                LOGGER.exception("AI 任务 #%s 失败", task_id)
                self.repo.update(task_id,status='FAILED',error_code='AI_REQUEST_FAILED',error_message='AI 分析失败',error_detail=str(exc),retryable=1,finished_at=utc_now(),message='分析失败')
                self._publish('ai.task.failed', task_id, 'FAILED', '分析失败')
    def _process(self, task_id):
        row=self.repo.get(task_id)
        if not row: return
        state = self.database.fetch_one("SELECT status, cancel_requested, pause_requested FROM ai_analysis_task WHERE id=?", (task_id,))
        if not state or state['cancel_requested']:
            self.repo.update(task_id,status='CANCELED',message='已取消',finished_at=utc_now())
            self._publish('ai.task.updated', task_id, 'CANCELED', '已取消')
            return
        if state['pause_requested']:
            self.repo.update(task_id,status='PAUSED',message='已暂停')
            self._publish('ai.task.updated', task_id, 'PAUSED', '已暂停')
            return
        text=self.database.fetch_one("SELECT clean_text FROM transcript WHERE id=?", (row['transcript_id'],))['clean_text']
        provider_cfg = (getattr(self.settings,'extra',{}) or {}).get('ai', {})
        if not provider_cfg.get('enabled') or not provider_cfg.get('base_url'):
            raise RuntimeError('AI Provider 尚未配置')
        provider=create_provider(provider_cfg.get('provider_type','openai-compatible'), base_url=provider_cfg['base_url'], api_key=provider_cfg.get('api_key',''), model=provider_cfg.get('model',''))
        prompt=AIAnalysisQueueService.TYPES.get(row['analysis_type'], '') + "\n" + text
        result=provider.generate(prompt,{})
        state = self.database.fetch_one("SELECT cancel_requested, pause_requested FROM ai_analysis_task WHERE id=?", (task_id,))
        if state and state['cancel_requested']:
            self.repo.update(task_id,status='CANCELED',message='已取消',finished_at=utc_now())
            self._publish('ai.task.updated', task_id, 'CANCELED', '已取消')
            return
        if state and state['pause_requested']:
            self.repo.update(task_id,status='PAUSED',message='已暂停')
            self._publish('ai.task.updated', task_id, 'PAUSED', '已暂停')
            return
        now=utc_now()
        with self.database.connection() as conn:
            cur=conn.execute("INSERT INTO ai_analysis(task_id,analysis_type,content,provider_name,model,status,created_at) VALUES(?,?,?,?,?,?,?)", (row['transcription_task_id'], row['analysis_type'], result['content'], provider.name, result.get('model'), 'SUCCEEDED', now))
            conn.execute("UPDATE ai_analysis_task SET status='SUCCEEDED',progress=100,message='分析完成',result_id=?,finished_at=?,updated_at=? WHERE id=?", (cur.lastrowid,now,now,task_id))
        self._publish('ai.task.completed',task_id,'SUCCEEDED','分析完成',progress=100)
    def _publish(self, typ, task_id, status, message, progress=0):
        if self.event_hub: self.event_hub.publish({'type':typ,'taskId':task_id,'status':status,'progress':progress,'message':message,'updatedAt':utc_now()})
