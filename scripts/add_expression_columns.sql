-- 添加表情分析相关列（若已存在会报错，可忽略）
-- 请在 MySQL 中执行此脚本

-- evaluations 表：每道题的表情分析结果
ALTER TABLE evaluations ADD COLUMN expression_analysis_json JSON NULL;

-- 若 JSON 类型不支持，可改用：
-- ALTER TABLE evaluations ADD COLUMN expression_analysis_json TEXT NULL;

-- interview_sessions 表：整场面试的实时表情历史
ALTER TABLE interview_sessions ADD COLUMN expression_history_json JSON NULL;

-- 若 JSON 类型不支持，可改用：
-- ALTER TABLE interview_sessions ADD COLUMN expression_history_json TEXT NULL;
