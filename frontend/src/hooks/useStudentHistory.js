import { useCallback, useState } from 'react';
import axios from 'axios';

export function useStudentHistory({
  apiBaseUrl,
  authHeaders,
  mensagemErroApi,
  setMensagem,
}) {
  const [historico, setHistorico] = useState([]);
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);

  const authConfig = useCallback((config = {}) => ({
    ...config,
    headers: { ...(config.headers || {}), ...authHeaders },
  }), [authHeaders]);

  const limparHistorico = useCallback(() => {
    setHistorico([]);
    setCarregandoHistorico(false);
  }, []);

  const carregarHistorico = useCallback(async (matricula) => {
    if (!matricula) return;
    setCarregandoHistorico(true);
    setMensagem(null);
    try {
      const res = await axios.get(`${apiBaseUrl}/api/alunos/historico/${encodeURIComponent(matricula)}`, authConfig({ timeout: 12000 }));
      setHistorico(res.data);
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Não foi possível carregar o histórico.') });
    } finally {
      setCarregandoHistorico(false);
    }
  }, [apiBaseUrl, authConfig, mensagemErroApi, setMensagem]);

  return {
    historico,
    carregandoHistorico,
    carregarHistorico,
    limparHistorico,
  };
}
