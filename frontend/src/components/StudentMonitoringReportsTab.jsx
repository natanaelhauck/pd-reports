import { useEffect, useState } from 'react';
import axios from 'axios';
import { ClipboardList } from 'lucide-react';

export function StudentMonitoringReportsTab({
  aluno,
  authHeaders,
  apiBaseUrl,
  styles = {},
  mensagemErroApi,
  formatarDataIso,
  statusMonitoriaClass,
  statusMonitoriaLabel,
  resumoCurto,
}) {
  const [dados, setDados] = useState({ resumo: null, relatorios: [], total_lidos: 0 });
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState('');
  const [inicio, setInicio] = useState('2026-03-23');
  const [fim, setFim] = useState('');
  const [status, setStatus] = useState('');
  const [aberto, setAberto] = useState('');
  const [atualizando, setAtualizando] = useState(false);
  const [mensagemAtualizacao, setMensagemAtualizacao] = useState('');

  useEffect(() => {
    if (!aluno?.matricula) return undefined;
    let cancelado = false;
    const carregar = async () => {
      setCarregando(true);
      setErro('');
      setMensagemAtualizacao('');
      try {
        const res = await axios.get(`${apiBaseUrl}/api/alunos/${encodeURIComponent(aluno.matricula)}/relatorios-monitoria`, { headers: authHeaders, timeout: 20000 });
        if (!cancelado) setDados(res.data);
      } catch (err) {
        if (!cancelado) setErro(mensagemErroApi(err, 'Nao foi possivel carregar os relatorios de monitoria.'));
      } finally {
        if (!cancelado) setCarregando(false);
      }
    };
    const timer = setTimeout(carregar, 0);
    return () => {
      cancelado = true;
      clearTimeout(timer);
    };
  }, [aluno?.matricula, apiBaseUrl, authHeaders, mensagemErroApi]);

  const atualizarAgora = async () => {
    if (!aluno?.matricula || carregando || atualizando) return;
    setAtualizando(true);
    setCarregando(true);
    setErro('');
    setMensagemAtualizacao('');
    try {
      await axios.post(`${apiBaseUrl}/api/relatorios-monitoria/refresh`, {}, { headers: authHeaders, timeout: 12000 });
      const res = await axios.get(`${apiBaseUrl}/api/alunos/${encodeURIComponent(aluno.matricula)}/relatorios-monitoria`, { headers: authHeaders, timeout: 20000 });
      setDados(res.data);
      setMensagemAtualizacao('Relatórios atualizados com sucesso.');
    } catch (err) {
      setErro(mensagemErroApi(err, 'Nao foi possivel atualizar os relatorios de monitoria.'));
    } finally {
      setCarregando(false);
      setAtualizando(false);
    }
  };

  const relatoriosFiltrados = (dados.relatorios || []).filter((relatorio) => {
    if (inicio && relatorio.data < inicio) return false;
    if (fim && relatorio.data > fim) return false;
    if (status && relatorio.status !== status) return false;
    return true;
  });
  const statusOptions = ['Presente', 'Falta', 'Aluno não agendado', 'Aluno finalizou'];
  const resumo = dados.resumo || { total: 0, presentes: 0, faltas: 0, aluno_nao_agendado: 0, aluno_finalizou: 0 };

  return (
    <section className="monitoring-reports" style={styles.section}>
      <div className="monitoring-empty-head">
        <ClipboardList size={22} />
        <div>
          <h3>Relatorios de Monitoria</h3>
          <p>Dados lidos da aba Relatorios Monitoria a partir de 23/03/2026.</p>
          <p className="monitoring-sync-note">Os dados são sincronizados da planilha. Use o botão Atualizar se acabou de enviar um formulário.</p>
        </div>
        <button
          className="ui-button monitoring-refresh-button"
          type="button"
          onClick={atualizarAgora}
          disabled={carregando || atualizando}
        >
          {atualizando ? 'Atualizando...' : 'Atualizar'}
        </button>
      </div>

      {carregando && <p className="monitoring-state">Carregando relatorios...</p>}
      {erro && <p className="monitoring-state error">{erro}</p>}
      {mensagemAtualizacao && !erro && <p className="monitoring-state success">{mensagemAtualizacao}</p>}

      {!carregando && !erro && (
        <>
          <div className="monitoring-summary-grid">
            <MetricCard label="Total" value={resumo.total} tone="total" />
            <MetricCard label="Presentes" value={resumo.presentes} tone="present" />
            <MetricCard label="Faltas" value={resumo.faltas} tone="absent" />
            <MetricCard label="Não agendado" value={resumo.aluno_nao_agendado} tone="unscheduled" />
            <MetricCard label="Finalizou" value={resumo.aluno_finalizou} tone="finished" />
          </div>

          <div className="monitoring-filters">
            <ProfileField styles={styles} label="Data inicial" type="date" value={inicio} onChange={setInicio} />
            <ProfileField styles={styles} label="Data final" type="date" value={fim} onChange={setFim} />
            <ProfileSelect styles={styles} label="Status" value={status} onChange={setStatus} options={[['', 'Todos'], ...statusOptions.map((item) => [item, item])]} />
          </div>

          {relatoriosFiltrados.length === 0 ? (
            <p className="monitoring-state">Nenhum relatorio de monitoria encontrado para este aluno a partir de 23/03/2026.</p>
          ) : (
            <div className="monitoring-list">
              {relatoriosFiltrados.map((relatorio, index) => {
                const id = `${relatorio.data}-${index}`;
                const estaAberto = aberto === id;
                const statusClass = statusMonitoriaClass(relatorio.status);
                const ehPresente = statusClass === 'present';
                const ehFalta = statusClass === 'absent';
                const ehSimples = statusClass === 'unscheduled' || statusClass === 'finished';
                const temObservacao = Boolean(relatorio.relatorio || relatorio.outro_motivo);
                return (
                  <article className={`monitoring-report-card status-${statusClass}`} key={id}>
                    <div className="monitoring-report-head">
                      <div>
                        <strong>{formatarDataIso(relatorio.data)} · <span className={`monitoring-status-badge status-${statusClass}`}>{statusMonitoriaLabel(relatorio.status)}</span></strong>
                        <span>Monitor: {relatorio.agente || 'Não informado'}</span>
                        <span>Aluno: {relatorio.aluno || aluno?.nome || 'Não informado'}</span>
                      </div>
                      {(ehPresente || temObservacao) && (
                        <button className="ui-button" type="button" style={styles.secondaryBtn} onClick={() => setAberto(estaAberto ? '' : id)}>
                          {estaAberto ? 'Ocultar' : 'Ver detalhes'}
                        </button>
                      )}
                    </div>

                    {ehPresente && (
                      <>
                        <div className="monitoring-report-grid">
                          <DisplayItem styles={styles} label="Módulo" value={relatorio.modulo} compact />
                          <DisplayItem styles={styles} label="Curso" value={relatorio.curso} compact />
                          <DisplayItem styles={styles} label="READ IA" value={relatorio.read_ia_link ? <a className="read-ia-link" href={relatorio.read_ia_link} target="_blank" rel="noreferrer">Abrir READ IA</a> : ''} compact />
                        </div>
                        {!estaAberto && relatorio.relatorio && <p className="monitoring-preview">{resumoCurto(relatorio.relatorio)}</p>}
                      </>
                    )}

                    {ehFalta && (
                      <div className="monitoring-report-grid">
                        <DisplayItem styles={styles} label="Motivo da falta" value={relatorio.motivo_falta} compact />
                        {relatorio.outro_motivo && <DisplayItem styles={styles} label="Outro motivo" value={relatorio.outro_motivo} compact />}
                      </div>
                    )}

                    {ehSimples && temObservacao && !estaAberto && (
                      <p className="monitoring-preview">{resumoCurto(relatorio.relatorio || relatorio.outro_motivo)}</p>
                    )}

                    {estaAberto && (ehPresente || temObservacao) && (
                      <div className="monitoring-report-detail">
                        <strong>Relatório READ IA / Resumo</strong>
                        <p>{relatorio.relatorio || 'Não informado'}</p>
                        {relatorio.outro_motivo && <p><strong>Outro motivo:</strong> {relatorio.outro_motivo}</p>}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </>
      )}
    </section>
  );
}

function MetricCard({ label, value, tone, active = false, onClick }) {
  const Tag = onClick ? 'button' : 'div';
  return (
    <Tag
      className={`monitoring-metric-card metric-${tone || 'total'}${active ? ' active' : ''}${onClick ? ' clickable' : ''}`}
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      title={onClick ? `Filtrar por ${label}` : undefined}
      aria-label={onClick ? `Filtrar monitorias por ${label}` : undefined}
    >
      <span>{label}</span>
      <strong>{value}</strong>
    </Tag>
  );
}

function DisplayItem({ styles, label, value, compact = false }) {
  return (
    <div className={compact ? 'display-item compact' : 'display-item'}>
      <span style={styles.label}>{label}</span>
      <strong>{value || 'Não informado'}</strong>
    </div>
  );
}

function ProfileField({ styles, label, value, onChange, disabled, type = 'text', autoComplete }) {
  return (
    <label style={{ display: 'block', marginTop: '10px' }}>
      <span style={styles.label}>{label}</span>
      <input type={type} style={styles.fieldInput} value={value || ''} disabled={disabled} onChange={(event) => onChange(event.target.value)} autoComplete={autoComplete} />
    </label>
  );
}

function ProfileSelect({ styles, label, value, onChange, disabled, options, color }) {
  return (
    <label style={{ display: 'block', marginTop: '10px' }}>
      <span style={styles.label}>{label}</span>
      <select style={{ ...styles.fieldInput, color: color || 'var(--pd-text)', fontWeight: color ? 800 : 500 }} value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)}>
        {options.map(([optionValue, optionLabel]) => <option key={optionValue} value={optionValue}>{optionLabel}</option>)}
      </select>
    </label>
  );
}
