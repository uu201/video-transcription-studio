-- 性能优化索引迁移
-- 添加日期: 2025-01-XX
-- 目的: 优化常用查询的性能

-- 1. 任务心跳和状态查询优化（Worker 轮询使用）
CREATE INDEX IF NOT EXISTS idx_task_heartbeat ON processing_task(status, heartbeat_at);

-- 2. 任务状态和更新时间（任务列表查询）
CREATE INDEX IF NOT EXISTS idx_task_status_updated ON processing_task(status, updated_at DESC);

-- 3. 媒体文件按扫描源查询（扫描源管理页面）
CREATE INDEX IF NOT EXISTS idx_media_source_status ON media_file(scan_source_id, status);

-- 4. 媒体文件路径查询（去重检查）
CREATE INDEX IF NOT EXISTS idx_media_path ON media_file(scan_source_id, path);

-- 5. 任务事件按时间排序（任务详情页面）
CREATE INDEX IF NOT EXISTS idx_event_task_time ON task_event(task_id, created_at DESC);

-- 6. 转写记录查询优化
CREATE INDEX IF NOT EXISTS idx_transcript_task ON transcript(task_id);

-- 7. 转写分段查询优化
CREATE INDEX IF NOT EXISTS idx_segment_transcript ON transcript_segment(transcript_id, sequence);

-- 8. 任务取消标记查询（Worker 检查）
CREATE INDEX IF NOT EXISTS idx_task_cancel ON processing_task(cancel_requested) WHERE cancel_requested = 1;

-- 9. Worker ID 查询（多 Worker 场景）
CREATE INDEX IF NOT EXISTS idx_task_worker ON processing_task(worker_id, status);

-- 10. 导出记录按任务查询
CREATE INDEX IF NOT EXISTS idx_export_task ON export_record(task_id, created_at DESC);
