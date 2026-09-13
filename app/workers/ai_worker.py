"""独立 AI 分析 Worker。"""
from __future__ import annotations
import logging, threading, uuid, json
from queue import Empty, Queue
from app.db.database import utc_now
from app.repositories.ai_analysis_task import AIAnalysisTaskRepository
from app.services.ai_analysis_queue import AIAnalysisQueueService
from app.services.llm.factory import create_provider
from app.services.cloud_sync import auto_sync_task

LOGGER = logging.getLogger(__name__)

class AIWorkerPool:
    def __init__(self, settings, database, event_hub=None, worker_count=None):
        self.settings, self.database, self.event_hub = settings, database, event_hub
        self.worker_count = max(1, int(worker_count or getattr(settings, 'ai_worker_count', 3)))
        self.stop_event = threading.Event(); self.threads=[]
        self.repo = AIAnalysisTaskRepository(database)
    def start(self):
        if self.threads: return
        self._recover_interrupted_tasks()
        for _ in range(self.worker_count):
            t=threading.Thread(target=self._run, args=(f"ai-{uuid.uuid4().hex[:8]}",), daemon=True); t.start(); self.threads.append(t)
        LOGGER.info("AIWorkerPool 已启动，Worker 数量: %d", self.worker_count)
    def stop(self):
        self.stop_event.set()
        for t in self.threads: t.join(timeout=3)
        self.threads=[]
    def notify_new_task(self): pass

    def _recover_interrupted_tasks(self):
        """Recover AI tasks left RUNNING after a process interruption."""
        now = utc_now()
        with self.database.connection() as conn:
            rows = conn.execute(
                "SELECT id, cancel_requested, pause_requested FROM ai_analysis_task WHERE status='RUNNING'"
            ).fetchall()
            for row in rows:
                if row['cancel_requested']:
                    status, message = 'CANCELED', '已取消'
                    conn.execute(
                        "UPDATE ai_analysis_task SET status=?, message=?, finished_at=?, worker_id=NULL, heartbeat_at=NULL, updated_at=? WHERE id=?",
                        (status, message, now, now, row['id']),
                    )
                elif row['pause_requested']:
                    status, message = 'PAUSED', '已暂停'
                    conn.execute(
                        "UPDATE ai_analysis_task SET status=?, message=?, worker_id=NULL, heartbeat_at=NULL, updated_at=? WHERE id=?",
                        (status, message, now, row['id']),
                    )
                else:
                    status, message = 'QUEUED', '服务中断，已重新排队'
                    conn.execute(
                        "UPDATE ai_analysis_task SET status=?, progress=0, message=?, worker_id=NULL, heartbeat_at=NULL, started_at=NULL, updated_at=? WHERE id=?",
                        (status, message, now, row['id']),
                    )
        for row in rows:
            if row['cancel_requested']:
                status, message = 'CANCELED', '已取消'
            elif row['pause_requested']:
                status, message = 'PAUSED', '已暂停'
            else:
                status, message = 'QUEUED', '服务中断，已重新排队'
            self._publish('ai.task.updated', int(row['id']), status, message)

    def _run(self, worker_id):
        while not self.stop_event.is_set():
            task_id=self.repo.claim_next(worker_id)
            if not task_id:
                self.stop_event.wait(getattr(self.settings,'ai_poll_interval_seconds',2)); continue
            self._publish('ai.task.updated', task_id, 'RUNNING', '开始分析', progress=1)
            try: self._process(task_id)
            except Exception as exc:
                state = self.database.fetch_one("SELECT status, cancel_requested, pause_requested FROM ai_analysis_task WHERE id=?", (task_id,))
                if not state or state['status'] in ('CANCELED', 'PAUSED') or state['cancel_requested'] or state['pause_requested']:
                    continue
                LOGGER.exception("AI 任务 #%s 失败", task_id)
                self.repo.update(task_id,status='FAILED',error_code='AI_REQUEST_FAILED',error_message='AI 分析失败',error_detail=str(exc),retryable=1,finished_at=utc_now(),message='分析失败')
                self._publish('ai.task.failed', task_id, 'FAILED', '分析失败')

    def _requested_state(self, task_id):
        state = self.database.fetch_one(
            "SELECT status, cancel_requested, pause_requested FROM ai_analysis_task WHERE id=?",
            (task_id,),
        )
        if not state or state['status'] == 'CANCELED' or state['cancel_requested']:
            return 'CANCELED'
        if state['status'] == 'PAUSED' or state['pause_requested']:
            return 'PAUSED'
        if state['status'] != 'RUNNING':
            return state['status']
        return None

    def _generate_interruptibly(self, task_id, provider, prompt, options):
        """Wait for the provider without blocking pause/cancel queue control."""
        result_queue = Queue(maxsize=1)

        def request():
            try:
                result_queue.put(('result', provider.generate(prompt, options)))
            except Exception as exc:
                result_queue.put(('error', exc))

        threading.Thread(
            target=request,
            name=f"ai-request-{task_id}",
            daemon=True,
        ).start()
        while not self.stop_event.is_set():
            try:
                kind, value = result_queue.get(timeout=0.25)
                if kind == 'error':
                    raise value
                return value
            except Empty:
                if self._requested_state(task_id):
                    cancel = getattr(provider, 'cancel', None)
                    if callable(cancel):
                        threading.Thread(target=cancel, name=f"ai-cancel-{task_id}", daemon=True).start()
                    return None
        return None
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
        prompt_parts = [
            '你是一名擅长分析中文知识类/商业类/个人成长类口播内容的内容分析师。',
            '请严格依据原文分析，不要补充原文没有的事实、数字、人物、地点、因果关系或建议。',
            '请只输出一个合法 JSON 对象，不要输出 JSON 之外的前言、解释或 Markdown 代码围栏。',
            'JSON 必须包含以下键，键名必须完全一致：' + ', '.join(f'{kind}（{labels[kind]}）' for kind in analysis_types) + '。',
            '每个键的值必须是中文字符串，可以使用换行和 Markdown 小标题。',
        ]
        if 'SUMMARY' in analysis_types:
            prompt_parts.append(
                '''SUMMARY（摘要）：输出一段简洁但有判断力的摘要。必须以“这段内容的核心，其实可以浓缩成一句话：”开头，下一行用 Markdown 引用（> **...**）给出一句完整的核心判断；随后用 1-2 段说明这句话如何由原文得出。保留关键事实、数字、时间、地点和案例，不要写空泛评价。'''
            )
        if 'CONCLUSION' in analysis_types:
            prompt_parts.append(
                '''CONCLUSION（总结）：请对下面这段口语化视频文稿进行深度总结。

要求：
1. 提取全文的核心主题和中心观点。
2. 不要简单按照原文顺序复述，而是重新梳理作者的逻辑结构。
3. 将作者提出的主要观点分层归纳，并提炼每个观点背后的核心逻辑。
4. 对文稿中的案例进行概括，只保留能够支撑核心观点的部分。
5. 删除口语化表达、重复内容、语气词、情绪化表达和无实际信息的内容。
6. 将零散观点整理成清晰的结构，例如：
   - 核心观点
   - 主要分论点
   - 案例/论据
   - 作者的判断标准
   - 最终结论
7. 尽可能保留作者原本的观点和立场，不要加入原文没有表达的观点。
8. 最后提炼出：
   - 一句话核心总结
   - 关键观点列表
   - 一套可以复用的逻辑框架
9. 使用中文，表达清晰、直接、易于阅读。
10. 对于口播稿中的明显错别字、语音转写错误，可以根据上下文进行合理修正，但不要改变原意。

输出要求：使用 Markdown 标题、段落、引用和列表组织内容；不要按原文流水账复述；不要输出 Markdown 代码围栏；不要补充原文没有的事实、案例、建议或结论。'''
            )
        prompt_parts.append('\n原文：\n' + text)
        prompt = '\n\n'.join(prompt_parts)
        self._set_progress(task_id, 25, '等待 AI 返回')
        result=self._generate_interruptibly(task_id, provider, prompt, {
            'temperature': 0.2,
            'system_prompt': (
                '你是严谨的中文知识类、商业类和个人成长类内容分析师。'
                '你必须忠实理解用户提供的转录原文，区分原文事实与作者观点，'
                '不得臆测、补充或弱化作者没有明确表达的内容。'
            ),
        })
        if result is None:
            return
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
        auto_sync_task(self.database, row['transcription_task_id'])
    def _set_progress(self, task_id, progress, message):
        """持久化并广播 AI 分析阶段进度。"""
        changed = self.database.execute(
            "UPDATE ai_analysis_task SET progress=?, message=?, heartbeat_at=?, updated_at=? "
            "WHERE id=? AND status='RUNNING' AND cancel_requested=0 AND pause_requested=0",
            (progress, message, utc_now(), utc_now(), task_id),
        )
        if not changed:
            raise RuntimeError('AI task is no longer running')
        self._publish('ai.task.updated', task_id, 'RUNNING', message, progress=progress)
    def _publish(self, typ, task_id, status, message, progress=0):
        if self.event_hub: self.event_hub.publish({'type':typ,'taskId':task_id,'status':status,'progress':progress,'message':message,'updatedAt':utc_now()})
