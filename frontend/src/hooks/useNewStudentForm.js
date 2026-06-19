import { useCallback, useState } from 'react';
import axios from 'axios';

export function useNewStudentForm({
  apiBaseUrl,
  authHeaders,
  canCreateAluno,
  setMensagem,
  mensagemErroApi,
  novoAlunoInicial,
  perfilCadastroInicial,
  perfilCadastroTemDados,
  normalizarMonitor,
  normalizarStatus,
  onCreated,
  onClose,
}) {
  const [novoAluno, setNovoAluno] = useState(novoAlunoInicial);
  const [novoAlunoPerfil, setNovoAlunoPerfil] = useState(perfilCadastroInicial);
  const [mostrarPerfilNovoAluno, setMostrarPerfilNovoAluno] = useState(false);
  const [salvandoNovoAluno, setSalvandoNovoAluno] = useState(false);

  const authConfig = useCallback((config = {}) => ({
    ...config,
    headers: { ...(config.headers || {}), ...authHeaders },
  }), [authHeaders]);

  const limparNovoAluno = useCallback(() => {
    setNovoAluno(novoAlunoInicial);
    setMostrarPerfilNovoAluno(false);
    setNovoAlunoPerfil(perfilCadastroInicial());
  }, [novoAlunoInicial, perfilCadastroInicial]);

  const prepararNovoAluno = useCallback(() => {
    setMostrarPerfilNovoAluno(false);
    setNovoAlunoPerfil(perfilCadastroInicial());
  }, [perfilCadastroInicial]);

  const cancelarNovoAluno = useCallback(() => {
    onClose();
  }, [onClose]);

  const alternarPerfilNovoAluno = useCallback(() => {
    setMostrarPerfilNovoAluno((atual) => !atual);
  }, []);

  const cadastrarAluno = useCallback(async (e) => {
    e.preventDefault();
    if (!canCreateAluno || salvandoNovoAluno) return;
    setSalvandoNovoAluno(true);
    setMensagem(null);
    try {
      const payload = {
        ...novoAluno,
        monitor: normalizarMonitor(novoAluno.monitor),
        status: normalizarStatus(novoAluno.status),
      };
      if (mostrarPerfilNovoAluno && perfilCadastroTemDados(novoAlunoPerfil)) {
        payload.perfil = novoAlunoPerfil;
      }
      const res = await axios.post(`${apiBaseUrl}/api/alunos/create`, payload, authConfig({ timeout: 12000 }));
      onCreated(res.data);
      onClose();
      limparNovoAluno();
      setMensagem({ tipo: 'sucesso', texto: res.data.mensagem || 'Aluno cadastrado com sucesso.' });
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Erro ao cadastrar aluno.') });
    } finally {
      setSalvandoNovoAluno(false);
    }
  }, [
    apiBaseUrl,
    authConfig,
    canCreateAluno,
    limparNovoAluno,
    mensagemErroApi,
    mostrarPerfilNovoAluno,
    normalizarMonitor,
    normalizarStatus,
    novoAluno,
    novoAlunoPerfil,
    onClose,
    onCreated,
    perfilCadastroTemDados,
    salvandoNovoAluno,
    setMensagem,
  ]);

  return {
    novoAluno,
    novoAlunoPerfil,
    mostrarPerfilNovoAluno,
    salvandoNovoAluno,
    setNovoAluno,
    setNovoAlunoPerfil,
    alternarPerfilNovoAluno,
    cadastrarAluno,
    cancelarNovoAluno,
    limparNovoAluno,
    prepararNovoAluno,
  };
}
