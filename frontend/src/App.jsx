import { useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { Search, User, Mail, Hash, Calendar, ShieldCheck, Phone, Edit2, Save, X, LogIn, Briefcase, GraduationCap, Users, CheckCircle2, Moon, Sun, Plus, UserPlus } from 'lucide-react';
import pdLogo from './assets/pd-logo.svg';

const API_BASE = 'http://127.0.0.1:5000/api';
const MONITORES = ['Alex', 'André', 'Douglas', 'Gabriel', 'Kellen', 'Natanael'];
const STATUS_OPTIONS = ['MANTER', 'EM ANÁLISE', 'REMOVIDO', 'DESLIGADO'];
const TABS = ['Dados principais', 'Perfil do aluno', 'Histórico'];

const PERFIL_INICIAL = (matricula = '') => ({
  matricula,
  analise_perfil: '',
  trabalha: null,
  trabalho_descricao: '',
  turno_trabalho: '',
  estuda: null,
  estudo_instituicao: '',
  estudo_curso: '',
  turno_estudo: '',
  tem_filhos: null,
  filhos_descricao: '',
  nivel_engajamento: '',
  nivel_programacao: '',
  previsao_formacao_ano: '',
  previsao_formacao_semestre: '',
  monitoria_1: false,
  monitoria_2: false,
  monitoria_3: false,
  monitoria_4: false,
  dia_monitoria: '',
  horario_monitoria: '',
  acompanhamento_psicologico: null,
  psicologo: '',
});

const STATUS_COLORS = {
  MANTER: '#1f9d55',
  'EM ANÁLISE': '#d97706',
  REMOVIDO: '#64748b',
  DESLIGADO: '#991b1b',
  '': '#94a3b8',
};

const ENG_COLORS = { baixo: '#b91c1c', médio: '#d97706', medio: '#d97706', alto: '#15803d' };
const PROG_COLORS = { básico: '#0284c7', basico: '#0284c7', intermediário: '#4f46e5', intermediario: '#4f46e5', avançado: '#166534', avancado: '#166534' };

const semAcentos = (valor) => String(valor || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '');

const valorVazio = (valor) => {
  const texto = String(valor ?? '').trim().toLowerCase();
  return !texto || ['-', 'nan', 'none', 'null', 'não informado', 'nao informado'].includes(texto);
};

const normalizarStatus = (status) => {
  if (valorVazio(status)) return '';
  const chave = semAcentos(status).toUpperCase();
  if (['DESLIGAR', 'DESLIGADO', 'DESLIGADA', 'INATIVO', 'CANCELADO'].some((p) => chave.includes(p))) return 'DESLIGADO';
  if (['REMOVIDOS', 'REMOVIDO', 'REMOVER'].some((p) => chave.includes(p))) return 'REMOVIDO';
  if (['EM ANALISE', 'ANALISE'].some((p) => chave.includes(p))) return 'EM ANÁLISE';
  if (['MANTER', 'ATIVO', 'CURSANDO', 'CONTINUA', 'CONTINUAR'].some((p) => chave.includes(p))) return 'MANTER';
  return '';
};

const normalizarMonitor = (monitor) => {
  if (valorVazio(monitor)) return '';
  const local = String(monitor).trim().split('@')[0].replace(/\d+/g, '');
  const chave = semAcentos(local).toLowerCase().replace(/[^a-z]/g, '');
  return MONITORES.find((m) => {
    const monitorChave = semAcentos(m).toLowerCase();
    return chave === monitorChave || chave.startsWith(monitorChave);
  }) || '';
};

const monitorDisplay = (monitor) => normalizarMonitor(monitor) || 'Não informado';
const statusDisplay = (status) => normalizarStatus(status) || 'NÃO INFORMADO';
const getStatusColor = (status) => STATUS_COLORS[normalizarStatus(status)] || STATUS_COLORS[''];
const pillColor = (valor, mapa) => mapa[semAcentos(valor).toLowerCase()] || '#64748b';

const criarTempSeguro = (aluno = {}) => ({
  nome: aluno.nome ?? '',
  telefone: aluno.telefone ?? '',
  email: aluno.email ?? '',
  matricula: aluno.matricula ?? '',
  nascimento: aluno.nascimento ?? '',
  monitor: normalizarMonitor(aluno.monitor),
  status: normalizarStatus(aluno.status),
});

const normalizarPerfil = (perfil = {}) => ({ ...PERFIL_INICIAL(perfil.matricula), ...perfil });

const mensagemErroApi = (err, fallback) => {
  if (!err.response) return 'Não foi possível conectar ao backend. Verifique se o Flask está rodando em http://127.0.0.1:5000.';
  return err.response?.data?.erro || fallback;
};

const formatarData = (valor) => {
  if (!valor) return '-';
  return new Date(valor).toLocaleString('pt-BR');
};

const boolSelectValue = (valor) => (valor === true ? 'sim' : valor === false ? 'nao' : '');
const boolFromSelect = (valor) => (valor === 'sim' ? true : valor === 'nao' ? false : null);
const DIAS_MONITORIA = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira'];
const QTD_FILHOS = ['1', '2', '3', '4', '5', '6+'];
const TURNOS = ['Manhã', 'Tarde', 'Noite', 'Integral', 'Variável', 'EAD'];
const PSICOLOGOS = ['Isabela'];

const parseFilhos = (valor) => {
  if (!valor) return { filhos: [], textoLivre: '' };
  try {
    const parsed = JSON.parse(valor);
    if (Array.isArray(parsed)) {
      return { filhos: parsed.map((filho) => ({ nome: filho.nome || '', idade: filho.idade || '' })), textoLivre: '' };
    }
  } catch {
    return { filhos: [], textoLivre: valor };
  }
  return { filhos: [], textoLivre: String(valor) };
};

const stringifyFilhos = (filhos) => JSON.stringify(filhos.map((filho) => ({ nome: filho.nome || '', idade: filho.idade || '' })));

const quantidadeFromFilhos = (filhos) => {
  if (!filhos.length) return '';
  return filhos.length >= 6 ? '6+' : String(filhos.length);
};

const ajustarQuantidadeFilhos = (quantidade, filhosAtuais) => {
  const total = quantidade === '6+' ? 6 : Number(quantidade || 0);
  return Array.from({ length: total }, (_, index) => filhosAtuais[index] || { nome: '', idade: '' });
};

const filhosResumo = (valor) => {
  const { filhos, textoLivre } = parseFilhos(valor);
  if (filhos.length) {
    return filhos.map((filho, index) => {
      const idade = String(filho.idade || '').trim();
      const sufixoIdade = idade ? `, ${idade} ${Number(idade) === 1 ? 'ano' : 'anos'}` : '';
      return `${index + 1}. ${filho.nome || 'Nome não informado'}${sufixoIdade}`;
    });
  }
  return textoLivre ? [textoLivre] : ['Não informado'];
};

const formatarUsuario = (usuario) => {
  if (!usuario) return '';
  const nome = String(usuario.nome || usuario.email || '').trim();
  if (usuario.role !== 'admin') return nome;
  return nome.toLowerCase() === 'admin' ? 'Admin' : `Admin · ${nome}`;
};

const formatarUsuarioHistorico = (item) => {
  if (!item?.usuario_nome && !item?.usuario_email) return 'Usuário não registrado';
  return `Alterado por ${formatarUsuario({ nome: item.usuario_nome || item.usuario_email, role: item.usuario_role })}`;
};

const styles = {
  container: { width: '100%', maxWidth: '1180px', margin: '0 auto 36px', padding: '18px 24px 36px', fontFamily: '"Inter", sans-serif', boxSizing: 'border-box' },
  header: { marginBottom: '14px' },
  logo: { width: 'min(210px, 58vw)', maxHeight: '64px', objectFit: 'contain', display: 'block', margin: '0 auto 4px' },
  title: { fontSize: '30px', fontWeight: '850', color: '#243447', margin: 0, lineHeight: 1.05 },
  subtitle: { color: '#64748b', fontSize: '15px', marginTop: '4px' },
  hero: { textAlign: 'center', background: '#fff', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '18px 22px', boxShadow: '0 8px 24px rgba(15,23,42,0.05)', marginBottom: '14px' },
  searchBox: { display: 'flex', alignItems: 'center', gap: '10px', background: '#fff', padding: '8px 8px 8px 14px', borderRadius: '14px', boxShadow: '0 4px 15px rgba(15,23,42,0.06)', border: '1px solid #e2e8f0', marginBottom: '18px' },
  searchInput: { flex: 1, minWidth: 0, border: 'none', padding: '11px 8px', fontSize: '16px', outline: 'none', color: '#1a1a1a', backgroundColor: '#fff', colorScheme: 'light' },
  primaryBtn: { background: '#2563eb', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: '10px', fontWeight: '800', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center' },
  neutralBtn: { background: '#fff', color: '#1e293b', border: '1px solid #cbd5e1', padding: '10px 14px', borderRadius: '10px', cursor: 'pointer', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center' },
  iconBtn: { width: '38px', height: '38px', padding: 0, borderRadius: '10px', background: '#fff', color: '#334155', border: '1px solid #cbd5e1', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' },
  secondaryBtn: { background: '#fff', color: '#1e293b', border: '1px solid #cbd5e1', padding: '10px 14px', borderRadius: '10px', cursor: 'pointer', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center' },
  message: { marginBottom: '18px', padding: '12px 14px', borderRadius: '10px', fontSize: '14px', fontWeight: '700', textAlign: 'left' },
  results: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '10px', marginBottom: '18px' },
  resultBtn: { background: '#fff', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '12px', textAlign: 'left', cursor: 'pointer', color: '#334155' },
  card: { background: '#fff', borderRadius: '16px', padding: '22px', boxShadow: '0 10px 28px rgba(15,23,42,0.08)', position: 'relative' },
  cardHeader: { display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '14px', paddingBottom: '14px', borderBottom: '1px solid #e2e8f0' },
  avatar: { width: '50px', height: '50px', borderRadius: '13px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  headerInfo: { flex: 1, minWidth: 0, textAlign: 'left' },
  nome: { fontSize: '23px', fontWeight: '850', color: '#0f172a', margin: 0, overflowWrap: 'anywhere', lineHeight: 1.14 },
  badge: { marginTop: '6px', padding: '5px 10px', borderRadius: '999px', fontSize: '10px', fontWeight: '850', display: 'inline-flex', alignItems: 'center', textTransform: 'uppercase' },
  actions: { display: 'flex', gap: '10px', marginLeft: 'auto', alignItems: 'center', flexShrink: 0, flexWrap: 'wrap' },
  tabs: { display: 'flex', gap: '6px', overflowX: 'auto', padding: '3px', marginBottom: '14px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px' },
  tab: { border: 'none', background: 'transparent', color: '#475569', padding: '9px 12px', borderRadius: '9px', fontWeight: 850, cursor: 'pointer', whiteSpace: 'nowrap' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '12px' },
  profileGrid: { display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '12px' },
  section: { background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '14px', textAlign: 'left' },
  infoItem: { background: '#f8fafc', padding: '15px', borderRadius: '12px', display: 'flex', gap: '12px', border: '1px solid #e2e8f0', textAlign: 'left', minWidth: 0 },
  label: { fontSize: '10px', textTransform: 'uppercase', color: '#64748b', fontWeight: '800', display: 'block', marginBottom: '6px' },
  val: { fontSize: '15px', fontWeight: '650', color: '#334155', overflowWrap: 'anywhere' },
  fieldInput: { width: '100%', boxSizing: 'border-box', minHeight: '42px', padding: '10px 12px', borderRadius: '9px', border: '1px solid #cbd5e1', backgroundColor: '#fff', color: '#1a1a1a', fontSize: '14px', outline: 'none', colorScheme: 'light' },
  textarea: { width: '100%', boxSizing: 'border-box', minHeight: '120px', padding: '10px 12px', borderRadius: '9px', border: '1px solid #cbd5e1', backgroundColor: '#fff', color: '#1a1a1a', fontSize: '14px', outline: 'none', resize: 'vertical' },
  editInputName: { fontSize: '22px', fontWeight: '800', border: '1px solid #cbd5e1', borderRadius: '10px', padding: '9px 11px', width: '100%', boxSizing: 'border-box', color: '#0f172a', backgroundColor: '#fff', colorScheme: 'light' },
  loginBox: { maxWidth: '420px', margin: '90px auto', background: '#fff', border: '1px solid #e2e8f0', borderRadius: '18px', padding: '28px', boxShadow: '0 10px 30px rgba(15,23,42,0.08)' },
};

export default function App() {
  const [usuario, setUsuario] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('pd_user') || 'null');
    } catch {
      return null;
    }
  });
  const [loginEmail, setLoginEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [tema, setTema] = useState(() => localStorage.getItem('pd_theme') || 'light');
  const [alunos, setAlunos] = useState([]);
  const [busca, setBusca] = useState('');
  const [aluno, setAluno] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [temp, setTemp] = useState(criarTempSeguro());
  const [activeTab, setActiveTab] = useState('Dados principais');
  const [perfil, setPerfil] = useState(PERFIL_INICIAL());
  const [perfilTemp, setPerfilTemp] = useState(PERFIL_INICIAL());
  const [editPerfil, setEditPerfil] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [salvandoPerfil, setSalvandoPerfil] = useState(false);
  const [buscando, setBuscando] = useState(false);
  const [mensagem, setMensagem] = useState(null);
  const [historico, setHistorico] = useState([]);
  const [carregandoHistorico, setCarregandoHistorico] = useState(false);
  const [buscaRealizada, setBuscaRealizada] = useState(false);
  const [mostrarNovoAluno, setMostrarNovoAluno] = useState(false);
  const [mostrarUsuarios, setMostrarUsuarios] = useState(false);
  const [usuarios, setUsuarios] = useState([]);
  const [novoAluno, setNovoAluno] = useState({ nome: '', matricula: '', telefone: '', email: '', nascimento: '', monitor: '', status: 'MANTER' });
  const [novoUsuario, setNovoUsuario] = useState({ nome: '', email: '', senha: '', role: 'monitor' });
  const [salvandoNovoAluno, setSalvandoNovoAluno] = useState(false);
  const [salvandoUsuario, setSalvandoUsuario] = useState(false);
  const cardRef = useRef(null);
  const autenticado = Boolean(usuario);
  const isAdmin = usuario?.role === 'admin';
  const usuarioPayload = usuario ? {
    usuario_nome: usuario.nome,
    usuario_email: usuario.email,
    usuario_role: usuario.role,
  } : {};
  const temaEscuro = tema === 'dark';

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

  const estiloMensagem = mensagem?.tipo === 'sucesso'
    ? { background: '#ecfdf5', color: '#166534', border: '1px solid #bbf7d0' }
    : { background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca' };

  const buscarPerfilAluno = async (matricula) => {
    const res = await axios.get(`${API_BASE}/alunos/perfil/${encodeURIComponent(matricula)}`, { timeout: 12000 });
    const dados = normalizarPerfil(res.data);
    setPerfil(dados);
    setPerfilTemp(dados);
    return dados;
  };

  const salvarPerfilAluno = async () => {
    if (!aluno || salvandoPerfil) return;
    setSalvandoPerfil(true);
    setMensagem(null);
    try {
      const payload = { ...perfilTemp, matricula: aluno.matricula, ...usuarioPayload };
      const res = await axios.post(`${API_BASE}/alunos/perfil/update`, payload, { timeout: 12000 });
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
  };

  const carregarHistorico = async (matricula = aluno?.matricula) => {
    if (!matricula) return;
    setCarregandoHistorico(true);
    setMensagem(null);
    try {
      const res = await axios.get(`${API_BASE}/alunos/historico/${encodeURIComponent(matricula)}`, { timeout: 12000 });
      setHistorico(res.data);
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Não foi possível carregar o histórico.') });
    } finally {
      setCarregandoHistorico(false);
    }
  };

  const selecionarTab = (tab) => {
    setActiveTab(tab);
    if (tab === 'Perfil do aluno' && aluno) buscarPerfilAluno(aluno.matricula);
    if (tab === 'Histórico' && aluno) carregarHistorico(aluno.matricula);
  };

  const atualizarAlunoLocal = (atualizado) => {
    setAlunos((atuais) => atuais.map((a) => (a.matricula === atualizado.matricula ? atualizado : a)));
    setAluno(atualizado);
    setTemp(criarTempSeguro(atualizado));
  };

  const carregarAlunos = async (termo = '') => {
    if (!termo) {
      setAlunos([]);
      setAluno(null);
      return;
    }
    setBuscando(true);
    setMensagem(null);
    try {
      const res = await axios.get(`${API_BASE}/alunos`, { params: { q: termo }, timeout: 12000 });
      setAlunos(res.data);
      if (res.data.length === 0) {
        setAluno(null);
        setMensagem({ tipo: 'erro', texto: 'Nenhum aluno encontrado' });
      }
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Não foi possível buscar alunos.') });
    } finally {
      setBuscando(false);
    }
  };

  const login = async (e) => {
    e.preventDefault();
    setMensagem(null);
    try {
      const res = await axios.post(`${API_BASE}/login`, { email: loginEmail, senha }, { timeout: 12000 });
      localStorage.setItem('pd_user', JSON.stringify(res.data.usuario));
      localStorage.removeItem('pd_auth');
      setUsuario(res.data.usuario);
      setLoginEmail('');
      setSenha('');
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'E-mail ou senha inválidos.') });
    }
  };

  const alternarTema = () => {
    const proximoTema = temaEscuro ? 'light' : 'dark';
    setTema(proximoTema);
    localStorage.setItem('pd_theme', proximoTema);
  };

  const sair = () => {
    localStorage.removeItem('pd_user');
    localStorage.removeItem('pd_auth');
    setUsuario(null);
    setAluno(null);
    setAlunos([]);
    setBuscaRealizada(false);
  };

  const fecharAlunoSelecionado = () => {
    setAluno(null);
    setEditMode(false);
    setEditPerfil(false);
    setActiveTab('Dados principais');
    setHistorico([]);
  };

  const abrirNovoAluno = () => {
    fecharAlunoSelecionado();
    setMostrarUsuarios(false);
    setMostrarNovoAluno(true);
    setMensagem(null);
  };

  const abrirUsuarios = async () => {
    fecharAlunoSelecionado();
    setMostrarNovoAluno(false);
    await carregarUsuarios();
  };

  const carregarUsuarios = async () => {
    if (!isAdmin) return;
    setMensagem(null);
    try {
      const res = await axios.get(`${API_BASE}/usuarios`, { params: usuarioPayload, timeout: 12000 });
      setUsuarios(res.data);
      setMostrarUsuarios(true);
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Não foi possível carregar usuários.') });
    }
  };

  const cadastrarUsuario = async (e) => {
    e.preventDefault();
    if (!isAdmin || salvandoUsuario) return;
    setSalvandoUsuario(true);
    setMensagem(null);
    try {
      const res = await axios.post(`${API_BASE}/usuarios/create`, { ...novoUsuario, ...usuarioPayload }, { timeout: 12000 });
      setUsuarios((atuais) => [...atuais, res.data.usuario].sort((a, b) => String(a.nome).localeCompare(String(b.nome), 'pt-BR')));
      setNovoUsuario({ nome: '', email: '', senha: '', role: 'monitor' });
      setMensagem({ tipo: 'sucesso', texto: res.data.mensagem || 'Usuário cadastrado com sucesso.' });
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Erro ao cadastrar usuário.') });
    } finally {
      setSalvandoUsuario(false);
    }
  };

  const cadastrarAluno = async (e) => {
    e.preventDefault();
    if (!isAdmin || salvandoNovoAluno) return;
    setSalvandoNovoAluno(true);
    setMensagem(null);
    try {
      const payload = {
        ...novoAluno,
        monitor: normalizarMonitor(novoAluno.monitor),
        status: normalizarStatus(novoAluno.status),
        ...usuarioPayload,
      };
      const res = await axios.post(`${API_BASE}/alunos/create`, payload, { timeout: 12000 });
      const criado = res.data.aluno;
      setAlunos((atuais) => [...atuais.filter((a) => a.matricula !== criado.matricula), criado]);
      setAluno(criado);
      setTemp(criarTempSeguro(criado));
      setBuscaRealizada(true);
      setMostrarNovoAluno(false);
      setNovoAluno({ nome: '', matricula: '', telefone: '', email: '', nascimento: '', monitor: '', status: 'MANTER' });
      setMensagem({ tipo: 'sucesso', texto: res.data.mensagem || 'Aluno cadastrado com sucesso.' });
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Erro ao cadastrar aluno.') });
    } finally {
      setSalvandoNovoAluno(false);
    }
  };

  const buscar = async (e) => {
    e.preventDefault();
    setBuscaRealizada(true);
    await carregarAlunos(busca.trim());
    setEditMode(false);
    setActiveTab('Dados principais');
  };

  const selecionarAluno = (selecionado) => {
    setMostrarNovoAluno(false);
    setMostrarUsuarios(false);
    setAluno(selecionado);
    setTemp(criarTempSeguro(selecionado));
    setPerfil(PERFIL_INICIAL(selecionado.matricula));
    setPerfilTemp(PERFIL_INICIAL(selecionado.matricula));
    setEditMode(false);
    setEditPerfil(false);
    setActiveTab('Dados principais');
    setHistorico([]);
    setMensagem(null);
    requestAnimationFrame(() => cardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  };

  const salvar = async () => {
    if (salvando) return;
    setSalvando(true);
    setMensagem(null);
    try {
      const payload = { ...temp, monitor: normalizarMonitor(temp.monitor), status: normalizarStatus(temp.status), ...usuarioPayload };
      const res = await axios.post(`${API_BASE}/alunos/update`, payload, { timeout: 12000 });
      atualizarAlunoLocal(res.data.aluno || payload);
      setEditMode(false);
      setMensagem({ tipo: 'sucesso', texto: res.data.mensagem || 'Aluno atualizado com sucesso.' });
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Erro ao salvar o aluno.') });
    } finally {
      setSalvando(false);
    }
  };

  const cancelarEdicao = () => {
    setTemp(criarTempSeguro(aluno || {}));
    setEditMode(false);
  };

  if (!autenticado) {
    return (
      <div className={temaEscuro ? 'theme-dark app-shell' : 'theme-light app-shell'} style={styles.container}>
        <form className="login-box" onSubmit={login} style={styles.loginBox}>
          <img src={pdLogo} alt="PD Reports" className="pd-logo" style={styles.logo} />
          <h1 style={{ ...styles.title, textAlign: 'left' }}>PD Reports</h1>
          <p style={{ ...styles.subtitle, textAlign: 'left', marginBottom: '18px' }}>Gestão de Alunos</p>
          <input type="email" style={{ ...styles.fieldInput, marginBottom: '12px' }} placeholder="E-mail" value={loginEmail} onChange={(e) => setLoginEmail(e.target.value)} />
          <input type="password" style={{ ...styles.fieldInput, marginBottom: '12px' }} placeholder="Senha" value={senha} onChange={(e) => setSenha(e.target.value)} />
          <button className="ui-button" type="submit" style={{ ...styles.primaryBtn, width: '100%' }}><LogIn size={18} /> Entrar</button>
          <button className="ui-button theme-toggle-login" type="button" onClick={alternarTema} style={{ ...styles.secondaryBtn, width: '100%', marginTop: '10px' }}>
            {temaEscuro ? <Sun size={17} /> : <Moon size={17} />} {temaEscuro ? 'Tema claro' : 'Tema escuro'}
          </button>
          {mensagem && <div style={{ ...styles.message, ...estiloMensagem, marginTop: '14px', marginBottom: 0 }}>{mensagem.texto}</div>}
        </form>
      </div>
    );
  }

  const statusAtual = editMode ? temp.status : aluno?.status;
  const corStatus = getStatusColor(statusAtual);

  return (
    <div className={temaEscuro ? 'theme-dark app-shell' : 'theme-light app-shell'} style={styles.container}>
      <header className="app-header" style={styles.header}>
        <div className="header-user">
          <span className="user-chip">{formatarUsuario(usuario)}</span>
        </div>
        <div className="brand-block">
          <img src={pdLogo} alt="PD Reports" className="pd-logo" style={styles.logo} />
          <h1 style={styles.title}>PD Reports</h1>
          <p style={styles.subtitle}>Gestão de Alunos</p>
        </div>
        <div className="header-controls">
          <button className="ui-button icon-button" type="button" title="Alternar tema" aria-label="Alternar tema" onClick={alternarTema} style={styles.iconBtn}>
            {temaEscuro ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button className="ui-button logout-button" type="button" onClick={sair} style={styles.neutralBtn}>Sair</button>
        </div>
      </header>

      {isAdmin && (
        <div className="main-actions">
          <button className="ui-button" type="button" onClick={abrirNovoAluno} style={styles.neutralBtn}><Plus size={17} /> Novo aluno</button>
          <button className="ui-button" type="button" onClick={abrirUsuarios} style={styles.neutralBtn}><UserPlus size={17} /> Usuários</button>
        </div>
      )}

      <form className="search-form" onSubmit={buscar} style={styles.searchBox}>
        <Search size={20} color="#64748b" />
        <input style={styles.searchInput} placeholder="Buscar por nome, matrícula, e-mail ou telefone..." value={busca} onChange={(e) => setBusca(e.target.value)} />
        <button className="ui-button" type="submit" disabled={buscando} style={{ ...styles.primaryBtn, opacity: buscando ? 0.75 : 1 }}>
          {buscando ? 'Buscando...' : 'Buscar'}
        </button>
      </form>

      {mensagem && <div style={{ ...styles.message, ...estiloMensagem }}>{mensagem.texto}</div>}

      {isAdmin && mostrarNovoAluno && (
        <form className="admin-panel" onSubmit={cadastrarAluno} style={styles.section}>
          <div className="panel-title-row">
            <h2>Novo aluno</h2>
            <button className="ui-button" type="button" onClick={() => setMostrarNovoAluno(false)} style={styles.secondaryBtn}><X size={17} /></button>
          </div>
          <div className="admin-grid">
            <ProfileField label="Nome *" value={novoAluno.nome} onChange={(v) => setNovoAluno({ ...novoAluno, nome: v })} />
            <ProfileField label="Matrícula *" value={novoAluno.matricula} onChange={(v) => setNovoAluno({ ...novoAluno, matricula: v })} />
            <ProfileField label="Telefone" value={novoAluno.telefone} onChange={(v) => setNovoAluno({ ...novoAluno, telefone: v })} />
            <ProfileField label="E-mail" type="email" value={novoAluno.email} onChange={(v) => setNovoAluno({ ...novoAluno, email: v })} />
            <ProfileField label="Nascimento" type="date" value={novoAluno.nascimento} onChange={(v) => setNovoAluno({ ...novoAluno, nascimento: v })} />
            <ProfileSelect label="Monitor" value={novoAluno.monitor} onChange={(v) => setNovoAluno({ ...novoAluno, monitor: v })} options={[['', 'Selecione...'], ...MONITORES.map((m) => [m, m])]} />
            <ProfileSelect label="Status *" value={novoAluno.status} onChange={(v) => setNovoAluno({ ...novoAluno, status: v })} options={STATUS_OPTIONS.map((s) => [s, s])} />
          </div>
          <button className="ui-button" type="submit" disabled={salvandoNovoAluno} style={{ ...styles.primaryBtn, marginTop: '14px' }}>
            <Save size={17} /> {salvandoNovoAluno ? 'Salvando...' : 'Cadastrar aluno'}
          </button>
        </form>
      )}

      {isAdmin && mostrarUsuarios && (
        <section className="admin-panel" style={styles.section}>
          <div className="panel-title-row">
            <h2>Usuários</h2>
            <button className="ui-button" type="button" onClick={() => setMostrarUsuarios(false)} style={styles.secondaryBtn}><X size={17} /></button>
          </div>
          <form onSubmit={cadastrarUsuario} className="admin-grid">
            <ProfileField label="Nome" value={novoUsuario.nome} onChange={(v) => setNovoUsuario({ ...novoUsuario, nome: v })} />
            <ProfileField label="E-mail" type="email" value={novoUsuario.email} onChange={(v) => setNovoUsuario({ ...novoUsuario, email: v })} />
            <ProfileField label="Senha" type="password" value={novoUsuario.senha} onChange={(v) => setNovoUsuario({ ...novoUsuario, senha: v })} />
            <ProfileSelect label="Perfil" value={novoUsuario.role} onChange={(v) => setNovoUsuario({ ...novoUsuario, role: v })} options={[['monitor', 'Monitor'], ['admin', 'Admin']]} />
            <button className="ui-button" type="submit" disabled={salvandoUsuario} style={styles.primaryBtn}>
              <Save size={17} /> {salvandoUsuario ? 'Salvando...' : 'Cadastrar usuário'}
            </button>
          </form>
          <div className="users-list">
            {usuarios.map((u) => <span key={u.id || u.email}>{u.nome} · {u.email} · {u.role}</span>)}
          </div>
        </section>
      )}

      {aluno && (
        <div ref={cardRef} className="student-card" style={{ ...styles.card, borderLeft: `8px solid ${corStatus}`, marginBottom: '18px' }}>
          <button className="ui-button card-close" type="button" onClick={fecharAlunoSelecionado} aria-label="Fechar aluno selecionado" style={styles.iconBtn}><X size={17} /></button>
          <div className="student-card-header" style={styles.cardHeader}>
            <div style={{ ...styles.avatar, backgroundColor: `${corStatus}18` }}>
              <User size={30} color={corStatus} />
            </div>
            <div style={styles.headerInfo}>
              {editMode ? <input style={styles.editInputName} value={temp.nome || ''} onChange={(e) => setTemp({ ...temp, nome: e.target.value })} /> : <h2 style={styles.nome}>{aluno.nome}</h2>}
              <span style={{ ...styles.badge, color: corStatus, backgroundColor: `${corStatus}12`, border: `1px solid ${corStatus}35` }}>{statusDisplay(statusAtual)}</span>
            </div>
          </div>

          <div style={styles.tabs}>
            {TABS.map((tab) => (
              <button key={tab} className="ui-button" type="button" onClick={() => selecionarTab(tab)} style={{ ...styles.tab, background: activeTab === tab ? '#fff' : 'transparent', color: activeTab === tab ? '#0f172a' : '#64748b', boxShadow: activeTab === tab ? '0 1px 4px rgba(15,23,42,0.08)' : 'none' }}>{tab}</button>
            ))}
          </div>

          {activeTab === 'Dados principais' && (
            <DadosPrincipais
              aluno={aluno}
              temp={temp}
              setTemp={setTemp}
              editMode={editMode}
              setEditMode={setEditMode}
              salvar={salvar}
              cancelarEdicao={cancelarEdicao}
              salvando={salvando}
              corStatus={corStatus}
            />
          )}

          {activeTab === 'Perfil do aluno' && (
            <PerfilAluno
              perfil={perfil}
              perfilTemp={perfilTemp}
              setPerfilTemp={setPerfilTemp}
              editPerfil={editPerfil}
              setEditPerfil={setEditPerfil}
              salvarPerfilAluno={salvarPerfilAluno}
              salvandoPerfil={salvandoPerfil}
            />
          )}

          {activeTab === 'Histórico' && (
            <Historico historico={historico} carregandoHistorico={carregandoHistorico} />
          )}
        </div>
      )}

      {buscaRealizada && resultadosVisiveis.length > 0 && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: '#334155', margin: 0 }}>Resultados</h2>
            <span style={{ fontSize: '13px', color: '#64748b', fontWeight: 700 }}>{alunosOrdenados.length} aluno(s)</span>
          </div>
          <div style={styles.results}>
            {resultadosVisiveis.map((item) => {
              const selecionado = aluno?.matricula === item.matricula;
              const itemColor = getStatusColor(item.status);
              return (
                <button className={`result-button${selecionado ? ' selected' : ''}`} type="button" key={item.matricula || item.id} style={{ ...styles.resultBtn, borderColor: selecionado ? itemColor : '#e2e8f0', backgroundColor: selecionado ? `${itemColor}0d` : '#fff' }} onClick={() => selecionarAluno(item)}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px' }}>
                    <strong style={{ color: '#0f172a', lineHeight: 1.25 }}>{item.nome}</strong>
                    <span style={{ flexShrink: 0, color: itemColor, background: `${itemColor}14`, border: `1px solid ${itemColor}35`, borderRadius: '999px', padding: '3px 8px', fontSize: '10px', fontWeight: 900 }}>{statusDisplay(item.status)}</span>
                  </div>
                  <div style={{ fontSize: '13px', marginTop: '8px', color: '#475569' }}>{item.matricula}</div>
                  <div style={{ fontSize: '13px', marginTop: '3px', color: '#64748b' }}>Monitor: {monitorDisplay(item.monitor)}</div>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

function DadosPrincipais({ aluno, temp, setTemp, editMode, setEditMode, salvar, cancelarEdicao, salvando, corStatus }) {
  return (
    <>
      <div style={{ ...styles.actions, marginLeft: 0, marginBottom: '14px' }}>
        {editMode ? (
          <>
            <button className="ui-button" type="button" onClick={salvar} disabled={salvando} style={{ ...styles.primaryBtn, background: '#166534', opacity: salvando ? 0.75 : 1 }}><Save size={18} /> {salvando ? 'Salvando...' : 'Salvar'}</button>
            <button className="ui-button" type="button" onClick={cancelarEdicao} disabled={salvando} style={styles.secondaryBtn}><X size={18} /></button>
          </>
        ) : (
          <button className="ui-button" type="button" onClick={() => setEditMode(true)} style={styles.secondaryBtn}><Edit2 size={18} /> Editar</button>
        )}
      </div>
      <div className="student-grid" style={styles.grid}>
        <InfoItem icon={<Hash size={18} color={corStatus} />} label="Matrícula" value={aluno.matricula} />
        <FieldItem icon={<Phone size={18} color={corStatus} />} label="Telefone" editMode={editMode} value={temp.telefone} display={aluno.telefone} onChange={(v) => setTemp({ ...temp, telefone: v })} />
        <FieldItem full icon={<Mail size={18} color={corStatus} />} label="E-mail" editMode={editMode} value={temp.email} display={aluno.email} onChange={(v) => setTemp({ ...temp, email: v })} />
        <FieldItem icon={<Calendar size={18} color={corStatus} />} label="Nascimento e Idade" type="date" editMode={editMode} value={temp.nascimento} display={`${aluno.nascimento_formatado} ${aluno.idade !== '-' ? `(${aluno.idade} anos)` : ''}`} onChange={(v) => setTemp({ ...temp, nascimento: v })} />
        <div style={styles.infoItem}>
          <ShieldCheck size={18} color={corStatus} />
          <div style={{ width: '100%', minWidth: 0 }}>
            <span style={styles.label}>Monitor Responsável</span>
            {editMode ? <select style={styles.fieldInput} value={temp.monitor || ''} onChange={(e) => setTemp({ ...temp, monitor: e.target.value })}><option value="">Selecione...</option>{MONITORES.map((m) => <option key={m} value={m}>{m}</option>)}</select> : <span style={styles.val}>{monitorDisplay(aluno.monitor)}</span>}
          </div>
        </div>
        <div style={styles.infoItem}>
          <CheckCircle2 size={18} color={corStatus} />
          <div style={{ width: '100%', minWidth: 0 }}>
            <span style={styles.label}>Status</span>
            {editMode ? <select style={styles.fieldInput} value={temp.status || ''} onChange={(e) => setTemp({ ...temp, status: e.target.value })}><option value="">NÃO INFORMADO</option>{STATUS_OPTIONS.map((status) => <option key={status} value={status}>{status}</option>)}</select> : <span style={styles.val}>{statusDisplay(aluno.status)}</span>}
          </div>
        </div>
      </div>
    </>
  );
}

function PerfilAluno({ perfil, perfilTemp, setPerfilTemp, editPerfil, setEditPerfil, salvarPerfilAluno, salvandoPerfil }) {
  const p = editPerfil ? perfilTemp : perfil;
  const setCampo = (campo, valor) => setPerfilTemp({ ...perfilTemp, [campo]: valor });
  const filhosInfo = parseFilhos(p.filhos_descricao);
  const filhos = filhosInfo.filhos;
  const setFilhos = (novosFilhos) => setCampo('filhos_descricao', stringifyFilhos(novosFilhos));

  if (!editPerfil) {
    return (
      <>
        <div style={{ ...styles.actions, marginLeft: 0, marginBottom: '14px' }}>
          <button className="ui-button" type="button" onClick={() => setEditPerfil(true)} style={styles.secondaryBtn}><Edit2 size={18} /> Editar perfil</button>
        </div>
        <div style={styles.profileGrid} className="profile-grid">
          <section style={{ ...styles.section, gridColumn: '1 / -1' }}>
            <h3><User size={18} /> Breve análise de perfil</h3>
            <p className="profile-text">{p.analise_perfil || 'Não informado'}</p>
          </section>
          <section style={styles.section}>
            <h3><Briefcase size={18} /> Trabalho e Estudos</h3>
            <DisplayItem label="Trabalha?" value={p.trabalha === true ? 'Sim' : p.trabalha === false ? 'Não' : 'Não informado'} />
            <DisplayItem label="Com o que trabalha?" value={p.trabalho_descricao} />
            {p.trabalha === true && <DisplayItem label="Turno de trabalho" value={p.turno_trabalho} />}
            <DisplayItem label="Estuda?" value={p.estuda === true ? 'Sim' : p.estuda === false ? 'Não' : 'Não informado'} />
            <DisplayItem label="Onde estuda?" value={p.estudo_instituicao} />
            <DisplayItem label="Qual curso?" value={p.estudo_curso} />
            {p.estuda === true && <DisplayItem label="Turno de estudo" value={p.turno_estudo} />}
          </section>
          <section style={styles.section}>
            <h3><Users size={18} /> Família</h3>
            <DisplayItem label="Tem filhos?" value={p.tem_filhos === true ? 'Sim' : p.tem_filhos === false ? 'Não' : 'Não informado'} />
            {p.tem_filhos === true ? (
              <div className="children-list">
                {filhosResumo(p.filhos_descricao).map((linha) => <strong key={linha}>{linha}</strong>)}
              </div>
            ) : (
              <DisplayItem label="Filhos" value="Não informado" />
            )}
          </section>
          <section style={styles.section}>
            <h3><GraduationCap size={18} /> Curso</h3>
            <div className="profile-badge-row">
              <ProfileBadge label="Nível de Engajamento" value={p.nivel_engajamento} color={pillColor(p.nivel_engajamento, ENG_COLORS)} />
              <ProfileBadge label="Nível de Conhecimento em Programação" value={p.nivel_programacao} color={pillColor(p.nivel_programacao, PROG_COLORS)} />
            </div>
            <DisplayItem label="Previsão de formação" value={[p.previsao_formacao_ano, p.previsao_formacao_semestre].filter(Boolean).join(' - ')} />
          </section>
          <section style={styles.section}>
            <h3><Calendar size={18} /> Monitorias</h3>
            <div className="mini-card-row">
              <DisplayItem label="Dia" value={p.dia_monitoria} compact />
              <DisplayItem label="Horário" value={p.horario_monitoria} compact />
            </div>
          </section>
          <section style={styles.section}>
            <h3><ShieldCheck size={18} /> Acompanhamento psicológico</h3>
            <DisplayItem label="Faz acompanhamento?" value={p.acompanhamento_psicologico === true ? 'Sim' : p.acompanhamento_psicologico === false ? 'Não' : 'Não informado'} />
            {p.acompanhamento_psicologico === true && <DisplayItem label="Psicólogo responsável" value={p.psicologo} />}
          </section>
        </div>
      </>
    );
  }

  return (
    <>
      <div style={{ ...styles.actions, marginLeft: 0, marginBottom: '14px' }}>
        {editPerfil ? (
          <>
            <button className="ui-button" type="button" onClick={salvarPerfilAluno} disabled={salvandoPerfil} style={{ ...styles.primaryBtn, background: '#166534', opacity: salvandoPerfil ? 0.75 : 1 }}><Save size={18} /> {salvandoPerfil ? 'Salvando...' : 'Salvar perfil'}</button>
            <button className="ui-button" type="button" onClick={() => { setPerfilTemp(perfil); setEditPerfil(false); }} disabled={salvandoPerfil} style={styles.secondaryBtn}><X size={18} /></button>
          </>
        ) : (
          <button className="ui-button" type="button" onClick={() => setEditPerfil(true)} style={styles.secondaryBtn}><Edit2 size={18} /> Editar perfil</button>
        )}
      </div>
      <div style={styles.profileGrid} className="profile-grid">
        <section style={{ ...styles.section, gridColumn: '1 / -1' }}>
          <h3><User size={18} /> Breve análise de perfil</h3>
          {editPerfil ? <textarea style={styles.textarea} value={p.analise_perfil || ''} onChange={(e) => setCampo('analise_perfil', e.target.value)} /> : <p>{p.analise_perfil || 'Não informado'}</p>}
        </section>
        <section style={styles.section}>
          <h3><Briefcase size={18} /> Trabalho e Estudos</h3>
          <ProfileSelect label="Trabalha?" value={boolSelectValue(p.trabalha)} disabled={!editPerfil} onChange={(v) => setCampo('trabalha', boolFromSelect(v))} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
          {p.trabalha === true && (
            <>
              <ProfileField label="Com o que trabalha?" value={p.trabalho_descricao} disabled={!editPerfil} onChange={(v) => setCampo('trabalho_descricao', v)} />
              <ProfileSelect label="Turno de trabalho" value={p.turno_trabalho || ''} disabled={!editPerfil} onChange={(v) => setCampo('turno_trabalho', v)} options={[['', 'Não informado'], ...TURNOS.map((turno) => [turno, turno])]} />
            </>
          )}
          <ProfileSelect label="Estuda?" value={boolSelectValue(p.estuda)} disabled={!editPerfil} onChange={(v) => setCampo('estuda', boolFromSelect(v))} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
          {p.estuda === true && (
            <>
              <ProfileField label="Onde estuda?" value={p.estudo_instituicao} disabled={!editPerfil} onChange={(v) => setCampo('estudo_instituicao', v)} />
              <ProfileField label="Qual curso?" value={p.estudo_curso} disabled={!editPerfil} onChange={(v) => setCampo('estudo_curso', v)} />
              <ProfileSelect label="Turno de estudo" value={p.turno_estudo || ''} disabled={!editPerfil} onChange={(v) => setCampo('turno_estudo', v)} options={[['', 'Não informado'], ...TURNOS.map((turno) => [turno, turno])]} />
            </>
          )}
        </section>
        <section style={styles.section}>
          <h3><Users size={18} /> Família</h3>
          <ProfileSelect label="Tem filhos?" value={boolSelectValue(p.tem_filhos)} disabled={!editPerfil} onChange={(v) => {
            const temFilhos = boolFromSelect(v);
            setPerfilTemp({ ...perfilTemp, tem_filhos: temFilhos, filhos_descricao: temFilhos === true ? perfilTemp.filhos_descricao : '' });
          }} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
          {p.tem_filhos === true && (
            <>
              <ProfileSelect
                label="Quantidade de filhos"
                value={quantidadeFromFilhos(filhos)}
                disabled={!editPerfil}
                onChange={(v) => setFilhos(ajustarQuantidadeFilhos(v, filhos))}
                options={[['', 'Selecione...'], ...QTD_FILHOS.map((qtd) => [qtd, qtd])]}
              />
              <div className="children-editor">
                {filhos.map((filho, index) => (
                  <div key={index} className="child-row">
                    <ProfileField label={`Nome do filho ${index + 1}`} value={filho.nome} disabled={!editPerfil} onChange={(v) => {
                      const novos = [...filhos];
                      novos[index] = { ...novos[index], nome: v };
                      setFilhos(novos);
                    }} />
                    <ProfileField label="Idade" value={filho.idade} disabled={!editPerfil} onChange={(v) => {
                      const novos = [...filhos];
                      novos[index] = { ...novos[index], idade: v };
                      setFilhos(novos);
                    }} />
                  </div>
                ))}
              </div>
              {filhosInfo.textoLivre && <p className="legacy-note">Dado antigo: {filhosInfo.textoLivre}</p>}
            </>
          )}
        </section>
        <section style={styles.section}>
          <h3><GraduationCap size={18} /> Curso</h3>
          <ProfileSelect label="Nível de Engajamento" value={p.nivel_engajamento || ''} disabled={!editPerfil} onChange={(v) => setCampo('nivel_engajamento', v)} options={[['', 'Não informado'], ['baixo', 'Baixo'], ['médio', 'Médio'], ['alto', 'Alto']]} color={pillColor(p.nivel_engajamento, ENG_COLORS)} />
          <ProfileSelect label="Nível de Conhecimento em Programação" value={p.nivel_programacao || ''} disabled={!editPerfil} onChange={(v) => setCampo('nivel_programacao', v)} options={[['', 'Não informado'], ['básico', 'Básico'], ['intermediário', 'Intermediário'], ['avançado', 'Avançado']]} color={pillColor(p.nivel_programacao, PROG_COLORS)} />
          <ProfileField label="Ano de previsão de formação" type="number" value={p.previsao_formacao_ano || ''} disabled={!editPerfil} onChange={(v) => setCampo('previsao_formacao_ano', v)} />
          <ProfileSelect label="Semestre de previsão" value={p.previsao_formacao_semestre || ''} disabled={!editPerfil} onChange={(v) => setCampo('previsao_formacao_semestre', v)} options={[['', 'Não informado'], ['1º semestre', '1º semestre'], ['2º semestre', '2º semestre']]} />
        </section>
        <section style={styles.section}>
          <h3><Calendar size={18} /> Monitorias</h3>
          <ProfileSelect label="Dia da monitoria" value={p.dia_monitoria || ''} disabled={!editPerfil} onChange={(v) => setCampo('dia_monitoria', v)} options={[['', 'Não informado'], ...DIAS_MONITORIA.map((dia) => [dia, dia])]} />
          <ProfileField label="Horário da monitoria" type="time" value={p.horario_monitoria} disabled={!editPerfil} onChange={(v) => setCampo('horario_monitoria', v)} />
        </section>
        <section style={styles.section}>
          <h3><ShieldCheck size={18} /> Acompanhamento psicológico</h3>
          <ProfileSelect label="Faz acompanhamento?" value={boolSelectValue(p.acompanhamento_psicologico)} disabled={!editPerfil} onChange={(v) => {
            const faz = boolFromSelect(v);
            setPerfilTemp({ ...perfilTemp, acompanhamento_psicologico: faz, psicologo: faz === true ? perfilTemp.psicologo : '' });
          }} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
          {p.acompanhamento_psicologico === true && (
            <ProfileSelect label="Psicólogo responsável" value={p.psicologo || ''} disabled={!editPerfil} onChange={(v) => setCampo('psicologo', v)} options={[['', 'Selecione...'], ...PSICOLOGOS.map((nome) => [nome, nome])]} />
          )}
        </section>
      </div>
    </>
  );
}

function Historico({ historico, carregandoHistorico }) {
  return (
    <div style={styles.section}>
      <strong>Histórico de alterações</strong>
      {carregandoHistorico && <p style={{ marginTop: '10px' }}>Carregando histórico...</p>}
      {!carregandoHistorico && historico.length === 0 && <p style={{ marginTop: '10px' }}>Nenhuma alteração registrada.</p>}
      {!carregandoHistorico && historico.map((item) => (
        <div key={item.id} className="history-card">
          <strong>{String(item.campo || '').replace('perfil.', 'Perfil · ').replaceAll('_', ' ')}</strong>
          <div className="history-values">
            <span>{item.valor_antigo || 'vazio'}</span>
            <span>→</span>
            <span>{item.valor_novo || 'vazio'}</span>
          </div>
          <div className="history-user">{formatarUsuarioHistorico(item)}</div>
          <div style={{ fontSize: '12px', color: '#64748b', marginTop: '2px' }}>{formatarData(item.data)}</div>
        </div>
      ))}
    </div>
  );
}

function DisplayItem({ label, value, compact = false }) {
  return (
    <div className={compact ? 'display-item compact' : 'display-item'}>
      <span style={styles.label}>{label}</span>
      <strong>{value || 'Não informado'}</strong>
    </div>
  );
}

function ProfileBadge({ label, value, color }) {
  return (
    <div className="profile-badge">
      <span style={styles.label}>{label}</span>
      <strong style={{ color, backgroundColor: `${color}14`, borderColor: `${color}35` }}>{value || 'Não informado'}</strong>
    </div>
  );
}

function ProfileField({ label, value, onChange, disabled, type = 'text' }) {
  return (
    <label style={{ display: 'block', marginTop: '10px' }}>
      <span style={styles.label}>{label}</span>
      <input type={type} style={styles.fieldInput} value={value || ''} disabled={disabled} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

function ProfileSelect({ label, value, onChange, disabled, options, color }) {
  return (
    <label style={{ display: 'block', marginTop: '10px' }}>
      <span style={styles.label}>{label}</span>
      <select style={{ ...styles.fieldInput, color: color || '#1a1a1a', fontWeight: color ? 800 : 500 }} value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
        {options.map(([optionValue, optionLabel]) => <option key={optionValue} value={optionValue}>{optionLabel}</option>)}
      </select>
    </label>
  );
}

function InfoItem({ icon, label, value }) {
  return (
    <div style={styles.infoItem}>
      {icon}
      <div style={{ width: '100%', minWidth: 0 }}>
        <span style={styles.label}>{label}</span>
        <span style={styles.val}>{value}</span>
      </div>
    </div>
  );
}

function FieldItem({ icon, label, editMode, value, display, onChange, type = 'text', full = false }) {
  return (
    <div className={full ? 'full-row' : undefined} style={{ ...styles.infoItem, gridColumn: full ? '1 / -1' : undefined }}>
      {icon}
      <div style={{ width: '100%', minWidth: 0 }}>
        <span style={styles.label}>{label}</span>
        {editMode ? <input type={type} style={styles.fieldInput} value={value || ''} onChange={(e) => onChange(e.target.value)} /> : <span style={styles.val}>{display}</span>}
      </div>
    </div>
  );
}
