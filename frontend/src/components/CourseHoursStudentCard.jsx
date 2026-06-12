import { Trophy } from 'lucide-react';

const pctColor = (pct) => {
  if (pct >= 80) return 'var(--course-pct-good)';
  if (pct >= 60) return 'var(--course-pct-mid)';
  return 'var(--course-pct-low)';
};

const statusLabel = (aluno) => {
  if (!aluno?.vinculado) return 'Não vinculado';
  return aluno.ativo ? 'Ativo' : (aluno.decisao || 'Inativo');
};

export function CourseHoursStudentCard({ aluno, compact = false, onClick }) {
  const pct = Math.max(0, Math.min(100, Number(aluno?.percentualIntegralizacao || 0)));
  const color = pctColor(pct);
  const nome = aluno?.nome || aluno?.email || 'Aluno sem nome';
  const Tag = onClick ? 'button' : 'article';

  return (
    <Tag
      className={`${compact ? 'course-hours-card compact' : 'course-hours-card'}${onClick ? ' clickable' : ''}`}
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      aria-label={onClick ? `Abrir consumo de ${nome}` : undefined}
    >
      <div className="course-hours-card-main">
        <div className="course-hours-card-title">
          <strong>{nome}</strong>
          <span>{aluno?.email || 'E-mail não informado'}</span>
          <div className="course-hours-badges">
            <span className={aluno?.ativo ? 'course-pill success' : 'course-pill muted'}>
              {statusLabel(aluno)}
            </span>
            {aluno?.desafioFinal && <span className="course-pill final challenge-final-badge"><Trophy size={14} /> Desafio Final</span>}
            {!aluno?.vinculado && (
              <span className="course-pill warning">Não vinculado</span>
            )}
          </div>
        </div>

        <div className="course-hours-percent" style={{ color }}>
          <strong>{pct.toFixed(1)}%</strong>
          <span>consumo</span>
        </div>
      </div>

      {aluno?.alunoPd && (
        <div className="course-hours-link-info">
          <span>Matrícula: {aluno.alunoPd.matricula || 'não informada'}</span>
          <span>Monitor: {aluno.alunoPd.monitor || 'não informado'}</span>
        </div>
      )}

      <div className="course-progress-track" aria-label={`Consumo ${pct.toFixed(1)}%`}>
        <div className="course-progress-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </Tag>
  );
}
