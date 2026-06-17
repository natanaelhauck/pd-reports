import { useCallback, useState } from 'react';
import axios from 'axios';

export function useStudentMainData({
  aluno,
  setAluno,
  apiBaseUrl,
  authHeaders,
  mensagemErroApi,
  setMensagem,
  criarTempSeguro,
  normalizarMonitor,
  normalizarStatus,
  atualizarAlunoNosResultados,
}) {
  const [temp, setTemp] = useState(criarTempSeguro());
  const [editMode, setEditMode] = useState(false);
  const [salvando, setSalvando] = useState(false);

  const authConfig = useCallback((config = {}) => ({
    ...config,
    headers: { ...(config.headers || {}), ...authHeaders },
  }), [authHeaders]);

  const sincronizarComAluno = useCallback((alunoAtual = aluno || {}) => {
    setTemp(criarTempSeguro(alunoAtual));
    setEditMode(false);
  }, [aluno, criarTempSeguro]);

  const resetarDadosPrincipais = useCallback(() => {
    setTemp(criarTempSeguro());
    setEditMode(false);
  }, [criarTempSeguro]);

  const iniciarEdicao = useCallback(() => {
    setEditMode(true);
  }, []);

  const cancelarEdicao = useCallback(() => {
    sincronizarComAluno(aluno || {});
  }, [aluno, sincronizarComAluno]);

  const setCampoTemp = useCallback((campo, valor) => {
    setTemp((atual) => ({ ...atual, [campo]: valor }));
  }, []);

  const salvarEdicao = useCallback(async () => {
    if (salvando) return;
    setSalvando(true);
    setMensagem(null);
    try {
      const payload = { ...temp, monitor: normalizarMonitor(temp.monitor), status: normalizarStatus(temp.status) };
      const res = await axios.post(`${apiBaseUrl}/api/alunos/update`, payload, authConfig({ timeout: 12000 }));
      const atualizado = {
        ...aluno,
        ...(res.data.aluno || payload),
        dataEntradaCurso: aluno?.dataEntradaCurso || '',
        dataEntradaCursoFormatada: aluno?.dataEntradaCursoFormatada || '',
      };
      atualizarAlunoNosResultados(atualizado);
      setAluno(atualizado);
      setTemp(criarTempSeguro(atualizado));
      setEditMode(false);
      setMensagem(res.data.sync_warning
        ? { tipo: 'aviso', texto: res.data.sync_warning }
        : { tipo: 'sucesso', texto: res.data.mensagem || 'Aluno atualizado com sucesso.' });
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Erro ao salvar o aluno.') });
    } finally {
      setSalvando(false);
    }
  }, [
    aluno,
    apiBaseUrl,
    authConfig,
    atualizarAlunoNosResultados,
    criarTempSeguro,
    mensagemErroApi,
    normalizarMonitor,
    normalizarStatus,
    salvando,
    setAluno,
    setMensagem,
    temp,
  ]);

  return {
    temp,
    editMode,
    salvando,
    iniciarEdicao,
    cancelarEdicao,
    salvarEdicao,
    setCampoTemp,
    sincronizarComAluno,
    resetarDadosPrincipais,
  };
}
