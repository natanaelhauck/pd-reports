const fmtPct = (value) => {
  const numero = Number(value || 0);
  return `${Math.max(0, Math.min(100, numero)).toFixed(numero < 1 ? 2 : 1)}%`;
};

const statusKey = (status) => String(status || '')
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .toLowerCase();

function CourseStat({ label, value, tone }) {
  return (
    <div className={`course-stat ${tone || ''}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function CourseList({ title, courses, tone }) {
  const itens = courses || [];
  return (
    <div className={`course-list-box ${tone || ''}`}>
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
              <li key={`${course.courseId || course.curso}-${course.status || ''}`}>
                <div>
                  <strong>{course.curso || 'Curso sem nome'}</strong>
                  <span>{course.status || 'Não informado'}</span>
                </div>
                <span className={course.certificadoGerado ? 'course-cert-badge ok' : `course-cert-badge ${tone || ''}`}>
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

export function CourseCertificatesSection({ certificados, aluno }) {
  const dados = certificados || {};
  const cursos = dados.cursos || [];
  const concluidoPorDesafioFinal = Boolean(aluno?.desafioFinal);
  const certificadosGerados = Number(dados.certificadosGerados || 0);
  const totalCursos = Number(dados.totalCursosCertificaveis || 0) || cursos.length || (
    Number(dados.cursosConcluidos || 0)
    + Number(dados.cursosEmAndamento || 0)
    + Number(dados.cursosNaoIniciados || 0)
  );
  const certificadoPct = totalCursos > 0 ? Math.min(100, (certificadosGerados / totalCursos) * 100) : 0;
  const comCertificado = cursos.filter((curso) => curso.certificadoGerado);
  const semCertificado = cursos.filter((curso) => !curso.certificadoGerado);
  const semCertificadoTotal = Math.max(0, totalCursos - certificadosGerados);
  const emAndamentoSemCertificado = semCertificado;

  return (
    <section className="course-section certificates-section">
      <div className="course-section-head certificates-head">
        <div>
          <h3>Certificados e cursos</h3>
          <p>{concluidoPorDesafioFinal ? 'Conclusão reconhecida pelo Desafio Final.' : 'Progresso de certificados gerados nos cursos mapeados.'}</p>
        </div>
        <div className="certificate-score">
          <strong>{certificadosGerados}/{totalCursos}</strong>
          <span>certificados</span>
        </div>
      </div>

      <div className="course-progress-track large certificate-track">
        <div className="course-progress-fill" style={{ width: `${certificadoPct}%` }} />
      </div>

      <div className="course-stats-grid certificates-stats">
        <CourseStat label="Concluídos" value={dados.cursosConcluidos || 0} tone="done" />
        <CourseStat label="Em andamento" value={dados.cursosEmAndamento || 0} tone="progress" />
        <CourseStat label="Não iniciados" value={dados.cursosNaoIniciados || 0} tone="muted" />
        <CourseStat label="Sem certificado" value={semCertificadoTotal} tone="risk" />
      </div>

      <div className="course-lists-grid certificates-lists">
        <CourseList title="Com certificado" courses={comCertificado} tone="done" />
        {!concluidoPorDesafioFinal && (
          <CourseList title="Em andamento / sem certificado" courses={emAndamentoSemCertificado} tone="progress" />
        )}
      </div>
    </section>
  );
}
