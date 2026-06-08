import { useEffect, useState } from 'react';
import axios from 'axios';
import { CourseCertificatesSection } from './CourseCertificatesSection.jsx';
import { CourseScheduleSection } from './CourseScheduleSection.jsx';

const pctColor = (pct) => {
  if (pct >= 80) return '#15803d';
  if (pct >= 50) return '#d97706';
  return '#dc2626';
};

const alunoNome = (aluno) => aluno?.nome || aluno?.alunoPd?.nome || aluno?.email || 'Aluno sem nome';
const alunoEmail = (aluno) => aluno?.email || aluno?.alunoPd?.email || 'E-mail não informado';
const entradaCurso = (aluno) => aluno?.dataEntradaCursoFormatada || aluno?.dataIngresso || 'Não informada';

function ConsumptionHeader({ aluno }) {
  const pct = Math.max(0, Math.min(100, Number(aluno?.percentualIntegralizacao || 0)));
  const color = pctColor(pct);

  return (
    <section className="consumption-hero">
      <div className="consumption-hero-main">
        <div>
          <h2>{alunoNome(aluno)}</h2>
          <p>{alunoEmail(aluno)}</p>
        </div>
        <div className="course-hours-badges">
          <span className={aluno?.ativo ? 'course-pill success' : 'course-pill muted'}>
            {aluno?.ativo ? 'Ativo' : (aluno?.decisao || 'Inativo')}
          </span>
          {aluno?.desafioFinal && <span className="course-pill final">Desafio Final</span>}
          {aluno?.vinculado ? (
            <span className="course-pill linked">PD Reports</span>
          ) : (
            <span className="course-pill warning">Não vinculado</span>
          )}
        </div>
        <div className="consumption-hero-meta">
          <span>Entrada no curso</span>
          <strong>{entradaCurso(aluno)}</strong>
        </div>
      </div>

      <div className="consumption-hero-score" style={{ color }}>
        <strong>{pct.toFixed(1)}%</strong>
        <span>consumo</span>
      </div>

      <div className="course-progress-track large" aria-label={`Consumo ${pct.toFixed(1)}%`}>
        <div className="course-progress-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </section>
  );
}

function ConsumptionStudentMeta({ aluno }) {
  const alunoPd = aluno?.alunoPd;
  if (!alunoPd && aluno?.vinculado) return null;

  return (
    <section className="course-section consumption-link-section">
      {alunoPd ? (
        <div className="course-stats-grid compact-stats">
          <div className="course-stat muted">
            <span>Matrícula</span>
            <strong>{alunoPd.matricula || '-'}</strong>
          </div>
          <div className="course-stat muted">
            <span>Monitor</span>
            <strong>{alunoPd.monitor || 'Não informado'}</strong>
          </div>
          <div className="course-stat muted">
            <span>Status PD</span>
            <strong>{alunoPd.status || 'Não informado'}</strong>
          </div>
        </div>
      ) : (
        <div className="consumption-empty-inline">
          <strong>Aluno sem vínculo no PD Reports</strong>
          <p>O consumo existe na planilha, mas não há aluno vinculado por e-mail no sistema.</p>
        </div>
      )}
    </section>
  );
}

function ConsumptionDetail({ aluno, onBack }) {
  return (
    <div className="course-hours-details">
      {onBack && (
        <button className="course-back-button" type="button" onClick={onBack}>
          Voltar para lista
        </button>
      )}
      <ConsumptionHeader aluno={aluno} />
      <ConsumptionStudentMeta aluno={aluno} />
      <CourseScheduleSection aluno={aluno} />
      <CourseCertificatesSection certificados={aluno.certificados} />
    </div>
  );
}

export function CourseHoursStudentDetails({ aluno, alunoConsumo, apiBaseUrl, authHeaders, onBack }) {
  const [dados, setDados] = useState(alunoConsumo ? { encontrado: true, aluno: alunoConsumo } : null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState('');

  useEffect(() => {
    if (alunoConsumo) {
      setDados({ encontrado: true, aluno: alunoConsumo });
      setErro('');
      setCarregando(false);
      return undefined;
    }

    if (!aluno?.matricula) return undefined;
    let cancelado = false;

    const carregar = async () => {
      setCarregando(true);
      setErro('');
      setDados(null);
      try {
        const res = await axios.get(
          `${apiBaseUrl}/api/alunos/${encodeURIComponent(aluno.matricula)}/integralizacao`,
          { headers: authHeaders, timeout: 20000 },
        );
        if (!cancelado) setDados(res.data);
      } catch (err) {
        const mensagem = err.response?.data?.erro || 'Não foi possível carregar o consumo do aluno.';
        if (!cancelado) setErro(mensagem);
      } finally {
        if (!cancelado) setCarregando(false);
      }
    };

    carregar();
    return () => {
      cancelado = true;
    };
  }, [aluno?.matricula, alunoConsumo, apiBaseUrl, authHeaders]);

  if (carregando) {
    return <p className="monitoring-state">Carregando consumo...</p>;
  }

  if (erro) {
    return <p className="monitoring-state error">{erro}</p>;
  }

  if (!dados) {
    return null;
  }

  if (!dados.encontrado) {
    return (
      <section className="course-section">
        {onBack && (
          <button className="course-back-button" type="button" onClick={onBack}>
            Voltar para lista
          </button>
        )}
        <div className="course-section-head">
          <div>
            <h3>Consumo</h3>
            <p>{dados.mensagem || 'Sem dados de consumo para este aluno.'}</p>
          </div>
        </div>
      </section>
    );
  }

  return <ConsumptionDetail aluno={dados.aluno} onBack={onBack} />;
}
