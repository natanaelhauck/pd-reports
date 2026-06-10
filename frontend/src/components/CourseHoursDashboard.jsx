import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { AlertTriangle, Clock3, FileSpreadsheet, Upload, X } from 'lucide-react';
import { CourseHoursStudentCard } from './CourseHoursStudentCard.jsx';

const TABS = [
  ['ativos', 'Ativos'],
  ['inativos', 'Inativos'],
  ['todos', 'Todos'],
  ['naoVinculados', 'Não vinculados'],
];

const MIME_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

const formatarAtualizacao = (valor) => {
  if (!valor) return '';
  const data = new Date(valor);
  if (Number.isNaN(data.getTime())) return '';
  const dia = data.toLocaleDateString('pt-BR');
  const hora = data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  return `${dia} às ${hora}`;
};

const formatarTamanhoArquivo = (bytes) => {
  const tamanho = Number(bytes || 0);
  if (tamanho <= 0) return '0 B';
  if (tamanho < 1024) return `${tamanho} B`;
  if (tamanho < 1024 * 1024) return `${(tamanho / 1024).toFixed(1)} KB`;
  return `${(tamanho / (1024 * 1024)).toFixed(1)} MB`;
};

const statusAtualizacaoInfo = (status) => {
  if (!status) {
    return { label: 'Sem atualização recente', tone: 'neutral', detail: '' };
  }
  if (status.status === 'running' || status.status === 'pending') {
    return {
      label: 'Processando',
      tone: 'progress',
      detail: status.started_at ? `Iniciada em ${formatarAtualizacao(status.started_at)}` : 'Processamento em andamento',
    };
  }
  if (status.status === 'success') {
    return {
      label: 'Atualização concluída',
      tone: 'success',
      detail: status.finished_at ? `Atualizado em ${formatarAtualizacao(status.finished_at)}` : '',
    };
  }
  if (status.status === 'error') {
    return {
      label: 'Falha na atualização',
      tone: 'error',
      detail: status.finished_at ? `Falhou em ${formatarAtualizacao(status.finished_at)}` : 'Falha na atualização',
    };
  }
  return { label: 'Sem atualização recente', tone: 'neutral', detail: '' };
};

