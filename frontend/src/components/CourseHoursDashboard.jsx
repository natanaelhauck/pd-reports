import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { AlertTriangle, Clock3, FileJson, FileText, LoaderCircle, Upload, X } from 'lucide-react';
import { CourseHoursStudentCard } from './CourseHoursStudentCard.jsx';

const TABS = [
  ['ativos', 'Ativos'],
  ['inativos', 'Inativos'],
  ['todos', 'Todos'],
  ['naoVinculados', 'Não vinculados'],
];

const MIME_JSON = ['application/json', 'text/plain', 'application/octet-stream'];
const MIME_CSV = ['text/csv', 'application/csv', 'application/vnd.ms-excel', 'text/plain', 'application/octet-stream'];
const CONSUMPTION_REQUEST_TIMEOUT_MS = 60000;
const CONSUMPTION_STATUS_TIMEOUT_MS = 45000;
const CONSUMPTION_RETRY_DELAY_MS = 3000;
const isDev = import.meta.env.DEV;

const aguardar = (ms) => new Promise((resolve) => {
  window.setTimeout(resolve, ms);
});

const isRequestCanceledOrTimeout = (err) => (
  axios.isCancel?.(err)
  || err?.name === 'AbortError'
  || err?.code === 'ERR_CANCELED'
  || err?.code === 'ECONNABORTED'
  || /timeout|aborted|canceled|cancelled/i.test(String(err?.message || ''))
);

const consumoErroEhEstadoVazio = (err) => (
  err?.response?.status === 404
  && (err?.response?.data?.code === 'consumption_not_found' || err?.response?.data?.error === 'consumption_not_found')
);

