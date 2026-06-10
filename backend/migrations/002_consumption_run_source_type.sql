ALTER TABLE course_consumption_runs
ADD COLUMN IF NOT EXISTS source_type TEXT;

UPDATE course_consumption_runs
SET source_type = COALESCE(source_type, 'checker_report_xlsx')
WHERE source_type IS NULL;
