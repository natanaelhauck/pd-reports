const pctColor = (pct) => {
  if (pct >= 80) return '#15803d';
  if (pct >= 50) return '#d97706';
  return '#dc2626';
};

const statusLabel = (aluno) => {
  if (!aluno?.vinculado) return 'Não vinculado';
  return aluno.ativo ? 'Ativo' : (aluno.decisao || 'Inativo');
};

export function CourseHoursStudentCard({ aluno, compact = false }) {
  const pct = Math.max(0, Math.min(100, Number(aluno?.percentualIntegralizacao || 0)));
  const color = pctColor(pct);
  const nome = aluno?.nome || aluno?.email || 'Aluno sem nome';

  return (
    <article className={compact ? 'course-hours-card compact' : 'course-hours-card'}>
      <div className="course-hours-card-head">
        <div className="course-hours-card-title">
          <strong>{nome}</strong>
          <span>{aluno?.email || 'E-mail não informado'}</span>
        </div>
        <div className="course-hours-percent" style={{ color }}>
          {pct.toFixed(1)}%
        </div>
      </div>

      <div className="course-hours-badges">
        <span className={aluno?.ativo ? 'course-pill success' : 'course-pill muted'}>
          {statusLabel(aluno)}
        </span>
        {aluno?.desafioFinal && <span className="course-pill final">Desafio Final</span>}
        {aluno?.vinculado ? (
          <span className="course-pill linked">PD Reports</span>
        ) : (
          <span className="course-pill warning">Não vinculado</span>
        )}
      </div>

      {aluno?.alunoPd && (
        <div className="course-hours-link-info">
          <span>Matrícula: {aluno.alunoPd.matricula || 'não informada'}</span>
          <span>Monitor: {aluno.alunoPd.monitor || 'não informado'}</span>
        </div>
      )}

      <div className="course-progress-track" aria-label={`Integralização ${pct.toFixed(1)}%`}>
        <div className="course-progress-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </article>
  );
}
