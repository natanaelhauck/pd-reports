import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { CourseHoursStudentCard } from './CourseHoursStudentCard.jsx';

const TABS = [
  ['ativos', 'Ativos'],
  ['inativos', 'Inativos'],
  ['todos', 'Todos'],
  ['naoVinculados', 'Não vinculados'],
];

export function CourseHoursDashboard({ apiBaseUrl, authHeaders }) {
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState('');
  const [tab, setTab] = useState('ativos');
  const [filtro, setFiltro] = useState('');

  const carregar = async () => {
    setCarregando(true);
    setErro('');
    try {
      const res = await axios.get(`${apiBaseUrl}/api/integralizacao`, { headers: authHeaders, timeout: 25000 });
      setDados(res.data);
    } catch (err) {
      setErro(err.response?.data?.erro || 'Não foi possível carregar a integralização.');
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

  return (
    <section className="course-hours-panel">
      <div className="course-hours-panel-head">
        <div>
          <h2>Integralização</h2>
          <p>Dados de horas, certificados e conclusão lidos da planilha local de integralização.</p>
          {dados?.fonte && (
            <span>
              Fonte: {dados.fonte.aba} · {dados.fonte.caminhoConfigurado}
            </span>
          )}
        </div>
        <button className="ui-button monitoring-refresh-button" type="button" onClick={carregar} disabled={carregando}>
          {carregando ? 'Atualizando...' : 'Atualizar'}
        </button>
      </div>

      {erro && <p className="monitoring-state error">{erro}</p>}
      {carregando && !dados && <p className="monitoring-state">Carregando integralização...</p>}

      {dados && (
        <>
          <div className="course-summary-grid">
            <div><span>Total</span><strong>{dados.resumo?.total || 0}</strong></div>
            <div><span>Ativos</span><strong>{dados.resumo?.ativos || 0}</strong></div>
            <div><span>Concluídos</span><strong>{dados.resumo?.concluidos || 0}</strong></div>
            {podeVerNaoVinculados && <div><span>Não vinculados</span><strong>{dados.resumo?.naoVinculados || 0}</strong></div>}
          </div>

          <div className="course-dashboard-controls">
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
              placeholder="Filtrar por nome ou e-mail"
            />
          </div>

          {filtrados.length === 0 ? (
            <p className="monitoring-state">Nenhum aluno encontrado para os filtros selecionados.</p>
          ) : (
            <div className="course-hours-grid">
              {filtrados.map((aluno) => (
                <CourseHoursStudentCard key={`${aluno.emailNormalizado}-${aluno.alunoPd?.matricula || 'sem-vinculo'}`} aluno={aluno} />
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