export function CourseHoursDashboard({ apiBaseUrl, authHeaders, onSelectStudent, usuario }) {
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState('');
  const [tab, setTab] = useState('ativos');
  const [filtro, setFiltro] = useState('');
  const [statusAtualizacao, setStatusAtualizacao] = useState(null);
  const [carregandoStatus, setCarregandoStatus] = useState(false);
  const [modalAberto, setModalAberto] = useState(false);
  const [arquivoSelecionado, setArquivoSelecionado] = useState(null);
  const [enviandoUpload, setEnviandoUpload] = useState(false);
  const [erroUpload, setErroUpload] = useState('');
  const [mensagemUpload, setMensagemUpload] = useState('');
  const [warningsUpload, setWarningsUpload] = useState([]);

  const isAdmin = usuario?.role === 'admin';

  const carregar = async () => {
    setCarregando(true);
    setErro('');
    try {
      const res = await axios.get(`${apiBaseUrl}/api/integralizacao`, { headers: authHeaders, timeout: 25000 });
      setDados(res.data);
    } catch (err) {
      setErro(err.response?.data?.erro || 'Não foi possível carregar os dados de consumo.');
    } finally {
      setCarregando(false);
    }
  };

  const carregarStatus = async () => {
    setCarregandoStatus(true);
    try {
      const res = await axios.get(`${apiBaseUrl}/api/consumo/atualizacao/status`, { headers: authHeaders, timeout: 15000 });
      setStatusAtualizacao(res.data);
    } catch {
      setStatusAtualizacao(null);
    } finally {
      setCarregandoStatus(false);
    }
  };

  useEffect(() => {
    carregar();
    carregarStatus();
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

  const atualizarStatus = async () => {
    await carregar();
    await carregarStatus();
  };

  const abrirModalUpload = () => {
    setErroUpload('');
    setMensagemUpload('');
    setWarningsUpload([]);
    setArquivoSelecionado(null);
    setModalAberto(true);
  };

  const enviarUpload = async () => {
    if (!arquivoSelecionado || enviandoUpload) return;
    const mimeOk = !arquivoSelecionado.type || [MIME_XLSX, 'application/octet-stream', 'application/zip'].includes(arquivoSelecionado.type);
    if (!arquivoSelecionado.name.toLowerCase().endsWith('.xlsx') || !mimeOk) {
      setErroUpload('Selecione um arquivo .xlsx válido.');
      return;
    }

    const formData = new FormData();
    formData.append('arquivo', arquivoSelecionado, arquivoSelecionado.name);

    setEnviandoUpload(true);
    setErroUpload('');
    setMensagemUpload('');
    setWarningsUpload([]);
    try {
      const res = await axios.post(
        `${apiBaseUrl}/api/admin/consumo/importar-relatorio`,
        formData,
        {
          headers: { ...authHeaders, 'Content-Type': 'multipart/form-data' },
          timeout: 900000,
        },
      );
      const warnings = Array.isArray(res.data?.warnings) ? res.data.warnings : [];
      setMensagemUpload(res.data?.mensagem || 'Atualização concluída com sucesso.');
      setWarningsUpload(warnings);
      setModalAberto(false);
      setArquivoSelecionado(null);
      await atualizarStatus();
    } catch (err) {
      setErroUpload(err.response?.data?.erro || 'Não foi possível importar o relatório.');
      await carregarStatus();
    } finally {
      setEnviandoUpload(false);
    }
  };

  const statusInfo = statusAtualizacaoInfo(statusAtualizacao);
  const ultimoSucesso = statusAtualizacao?.ultimaAtualizacaoBemSucedida;
  const atualizadoEm = formatarAtualizacao(ultimoSucesso?.finished_at);
  const textoStatusTopo = isAdmin
    ? (carregandoStatus ? 'Verificando atualização...' : (statusInfo.detail || (atualizadoEm ? `Atualizado em ${atualizadoEm}` : 'Sem atualização recente')))
    : (atualizadoEm ? `Atualizado em ${atualizadoEm}` : 'Sem atualização recente');

  return (
    <section className="course-hours-panel consumption-panel">
      <div className="course-hours-panel-head consumption-panel-head">
        <div className="consumption-panel-head-main">
          <h2>Consumo</h2>
          <p>Acompanhamento de horas, certificados e conclusão dos alunos.</p>
          <div className={`consumption-status-line ${statusInfo.tone}`}>
            <Clock3 size={13} />
            <span>{statusInfo.label}</span>
            <strong>{textoStatusTopo}</strong>
          </div>
          {mensagemUpload && isAdmin && <p className="consumption-upload-feedback success">{mensagemUpload}</p>}
          {warningsUpload.length > 0 && isAdmin && (
            <ul className="consumption-upload-warnings">
              {warningsUpload.map((warning) => <li key={warning}>{warning}</li>)}
            </ul>
          )}
        </div>
        <div className="consumption-panel-actions">
          {!isAdmin ? (
            <span className="consumption-last-update-only">{textoStatusTopo}</span>
          ) : (
            <>
              <button className="ui-button monitoring-refresh-button" type="button" onClick={abrirModalUpload}>
                <Upload size={16} />
                Atualizar
              </button>
              <span className="consumption-last-update-only">{textoStatusTopo}</span>
            </>
          )}
        </div>
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
                  onClick={() => onSelectStudent?.(aluno)}
                />
              ))}
            </div>
          )}
        </>
      )}

      {modalAberto && isAdmin && (
        <div className="consumption-upload-modal-backdrop" role="presentation" onClick={() => !enviandoUpload && setModalAberto(false)}>
          <div className="consumption-upload-modal" role="dialog" aria-modal="true" aria-labelledby="consumption-upload-title" onClick={(e) => e.stopPropagation()}>
            <div className="consumption-upload-modal-head">
              <div>
                <h3 id="consumption-upload-title">Atualizar consumo</h3>
                <p>Envie o relatório final gerado pelo checker para atualizar os dados de consumo.</p>
              </div>
              <button className="consumption-upload-close" type="button" onClick={() => setModalAberto(false)} disabled={enviandoUpload} aria-label="Fechar">
                <X size={16} />
              </button>
            </div>

            <div className="consumption-upload-drop">
              <FileSpreadsheet size={18} />
              <label className="consumption-upload-file">
                <span>Selecionar arquivo .xlsx</span>
                <input
                  type="file"
                  accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                  onChange={(e) => {
                    const file = e.target.files?.[0] || null;
                    setErroUpload('');
                    setMensagemUpload('');
                    setWarningsUpload([]);
                    setArquivoSelecionado(file);
                  }}
                  disabled={enviandoUpload}
                />
              </label>
              <p>Somente planilhas do relatório final são aceitas. O arquivo precisa conter as abas Resumo por aluno e Cursos por aluno.</p>
            </div>

            {arquivoSelecionado ? (
              <div className="consumption-upload-file-meta">
                <strong>{arquivoSelecionado.name}</strong>
                <span>{formatarTamanhoArquivo(arquivoSelecionado.size)}</span>
              </div>
            ) : (
              <div className="consumption-upload-file-meta empty">Nenhum arquivo selecionado.</div>
            )}

            {erroUpload && (
              <div className="consumption-upload-feedback error">
                <AlertTriangle size={16} />
                <span>{erroUpload}</span>
              </div>
            )}

            <div className="consumption-upload-actions">
              <button className="ui-button" type="button" onClick={() => setModalAberto(false)} disabled={enviandoUpload}>
                Cancelar
              </button>
              <button
                className="ui-button monitoring-refresh-button"
                type="button"
                onClick={enviarUpload}
                disabled={!arquivoSelecionado || enviandoUpload}
              >
                {enviandoUpload ? 'Enviando...' : 'Confirmar envio'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
