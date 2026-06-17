import { useCallback, useMemo, useState } from 'react';
import axios from 'axios';

export function useAlunoSearch({
  apiBaseUrl,
  authHeaders,
  aluno,
  setAluno,
  setActiveTab,
  limparHistorico,
  setMensagem,
  setVoltarParaListaConsumo,
  setMostrarNovoAluno,
  setMostrarUsuarios,
  setMostrarMonitores,
  setMostrarIntegralizacao,
  prepararDadosPrincipais,
  resetarDadosPrincipais,
  prepararPerfilInicial,
  limparPerfil,
  mensagemErroApi,
  mensagemErroAbrirAluno,
  cardRef,
}) {
  const [alunos, setAlunos] = useState([]);
  const [busca, setBusca] = useState('');
  const [buscando, setBuscando] = useState(false);
  const [buscaRealizada, setBuscaRealizada] = useState(false);

  const authConfig = useCallback((config = {}) => ({
    ...config,
    headers: { ...(config.headers || {}), ...authHeaders },
  }), [authHeaders]);

  const alunosOrdenados = useMemo(() => {
    const porMatricula = new Map();
    alunos.forEach((item) => {
      const chave = item.matricula || item.id;
      if (!porMatricula.has(chave)) porMatricula.set(chave, item);
    });
    return Array.from(porMatricula.values()).sort((a, b) =>
      String(a.nome || '').localeCompare(String(b.nome || ''), 'pt-BR', { sensitivity: 'base' })
    );
  }, [alunos]);

  const resultadosVisiveis = useMemo(() => {
    if (aluno && alunosOrdenados.length === 1 && alunosOrdenados[0].matricula === aluno.matricula) {
      return [];
    }
    return alunosOrdenados;
  }, [aluno, alunosOrdenados]);

  const resetBuscaGeral = useCallback(() => {
    setBusca('');
    setAlunos([]);
    setBuscaRealizada(false);
  }, []);

  const fecharAlunoSelecionado = useCallback(() => {
    setAluno(null);
    resetarDadosPrincipais();
    limparPerfil();
    setActiveTab('Dados principais');
    limparHistorico();
    setVoltarParaListaConsumo(false);
  }, [limparHistorico, limparPerfil, resetarDadosPrincipais, setActiveTab, setAluno, setVoltarParaListaConsumo]);

  const limparBuscaGeral = useCallback(({ fecharAluno = true } = {}) => {
    resetBuscaGeral();
    setMensagem(null);
    if (fecharAluno) {
      fecharAlunoSelecionado();
    }
  }, [fecharAlunoSelecionado, resetBuscaGeral, setMensagem]);

  const buscarAlunosPorTermo = useCallback(async (termo = '') => {
    if (!termo) {
      setAlunos([]);
      setAluno(null);
      resetarDadosPrincipais();
      return 0;
    }
    setBuscando(true);
    setMensagem(null);
    try {
      const res = await axios.get(`${apiBaseUrl}/api/alunos`, authConfig({ params: { q: termo }, timeout: 12000 }));
      setAlunos(res.data);
      if (res.data.length === 0) {
        setAluno(null);
        resetarDadosPrincipais();
        setMensagem({ tipo: 'erro', texto: 'Nenhum aluno encontrado' });
      }
      return res.data.length;
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Não foi possível buscar alunos.') });
      return null;
    } finally {
      setBuscando(false);
    }
  }, [apiBaseUrl, authConfig, mensagemErroApi, resetarDadosPrincipais, setAluno, setMensagem]);

  const buscarAlunos = useCallback(async (e) => {
    e.preventDefault();
    setMostrarMonitores(false);
    setMostrarIntegralizacao(false);
    setVoltarParaListaConsumo(false);
    setBuscaRealizada(true);
    const total = await buscarAlunosPorTermo(busca.trim());
    if (total > 0) {
      prepararDadosPrincipais(aluno || {});
    }
    setActiveTab('Dados principais');
  }, [
    aluno,
    busca,
    buscarAlunosPorTermo,
    prepararDadosPrincipais,
    setActiveTab,
    setMostrarIntegralizacao,
    setMostrarMonitores,
    setVoltarParaListaConsumo,
  ]);

  const selecionarAluno = useCallback((selecionado) => {
    setMostrarNovoAluno(false);
    setMostrarUsuarios(false);
    setMostrarMonitores(false);
    setMostrarIntegralizacao(false);
    setAluno(selecionado);
    prepararDadosPrincipais(selecionado);
    prepararPerfilInicial(selecionado.matricula);
    setActiveTab('Dados principais');
    limparHistorico();
    setVoltarParaListaConsumo(false);
    setMensagem(null);
    requestAnimationFrame(() => cardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  }, [
    cardRef,
    limparHistorico,
    prepararPerfilInicial,
    prepararDadosPrincipais,
    setActiveTab,
    setAluno,
    setMensagem,
    setMostrarIntegralizacao,
    setMostrarMonitores,
    setMostrarNovoAluno,
    setMostrarUsuarios,
    setVoltarParaListaConsumo,
  ]);

  const abrirAlunoPorMatricula = useCallback(async (matricula, origem = 'geral') => {
    if (!matricula) {
      setMensagem({ tipo: 'aviso', texto: 'Este registro de consumo ainda não tem aluno vinculado no PD Reports.' });
      return;
    }

    setBuscando(true);
    setMensagem(null);
    try {
      const res = await axios.get(`${apiBaseUrl}/api/alunos/${encodeURIComponent(matricula)}`, authConfig({ timeout: 12000 }));
      const selecionado = res.data;
      resetBuscaGeral();
      setMostrarNovoAluno(false);
      setMostrarUsuarios(false);
      setMostrarMonitores(false);
      setMostrarIntegralizacao(false);
      setAluno(selecionado);
      prepararDadosPrincipais(selecionado);
      prepararPerfilInicial(selecionado.matricula);
      setActiveTab(origem === 'consumo' ? 'Consumo' : 'Dados principais');
      limparHistorico();
      setVoltarParaListaConsumo(origem === 'consumo');
      requestAnimationFrame(() => cardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroAbrirAluno(err) });
    } finally {
      setBuscando(false);
    }
  }, [
    apiBaseUrl,
    authConfig,
    cardRef,
    limparHistorico,
    mensagemErroAbrirAluno,
    prepararPerfilInicial,
    prepararDadosPrincipais,
    resetBuscaGeral,
    setActiveTab,
    setAluno,
    setMensagem,
    setMostrarIntegralizacao,
    setMostrarMonitores,
    setMostrarNovoAluno,
    setMostrarUsuarios,
    setVoltarParaListaConsumo,
  ]);

  const selecionarAlunoConsumo = useCallback(async (alunoConsumo) => {
    const matricula = alunoConsumo?.alunoPd?.matricula;
    await abrirAlunoPorMatricula(matricula, 'consumo');
  }, [abrirAlunoPorMatricula]);

  const voltarParaConsumoGeral = useCallback(() => {
    resetBuscaGeral();
    setAluno(null);
    resetarDadosPrincipais();
    limparPerfil();
    setActiveTab('Dados principais');
    limparHistorico();
    setVoltarParaListaConsumo(false);
    setMostrarNovoAluno(false);
    setMostrarUsuarios(false);
    setMostrarMonitores(false);
    setMostrarIntegralizacao(true);
    setMensagem(null);
  }, [
    resetBuscaGeral,
    limparHistorico,
    limparPerfil,
    resetarDadosPrincipais,
    setActiveTab,
    setAluno,
    setMensagem,
    setMostrarIntegralizacao,
    setMostrarMonitores,
    setMostrarNovoAluno,
    setMostrarUsuarios,
    setVoltarParaListaConsumo,
  ]);

  const atualizarAlunoNosResultados = useCallback((atualizado) => {
    setAlunos((atuais) => atuais.map((item) => (item.matricula === atualizado.matricula ? atualizado : item)));
  }, []);

  const adicionarAlunoAResultados = useCallback((criado) => {
    setAlunos((atuais) => [...atuais.filter((item) => item.matricula !== criado.matricula), criado]);
    setBuscaRealizada(true);
  }, []);

  return {
    alunos,
    alunosOrdenados,
    resultadosVisiveis,
    busca,
    setBusca,
    buscaRealizada,
    buscando,
    buscarAlunos,
    limparBuscaGeral,
    fecharAlunoSelecionado,
    selecionarAluno,
    abrirAlunoPorMatricula,
    selecionarAlunoConsumo,
    voltarParaConsumoGeral,
    resetBuscaGeral,
    atualizarAlunoNosResultados,
    adicionarAlunoAResultados,
  };
}
