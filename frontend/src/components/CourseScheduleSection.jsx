const plural = (valor, singular, pluralizado) => `${valor} ${valor === 1 ? singular : pluralizado}`;

const formatDurationLongFromMinutes = (minutos) => {
  const numero = Number(minutos || 0);
  const totalMin = Number.isFinite(numero) ? Math.max(0, Math.round(numero)) : 0;
  const hh = Math.floor(totalMin / 60);
  const mm = totalMin % 60;
  const partes = [];
  if (hh > 0) partes.push(plural(hh, 'hora', 'horas'));
  if (mm > 0) partes.push(plural(mm, 'minuto', 'minutos'));
  return partes.length ? partes.join(' e ') : '0 minutos';
};

const formatDurationLong = (horas) => {
  const numero = Number(horas || 0);
  const totalMin = Number.isFinite(numero) ? Math.max(0, Math.round(numero * 60)) : 0;
  return formatDurationLongFromMinutes(totalMin);
};

const formatDurationCompactFromMinutes = (minutos) => {
  const numero = Number(minutos || 0);
  const totalMin = Number.isFinite(numero) ? Math.max(0, Math.round(numero)) : 0;
  const hh = Math.floor(totalMin / 60);
  const mm = totalMin % 60;
  const partes = [];
  if (hh > 0) partes.push(plural(hh, 'hora', 'horas'));
  if (mm > 0 || partes.length === 0) partes.push(`${mm} min`);
  return partes.join(' e ');
};

const formatDurationCompact = (horas) => {
  const numero = Number(horas || 0);
  const totalMin = Number.isFinite(numero) ? Math.max(0, Math.round(numero * 60)) : 0;
  return formatDurationCompactFromMinutes(totalMin);
};

const DIAS = [
  ['segunda', 'Segunda'],
  ['terca', 'Terça'],
  ['quarta', 'Quarta'],
  ['quinta', 'Quinta'],
  ['sexta', 'Sexta'],
];

export function CourseScheduleSection({ aluno }) {
  const meta = aluno?.metaDiaria || {};
  const concluido = aluno?.alunoConcluido || aluno?.desafioFinal;

  if (!meta.aplicavel) {
    return (
      <section className={concluido ? 'course-section course-complete' : 'course-section'}>
        <div className="course-section-head schedule-head">
          <div>
            <h3>{concluido ? 'Consumo concluído' : 'Meta diária'}</h3>
            <p>
              {aluno?.desafioFinal
                ? 'Aluno concluiu o curso pelo Desafio Final. A meta diária não se aplica.'
                : (meta.mensagem || 'Não há meta diária disponível para este aluno.')}
            </p>
          </div>
          {concluido && <strong>100%</strong>}
        </div>
      </section>
    );
  }

  return (
    <section className="course-section schedule-section">
      <div className="course-section-head schedule-head">
        <div>
          <h3 className="course-section-kicker">META DIÁRIA - HORAS DO CURSO</h3>
          <p>
            Faltam {formatDurationLong(meta.horasRestantesCurso)} até {meta.prazoFinalFormatado}.
            Ritmo mínimo de {formatDurationLongFromMinutes(meta.minMinutosPorDia)} por dia útil.
          </p>
        </div>
        <div className="daily-goal-score">
          <strong>{formatDurationCompact(meta.horasPorDia)}</strong>
          <span>por dia útil</span>
        </div>
      </div>

      <div className="course-stats-grid schedule-stats">
        <div className="course-stat progress">
          <span>Dias úteis restantes</span>
          <strong>{meta.diasUteisRestantes}</strong>
        </div>
        <div className="course-stat done">
          <span>Previsão de conclusão</span>
          <strong>{meta.dataPrevistaConclusaoFormatada || '-'}</strong>
        </div>
        <div className="course-stat muted">
          <span>Prazo final</span>
          <strong>{meta.prazoFinalFormatado || '-'}</strong>
        </div>
      </div>

      <div className="course-week-grid">
        {DIAS.map(([key, label]) => (
          <div key={key}>
            <span>{label}</span>
            <strong>{formatDurationCompact(meta.semana?.[key])}</strong>
            <em>de curso</em>
          </div>
        ))}
      </div>
      <p className="course-week-note">
        Sábados e domingos ficam livres — o avanço é distribuído igualmente pelos dias úteis.
      </p>
    </section>
  );
}
