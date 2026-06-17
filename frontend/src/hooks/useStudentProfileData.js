import { useCallback, useState } from 'react';
import axios from 'axios';

export function useStudentProfileData({
  aluno,
  apiBaseUrl,
  authHeaders,
  mensagemErroApi,
  setMensagem,
  perfilInicial,
  normalizarPerfil,
  montarPayloadPerfil,
  carregarHistorico,
  activeTab,
}) {
  const [perfil, setPerfil] = useState(perfilInicial());
  const [perfilTemp, setPerfilTemp] = useState(perfilInicial());
  const [editPerfil, setEditPerfil] = useState(false);
  const [salvandoPerfil, setSalvandoPerfil] = useState(false);

  const authConfig = useCallback((config = {}) => ({
    ...config,
    headers: { ...(config.headers || {}), ...authHeaders },
  }), [authHeaders]);

  const sincronizarPerfil = useCallback((proximoPerfil = {}) => {
    const normalizado = normalizarPerfil(proximoPerfil);
    setPerfil(normalizado);
    setPerfilTemp(normalizado);
    setEditPerfil(false);
    return normalizado;
  }, [normalizarPerfil]);

  const prepararPerfilInicial = useCallback((matricula = '') => {
    return sincronizarPerfil(perfilInicial(matricula));
  }, [perfilInicial, sincronizarPerfil]);

  const limparPerfil = useCallback(() => {
    sincronizarPerfil(perfilInicial());
  }, [perfilInicial, sincronizarPerfil]);

  const carregarPerfilAluno = useCallback(async (matricula) => {
    if (!matricula) return null;
    const res = await axios.get(`${apiBaseUrl}/api/alunos/perfil/${encodeURIComponent(matricula)}`, authConfig({ timeout: 12000 }));
    return sincronizarPerfil(res.data);
  }, [apiBaseUrl, authConfig, sincronizarPerfil]);

  const iniciarEdicaoPerfil = useCallback(() => {
    setEditPerfil(true);
  }, []);

  const cancelarEdicaoPerfil = useCallback(() => {
    setPerfilTemp(perfil);
    setEditPerfil(false);
  }, [perfil]);

  const setCampoPerfilTemp = useCallback((campo, valor) => {
    setPerfilTemp((atual) => ({ ...atual, [campo]: valor }));
  }, []);

  const salvarPerfil = useCallback(async () => {
    if (!aluno || salvandoPerfil) return;
    setSalvandoPerfil(true);
    setMensagem(null);
    try {
      const payload = montarPayloadPerfil(perfilTemp, aluno.matricula);
      const res = await axios.post(`${apiBaseUrl}/api/alunos/perfil/update`, payload, authConfig({ timeout: 12000 }));
      const atualizado = normalizarPerfil(res.data.perfil);
      setPerfil(atualizado);
      setPerfilTemp(atualizado);
      setEditPerfil(false);
      setMensagem({ tipo: 'sucesso', texto: res.data.mensagem || 'Perfil atualizado com sucesso.' });
      if (activeTab === 'Histórico') carregarHistorico(aluno.matricula);
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Erro ao salvar perfil.') });
    } finally {
      setSalvandoPerfil(false);
    }
  }, [
    activeTab,
    aluno,
    apiBaseUrl,
    authConfig,
    carregarHistorico,
    mensagemErroApi,
    montarPayloadPerfil,
    normalizarPerfil,
    perfilTemp,
    salvandoPerfil,
    setMensagem,
  ]);

  return {
    perfil,
    perfilTemp,
    editPerfil,
    salvandoPerfil,
    setPerfilTemp,
    setCampoPerfilTemp,
    carregarPerfilAluno,
    iniciarEdicaoPerfil,
    cancelarEdicaoPerfil,
    salvarPerfil,
    sincronizarPerfil,
    prepararPerfilInicial,
    limparPerfil,
  };
}
