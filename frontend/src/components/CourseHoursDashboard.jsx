import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { CourseHoursStudentCard } from './CourseHoursStudentCard.jsx';
import { CourseHoursStudentDetails } from './CourseHoursStudentDetails.jsx';

const TABS = [
  ['ativos', 'Ativos'],
  ['inativos', 'Inativos'],
  ['todos', 'Todos'],
  ['naoVinculados', 'Não vinculados'],
];

const formatarAtualizacao = (valor) => {
  if (!valor) return '';
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return '';
  return data.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
};

export function CourseHoursDashboard({ apiBaseUrl, authHeaders }) {
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState('');
  const [tab, setTab] = useState('ativos');
  const [filtro, setFiltro] = useState('');
  const [alunoSelecionado, setAlunoSelecionado] = useState(null);

  const carregar = async () => {
    setCarregando(true);
    setErro('');
    try {
      const res = await axios.get(`${apiBaseUrl}/api/integralizacao`, { headers: authHeaders, timeout: 25000 });
      setDados(res.data);
      if (alunoSelecionado) {
        const atualizado = (res.data.alunos || []).find((aluno) => aluno.emailNormalizado === alunoSelecionado.emailNormalizado);
        if (atualizado) setAlunoSelecionado(atualizado);
      }
    } catch (err) {
      setErro(err.response?.data?.erro || 'Não foi possível carregar os dados de consumo.');
    } finally {
      setCarregando(false);
    }
  };

  useEffect(() => {
    carregar();
  }, [apiBaseUrl, authHeaders]);

  const alunos = dados?.alunos || [];
  const podeVerNaoVinculados = dados?.permissoes?.podeVerNaoVinculados;
  const tabsVisiveis = TABS.filter(([key]) => key !== 'naoVinculados' || podeVerNaoVinculados);
  const atualizadoEm = formatarAtualizacao(dados?.fonte?.atualizadoEm);

  useEffect(() => {
    if (tab === 'naoVinculados' && !podeVerNaoVinculados) setTab('ativos');
  }, [tab, podeVerNaoVinculados]);

  const counts = useMemo(() => ({
    ativos: alunos.filter((aluno) => aluno.ativo).length,
    inativos: alunos.filter((aluno) => !aluno.ativo).length,
    todos: alunos.length,
    naoVinculados: alunos.filter((aluno) => !aluno.vinculado).length,
  }), [alunos]);

  const filtrados = useMemo(() => {
    const q = filtro.trim().toLowerCase();
    return alunos
      .filter((aluno) => {
        if (tab === 'ativos' && !aluno.ativo) return false;
        if (tab === 'inativos' && aluno.ativo) return false;
        if (tab === 'naoVinculados' && aluno.vinculado) return false;
        if (!q) return true;
        return String(aluno.nome || '').toLowerCase().includes(q)
          || String(aluno.email || '').toLowerCase().includes(q);
      })
      .sort((a, b) => Number(b.percentualIntegralizacao || 0) - Number(a.percentualIntegralizacao || 0));
  }, [alunos, filtro, tab]);

  if (alunoSelecionado) {
    return (
      <section className="course-hours-panel consumption-panel detail-mode">
        <CourseHoursStudentDetails
          alunoConsumo={alunoSelecionado}
          onBack={() => setAlunoSelecionado(null)}
        />
      </section>
    );
  }

  return (
    <section className="course-hours-panel consumption-panel">
      <div className="course-hours-panel-head consumption-panel-head">
        <div>
          <h2>Consumo</h2>
          <p>Acompanhamento de horas, certificados e conclusão dos alunos.</p>
          {atualizadoEm && <span>Atualizado em {atualizadoEm}</span>}
        </div>
        <button className="ui-button monitoring-refresh-button" type="button" onClick={carregar} disabled={carregando}>
          {carregando ? 'Atualizando...' : 'Atualizar'}
        </button>
      </div>

      {erro && <p className="monitoring-state error">{erro}</p>}
      {carregando && !dados && <p className="monitoring-state">Carregando consumo...</p>}

      {dados && (
        <>
          <div className="course-dashboard-controls consumption-controls">
            <div className="course-tab-list">
              {tabsVisiveis.map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  className={tab === key ? 'active' : ''}
                  onClick={() => setTab(key)}
                >
                  {label}
                  <span>{counts[key]}</span>
                </button>
              ))}
            </div>
            <input
              value={filtro}
              onChange={(e) => setFiltro(e.target.value)}
              placeholder="Buscar por nome ou e-mail"
            />
          </div>

          {filtrados.length === 0 ? (
            <p className="monitoring-state">Nenhum aluno encontrado para os filtros selecionados.</p>
          ) : (
            <div className="course-hours-list">
              {filtrados.map((aluno) => (
                <CourseHoursStudentCard
                  key={`${aluno.emailNormalizado}-${aluno.alunoPd?.matricula || 'sem-vinculo'}`}
                  aluno={aluno}
                  onClick={() => setAlunoSelecionado(aluno)}
                />
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
