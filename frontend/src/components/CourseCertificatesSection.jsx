const fmtPct = (value) => {
  const numero = Number(value || 0);
  return `${Math.max(0, Math.min(100, numero)).toFixed(numero < 1 ? 2 : 1)}%`;
};

function CourseStat({ label, value, tone }) {
  return (
    <div className={`course-stat ${tone || ''}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function CourseList({ title, courses }) {
  const itens = courses || [];
  return (
    <div className="course-list-box">
      <div className="course-list-title">
        <strong>{title}</strong>
        <span>{itens.length}</span>
      </div>
      {itens.length === 0 ? (
        <p className="course-empty-text">Nenhum curso nesta categoria.</p>
      ) : (
        <ul>
          {itens.map((course) => {
            const pct = Math.max(0, Math.min(100, Number(course.percentual || 0)));
            return (
              <li key={course.courseId || course.curso}>
                <div>
                  <strong>{course.curso || 'Curso sem nome'}</strong>
                  <span>{course.status || 'Não informado'}</span>
                </div>
                <span className={course.certificadoGerado ? 'course-cert-badge ok' : 'course-cert-badge'}>
                  {course.certificadoGerado ? 'Certificado' : fmtPct(pct)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function CourseCertificatesSection({ certificados }) {
  const dados = certificados || {};
  const grupos = dados.grupos || {};
  const totalCursos = Number(dados.cursosConcluidos || 0)
    + Number(dados.cursosEmAndamento || 0)
    + Number(dados.cursosNaoIniciados || 0);
  const certificadosGerados = Number(dados.certificadosGerados || 0);
  const certificadoPct = totalCursos > 0 ? Math.min(100, (certificadosGerados / totalCursos) * 100) : 0;

  return (
    <section className="course-section">
      <div className="course-section-head">
        <div>
          <h3>Certificados e cursos</h3>
          <p>{certificadosGerados} certificados gerados de {totalCursos} cursos mapeados.</p>
        </div>
        <strong>{fmtPct(certificadoPct)}</strong>
      </div>

      <div className="course-progress-track large">
        <div className="course-progress-fill" style={{ width: `${certificadoPct}%` }} />
      </div>

      <div className="course-stats-grid">
        <CourseStat label="Concluídos" value={dados.cursosConcluidos || 0} tone="done" />
        <CourseStat label="Em andamento" value={dados.cursosEmAndamento || 0} tone="progress" />
        <CourseStat label="Não iniciados" value={dados.cursosNaoIniciados || 0} tone="muted" />
        <CourseStat label="Sem certificado" value={Math.max(0, totalCursos - certificadosGerados)} tone="risk" />
      </div>

      <div className="course-lists-grid">
        <CourseList title="Concluídos" courses={grupos.concluidos} />
        <CourseList title="Em andamento" courses={grupos.emAndamento} />
        <CourseList title="Não iniciados" courses={grupos.naoIniciados} />
        <CourseList title="Com certificado" courses={grupos.comCertificado} />
        <CourseList title="Sem certificado" courses={grupos.semCertificado} />
      </div>
    </section>
  );
}
