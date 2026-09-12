CREATE TABLE IF NOT EXISTS app_setting (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
