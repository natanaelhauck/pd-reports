import { useEffect, useState } from 'react';
import axios from 'axios';
import { Trophy } from 'lucide-react';
import { CourseCertificatesSection } from './CourseCertificatesSection.jsx';
import { CourseScheduleSection } from './CourseScheduleSection.jsx';

const pctColor = (pct) => {
  if (pct >= 80) return 'var(--course-pct-good)';
  if (pct >= 60) return 'var(--course-pct-mid)';
  return 'var(--course-pct-low)';
};

const alunoNome = (aluno) => aluno?.nome || aluno?.alunoPd?.nome || aluno?.email || 'Aluno sem nome';
const alunoEmail = (aluno) => aluno?.email || aluno?.alunoPd?.email || 'E-mail não informado';
const alunoMatricula = (aluno) => aluno?.alunoPd?.matricula || aluno?.matricula || '';
const ingresso = (aluno) => aluno?.dataEntradaCursoFormatada || aluno?.dataIngresso || 'Não informado';

function ConsumptionHeader({ aluno }) {
  const pct = Math.max(0, Math.min(100, Number(aluno?.percentualIntegralizacao || 0)));
  const remainingPct = Math.max(0, 100 - pct);
  const color = pctColor(pct);
  const matricula = alunoMatricula(aluno);

  return (
    <section className="consumption-hero">
      <div className="consumption-hero-main">
        <div className="consumption-hero-identity">
          <h2>{alunoNome(aluno)}</h2>
          <p>{alunoEmail(aluno)}</p>
          {matricula && <p className="consumption-hero-registration">Matrícula: {matricula}</p>}
          <span className="consumption-hero-entry">Ingresso: {ingresso(aluno)}</span>
          {(aluno?.desafioFinal || !aluno?.vinculado) && (
            <div className="course-hours-badges consumption-hero-badges">
              {aluno?.desafioFinal && <span className="course-pill final"><Trophy size={13} /> Desafio Final</span>}
              {!aluno?.vinculado && (
                <span className="course-pill warning">Não vinculado</span>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="consumption-hero-score consumption-hero-score-card" style={{ color }}>
        <span>CONSUMO</span>
        <strong>{pct.toFixed(1)}%</strong>
      </div>

      <div className="consumption-progress-row">
        <div className="consumption-progress-caption">
          <span className="consumption-progress-complete" style={{ color }}>{pct.toFixed(1)}% concluído</span>
          <span className="consumption-progress-separator">·</span>
          <span className={remainingPct > 0 ? 'consumption-progress-remaining pending' : 'consumption-progress-remaining'}>
            {remainingPct.toFixed(1)}% restante
          </span>
        </div>
        <div className="course-progress-track large" aria-label={`Consumo ${pct.toFixed(1)}%`}>
          <div className="course-progress-fill" style={{ width: `${pct}%`, background: color }} />
        </div>
      </div>
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
      <CourseCertificatesSection certificados={aluno.certificados} aluno={aluno} />
      <CourseScheduleSection aluno={aluno} />
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
    return (
      <>
        {onBack && (
          <button className="course-back-button" type="button" onClick={onBack}>
            Voltar para lista
          </button>
        )}
        <p className="monitoring-state">Carregando consumo...</p>
      </>
    );
  }

  if (erro) {
    return (
      <>
        {onBack && (
          <button className="course-back-button" type="button" onClick={onBack}>
            Voltar para lista
          </button>
        )}
        <p className="monitoring-state error">{erro}</p>
      </>
    );
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
