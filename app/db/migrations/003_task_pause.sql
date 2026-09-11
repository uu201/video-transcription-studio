-- 支持任务暂停与恢复
ALTER TABLE processing_task ADD COLUMN pause_requested INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_task_pause ON processing_task(status, pause_requested);
