CREATE TABLE IF NOT EXISTS ai_analysis_task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transcript_id INTEGER NOT NULL REFERENCES transcript(id) ON DELETE CASCADE,
    processing_task_id INTEGER REFERENCES processing_task(id) ON DELETE SET NULL,
    analysis_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'QUEUED',
    progress INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL DEFAULT '等待分析',
    provider_name TEXT,
    model TEXT,
    prompt_version INTEGER,
    result_id INTEGER,
    error_code TEXT,
    error_message TEXT,
    error_detail TEXT,
    retryable INTEGER NOT NULL DEFAULT 0,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    pause_requested INTEGER NOT NULL DEFAULT 0,
    worker_id TEXT,
    heartbeat_at TEXT,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ai_task_status ON ai_analysis_task(status, created_at);
CREATE INDEX IF NOT EXISTS idx_ai_task_transcript ON ai_analysis_task(transcript_id, analysis_type);
CREATE INDEX IF NOT EXISTS idx_ai_task_heartbeat ON ai_analysis_task(status, heartbeat_at);
