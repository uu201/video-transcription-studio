PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS scan_source (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    root_path TEXT NOT NULL UNIQUE,
    recursive INTEGER NOT NULL DEFAULT 1,
    stable_wait_seconds INTEGER NOT NULL DEFAULT 3,
    auto_scan INTEGER NOT NULL DEFAULT 0,
    result_dir TEXT,
    transfer_policy TEXT NOT NULL DEFAULT 'keep',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS media_file (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_source_id INTEGER NOT NULL REFERENCES scan_source(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    extension TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    modified_at TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'DISCOVERED',
    media_info_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(scan_source_id, path, fingerprint)
);

CREATE TABLE IF NOT EXISTS processing_task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_file_id INTEGER NOT NULL REFERENCES media_file(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'QUEUED',
    current_stage TEXT NOT NULL DEFAULT 'QUEUED',
    progress INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL DEFAULT '等待处理',
    requested_ai INTEGER NOT NULL DEFAULT 0,
    language TEXT NOT NULL DEFAULT 'auto',
    asr_options_json TEXT,
    error_code TEXT,
    error_message TEXT,
    error_detail TEXT,
    retryable INTEGER NOT NULL DEFAULT 0,
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    worker_id TEXT,
    heartbeat_at TEXT,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_event (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES processing_task(id) ON DELETE CASCADE,
    stage TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'INFO',
    message TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transcript (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL UNIQUE REFERENCES processing_task(id) ON DELETE CASCADE,
    language TEXT,
    raw_text TEXT NOT NULL DEFAULT '',
    clean_text TEXT NOT NULL DEFAULT '',
    raw_json TEXT NOT NULL DEFAULT '[]',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transcript_segment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transcript_id INTEGER NOT NULL REFERENCES transcript(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    start_seconds REAL NOT NULL,
    end_seconds REAL NOT NULL,
    text TEXT NOT NULL,
    speaker TEXT,
    confidence REAL
);

CREATE TABLE IF NOT EXISTS export_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES processing_task(id) ON DELETE CASCADE,
    export_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_provider (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    provider_type TEXT NOT NULL,
    base_url TEXT,
    api_key_ref TEXT,
    model TEXT,
    enabled INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_template (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    template TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES processing_task(id) ON DELETE CASCADE,
    analysis_type TEXT NOT NULL,
    content TEXT NOT NULL,
    provider_name TEXT,
    model TEXT,
    prompt_version INTEGER,
    status TEXT NOT NULL DEFAULT 'SUCCEEDED',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS file_transfer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES processing_task(id) ON DELETE CASCADE,
    operation TEXT NOT NULL,
    source_path TEXT NOT NULL,
    target_path TEXT NOT NULL,
    source_hash TEXT,
    target_hash TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    error_message TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_task_status ON processing_task(status, created_at);
CREATE INDEX IF NOT EXISTS idx_event_task ON task_event(task_id, created_at);
CREATE INDEX IF NOT EXISTS idx_media_fingerprint ON media_file(fingerprint);
