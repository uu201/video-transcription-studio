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
            self._publish('ai.task.updated', task_id, 'RUNNING', '开始分析', progress=1)
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
        self._set_progress(task_id, 5, '读取转录内容')
        text=self.database.fetch_one("SELECT clean_text FROM transcript WHERE id=?", (row['transcript_id'],))['clean_text']
        provider_cfg = (getattr(self.settings,'extra',{}) or {}).get('ai', {}).copy()
        saved = self.database.fetch_one("SELECT value_json FROM app_setting WHERE key='system_settings'")
        if saved:
            try:
                saved_config = json.loads(saved['value_json']).get('aiConfig') or {}
                provider_cfg.update({
                    'enabled': saved_config.get('enabled', provider_cfg.get('enabled', False)),
                    'base_url': saved_config.get('base_url', provider_cfg.get('base_url', '')),
                    'api_key': saved_config.get('api_key', provider_cfg.get('api_key', '')),
                    'model': saved_config.get('model_name', provider_cfg.get('model', '')),
                    'provider_type': saved_config.get('provider', provider_cfg.get('provider_type', 'openai-compatible')),
                    'timeout_seconds': saved_config.get('timeout_seconds', provider_cfg.get('timeout_seconds', 300)),
                })
            except (TypeError, ValueError, AttributeError):
                LOGGER.warning('AI 设置读取失败，将使用启动配置')
        if not provider_cfg.get('enabled') or not provider_cfg.get('base_url'):
            raise RuntimeError('AI Provider 尚未配置')
        provider_type = provider_cfg.get('provider_type', 'openai-compatible')
        if provider_type in ('openai', 'claude'):
            provider_type = 'openai-compatible'
        provider=create_provider(
            provider_type,
            base_url=provider_cfg['base_url'],
            api_key=provider_cfg.get('api_key',''),
            model=provider_cfg.get('model',''),
            timeout=provider_cfg.get('timeout_seconds', provider_cfg.get('timeout', 300)),
        )
        self._set_progress(task_id, 20, '准备分析请求')
        requested_types = json.loads(row['analysis_types_json'] or '["SUMMARY","CONCLUSION"]')
        analysis_types = AIAnalysisQueueService.normalize_types(requested_types) or ['SUMMARY', 'CONCLUSION']
        labels = {'SUMMARY': '摘要', 'CONCLUSION': '总结'}
        prompt = (
            '你是一名严谨的中文内容编辑。请严格依据“转录内容”进行整理，只能使用原文明确表达的信息，禁止补充原文没有的事实、数字、人物、地点、因果关系或建议。'
            '请只输出一个合法 JSON 对象，不要输出 Markdown 代码块、前言或其他文字。'
            'JSON 必须包含以下键，键名必须完全一致：'
            + ', '.join(f'{kind}（{labels[kind]}）' for kind in analysis_types)
            + '。每个键的值必须是中文纯文本字符串，可以使用换行和 Markdown 小标题。'
            + '\n对 SUMMARY（摘要）的要求：用 3-6 句话压缩说明主题、背景、关键事实、主要观点和结论；保留原文中的关键数字、时间、地点和案例，不要写空泛评价。'
            + '\n对 CONCLUSION（总结）的要求：对原文进行完整、忠实、结构化归纳，至少覆盖“讨论背景/案例事实、投入或问题、核心矛盾、作者的判断依据、行动原则或建议”（仅在原文提到时写）；可以分段或列点，但不要扩展成原文之外的鸡汤。'
            + '\n摘要必须短， 总结必须完整；二者不能互相替代。不要逐句复述口语，不要输出“根据这段文字”等套话。'
            + '\n\n转录内容：\n' + text
        )
        self._set_progress(task_id, 25, '等待 AI 返回')
        result=provider.generate(prompt, {'temperature': 0.2, 'max_tokens': 4096})
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
        try:
            raw_content = str(result['content']).strip()
            if raw_content.startswith('```'):
                raw_content = raw_content.split('\n', 1)[1] if '\n' in raw_content else raw_content
                if raw_content.rstrip().endswith('```'):
                    raw_content = raw_content.rstrip()[:-3].rstrip()
            parsed = json.loads(raw_content)
        except (TypeError, ValueError):
            parsed = {'SUMMARY': result['content'], 'CONCLUSION': result['content']}
        if isinstance(parsed, dict):
            parsed = {
                {'摘要': 'SUMMARY', '总结': 'CONCLUSION', '结论': 'CONCLUSION'}.get(str(key).strip().upper().split('（', 1)[0], str(key).strip().upper().split('（', 1)[0]): value
                for key, value in parsed.items()
            }
        self._set_progress(task_id, 85, '解析分析结果')
        self._set_progress(task_id, 95, '保存分析结果')
        with self.database.connection() as conn:
            result_id = None
            for kind in analysis_types:
                content = parsed.get(kind) or parsed.get(kind.lower())
                if not content: continue
                conn.execute("DELETE FROM ai_analysis WHERE task_id=? AND analysis_type=?", (row['transcription_task_id'], kind))
                cur=conn.execute("INSERT INTO ai_analysis(task_id,analysis_type,content,provider_name,model,status,created_at) VALUES(?,?,?,?,?,?,?)", (row['transcription_task_id'], kind, str(content), provider.name, result.get('model'), 'SUCCEEDED', now))
                result_id = result_id or cur.lastrowid
            conn.execute("UPDATE ai_analysis_task SET status='SUCCEEDED',progress=100,message='分析完成',result_id=?,finished_at=?,updated_at=? WHERE id=?", (result_id,now,now,task_id))
        self._publish('ai.task.completed',task_id,'SUCCEEDED','分析完成',progress=100)
    def _set_progress(self, task_id, progress, message):
        """持久化并广播 AI 分析阶段进度。"""
        self.repo.update(task_id, progress=progress, message=message)
        self._publish('ai.task.updated', task_id, 'RUNNING', message, progress=progress)
    def _publish(self, typ, task_id, status, message, progress=0):
        if self.event_hub: self.event_hub.publish({'type':typ,'taskId':task_id,'status':status,'progress':progress,'message':message,'updatedAt':utc_now()})
