ALTER TABLE ai_analysis_task ADD COLUMN analysis_types_json TEXT NOT NULL DEFAULT '["SUMMARY","CONCLUSION"]';
