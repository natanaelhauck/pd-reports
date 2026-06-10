CREATE TABLE IF NOT EXISTS course_consumption_runs (
    id SERIAL PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'success', 'error')),
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    triggered_by_user_id INTEGER,
    error_message TEXT,
    source_files_info JSONB DEFAULT '{}'::jsonb,
    warnings JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course_catalog (
    course_id TEXT PRIMARY KEY,
    course_name TEXT NOT NULL,
    certificavel BOOLEAN DEFAULT TRUE,
    ignored BOOLEAN DEFAULT FALSE,
    ordem INTEGER
);

CREATE TABLE IF NOT EXISTS course_consumption_students (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES course_consumption_runs(id) ON DELETE CASCADE,
    student_email TEXT NOT NULL,
    student_name TEXT,
    matricula_pd TEXT,
    cidade TEXT,
    linked_student_id INTEGER,
    consumo_percentual NUMERIC(6,2) DEFAULT 0,
    certificados_gerados INTEGER DEFAULT 0,
    cursos_concluidos INTEGER DEFAULT 0,
    cursos_em_andamento INTEGER DEFAULT 0,
    cursos_nao_iniciados INTEGER DEFAULT 0,
    cursos_sem_certificado INTEGER DEFAULT 0,
    desafio_final BOOLEAN DEFAULT FALSE,
    ingresso DATE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course_consumption_courses (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES course_consumption_runs(id) ON DELETE CASCADE,
    student_email TEXT NOT NULL,
    course_id TEXT,
    course_name TEXT NOT NULL,
    status TEXT,
    percentual NUMERIC(6,2) DEFAULT 0,
    certificado_gerado BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consumption_runs_status_finished_at
    ON course_consumption_runs(status, finished_at DESC);

CREATE INDEX IF NOT EXISTS idx_consumption_students_run_email
    ON course_consumption_students(run_id, student_email);

CREATE INDEX IF NOT EXISTS idx_consumption_students_run_linked
    ON course_consumption_students(run_id, linked_student_id);

CREATE INDEX IF NOT EXISTS idx_consumption_students_run_matricula
    ON course_consumption_students(run_id, matricula_pd);

CREATE INDEX IF NOT EXISTS idx_consumption_courses_run_email
    ON course_consumption_courses(run_id, student_email);

CREATE INDEX IF NOT EXISTS idx_consumption_courses_run_course
    ON course_consumption_courses(run_id, course_id);
