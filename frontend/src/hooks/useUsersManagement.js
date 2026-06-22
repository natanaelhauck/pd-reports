import { useCallback, useState } from 'react';
import axios from 'axios';

const NOVO_USUARIO_INICIAL = { nome: '', email: '', senha: '', role: 'monitor' };
const USUARIO_TEMP_INICIAL = { nome: '', email: '', role: 'monitor' };

const ordenarUsuarios = (usuarios) => [...usuarios].sort((a, b) =>
  String(a.nome).localeCompare(String(b.nome), 'pt-BR')
);

export function useUsersManagement({
  apiBaseUrl,
  authHeaders,
  canManageUsuarios,
  setMensagem,
  getErrorMessage,
}) {
  const [usuarios, setUsuarios] = useState([]);
  const [novoUsuario, setNovoUsuario] = useState(NOVO_USUARIO_INICIAL);
  const [usuarioEditando, setUsuarioEditando] = useState(null);
  const [usuarioTemp, setUsuarioTemp] = useState(USUARIO_TEMP_INICIAL);
  const [senhaUsuarioEditando, setSenhaUsuarioEditando] = useState(null);
  const [novaSenhaUsuario, setNovaSenhaUsuario] = useState('');
  const [mostrarSenhaUsuario, setMostrarSenhaUsuario] = useState(false);
  const [salvandoSenhaUsuario, setSalvandoSenhaUsuario] = useState(false);
  const [salvandoUsuarioEditando, setSalvandoUsuarioEditando] = useState(false);
  const [salvandoUsuario, setSalvandoUsuario] = useState(false);

  const authConfig = useCallback((config = {}) => ({
    ...config,
    headers: { ...(config.headers || {}), ...authHeaders },
  }), [authHeaders]);

  const resetarFormularioUsuarios = useCallback(() => {
    setNovoUsuario(NOVO_USUARIO_INICIAL);
    setUsuarioEditando(null);
    setUsuarioTemp(USUARIO_TEMP_INICIAL);
    setSenhaUsuarioEditando(null);
    setNovaSenhaUsuario('');
    setMostrarSenhaUsuario(false);
  }, []);

  const limparGestaoUsuarios = useCallback(() => {
    setUsuarios([]);
    resetarFormularioUsuarios();
  }, [resetarFormularioUsuarios]);

  const carregarUsuarios = useCallback(async () => {
    if (!canManageUsuarios) return false;
    setMensagem(null);
    try {
      const res = await axios.get(`${apiBaseUrl}/api/usuarios`, authConfig({ timeout: 12000 }));
      setUsuarios(res.data);
      return true;
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: getErrorMessage(err, 'Não foi possível carregar usuários.') });
      return false;
    }
  }, [apiBaseUrl, authConfig, canManageUsuarios, getErrorMessage, setMensagem]);

  const cadastrarUsuario = useCallback(async (e) => {
    e.preventDefault();
    if (!canManageUsuarios || salvandoUsuario) return;
    setSalvandoUsuario(true);
    setMensagem(null);
    try {
      const res = await axios.post(`${apiBaseUrl}/api/usuarios/create`, novoUsuario, authConfig({ timeout: 12000 }));
      setUsuarios((atuais) => ordenarUsuarios([...atuais, res.data.usuario]));
      setNovoUsuario(NOVO_USUARIO_INICIAL);
      setMensagem({ tipo: 'sucesso', texto: res.data.mensagem || 'Usuário cadastrado com sucesso.' });
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: getErrorMessage(err, 'Erro ao cadastrar usuário.') });
    } finally {
      setSalvandoUsuario(false);
    }
  }, [apiBaseUrl, authConfig, canManageUsuarios, getErrorMessage, novoUsuario, salvandoUsuario, setMensagem]);

  const editarUsuario = useCallback((usuarioAlvo) => {
    setUsuarioEditando(usuarioAlvo.id);
    setUsuarioTemp({
      nome: usuarioAlvo.nome || '',
      email: usuarioAlvo.email || '',
      role: usuarioAlvo.role || 'monitor',
    });
    setSenhaUsuarioEditando(null);
    setNovaSenhaUsuario('');
    setMostrarSenhaUsuario(false);
    setMensagem(null);
  }, [setMensagem]);

  const cancelarEdicaoUsuario = useCallback(() => {
    setUsuarioEditando(null);
    setUsuarioTemp(USUARIO_TEMP_INICIAL);
  }, []);

  const salvarUsuario = useCallback(async (usuarioAlvo) => {
    if (!canManageUsuarios || salvandoUsuarioEditando) return;
    setSalvandoUsuarioEditando(true);
    setMensagem(null);
    try {
      const res = await axios.put(`${apiBaseUrl}/api/usuarios/${usuarioAlvo.id}`, usuarioTemp, authConfig({ timeout: 12000 }));
      setUsuarios((atuais) => ordenarUsuarios(
        atuais.map((item) => (item.id === usuarioAlvo.id ? res.data.usuario : item))
      ));
      cancelarEdicaoUsuario();
      setMensagem({ tipo: 'sucesso', texto: res.data.mensagem || 'Usuário atualizado com sucesso.' });
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: getErrorMessage(err, 'Erro ao atualizar usuário.') });
    } finally {
      setSalvandoUsuarioEditando(false);
    }
  }, [
    apiBaseUrl,
    authConfig,
    cancelarEdicaoUsuario,
    getErrorMessage,
    canManageUsuarios,
    salvandoUsuarioEditando,
    setMensagem,
    usuarioTemp,
  ]);

  const iniciarEdicaoSenha = useCallback((usuarioAlvo) => {
    setSenhaUsuarioEditando(usuarioAlvo.id);
    setNovaSenhaUsuario('');
    setMostrarSenhaUsuario(false);
    setUsuarioEditando(null);
  }, []);

  const cancelarEdicaoSenha = useCallback(() => {
    setSenhaUsuarioEditando(null);
    setNovaSenhaUsuario('');
    setMostrarSenhaUsuario(false);
  }, []);

  const alternarMostrarSenhaUsuario = useCallback(() => {
    setMostrarSenhaUsuario((atual) => !atual);
  }, []);

  const salvarSenhaUsuario = useCallback(async (usuarioAlvo) => {
    if (!canManageUsuarios || salvandoSenhaUsuario) return;
    setSalvandoSenhaUsuario(true);
    setMensagem(null);
    try {
      const res = await axios.post(`${apiBaseUrl}/api/usuarios/update-password`, {
        usuario_id: usuarioAlvo.id,
        nova_senha: novaSenhaUsuario,
      }, authConfig({ timeout: 12000 }));
      setSenhaUsuarioEditando(null);
      setNovaSenhaUsuario('');
      setMostrarSenhaUsuario(false);
      setMensagem({ tipo: 'sucesso', texto: res.data.mensagem || 'Senha alterada com sucesso.' });
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: getErrorMessage(err, 'Erro ao alterar senha.') });
    } finally {
      setSalvandoSenhaUsuario(false);
    }
  }, [
    apiBaseUrl,
    authConfig,
    getErrorMessage,
    canManageUsuarios,
    novaSenhaUsuario,
    salvandoSenhaUsuario,
    setMensagem,
  ]);

  const desativarUsuario = useCallback(async (usuarioAlvo) => {
    if (!canManageUsuarios || !usuarioAlvo?.id) return;
    setMensagem(null);
    try {
      const res = await axios.delete(`${apiBaseUrl}/api/usuarios/${usuarioAlvo.id}`, authConfig({ timeout: 12000 }));
      setUsuarios((atuais) => atuais.filter((item) => item.id !== usuarioAlvo.id));
      if (usuarioEditando === usuarioAlvo.id) cancelarEdicaoUsuario();
      if (senhaUsuarioEditando === usuarioAlvo.id) cancelarEdicaoSenha();
      await carregarUsuarios();
      setMensagem({ tipo: 'sucesso', texto: res.data.mensagem || 'Usuario desativado com sucesso.' });
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: getErrorMessage(err, 'Erro ao desativar usuÃ¡rio.') });
    }
  }, [
    apiBaseUrl,
    authConfig,
    cancelarEdicaoSenha,
    cancelarEdicaoUsuario,
    canManageUsuarios,
    carregarUsuarios,
    getErrorMessage,
    senhaUsuarioEditando,
    setMensagem,
    usuarioEditando,
  ]);

  return {
    usuarios,
    novoUsuario,
    usuarioTemp,
    usuarioEditando,
    senhaUsuarioEditando,
    novaSenhaUsuario,
    mostrarSenhaUsuario,
    salvandoUsuario,
    salvandoUsuarioEditando,
    salvandoSenhaUsuario,
    setNovoUsuario,
    setUsuarioTemp,
    setNovaSenhaUsuario,
    carregarUsuarios,
    cadastrarUsuario,
    editarUsuario,
    cancelarEdicaoUsuario,
    salvarUsuario,
    iniciarEdicaoSenha,
    cancelarEdicaoSenha,
    alternarMostrarSenhaUsuario,
    salvarSenhaUsuario,
    desativarUsuario,
    resetarFormularioUsuarios,
    limparGestaoUsuarios,
  };
}