const consumoErroMensagem = (err, usuario) => {
  const code = err?.response?.data?.code || err?.response?.data?.error;
  if (code === 'consumption_not_found') {
    return ['owner_admin', 'admin'].includes(usuario?.role)
      ? 'Nenhuma atualização de consumo encontrada. Clique em "Atualizar consumo" para carregar os dados.'
      : 'Nenhuma atualização de consumo disponível no momento.';
  }
  return err?.response?.data?.erro || err?.response?.data?.message || 'Não foi possível carregar os dados de consumo.';
};

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
    const aguardando = status.status === 'pending';
    return {
      label: aguardando ? 'Aguardando' : 'Processando',
      tone: 'progress',
      detail: status.started_at ? `Iniciada em ${formatarAtualizacao(status.started_at)}` : (aguardando ? 'Aguardando processamento' : 'Processamento em andamento'),
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
  const [avisoCarregamento, setAvisoCarregamento] = useState('');
  const [estadoVazio, setEstadoVazio] = useState('');
  const [tab, setTab] = useState('ativos');
  const [filtro, setFiltro] = useState('');
  const [statusAtualizacao, setStatusAtualizacao] = useState(null);
  const [carregandoStatus, setCarregandoStatus] = useState(false);
  const [modalAberto, setModalAberto] = useState(false);
  const [arquivoGrades, setArquivoGrades] = useState(null);
  const [arquivoCertificados, setArquivoCertificados] = useState(null);
  const [enviandoUpload, setEnviandoUpload] = useState(false);
  const [erroUpload, setErroUpload] = useState('');
  const [mensagemUpload, setMensagemUpload] = useState('');
  const [warningsUpload, setWarningsUpload] = useState([]);
  const [uploadStage, setUploadStage] = useState('idle');

  const canManageConsumption = ['owner_admin', 'admin'].includes(usuario?.role);
  const statusRunAtiva = statusAtualizacao?.status === 'pending' || statusAtualizacao?.status === 'running';
  const uploadEmAndamento = enviandoUpload || uploadStage === 'enviando' || uploadStage === 'processando';
  const carregarRequestId = useRef(0);
  const statusRequestId = useRef(0);

  const carregar = useCallback(async () => {
    const requestId = carregarRequestId.current + 1;
    carregarRequestId.current = requestId;
    setCarregando(true);
    setErro('');
    setEstadoVazio('');
    setAvisoCarregamento('');
    try {
      const url = `${apiBaseUrl}/api/integralizacao`;
      let res;
      try {
        res = await axios.get(url, { headers: authHeaders, timeout: CONSUMPTION_REQUEST_TIMEOUT_MS });
      } catch (err) {
        if (!isRequestCanceledOrTimeout(err)) throw err;
        if (isDev) console.info('Request de consumo abortado/timeout; tentando novamente.', err.code || err.name || err.message);
        if (carregarRequestId.current !== requestId) return;
        setAvisoCarregamento('Carregando dados de consumo. O servidor pode levar alguns segundos para responder.');
        await aguardar(CONSUMPTION_RETRY_DELAY_MS);
        if (carregarRequestId.current !== requestId) return;
        res = await axios.get(url, { headers: authHeaders, timeout: CONSUMPTION_REQUEST_TIMEOUT_MS });
      }
      if (carregarRequestId.current !== requestId) return;
      setDados(res.data);
    } catch (err) {
      if (carregarRequestId.current !== requestId) return;
      if (isRequestCanceledOrTimeout(err)) {
        if (isDev) console.info('Request de consumo abortado/timeout após retry.', err.code || err.name || err.message);
        setErro('Não foi possível carregar a lista de consumo. Tente novamente em instantes.');
      } else if (consumoErroEhEstadoVazio(err)) {
        setDados({ alunos: [], resumo: {}, permissoes: { podeVerNaoVinculados: canManageConsumption }, resumoGeralFonte: {} });
        setEstadoVazio(consumoErroMensagem(err, usuario));
      } else {
        setErro(consumoErroMensagem(err, usuario));
      }
    } finally {
      if (carregarRequestId.current === requestId) {
        setCarregando(false);
        setAvisoCarregamento('');
      }
    }
  }, [apiBaseUrl, authHeaders, canManageConsumption, usuario]);

  const carregarStatus = useCallback(async () => {
    const requestId = statusRequestId.current + 1;
    statusRequestId.current = requestId;
    setCarregandoStatus(true);
    try {
      const url = `${apiBaseUrl}/api/consumo/atualizacao/status`;
      let res;
      try {
        res = await axios.get(url, { headers: authHeaders, timeout: CONSUMPTION_STATUS_TIMEOUT_MS });
      } catch (err) {
        if (!isRequestCanceledOrTimeout(err)) throw err;
        if (isDev) console.info('Request de status do consumo abortado/timeout; tentando novamente.', err.code || err.name || err.message);
        if (statusRequestId.current !== requestId) return null;
        await aguardar(CONSUMPTION_RETRY_DELAY_MS);
        if (statusRequestId.current !== requestId) return null;
        res = await axios.get(url, { headers: authHeaders, timeout: CONSUMPTION_STATUS_TIMEOUT_MS });
      }
      if (statusRequestId.current !== requestId) return null;
      setStatusAtualizacao(res.data);
      return res.data;
    } catch (err) {
      if (statusRequestId.current !== requestId) return null;
      if (isRequestCanceledOrTimeout(err) && isDev) {
        console.info('Request de status do consumo abortado/timeout após retry.', err.code || err.name || err.message);
      }
      if (!isRequestCanceledOrTimeout(err)) {
        setStatusAtualizacao(null);
      }
      return null;
    } finally {
      if (statusRequestId.current === requestId) setCarregandoStatus(false);
    }
  }, [apiBaseUrl, authHeaders]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      carregar();
      carregarStatus();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [carregar, carregarStatus]);

  useEffect(() => {
    const status = statusAtualizacao?.status;
    if (status !== 'pending' && status !== 'running') return undefined;
    const timer = window.setInterval(async () => {
      const atualizado = await carregarStatus();
      if (atualizado?.status === 'success') {
        await carregar();
      }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [statusAtualizacao?.status, carregar, carregarStatus]);

  const alunos = useMemo(() => dados?.alunos || [], [dados?.alunos]);
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

  const abrirModalUpload = () => {
    setErroUpload('');
    setMensagemUpload('');
    setWarningsUpload([]);
    setUploadStage('idle');
    setArquivoGrades(null);
    setArquivoCertificados(null);
    setModalAberto(true);
  };

  const enviarUpload = async () => {
    if (!arquivoGrades || !arquivoCertificados || enviandoUpload) return;
    const gradesMimeOk = !arquivoGrades.type || MIME_JSON.includes(arquivoGrades.type);
    const certificatesMimeOk = !arquivoCertificados.type || MIME_CSV.includes(arquivoCertificados.type);
    if (!arquivoGrades.name.toLowerCase().endsWith('.json') || !gradesMimeOk) {
      setErroUpload('Selecione um all_grades.json valido.');
      return;
    }
    if (!arquivoCertificados.name.toLowerCase().endsWith('.csv') || !certificatesMimeOk) {
      setErroUpload('Selecione um CSV de certificados valido.');
      return;
    }

    const formData = new FormData();
    formData.append('all_grades', arquivoGrades, arquivoGrades.name);
    formData.append('certificates', arquivoCertificados, arquivoCertificados.name);

    setEnviandoUpload(true);
    setErroUpload('');
    setMensagemUpload('');
    setWarningsUpload([]);
    setUploadStage('enviando');
    let processandoTimer = null;
    try {
      processandoTimer = window.setTimeout(() => {
        setUploadStage((stage) => (stage === 'enviando' ? 'processando' : stage));
      }, 1200);
      const res = await axios.post(
        `${apiBaseUrl}/api/admin/consumo/atualizar`,
        formData,
        {
          headers: { ...authHeaders, 'Content-Type': 'multipart/form-data' },
          timeout: 1200000,
          onUploadProgress: (event) => {
            if (event.total && event.loaded >= event.total) {
              setUploadStage('processando');
            }
          },
        },
      );
      const warnings = Array.isArray(res.data?.warnings) ? res.data.warnings : [];
      const statusResposta = res.data?.status;
      const mensagemSucesso = statusResposta === 'success'
        ? 'Atualizacao de consumo concluida com sucesso.'
        : 'Atualizacao recebida. Acompanhe o processamento pelo status.';
      setUploadStage('concluido');
      setMensagemUpload(res.data?.mensagem || res.data?.message || mensagemSucesso);
      setWarningsUpload(warnings);
      setModalAberto(false);
      setArquivoGrades(null);
      setArquivoCertificados(null);
      await carregarStatus();
      if (statusResposta === 'success') {
        await carregar();
      }
    } catch (err) {
      setUploadStage('falhou');
      setErroUpload(err.response?.data?.erro || 'Nao foi possivel processar a atualizacao.');
      await carregarStatus();
    } finally {
      if (processandoTimer) {
        window.clearTimeout(processandoTimer);
      }
      setEnviandoUpload(false);
    }
  };
  const textoUploadStage = uploadStage === 'processando'
    ? 'Processando dados de consumo. Esta operacao pode levar alguns minutos.'
    : 'Enviando arquivos.';
  const statusInfo = statusAtualizacaoInfo(statusAtualizacao);
  const ultimoSucesso = statusAtualizacao?.ultimaAtualizacaoBemSucedida;
  const atualizadoEm = formatarAtualizacao(ultimoSucesso?.finished_at);
  const textoStatusTopo = canManageConsumption
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
          {mensagemUpload && canManageConsumption && <p className="consumption-upload-feedback success">{mensagemUpload}</p>}
          {warningsUpload.length > 0 && canManageConsumption && (
            <ul className="consumption-upload-warnings">
              {warningsUpload.map((warning) => <li key={warning}>{warning}</li>)}
            </ul>
          )}
        </div>
        <div className="consumption-panel-actions">
          {!canManageConsumption ? (
            <span className="consumption-last-update-only">{textoStatusTopo}</span>
          ) : (
            <>
              <button className="ui-button monitoring-refresh-button" type="button" onClick={abrirModalUpload} disabled={uploadEmAndamento || statusRunAtiva}>
                <Upload size={16} />
                Atualizar consumo
              </button>
              <span className="consumption-last-update-only">{textoStatusTopo}</span>
            </>
          )}
        </div>
      </div>

      {avisoCarregamento && <p className="monitoring-state">{avisoCarregamento}</p>}
      {estadoVazio && <p className="monitoring-state consumption-empty-state">{estadoVazio}</p>}
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

      {modalAberto && canManageConsumption && (
        <div className="consumption-upload-modal-backdrop" role="presentation" onClick={() => !uploadEmAndamento && setModalAberto(false)}>
          <div className="consumption-upload-modal" role="dialog" aria-modal="true" aria-labelledby="consumption-upload-title" onClick={(e) => e.stopPropagation()}>
            <div className="consumption-upload-modal-head">
              <div>
                <h3 id="consumption-upload-title">Atualizar consumo</h3>
                <p>Envie o JSON de notas e o CSV de certificados gerados pelo checker.</p>
              </div>
              <button className="consumption-upload-close" type="button" onClick={() => setModalAberto(false)} disabled={uploadEmAndamento} aria-label="Fechar">
                <X size={16} />
              </button>
            </div>

            <div className="consumption-upload-drop">
              <FileJson size={18} />
              <label className="consumption-upload-file">
                <span>Selecionar all_grades.json</span>
                <input
                  type="file"
                  accept=".json,application/json"
                  onChange={(e) => {
                    const file = e.target.files?.[0] || null;
                    setErroUpload('');
                    setMensagemUpload('');
                    setWarningsUpload([]);
                    setUploadStage('idle');
                    setArquivoGrades(file);
                  }}
                  disabled={uploadEmAndamento}
                />
              </label>
              <p>Arquivo de notas exportado pelo checker. O processamento pode demorar alguns minutos.</p>
            </div>

            {arquivoGrades ? (
              <div className="consumption-upload-file-meta">
                <strong>{arquivoGrades.name}</strong>
                <span>{formatarTamanhoArquivo(arquivoGrades.size)}</span>
              </div>
            ) : (
              <div className="consumption-upload-file-meta empty">Nenhum JSON selecionado.</div>
            )}

            <div className="consumption-upload-drop">
              <FileText size={18} />
              <label className="consumption-upload-file">
                <span>Selecionar certificados.csv</span>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => {
                    const file = e.target.files?.[0] || null;
                    setErroUpload('');
                    setMensagemUpload('');
                    setWarningsUpload([]);
                    setUploadStage('idle');
                    setArquivoCertificados(file);
                  }}
                  disabled={uploadEmAndamento}
                />
              </label>
              <p>CSV de certificados correspondente ao mesmo ciclo de exportacao do all_grades.</p>
            </div>

            {arquivoCertificados ? (
              <div className="consumption-upload-file-meta">
                <strong>{arquivoCertificados.name}</strong>
                <span>{formatarTamanhoArquivo(arquivoCertificados.size)}</span>
              </div>
            ) : (
              <div className="consumption-upload-file-meta empty">Nenhum CSV selecionado.</div>
            )}
            {erroUpload && (
              <div className="consumption-upload-feedback error">
                <AlertTriangle size={16} />
                <span>{erroUpload}</span>
              </div>
            )}
            {uploadEmAndamento && (
              <div className="consumption-upload-feedback progress">
                <LoaderCircle className="consumption-upload-spinner" size={16} />
                <span>{textoUploadStage}</span>
              </div>
            )}

            <div className="consumption-upload-actions">
              <button className="ui-button" type="button" onClick={() => setModalAberto(false)} disabled={uploadEmAndamento}>
                Cancelar
              </button>
              <button
                className="ui-button monitoring-refresh-button"
                type="button"
                onClick={enviarUpload}
                disabled={!arquivoGrades || !arquivoCertificados || uploadEmAndamento}
              >
                {uploadEmAndamento ? (uploadStage === 'processando' ? 'Processando...' : 'Enviando...') : 'Confirmar atualizacao'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
