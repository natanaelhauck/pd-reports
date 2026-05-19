import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { Search, User, Mail, Hash, Calendar, ShieldCheck, Phone, Edit2, Save, X, LogIn, Briefcase, GraduationCap, Users, CheckCircle2, Moon, Sun, Plus, UserPlus, ClipboardList, Laptop, Eye, EyeOff } from 'lucide-react';
import pdLogo from './assets/pd-logo.svg';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:5000').replace(/\/$/, '');
const MONITORES = ['Alex', 'André', 'Douglas', 'Gabriel', 'Kellen', 'Natanael'];
const MONITORES_DASHBOARD = ['Alex', 'André', 'Douglas', 'Gabriel', 'Kellen', 'Natanael'];
const STATUS_OPTIONS = ['MANTER', 'EM ANÁLISE', 'REMOVIDO', 'DESLIGADO'];
const TABS = ['Dados principais', 'Perfil do aluno', 'Relatórios Monitoria', 'Histórico'];
const MONITORIA_COLUNAS = [
  ['presente', 'Presente'],
  ['falta', 'Falta'],
  ['aluno_nao_agendado', 'Não agendado'],
  ['aluno_finalizou', 'Finalizou'],
  ['total', 'Total'],
];
const STATUS_MONITORIA_FILTROS = [
  ['', 'Todos'],
  ['Presente', 'Presente'],
  ['Falta', 'Falta'],
  ['Não agendado', 'Não agendado'],
  ['Finalizou', 'Finalizou'],
];
const TIPO_MATRICULA_FILTROS = [
  ['todos', 'Todos'],
  ['pdita', 'Itabira - PDITA'],
  ['pdbd', 'Bom Despacho - PDBD'],
];

const PERFIL_INICIAL = (matricula = '') => ({
  matricula,
  analise_perfil: '',
  trabalha: null,
  trabalho_descricao: '',
  area_profissional_interesse: '',
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

const NOVO_ALUNO_INICIAL = { nome: '', matricula: '', telefone: '', email: '', nascimento: '', patrimonio: '', monitor: '', status: 'MANTER' };
const PERFIL_CADASTRO_INICIAL = () => {
  const perfil = PERFIL_INICIAL();
  delete perfil.matricula;
  return perfil;
};

const STATUS_COLORS = {
  MANTER: '#1f9d55',
  'EM ANÁLISE': '#d97706',
  REMOVIDO: '#64748b',
  DESLIGADO: '#991b1b',
  '': '#94a3b8',
};

const ENG_COLORS = { baixo: '#b91c1c', médio: '#d97706', medio: '#d97706', alto: '#15803d' };
const PROG_COLORS = { básico: '#0284c7', basico: '#0284c7', intermediário: '#4f46e5', intermediario: '#4f46e5', avançado: '#166534', avancado: '#166534' };
const CAMPO_LABELS = {
  nome: 'Nome',
  telefone: 'Telefone',
  email: 'E-mail',
  nascimento: 'Nascimento',
  patrimonio: 'Patrimônio',
  monitor: 'Monitor responsável',
  status: 'Status',
  'sistema.cadastro': 'Cadastro do aluno',
  'perfil.analise_perfil': 'Perfil · Análise de perfil',
  'perfil.trabalha': 'Perfil · Trabalha?',
  'perfil.trabalho_descricao': 'Perfil · Descrição do trabalho',
  'Área profissional de interesse': 'Área profissional de interesse',
  'perfil.area_profissional_interesse': 'Área profissional de interesse',
  'perfil.turno_trabalho': 'Perfil · Turno de trabalho',
  'perfil.estuda': 'Perfil · Estuda?',
  'perfil.estudo_instituicao': 'Perfil · Instituição de estudo',
  'perfil.estudo_curso': 'Perfil · Curso',
  'perfil.turno_estudo': 'Perfil · Turno de estudo',
  'perfil.tem_filhos': 'Perfil · Tem filhos?',
  'perfil.filhos_descricao': 'Perfil · Filhos',
  'perfil.nivel_engajamento': 'Perfil · Nível de Engajamento',
  'perfil.nivel_programacao': 'Perfil · Nível de Conhecimento em Programação',
  'perfil.previsao_formacao_ano': 'Perfil · Ano de previsão de formação',
  'perfil.previsao_formacao_semestre': 'Perfil · Semestre de previsão de formação',
  'perfil.dia_monitoria': 'Perfil · Dia da monitoria',
  'perfil.horario_monitoria': 'Perfil · Horário da monitoria',
  'perfil.acompanhamento_psicologico': 'Perfil · Faz acompanhamento?',
  'perfil.psicologo': 'Perfil · Psicólogo',
};

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
  patrimonio: aluno.patrimonio ?? '',
  monitor: normalizarMonitor(aluno.monitor),
  status: normalizarStatus(aluno.status),
});

const normalizarPerfil = (perfil = {}) => ({ ...PERFIL_INICIAL(perfil.matricula), ...perfil });
const MENSAGEM_BACKEND_INICIANDO = 'O servidor está iniciando. Aguarde alguns segundos e clique em Atualizar novamente.';
const erroDeConexao = (err) => (
  !err.response
  || err.code === 'ECONNABORTED'
  || err.code === 'ERR_NETWORK'
  || [502, 503, 504].includes(err.response?.status)
);
const aguardar = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const mensagemErroApi = (err, fallback) => {
  if (erroDeConexao(err)) return MENSAGEM_BACKEND_INICIANDO;
  return err.response?.data?.erro || fallback;
};

const formatarData = (valor) => {
  if (!valor) return '-';
  return new Date(valor).toLocaleString('pt-BR');
};

const formatarDataIso = (valor) => {
  if (!valor) return 'Sem data';
  const [ano, mes, dia] = String(valor).split('-');
  if (!ano || !mes || !dia) return valor;
  return `${dia}/${mes}/${ano}`;
};

const mesAtualInput = () => {
  const hoje = new Date();
  return `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, '0')}`;
};

const dataInputLocal = (data = new Date()) => {
  const ano = data.getFullYear();
  const mes = String(data.getMonth() + 1).padStart(2, '0');
  const dia = String(data.getDate()).padStart(2, '0');
  return `${ano}-${mes}-${dia}`;
};

const formatarDiaMes = (data) => `${String(data.getDate()).padStart(2, '0')}/${String(data.getMonth() + 1).padStart(2, '0')}`;

const semanasUteisMonitoriaMes = (mesValor) => {
  const [anoTexto, mesTexto] = String(mesValor || '').split('-');
  const ano = Number(anoTexto);
  const mes = Number(mesTexto);
  if (!ano || !mes) return [];

  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);
  const primeiroDia = new Date(ano, mes - 1, 1);
  const ultimoDia = new Date(ano, mes, 0);
  const diasAteSegunda = (8 - primeiroDia.getDay()) % 7;
  let inicio = new Date(ano, mes - 1, primeiroDia.getDate() + diasAteSegunda);
  const semanas = [];

  while (inicio <= ultimoDia) {
    const fim = new Date(inicio);
    fim.setDate(inicio.getDate() + 4);
    if (fim.getMonth() !== mes - 1) break;
    if (inicio > hoje) break;
    semanas.push({
      valor: `semana_${semanas.length + 1}`,
      label: `Semana ${semanas.length + 1}`,
      periodo: `${formatarDiaMes(inicio)} a ${formatarDiaMes(fim)}`,
    });
    inicio = new Date(inicio);
    inicio.setDate(inicio.getDate() + 7);
  }
  return semanas;
};

const statusMonitoriaClass = (status) => {
  const chave = semAcentos(status).toLowerCase();
  if (chave.includes('presente')) return 'present';
  if (chave.includes('falta')) return 'absent';
  if (chave.includes('nao agendado')) return 'unscheduled';
  if (chave.includes('finalizou')) return 'finished';
  return 'neutral';
};

const statusMonitoriaLabel = (status) => {
  const classe = statusMonitoriaClass(status);
  if (classe === 'finished') return 'Aluno Finalizou';
  if (classe === 'unscheduled') return 'Não agendado';
  return status || 'Sem status';
};

const resumoCurto = (texto, limite = 180) => {
  const valor = String(texto || '').trim();
  if (valor.length <= limite) return valor;
  return `${valor.slice(0, limite).trim()}...`;
};

const resumoMonitoriaVazio = () => ({ aluno_finalizou: 0, aluno_nao_agendado: 0, falta: 0, presente: 0, total: 0 });
const monitorDoUsuario = (usuario) => {
  const porEmail = {
    'alex.fonseca@projetodesenvolve.com.br': 'Alex',
    'andre.costa@projetodesenvolve.com.br': 'André',
    'douglas.freitas@projetodesenvolve.com.br': 'Douglas',
    'gabriel.lopes@projetodesenvolve.com.br': 'Gabriel',
    'kellen.cruz@projetodesenvolve.com.br': 'Kellen',
    'natanaelhauck@projetodesenvolve.com.br': 'Natanael',
  };
  return porEmail[String(usuario?.email || '').toLowerCase()] || normalizarMonitor(usuario?.nome);
};

const boolSelectValue = (valor) => (valor === true ? 'sim' : valor === false ? 'nao' : '');
const boolFromSelect = (valor) => (valor === 'sim' ? true : valor === 'nao' ? false : null);
const DIAS_MONITORIA = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira'];
const QTD_FILHOS = ['1', '2', '3', '4', '5', '6+'];
const TURNOS = ['Manhã', 'Tarde', 'Noite', 'Integral', 'Variável', 'EAD'];
const TURNOS_TRABALHO = ['Manhã', 'Tarde', 'Noite', 'Integral', 'Escala', 'Freelancer', 'Outro'];
const PSICOLOGOS = ['Isabela'];
const PERFIS_USUARIO = [
  ['monitor', 'Monitor'],
  ['admin', 'Admin'],
  ['psicologa', 'Psicóloga'],
];

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

const perfilCadastroTemDados = (perfil) => Object.values(perfil || {}).some((valor) => {
  if (typeof valor === 'boolean') return true;
  if (valor === null || valor === undefined) return false;
  return String(valor).trim() !== '';
});

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
  const perfil = String(usuario.role || '').trim().toLowerCase();
  const email = String(usuario.email || '').trim().toLowerCase();
  let nome = String(usuario.nome || usuario.email || '').trim();
  if (perfil === 'admin' && nome.toLowerCase() === 'admin') nome = 'Natanael';
  if (!nome && email === 'natanaelhauck@projetodesenvolve.com.br') nome = 'Natanael';
  const perfilLabel = rotuloPerfilUsuario({ ...usuario, nome });
  return [nome || 'Usuário', perfilLabel].filter(Boolean).join(' - ');
};

const rotuloPerfilUsuario = (usuario) => {
  const perfil = String(usuario?.role || '').trim().toLowerCase();
  const nome = String(usuario?.nome || '').trim().toLowerCase();
  if (perfil === 'admin') return 'Admin';
  if (perfil === 'psicologa') return 'Psicóloga';
  if (perfil === 'monitor' && nome.startsWith('kellen')) return 'Monitora';
  if (perfil === 'monitor') return 'Monitor';
  return perfil ? perfil.charAt(0).toUpperCase() + perfil.slice(1) : '';
};

const formatarUsuarioHistorico = (item) => {
  if (!item?.usuario_nome && !item?.usuario_email) return 'Usuário não registrado';
  return `Alterado por ${formatarUsuario({ nome: item.usuario_nome || item.usuario_email, role: item.usuario_role })}`;
};

const rotuloCampoHistorico = (campo) => CAMPO_LABELS[campo] || String(campo || '')
  .replace('perfil.', 'Perfil · ')
  .replaceAll('_', ' ');

const styles = {
  container: { width: '100%', maxWidth: '1180px', margin: '0 auto 36px', padding: '18px 24px 36px', fontFamily: '"Inter", sans-serif', boxSizing: 'border-box' },
  header: { marginBottom: '14px' },
  logo: { width: 'min(210px, 58vw)', maxHeight: '64px', objectFit: 'contain', display: 'block', margin: '0 auto 4px' },
  title: { fontSize: '30px', fontWeight: '850', color: 'var(--pd-title)', margin: 0, lineHeight: 1.05 },
  subtitle: { color: 'var(--pd-muted)', fontSize: '15px', marginTop: '4px' },
  hero: { textAlign: 'center', background: '#fff', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '18px 22px', boxShadow: '0 8px 24px rgba(15,23,42,0.05)', marginBottom: '14px' },
  searchBox: { display: 'flex', alignItems: 'center', gap: '10px', background: 'var(--pd-surface)', padding: '8px 8px 8px 14px', borderRadius: '14px', boxShadow: 'var(--pd-shadow)', border: '1px solid var(--pd-border)', marginBottom: '18px' },
  searchInput: { flex: 1, minWidth: 0, border: 'none', padding: '11px 8px', fontSize: '16px', outline: 'none', color: 'var(--pd-text)', backgroundColor: 'transparent', colorScheme: 'var(--pd-color-scheme)' },
  primaryBtn: { background: '#2563eb', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: '10px', fontWeight: '800', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center' },
  neutralBtn: { background: 'var(--pd-button-bg)', color: 'var(--pd-button-text)', border: '1px solid var(--pd-button-border)', padding: '10px 14px', borderRadius: '10px', cursor: 'pointer', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center', minHeight: '40px' },
  iconBtn: { width: '40px', height: '40px', padding: 0, borderRadius: '10px', background: 'var(--pd-button-bg)', color: 'var(--pd-button-text)', border: '1px solid var(--pd-button-border)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' },
  secondaryBtn: { background: 'var(--pd-button-bg)', color: 'var(--pd-button-text)', border: '1px solid var(--pd-button-border)', padding: '10px 14px', borderRadius: '10px', cursor: 'pointer', fontWeight: '800', display: 'flex', alignItems: 'center', gap: '8px', justifyContent: 'center', minHeight: '40px' },
  message: { marginBottom: '18px', padding: '12px 14px', borderRadius: '10px', fontSize: '14px', fontWeight: '700', textAlign: 'left' },
  results: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '10px', marginBottom: '18px' },
  resultBtn: { background: 'var(--pd-surface)', border: '1px solid var(--pd-border)', borderRadius: '12px', padding: '12px', textAlign: 'left', cursor: 'pointer', color: 'var(--pd-text)' },
  card: { background: 'var(--pd-surface)', borderRadius: '16px', padding: '22px', boxShadow: 'var(--pd-card-shadow)', position: 'relative' },
  cardHeader: { display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '14px', paddingBottom: '14px', borderBottom: '1px solid var(--pd-border)' },
  avatar: { width: '50px', height: '50px', borderRadius: '13px', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  headerInfo: { flex: 1, minWidth: 0, textAlign: 'left' },
  nome: { fontSize: '23px', fontWeight: '850', color: 'var(--pd-title)', margin: 0, overflowWrap: 'anywhere', lineHeight: 1.14 },
  badge: { marginTop: '6px', padding: '5px 10px', borderRadius: '999px', fontSize: '10px', fontWeight: '850', display: 'inline-flex', alignItems: 'center', textTransform: 'uppercase' },
  actions: { display: 'flex', gap: '10px', marginLeft: 'auto', alignItems: 'center', flexShrink: 0, flexWrap: 'wrap' },
  tabs: { display: 'flex', gap: '6px', overflowX: 'auto', padding: '3px', marginBottom: '14px', background: 'var(--pd-subtle)', border: '1px solid var(--pd-border)', borderRadius: '12px' },
  tab: { border: 'none', background: 'transparent', color: 'var(--pd-muted)', padding: '9px 12px', borderRadius: '9px', fontWeight: 850, cursor: 'pointer', whiteSpace: 'nowrap' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '12px' },
  profileGrid: { display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '12px' },
  section: { background: 'var(--pd-subtle)', border: '1px solid var(--pd-border)', borderRadius: '12px', padding: '14px', textAlign: 'left' },
  infoItem: { background: 'var(--pd-subtle)', padding: '15px', borderRadius: '12px', display: 'flex', gap: '12px', border: '1px solid var(--pd-border)', textAlign: 'left', minWidth: 0 },
  label: { fontSize: '10px', textTransform: 'uppercase', color: 'var(--pd-label)', fontWeight: '850', display: 'block', marginBottom: '6px' },
  val: { fontSize: '15px', fontWeight: '650', color: 'var(--pd-text)', overflowWrap: 'anywhere' },
  fieldInput: { width: '100%', boxSizing: 'border-box', minHeight: '42px', padding: '10px 12px', borderRadius: '9px', border: '1px solid var(--pd-input-border)', backgroundColor: 'var(--pd-input-bg)', color: 'var(--pd-text)', fontSize: '14px', outline: 'none', colorScheme: 'var(--pd-color-scheme)' },
  textarea: { width: '100%', boxSizing: 'border-box', minHeight: '120px', padding: '10px 12px', borderRadius: '9px', border: '1px solid var(--pd-input-border)', backgroundColor: 'var(--pd-input-bg)', color: 'var(--pd-text)', fontSize: '14px', outline: 'none', resize: 'vertical', colorScheme: 'var(--pd-color-scheme)' },
  editInputName: { fontSize: '22px', fontWeight: '800', border: '1px solid var(--pd-input-border)', borderRadius: '10px', padding: '9px 11px', width: '100%', boxSizing: 'border-box', color: 'var(--pd-title)', backgroundColor: 'var(--pd-input-bg)', colorScheme: 'var(--pd-color-scheme)' },
  loginBox: { maxWidth: '420px', margin: '90px auto', background: 'var(--pd-surface)', border: '1px solid var(--pd-border)', borderRadius: '18px', padding: '28px', boxShadow: 'var(--pd-card-shadow)' },
  passwordWrap: { position: 'relative', marginBottom: '12px' },
  passwordToggle: { position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)', width: '34px', height: '34px', padding: 0, border: 'none', borderRadius: '8px', background: 'transparent', color: 'var(--pd-muted)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' },
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
  const [mostrarSenhaLogin, setMostrarSenhaLogin] = useState(false);
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
  const [mostrarMonitores, setMostrarMonitores] = useState(false);
  const [usuarios, setUsuarios] = useState([]);
  const [novoAluno, setNovoAluno] = useState(NOVO_ALUNO_INICIAL);
  const [mostrarPerfilNovoAluno, setMostrarPerfilNovoAluno] = useState(false);
  const [novoAlunoPerfil, setNovoAlunoPerfil] = useState(PERFIL_CADASTRO_INICIAL);
  const [novoUsuario, setNovoUsuario] = useState({ nome: '', email: '', senha: '', role: 'monitor' });
  const [usuarioEditando, setUsuarioEditando] = useState(null);
  const [usuarioTemp, setUsuarioTemp] = useState({ nome: '', email: '', role: 'monitor' });
  const [senhaUsuarioEditando, setSenhaUsuarioEditando] = useState(null);
  const [novaSenhaUsuario, setNovaSenhaUsuario] = useState('');
  const [mostrarSenhaUsuario, setMostrarSenhaUsuario] = useState(false);
  const [salvandoSenhaUsuario, setSalvandoSenhaUsuario] = useState(false);
  const [salvandoUsuarioEditando, setSalvandoUsuarioEditando] = useState(false);
  const [salvandoNovoAluno, setSalvandoNovoAluno] = useState(false);
  const [salvandoUsuario, setSalvandoUsuario] = useState(false);
  const cardRef = useRef(null);
  const isAdmin = usuario?.role === 'admin';
  const autenticado = Boolean(usuario?.token);
  const authHeaders = useMemo(() => (
    usuario?.token ? { Authorization: `Bearer ${usuario.token}` } : {}
  ), [usuario]);
  const authConfig = (config = {}) => ({
    ...config,
    headers: { ...(config.headers || {}), ...authHeaders },
  });
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
    : mensagem?.tipo === 'aviso'
      ? { background: '#fffbeb', color: '#92400e', border: '1px solid #fde68a' }
      : { background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca' };

  const buscarPerfilAluno = async (matricula) => {
    const res = await axios.get(`${API_BASE_URL}/api/alunos/perfil/${encodeURIComponent(matricula)}`, authConfig({ timeout: 12000 }));
    const dados = normalizarPerfil(res.data);
    setPerfil(dados);
    setPerfilTemp(dados);
    return dados;
  };

  const limparEstadoAplicacao = () => {
    setAlunos([]);
    setBusca('');
    setAluno(null);
    setEditMode(false);
    setTemp(criarTempSeguro());
    setActiveTab('Dados principais');
    setPerfil(PERFIL_INICIAL());
    setPerfilTemp(PERFIL_INICIAL());
    setEditPerfil(false);
    setMensagem(null);
    setHistorico([]);
    setBuscaRealizada(false);
    setMostrarNovoAluno(false);
    setMostrarUsuarios(false);
    setMostrarMonitores(false);
    setUsuarios([]);
    setNovoAluno(NOVO_ALUNO_INICIAL);
    setMostrarPerfilNovoAluno(false);
    setNovoAlunoPerfil(PERFIL_CADASTRO_INICIAL());
    setNovoUsuario({ nome: '', email: '', senha: '', role: 'monitor' });
    setUsuarioEditando(null);
    setUsuarioTemp({ nome: '', email: '', role: 'monitor' });
    setSenhaUsuarioEditando(null);
    setNovaSenhaUsuario('');
    setMostrarSenhaUsuario(false);
  };

  const salvarPerfilAluno = async () => {
    if (!aluno || salvandoPerfil) return;
    setSalvandoPerfil(true);
    setMensagem(null);
    try {
      const payload = { ...perfilTemp, matricula: aluno.matricula };
      const res = await axios.post(`${API_BASE_URL}/api/alunos/perfil/update`, payload, authConfig({ timeout: 12000 }));
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
      const res = await axios.get(`${API_BASE_URL}/api/alunos/historico/${encodeURIComponent(matricula)}`, authConfig({ timeout: 12000 }));
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
      const res = await axios.get(`${API_BASE_URL}/api/alunos`, authConfig({ params: { q: termo }, timeout: 12000 }));
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
      const res = await axios.post(`${API_BASE_URL}/api/login`, { email: loginEmail, senha }, { timeout: 12000 });
      localStorage.setItem('pd_user', JSON.stringify(res.data.usuario));
      localStorage.removeItem('pd_auth');
      limparEstadoAplicacao();
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
    Object.keys(localStorage).forEach((key) => {
      if (key.startsWith('pd_') && key !== 'pd_theme') localStorage.removeItem(key);
    });
    setUsuario(null);
    limparEstadoAplicacao();
    setLoginEmail('');
    setSenha('');
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
    setMostrarMonitores(false);
    setMostrarUsuarios(false);
    setMostrarNovoAluno(true);
    setMostrarPerfilNovoAluno(false);
    setNovoAlunoPerfil(PERFIL_CADASTRO_INICIAL());
    setMensagem(null);
  };

  const abrirUsuarios = async () => {
    fecharAlunoSelecionado();
    setMostrarMonitores(false);
    setMostrarNovoAluno(false);
    setNovoUsuario({ nome: '', email: '', senha: '', role: 'monitor' });
    setUsuarioEditando(null);
    setUsuarioTemp({ nome: '', email: '', role: 'monitor' });
    setSenhaUsuarioEditando(null);
    setNovaSenhaUsuario('');
    setMostrarSenhaUsuario(false);
    await carregarUsuarios();
  };

  const abrirMonitores = () => {
    fecharAlunoSelecionado();
    setMostrarNovoAluno(false);
    setMostrarUsuarios(false);
    setMostrarMonitores(true);
    setMensagem(null);
  };

  const carregarUsuarios = async () => {
    if (!isAdmin) return;
    setMensagem(null);
    try {
      const res = await axios.get(`${API_BASE_URL}/api/usuarios`, authConfig({ timeout: 12000 }));
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
      const res = await axios.post(`${API_BASE_URL}/api/usuarios/create`, novoUsuario, authConfig({ timeout: 12000 }));
      setUsuarios((atuais) => [...atuais, res.data.usuario].sort((a, b) => String(a.nome).localeCompare(String(b.nome), 'pt-BR')));
      setNovoUsuario({ nome: '', email: '', senha: '', role: 'monitor' });
      setMensagem({ tipo: 'sucesso', texto: res.data.mensagem || 'Usuário cadastrado com sucesso.' });
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Erro ao cadastrar usuário.') });
    } finally {
      setSalvandoUsuario(false);
    }
  };

  const editarUsuario = (usuarioAlvo) => {
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
  };

  const cancelarEdicaoUsuario = () => {
    setUsuarioEditando(null);
    setUsuarioTemp({ nome: '', email: '', role: 'monitor' });
  };

  const salvarUsuario = async (usuarioAlvo) => {
    if (!isAdmin || salvandoUsuarioEditando) return;
    setSalvandoUsuarioEditando(true);
    setMensagem(null);
    try {
      const res = await axios.put(`${API_BASE_URL}/api/usuarios/${usuarioAlvo.id}`, usuarioTemp, authConfig({ timeout: 12000 }));
      setUsuarios((atuais) => atuais
        .map((item) => (item.id === usuarioAlvo.id ? res.data.usuario : item))
        .sort((a, b) => String(a.nome).localeCompare(String(b.nome), 'pt-BR')));
      cancelarEdicaoUsuario();
      setMensagem({ tipo: 'sucesso', texto: res.data.mensagem || 'Usuário atualizado com sucesso.' });
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Erro ao atualizar usuário.') });
    } finally {
      setSalvandoUsuarioEditando(false);
    }
  };

  const salvarSenhaUsuario = async (usuarioAlvo) => {
    if (!isAdmin || salvandoSenhaUsuario) return;
    setSalvandoSenhaUsuario(true);
    setMensagem(null);
    try {
      const res = await axios.post(`${API_BASE_URL}/api/usuarios/update-password`, {
        usuario_id: usuarioAlvo.id,
        nova_senha: novaSenhaUsuario,
      }, authConfig({ timeout: 12000 }));
      setSenhaUsuarioEditando(null);
      setNovaSenhaUsuario('');
      setMostrarSenhaUsuario(false);
      setMensagem({ tipo: 'sucesso', texto: res.data.mensagem || 'Senha alterada com sucesso.' });
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Erro ao alterar senha.') });
    } finally {
      setSalvandoSenhaUsuario(false);
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
      };
      if (mostrarPerfilNovoAluno && perfilCadastroTemDados(novoAlunoPerfil)) {
        payload.perfil = novoAlunoPerfil;
      }
      const res = await axios.post(`${API_BASE_URL}/api/alunos/create`, payload, authConfig({ timeout: 12000 }));
      const criado = res.data.aluno;
      setAlunos((atuais) => [...atuais.filter((a) => a.matricula !== criado.matricula), criado]);
      setAluno(criado);
      setTemp(criarTempSeguro(criado));
      if (res.data.perfil) {
        const perfilCriado = normalizarPerfil(res.data.perfil);
        setPerfil(perfilCriado);
        setPerfilTemp(perfilCriado);
      } else {
        const perfilInicial = PERFIL_INICIAL(criado.matricula);
        setPerfil(perfilInicial);
        setPerfilTemp(perfilInicial);
      }
      setBuscaRealizada(true);
      setMostrarNovoAluno(false);
      setNovoAluno(NOVO_ALUNO_INICIAL);
      setMostrarPerfilNovoAluno(false);
      setNovoAlunoPerfil(PERFIL_CADASTRO_INICIAL());
      setMensagem({ tipo: 'sucesso', texto: res.data.mensagem || 'Aluno cadastrado com sucesso.' });
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Erro ao cadastrar aluno.') });
    } finally {
      setSalvandoNovoAluno(false);
    }
  };

  const buscar = async (e) => {
    e.preventDefault();
    setMostrarMonitores(false);
    setBuscaRealizada(true);
    await carregarAlunos(busca.trim());
    setEditMode(false);
    setActiveTab('Dados principais');
  };

  const selecionarAluno = (selecionado) => {
    setMostrarNovoAluno(false);
    setMostrarUsuarios(false);
    setMostrarMonitores(false);
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
      const payload = { ...temp, monitor: normalizarMonitor(temp.monitor), status: normalizarStatus(temp.status) };
      const res = await axios.post(`${API_BASE_URL}/api/alunos/update`, payload, authConfig({ timeout: 12000 }));
      atualizarAlunoLocal(res.data.aluno || payload);
      setEditMode(false);
      setMensagem(res.data.sync_warning
        ? { tipo: 'aviso', texto: 'Salvo no sistema, mas a planilha não foi atualizada.' }
        : { tipo: 'sucesso', texto: res.data.mensagem || 'Aluno atualizado com sucesso.' });
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
        <form className="login-box" onSubmit={login} style={styles.loginBox} autoComplete="off">
          <div className="login-logo-wrap">
            <img src={pdLogo} alt="PD Reports" className="pd-logo" style={styles.logo} />
          </div>
          <h1 style={{ ...styles.title, textAlign: 'left' }}>PD Reports</h1>
          <p style={{ ...styles.subtitle, textAlign: 'left', marginBottom: '18px' }}>Gestão de Alunos</p>
          <input type="email" style={{ ...styles.fieldInput, marginBottom: '12px' }} placeholder="E-mail" value={loginEmail} onChange={(e) => setLoginEmail(e.target.value)} autoComplete="username" />
          <div style={styles.passwordWrap}>
            <input type={mostrarSenhaLogin ? 'text' : 'password'} style={{ ...styles.fieldInput, paddingRight: '48px' }} placeholder="Senha" value={senha} onChange={(e) => setSenha(e.target.value)} autoComplete="current-password" />
            <button
              className="ui-button"
              type="button"
              aria-label={mostrarSenhaLogin ? 'Ocultar senha' : 'Mostrar senha'}
              title={mostrarSenhaLogin ? 'Ocultar senha' : 'Mostrar senha'}
              onClick={() => setMostrarSenhaLogin((atual) => !atual)}
              style={styles.passwordToggle}
            >
              {mostrarSenhaLogin ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
          <button className="ui-button" type="submit" style={{ ...styles.primaryBtn, width: '100%' }}><LogIn size={18} /> Entrar</button>
          <button className="ui-button icon-button theme-toggle-login" type="button" title="Alternar tema" aria-label="Alternar tema" onClick={alternarTema} style={{ ...styles.iconBtn, marginTop: '10px' }}>
            {temaEscuro ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          {mensagem && <div style={{ ...styles.message, ...estiloMensagem, marginTop: '14px', marginBottom: 0 }}>{mensagem.texto}</div>}
        </form>
      </div>
    );
  }

  const statusAtual = editMode ? temp.status : aluno?.status;
  const corStatus = getStatusColor(statusAtual);

  return (
    <div className={temaEscuro ? 'theme-dark app-shell' : 'theme-light app-shell'} style={mostrarMonitores ? { ...styles.container, maxWidth: '1500px' } : styles.container}>
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

      <div className="main-actions">
        <button className="ui-button" type="button" onClick={abrirMonitores} style={styles.neutralBtn}><Users size={17} /> Monitores</button>
        {isAdmin && (
          <>
            <button className="ui-button" type="button" onClick={abrirNovoAluno} style={styles.neutralBtn}><Plus size={17} /> Novo aluno</button>
            <button className="ui-button" type="button" onClick={abrirUsuarios} style={styles.neutralBtn}><UserPlus size={17} /> Usuários</button>
          </>
        )}
      </div>

      <form className="search-form" onSubmit={buscar} style={styles.searchBox}>
        <Search className="search-icon" size={20} color="#64748b" />
        <input style={styles.searchInput} placeholder="Buscar por nome, matrícula, e-mail ou telefone..." value={busca} onChange={(e) => setBusca(e.target.value)} autoComplete="off" />
        <button className="ui-button" type="submit" disabled={buscando} style={{ ...styles.primaryBtn, opacity: buscando ? 0.75 : 1 }}>
          {buscando ? 'Buscando...' : 'Buscar'}
        </button>
      </form>

      {mensagem && <div style={{ ...styles.message, ...estiloMensagem }}>{mensagem.texto}</div>}

      {mostrarMonitores && (
        <MonitoresDashboard usuario={usuario} authHeaders={authHeaders} />
      )}

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
            <ProfileField label="Patrimônio" value={novoAluno.patrimonio} onChange={(v) => setNovoAluno({ ...novoAluno, patrimonio: v })} />
            <ProfileSelect label="Monitor" value={novoAluno.monitor} onChange={(v) => setNovoAluno({ ...novoAluno, monitor: v })} options={[['', 'Selecione...'], ...MONITORES.map((m) => [m, m])]} />
            <ProfileSelect label="Status *" value={novoAluno.status} onChange={(v) => setNovoAluno({ ...novoAluno, status: v })} options={STATUS_OPTIONS.map((s) => [s, s])} />
          </div>
          <div className="new-student-profile">
            <div className="new-student-profile-head">
              <div>
                <h3>Perfil do aluno</h3>
                <p>Preenchimento opcional no cadastro</p>
              </div>
              <button className="ui-button" type="button" onClick={() => setMostrarPerfilNovoAluno((atual) => !atual)} style={styles.secondaryBtn}>
                {mostrarPerfilNovoAluno ? 'Ocultar perfil' : 'Preencher perfil agora'}
              </button>
            </div>
            {mostrarPerfilNovoAluno && (
              <NovoAlunoPerfilForm perfil={novoAlunoPerfil} setPerfil={setNovoAlunoPerfil} />
            )}
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
          <form onSubmit={cadastrarUsuario} className="admin-grid" autoComplete="off">
            <ProfileField label="Nome" value={novoUsuario.nome} onChange={(v) => setNovoUsuario({ ...novoUsuario, nome: v })} />
            <ProfileField label="E-mail" type="email" value={novoUsuario.email} onChange={(v) => setNovoUsuario({ ...novoUsuario, email: v })} autoComplete="new-email" />
            <ProfileField label="Senha" type="password" value={novoUsuario.senha} onChange={(v) => setNovoUsuario({ ...novoUsuario, senha: v })} autoComplete="new-password" />
            <ProfileSelect label="Perfil" value={novoUsuario.role} onChange={(v) => setNovoUsuario({ ...novoUsuario, role: v })} options={PERFIS_USUARIO} />
            <button className="ui-button" type="submit" disabled={salvandoUsuario} style={styles.primaryBtn}>
              <Save size={17} /> {salvandoUsuario ? 'Salvando...' : 'Cadastrar usuário'}
            </button>
          </form>
          <div className="users-table-wrap">
            <h3>Usuários cadastrados</h3>
            <table className="users-table">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>E-mail</th>
                  <th>Perfil</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {usuarios.map((u) => (
                  <Fragment key={u.id || u.email}>
                    <tr>
                      <td>{formatarUsuario(u)}</td>
                      <td>{u.email}</td>
                      <td>{rotuloPerfilUsuario(u)}</td>
                      <td>
                        <div style={{ ...styles.actions, marginLeft: 0 }}>
                          <button className="ui-button" type="button" style={styles.secondaryBtn} onClick={() => editarUsuario(u)}>
                            <Edit2 size={16} /> Editar
                          </button>
                          <button className="ui-button" type="button" style={styles.secondaryBtn} onClick={() => {
                            setSenhaUsuarioEditando(u.id);
                            setNovaSenhaUsuario('');
                            setMostrarSenhaUsuario(false);
                            setUsuarioEditando(null);
                          }}>
                            Alterar senha
                          </button>
                        </div>
                      </td>
                    </tr>
                    {usuarioEditando === u.id && (
                      <tr className="password-row">
                        <td colSpan="4">
                          <div className="password-inline-form">
                            <ProfileField label="Nome" value={usuarioTemp.nome} onChange={(v) => setUsuarioTemp({ ...usuarioTemp, nome: v })} />
                            <ProfileField label="E-mail" type="email" value={usuarioTemp.email} onChange={(v) => setUsuarioTemp({ ...usuarioTemp, email: v })} autoComplete="off" />
                            <ProfileSelect label="Perfil" value={usuarioTemp.role} onChange={(v) => setUsuarioTemp({ ...usuarioTemp, role: v })} options={PERFIS_USUARIO} />
                            <button className="ui-button" type="button" disabled={salvandoUsuarioEditando} style={styles.primaryBtn} onClick={() => salvarUsuario(u)}>
                              {salvandoUsuarioEditando ? 'Salvando...' : 'Salvar'}
                            </button>
                            <button className="ui-button" type="button" style={styles.secondaryBtn} onClick={cancelarEdicaoUsuario}>
                              Cancelar
                            </button>
                          </div>
                        </td>
                      </tr>
                    )}
                    {senhaUsuarioEditando === u.id && (
                      <tr className="password-row">
                        <td colSpan="4">
                          <div className="password-inline-form">
                            <label style={{ display: 'block', marginTop: '10px' }}>
                              <span style={styles.label}>Nova senha</span>
                              <div style={{ ...styles.passwordWrap, marginBottom: 0 }}>
                                <input type={mostrarSenhaUsuario ? 'text' : 'password'} style={{ ...styles.fieldInput, paddingRight: '48px' }} value={novaSenhaUsuario} onChange={(e) => setNovaSenhaUsuario(e.target.value)} autoComplete="new-password" />
                                <button
                                  className="ui-button"
                                  type="button"
                                  aria-label={mostrarSenhaUsuario ? 'Ocultar senha' : 'Mostrar senha'}
                                  title={mostrarSenhaUsuario ? 'Ocultar senha' : 'Mostrar senha'}
                                  onClick={() => setMostrarSenhaUsuario((atual) => !atual)}
                                  style={styles.passwordToggle}
                                >
                                  {mostrarSenhaUsuario ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                              </div>
                            </label>
                            <button className="ui-button" type="button" disabled={salvandoSenhaUsuario} style={styles.primaryBtn} onClick={() => salvarSenhaUsuario(u)}>
                              {salvandoSenhaUsuario ? 'Salvando...' : 'Salvar senha'}
                            </button>
                            <button className="ui-button" type="button" style={styles.secondaryBtn} onClick={() => {
                              setSenhaUsuarioEditando(null);
                              setNovaSenhaUsuario('');
                              setMostrarSenhaUsuario(false);
                            }}>
                              Cancelar
                            </button>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {aluno && (
        <div ref={cardRef} className="student-card" style={{ ...styles.card, '--student-status-color': corStatus, borderLeft: `8px solid ${corStatus}`, marginBottom: '18px' }}>
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
              <button key={tab} className="ui-button" type="button" onClick={() => selecionarTab(tab)} style={{ ...styles.tab, background: activeTab === tab ? 'var(--pd-surface)' : 'transparent', color: activeTab === tab ? 'var(--pd-title)' : 'var(--pd-muted)', boxShadow: activeTab === tab ? 'var(--pd-tab-shadow)' : 'none' }}>{tab}</button>
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

          {activeTab === 'Relatórios Monitoria' && (
            <RelatoriosMonitoria aluno={aluno} authHeaders={authHeaders} />
          )}
        </div>
      )}

      {!mostrarMonitores && buscaRealizada && resultadosVisiveis.length > 0 && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--pd-title)', margin: 0 }}>Resultados</h2>
            <span style={{ fontSize: '13px', color: 'var(--pd-muted)', fontWeight: 700 }}>{alunosOrdenados.length} aluno(s)</span>
          </div>
          <div style={styles.results}>
            {resultadosVisiveis.map((item) => {
              const selecionado = aluno?.matricula === item.matricula;
              const itemColor = getStatusColor(item.status);
              return (
                <button className={`result-button${selecionado ? ' selected' : ''}`} type="button" key={item.matricula || item.id} style={{ ...styles.resultBtn, borderColor: selecionado ? itemColor : 'var(--pd-border)', backgroundColor: selecionado ? `${itemColor}0d` : 'var(--pd-surface)' }} onClick={() => selecionarAluno(item)}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px' }}>
                    <strong style={{ color: 'var(--pd-title)', lineHeight: 1.25 }}>{item.nome}</strong>
                    <span style={{ flexShrink: 0, color: itemColor, background: `${itemColor}14`, border: `1px solid ${itemColor}35`, borderRadius: '999px', padding: '3px 8px', fontSize: '10px', fontWeight: 900 }}>{statusDisplay(item.status)}</span>
                  </div>
                  <div style={{ fontSize: '13px', marginTop: '8px', color: 'var(--pd-text)' }}>{item.matricula}</div>
                  <div style={{ fontSize: '13px', marginTop: '3px', color: 'var(--pd-muted)' }}>Monitor: {monitorDisplay(item.monitor)}</div>
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
        <FieldItem icon={<Laptop size={18} color={corStatus} />} label="Patrimônio" editMode={editMode} value={temp.patrimonio} display={aluno.patrimonio || 'Não informado'} onChange={(v) => setTemp({ ...temp, patrimonio: v })} />
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
            {p.trabalha === true && (
              <>
                <DisplayItem label="Com o que trabalha?" value={p.trabalho_descricao} />
                <DisplayItem label="Turno de trabalho" value={p.turno_trabalho} />
              </>
            )}
            <DisplayItem label="Em qual área profissional pretende trabalhar futuramente?" value={p.area_profissional_interesse} />
            <DisplayItem label="Estuda?" value={p.estuda === true ? 'Sim' : p.estuda === false ? 'Não' : 'Não informado'} />
            {p.estuda === true && (
              <>
                <DisplayItem label="Onde estuda?" value={p.estudo_instituicao} />
                <DisplayItem label="Qual curso?" value={p.estudo_curso} />
                <DisplayItem label="Turno de estudo" value={p.turno_estudo} />
              </>
            )}
          </section>
          <section style={styles.section}>
            <h3><Users size={18} /> Família</h3>
            <DisplayItem label="Tem filhos?" value={p.tem_filhos === true ? 'Sim' : p.tem_filhos === false ? 'Não' : 'Não informado'} />
            {p.tem_filhos === true && (
              <div className="children-list">
                {filhosResumo(p.filhos_descricao).map((linha) => <strong key={linha}>{linha}</strong>)}
              </div>
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
            <h3><Calendar size={18} /> Monitoria</h3>
            <div className="mini-card-row">
              <DisplayItem label="Dia da monitoria" value={p.dia_monitoria} compact />
              <DisplayItem label="Horário da monitoria" value={p.horario_monitoria} compact />
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
          <ProfileSelect label="Trabalha?" value={boolSelectValue(p.trabalha)} disabled={!editPerfil} onChange={(v) => {
            const trabalha = boolFromSelect(v);
            setPerfilTemp({
              ...perfilTemp,
              trabalha,
              trabalho_descricao: trabalha === true ? perfilTemp.trabalho_descricao : '',
              turno_trabalho: trabalha === true ? perfilTemp.turno_trabalho : '',
            });
          }} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
          {p.trabalha === true && (
            <>
              <ProfileField label="Com o que trabalha?" value={p.trabalho_descricao} disabled={!editPerfil} onChange={(v) => setCampo('trabalho_descricao', v)} />
              <ProfileSelect label="Turno de trabalho" value={p.turno_trabalho || ''} disabled={!editPerfil} onChange={(v) => setCampo('turno_trabalho', v)} options={[['', 'Não informado'], ...TURNOS_TRABALHO.map((turno) => [turno, turno])]} />
            </>
          )}
          <ProfileField label="Em qual área profissional pretende trabalhar futuramente?" value={p.area_profissional_interesse} disabled={!editPerfil} onChange={(v) => setCampo('area_profissional_interesse', v)} />
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
          <h3><Calendar size={18} /> Monitoria</h3>
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
          <strong>{rotuloCampoHistorico(item.campo)}</strong>
          <div className="history-values">
            <span>{item.valor_antigo || 'vazio'}</span>
            <span aria-hidden="true">→</span>
            <span>{item.valor_novo || 'vazio'}</span>
          </div>
          <div className="history-user">{formatarUsuarioHistorico(item)}</div>
          <div className="history-date">{formatarData(item.data)}</div>
        </div>
      ))}
    </div>
  );
}

function MonitoresDashboard({ usuario, authHeaders }) {
  const [mes, setMes] = useState(mesAtualInput());
  const [monitorFiltro, setMonitorFiltro] = useState('');
  const [statusFiltro, setStatusFiltro] = useState('');
  const [periodoFiltro, setPeriodoFiltro] = useState('mes');
  const [dataPeriodo, setDataPeriodo] = useState(dataInputLocal());
  const [tipoMatriculaFiltro, setTipoMatriculaFiltro] = useState('todos');
  const [mostrarDetalhes, setMostrarDetalhes] = useState(false);
  const [semanasAbertas, setSemanasAbertas] = useState({});
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState('');
  const [mensagemAtualizacao, setMensagemAtualizacao] = useState('');

  const isAdmin = usuario?.role === 'admin';
  const monitorUsuario = monitorDoUsuario(usuario);
  const monitorEfetivo = isAdmin ? monitorFiltro : monitorUsuario;
  const semanasPeriodo = useMemo(() => semanasUteisMonitoriaMes(mes), [mes]);
  const periodoOptions = useMemo(() => ([
    ['mes', 'Mês inteiro'],
    ...semanasPeriodo.map((semana) => [semana.valor, `${semana.label} — ${semana.periodo}`]),
    ['hoje', 'Hoje'],
    ['dia', 'Dia específico'],
  ]), [semanasPeriodo]);
  const periodoFiltroEfetivo = periodoOptions.some(([valor]) => valor === periodoFiltro) ? periodoFiltro : 'mes';
  const dataPeriodoEfetiva = dataPeriodo && dataPeriodo.startsWith(`${mes}-`) ? dataPeriodo : `${mes}-01`;
  const paramsResumo = useMemo(() => {
    const params = {
      mes,
      monitor: monitorEfetivo || 'Todos',
      status: statusFiltro || 'Todos',
      periodo: periodoFiltroEfetivo,
      tipo_matricula: tipoMatriculaFiltro,
    };
    if (periodoFiltroEfetivo === 'dia') params.data_periodo = dataPeriodoEfetiva;
    return params;
  }, [mes, monitorEfetivo, statusFiltro, periodoFiltroEfetivo, tipoMatriculaFiltro, dataPeriodoEfetiva]);

  useEffect(() => {
    let cancelado = false;
    const carregarResumo = () => axios.get(`${API_BASE_URL}/api/relatorios-monitoria/resumo-monitores`, {
      params: paramsResumo,
      headers: authHeaders,
      timeout: 20000,
    });
    const carregar = async () => {
      setCarregando(true);
      setErro('');
      setMensagemAtualizacao('');
      try {
        const res = await carregarResumo();
        if (!cancelado) setDados(res.data);
      } catch (err) {
        if (!erroDeConexao(err)) {
          if (!cancelado) setErro(mensagemErroApi(err, 'Nao foi possivel carregar o resumo dos monitores.'));
          return;
        }
        await aguardar(3000);
        if (cancelado) return;
        try {
          const res = await carregarResumo();
          if (!cancelado) setDados(res.data);
        } catch (retryErr) {
          if (!cancelado) setErro(mensagemErroApi(retryErr, 'Nao foi possivel carregar o resumo dos monitores.'));
        }
      } finally {
        if (!cancelado) setCarregando(false);
      }
    };
    const timer = setTimeout(carregar, 0);
    return () => {
      cancelado = true;
      clearTimeout(timer);
    };
  }, [paramsResumo, authHeaders]);

  const atualizarAgora = async () => {
    if (carregando) return;
    setCarregando(true);
    setErro('');
    setMensagemAtualizacao('');
    try {
      await axios.post(`${API_BASE_URL}/api/sync/refresh`, {}, { headers: authHeaders, timeout: 12000 });
      const res = await axios.get(`${API_BASE_URL}/api/relatorios-monitoria/resumo-monitores`, {
        params: paramsResumo,
        headers: authHeaders,
        timeout: 20000,
      });
      setDados(res.data);
      setMensagemAtualizacao('Dados atualizados.');
    } catch (err) {
      setErro(mensagemErroApi(err, 'Nao foi possivel atualizar o resumo dos monitores.'));
    } finally {
      setCarregando(false);
    }
  };

  const resumoMonitorMes = dados?.resumo_por_monitor || [];
  const resumo = dados ? (dados.resumo_geral || resumoMonitoriaVazio()) : resumoMonitoriaVazio();
  const semanasFiltradas = dados?.semanas || [];
  const detalhes = dados?.relatorios_detalhados || [];
  const resumoMotivosFalta = dados?.resumo_motivos_falta || [];
  const periodoAplicado = dados?.periodo_aplicado;
  const mostrarMotivosFalta = statusFiltro === 'Falta';
  const semDados = !carregando && !erro && dados && resumo.total === 0;
  const alternarSemana = (semana) => {
    setSemanasAbertas((atuais) => ({ ...atuais, [semana]: !atuais[semana] }));
  };

  return (
    <section className="monitors-panel" style={styles.section}>
      <div className="monitors-header">
        <div>
          <h2>Monitores</h2>
          <p>Resumo mensal das monitorias registradas</p>
        </div>
        <div className="monitors-actions">
          <ProfileField label="Mês" type="month" value={mes} onChange={setMes} />
          {isAdmin ? (
            <ProfileSelect label="Monitor" value={monitorFiltro} onChange={setMonitorFiltro} options={[['', 'Todos'], ...MONITORES_DASHBOARD.map((monitor) => [monitor, monitor])]} />
          ) : (
            <ProfileField label="Monitor" value={monitorUsuario || 'Monitor'} disabled onChange={() => {}} />
          )}
          <ProfileSelect label="Status" value={statusFiltro} onChange={setStatusFiltro} options={STATUS_MONITORIA_FILTROS} />
          <ProfileSelect label="Período" value={periodoFiltroEfetivo} onChange={setPeriodoFiltro} options={periodoOptions} />
          {periodoFiltroEfetivo === 'dia' && <ProfileField label="Data" type="date" value={dataPeriodoEfetiva} onChange={setDataPeriodo} />}
          <ProfileSelect label="Cidade - Matrícula" value={tipoMatriculaFiltro} onChange={setTipoMatriculaFiltro} options={TIPO_MATRICULA_FILTROS} />
          <button className={carregando ? 'ui-button monitoring-refresh-button is-loading' : 'ui-button monitoring-refresh-button'} type="button" onClick={atualizarAgora} disabled={carregando}>
            {carregando ? 'Atualizando...' : 'Atualizar'}
          </button>
        </div>
      </div>

      {carregando && <p className="monitoring-state">Carregando dados...</p>}
      {erro && <p className="monitoring-state error">{erro}</p>}
      {mensagemAtualizacao && !erro && <p className="monitoring-state success">{mensagemAtualizacao}</p>}
      {semDados && <p className="monitoring-state">Nenhum relatório de monitoria encontrado para este mês.</p>}

      {!carregando && !erro && dados && (
        <>
          <div className="monitoring-summary-grid">
            <MetricCard label="Presentes" value={resumo.presente} tone="present" active={statusFiltro === 'Presente'} onClick={() => setStatusFiltro('Presente')} />
            <MetricCard label="Faltas" value={resumo.falta} tone="absent" active={statusFiltro === 'Falta'} onClick={() => setStatusFiltro('Falta')} />
            <MetricCard label="Não agendado" value={resumo.aluno_nao_agendado} tone="unscheduled" active={statusFiltro === 'Não agendado'} onClick={() => setStatusFiltro('Não agendado')} />
            <MetricCard label="Finalizou" value={resumo.aluno_finalizou} tone="finished" active={statusFiltro === 'Finalizou'} onClick={() => setStatusFiltro('Finalizou')} />
            <MetricCard label="Total" value={resumo.total} tone="total" active={!statusFiltro} onClick={() => setStatusFiltro('')} />
          </div>
          <div className="monitors-legend" aria-label="Legenda dos status">
            <span className="legend-dot metric-present" /> Presente
            <span className="legend-dot metric-absent" /> Falta
            <span className="legend-dot metric-unscheduled" /> Não agendado
            <span className="legend-dot metric-finished" /> Finalizou
          </div>
          {periodoAplicado?.tipo && periodoAplicado.tipo !== 'mes' && (
            <p className="monitors-period-note">Período filtrado: {periodoAplicado.label}</p>
          )}

          {mostrarMotivosFalta && semDados && <MotivosFaltaCard motivos={resumoMotivosFalta} />}

          {!semDados && (
            <>
              <div className="monitors-section">
                <h3>Resumo por monitor no mês</h3>
                <MonitoresTabela linhas={resumoMonitorMes} />
              </div>

              {mostrarMotivosFalta && <MotivosFaltaCard motivos={resumoMotivosFalta} />}

              {dados.aviso_semanas ? (
                <p className="monitors-historical-note">{dados.aviso_semanas}</p>
              ) : (
                <div className="monitors-weeks">
                  {semanasFiltradas.map((semana) => (
                    <div className="week-panel" key={semana.semana}>
                      <div className="week-panel-head">
                        <div>
                          <h3>Semana {semana.semana} — {semana.periodo}</h3>
                          <span>Total: {semana.total_semana?.total || 0}</span>
                        </div>
                        <button className="ui-button week-toggle-button" type="button" onClick={() => alternarSemana(semana.semana)}>
                          {semanasAbertas[semana.semana] ? 'Ocultar semana' : 'Ver semana'}
                        </button>
                      </div>
                      {semanasAbertas[semana.semana] && <MonitoresTabela linhas={semana.monitores || []} total={semana.total_semana} />}
                    </div>
                  ))}
                </div>
              )}

              <div className="monitors-section">
                <div className="monitors-detail-head">
                  <h3>Monitorias do período</h3>
                  <button className="ui-button monitoring-refresh-button" type="button" onClick={() => setMostrarDetalhes((atual) => !atual)}>
                    {mostrarDetalhes ? 'Ocultar monitorias' : 'Ver monitorias'}
                  </button>
                </div>
                <p className="monitoring-state">{detalhes.length} monitorias encontradas</p>
                {dados.aviso_detalhes && <p className="monitors-historical-note">{dados.aviso_detalhes}</p>}
                {mostrarDetalhes && !dados.aviso_detalhes && <MonitoriasDetalhadasTabela linhas={detalhes} />}
              </div>
            </>
          )}
        </>
      )}
    </section>
  );
}

function MotivosFaltaCard({ motivos }) {
  const [outroAberto, setOutroAberto] = useState(false);
  const linhas = motivos || [];
  const total = linhas.reduce((soma, item) => soma + Number(item.total || 0), 0);
  const formatarPercentual = (valor) => `${Number(valor || 0).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;

  return (
    <div className="monitors-section absence-reasons-card">
      <div className="absence-reasons-head">
        <div>
          <h3>Motivos das faltas</h3>
          <p>Distribuição dos motivos de falta no período filtrado</p>
        </div>
        <span>Total analisado: {total}</span>
      </div>

      {linhas.length === 0 ? (
        <p className="monitoring-state">Nenhum motivo de falta encontrado para os filtros selecionados.</p>
      ) : (
        <div className="absence-reasons-table-wrap">
          <table className="absence-reasons-table">
            <thead>
              <tr>
                <th>Motivo da falta</th>
                <th>Quantidade</th>
                <th>Percentual</th>
              </tr>
            </thead>
            <tbody>
              {linhas.map((item) => {
                const percentual = Math.max(0, Math.min(100, Number(item.percentual || 0)));
                const detalhesOutro = item.motivo === 'Outro' ? (item.detalhes || []) : [];
                return (
                  <Fragment key={item.motivo}>
                    <tr>
                      <td>
                        <div className="absence-reason-name">
                          <span>{item.motivo}</span>
                          {detalhesOutro.length > 0 && (
                            <button className="absence-detail-toggle" type="button" onClick={() => setOutroAberto((atual) => !atual)}>
                              {outroAberto ? 'Ocultar detalhes' : 'Ver detalhes'}
                            </button>
                          )}
                        </div>
                      </td>
                      <td>{item.total || 0}</td>
                      <td>
                        <div className="absence-percent-cell">
                          <span>{formatarPercentual(item.percentual)}</span>
                          <div className="absence-percent-bar" aria-hidden="true">
                            <span style={{ width: `${percentual}%` }} />
                          </div>
                        </div>
                      </td>
                    </tr>
                    {item.motivo === 'Outro' && outroAberto && detalhesOutro.length > 0 && (
                      <tr className="absence-details-row">
                        <td colSpan={3}>
                          <div className="absence-details-list">
                            {detalhesOutro.map((detalhe) => <MotivoOutroDetalhe key={detalhe.texto} detalhe={detalhe} />)}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function MotivoOutroDetalhe({ detalhe }) {
  const [expandido, setExpandido] = useState(false);
  const texto = String(detalhe?.texto || '').trim();
  const textoLongo = texto.length > 180;

  return (
    <div className="absence-detail-item">
      <p className={expandido ? '' : 'clamped'}>{texto}</p>
      <div className="absence-detail-meta">
        <span>Quantidade: {detalhe?.total || 0}</span>
        {textoLongo && (
          <button className="absence-detail-toggle" type="button" onClick={() => setExpandido((atual) => !atual)}>
            {expandido ? 'Ver menos' : 'Ver mais'}
          </button>
        )}
      </div>
    </div>
  );
}

function NovoAlunoPerfilForm({ perfil, setPerfil }) {
  const setCampo = (campo, valor) => setPerfil((atual) => ({ ...atual, [campo]: valor }));
  const filhosInfo = parseFilhos(perfil.filhos_descricao);
  const filhos = filhosInfo.filhos;
  const setFilhos = (novosFilhos) => setCampo('filhos_descricao', stringifyFilhos(novosFilhos));

  return (
    <div style={styles.profileGrid} className="profile-grid new-student-profile-grid">
      <section style={{ ...styles.section, gridColumn: '1 / -1' }}>
        <h3><User size={18} /> Breve análise de perfil</h3>
        <textarea style={styles.textarea} value={perfil.analise_perfil || ''} onChange={(e) => setCampo('analise_perfil', e.target.value)} />
      </section>
      <section style={styles.section}>
        <h3><Briefcase size={18} /> Trabalho e Estudos</h3>
        <ProfileSelect label="Trabalha?" value={boolSelectValue(perfil.trabalha)} onChange={(v) => {
          const trabalha = boolFromSelect(v);
          setPerfil((atual) => ({
            ...atual,
            trabalha,
            trabalho_descricao: trabalha === true ? atual.trabalho_descricao : '',
            turno_trabalho: trabalha === true ? atual.turno_trabalho : '',
          }));
        }} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
        {perfil.trabalha === true && (
          <>
            <ProfileField label="Com o que trabalha?" value={perfil.trabalho_descricao} onChange={(v) => setCampo('trabalho_descricao', v)} />
            <ProfileSelect label="Turno de trabalho" value={perfil.turno_trabalho || ''} onChange={(v) => setCampo('turno_trabalho', v)} options={[['', 'Não informado'], ...TURNOS_TRABALHO.map((turno) => [turno, turno])]} />
          </>
        )}
        <ProfileField label="Em qual área profissional pretende trabalhar futuramente?" value={perfil.area_profissional_interesse} onChange={(v) => setCampo('area_profissional_interesse', v)} />
        <ProfileSelect label="Estuda?" value={boolSelectValue(perfil.estuda)} onChange={(v) => setCampo('estuda', boolFromSelect(v))} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
        {perfil.estuda === true && (
          <>
            <ProfileField label="Onde estuda?" value={perfil.estudo_instituicao} onChange={(v) => setCampo('estudo_instituicao', v)} />
            <ProfileField label="Qual curso?" value={perfil.estudo_curso} onChange={(v) => setCampo('estudo_curso', v)} />
            <ProfileSelect label="Turno de estudo" value={perfil.turno_estudo || ''} onChange={(v) => setCampo('turno_estudo', v)} options={[['', 'Não informado'], ...TURNOS.map((turno) => [turno, turno])]} />
          </>
        )}
      </section>
      <section style={styles.section}>
        <h3><Users size={18} /> Família</h3>
        <ProfileSelect label="Tem filhos?" value={boolSelectValue(perfil.tem_filhos)} onChange={(v) => {
          const temFilhos = boolFromSelect(v);
          setPerfil((atual) => ({ ...atual, tem_filhos: temFilhos, filhos_descricao: temFilhos === true ? atual.filhos_descricao : '' }));
        }} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
        {perfil.tem_filhos === true && (
          <>
            <ProfileSelect
              label="Quantidade de filhos"
              value={quantidadeFromFilhos(filhos)}
              onChange={(v) => setFilhos(ajustarQuantidadeFilhos(v, filhos))}
              options={[['', 'Selecione...'], ...QTD_FILHOS.map((qtd) => [qtd, qtd])]}
            />
            <div className="children-editor">
              {filhos.map((filho, index) => (
                <div key={index} className="child-row">
                  <ProfileField label={`Nome do filho ${index + 1}`} value={filho.nome} onChange={(v) => {
                    const novos = [...filhos];
                    novos[index] = { ...novos[index], nome: v };
                    setFilhos(novos);
                  }} />
                  <ProfileField label="Idade" value={filho.idade} onChange={(v) => {
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
        <ProfileSelect label="Nível de Engajamento" value={perfil.nivel_engajamento || ''} onChange={(v) => setCampo('nivel_engajamento', v)} options={[['', 'Não informado'], ['baixo', 'Baixo'], ['médio', 'Médio'], ['alto', 'Alto']]} color={pillColor(perfil.nivel_engajamento, ENG_COLORS)} />
        <ProfileSelect label="Nível de Conhecimento em Programação" value={perfil.nivel_programacao || ''} onChange={(v) => setCampo('nivel_programacao', v)} options={[['', 'Não informado'], ['básico', 'Básico'], ['intermediário', 'Intermediário'], ['avançado', 'Avançado']]} color={pillColor(perfil.nivel_programacao, PROG_COLORS)} />
        <ProfileField label="Ano de previsão de formação" type="number" value={perfil.previsao_formacao_ano || ''} onChange={(v) => setCampo('previsao_formacao_ano', v)} />
        <ProfileSelect label="Semestre de previsão" value={perfil.previsao_formacao_semestre || ''} onChange={(v) => setCampo('previsao_formacao_semestre', v)} options={[['', 'Não informado'], ['1º semestre', '1º semestre'], ['2º semestre', '2º semestre']]} />
      </section>
      <section style={styles.section}>
        <h3><Calendar size={18} /> Monitoria</h3>
        <ProfileSelect label="Dia da monitoria" value={perfil.dia_monitoria || ''} onChange={(v) => setCampo('dia_monitoria', v)} options={[['', 'Não informado'], ...DIAS_MONITORIA.map((dia) => [dia, dia])]} />
        <ProfileField label="Horário da monitoria" type="time" value={perfil.horario_monitoria} onChange={(v) => setCampo('horario_monitoria', v)} />
      </section>
      <section style={styles.section}>
        <h3><ShieldCheck size={18} /> Acompanhamento psicológico</h3>
        <ProfileSelect label="Faz acompanhamento?" value={boolSelectValue(perfil.acompanhamento_psicologico)} onChange={(v) => {
          const faz = boolFromSelect(v);
          setPerfil((atual) => ({ ...atual, acompanhamento_psicologico: faz, psicologo: faz === true ? atual.psicologo : '' }));
        }} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
        {perfil.acompanhamento_psicologico === true && (
          <ProfileSelect label="Psicólogo responsável" value={perfil.psicologo || ''} onChange={(v) => setCampo('psicologo', v)} options={[['', 'Selecione...'], ...PSICOLOGOS.map((nome) => [nome, nome])]} />
        )}
      </section>
    </div>
  );
}

function MonitoresTabela({ linhas, total }) {
  return (
    <div className="monitors-table-wrap">
      <table className="monitors-table">
        <thead>
          <tr>
            <th>Monitor</th>
            {MONITORIA_COLUNAS.map(([, label]) => <th key={label}>{label}</th>)}
          </tr>
        </thead>
        <tbody>
          {(linhas || []).map((linha) => (
            <tr key={linha.agente}>
              <td>{linha.agente}</td>
              {MONITORIA_COLUNAS.map(([campo]) => <td key={campo}>{linha[campo] || 0}</td>)}
            </tr>
          ))}
          {total && (
            <tr className="monitors-total-row">
              <td>Total da semana</td>
              {MONITORIA_COLUNAS.map(([campo]) => <td key={campo}>{total[campo] || 0}</td>)}
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function MonitoriasDetalhadasTabela({ linhas }) {
  const valorDetalhe = (valor) => String(valor || '').trim() || '—';
  return (
    <div className="monitorias-detail-scroll">
      <table className="monitorias-detail-table">
        <colgroup>
          <col className="col-data" />
          <col className="col-monitor" />
          <col className="col-aluno" />
          <col className="col-matricula" />
          <col className="col-status" />
          <col className="col-modulo" />
          <col className="col-curso" />
          <col className="col-motivo" />
          <col className="col-read" />
        </colgroup>
        <thead>
          <tr>
            <th>Data</th>
            <th>Monitor</th>
            <th>Aluno</th>
            <th>Matrícula</th>
            <th>Status</th>
            <th>Módulo</th>
            <th>Curso</th>
            <th>Motivo da falta</th>
            <th>READ IA</th>
          </tr>
        </thead>
        <tbody>
          {(linhas || []).map((linha, index) => {
            const statusClass = statusMonitoriaClass(linha.status);
            const ehPresente = statusClass === 'present';
            const ehFalta = statusClass === 'absent';
            return (
              <tr className={`detail-status-${statusClass}`} key={`${linha.data}-${linha.matricula}-${index}`}>
                <td>{formatarDataIso(linha.data)}</td>
                <td>{valorDetalhe(linha.monitor)}</td>
                <td className="text-cell" title={linha.aluno || ''}><span>{valorDetalhe(linha.aluno)}</span></td>
                <td>{valorDetalhe(linha.matricula)}</td>
                <td><span className={`monitoring-status-badge status-${statusClass}`}>{statusMonitoriaLabel(linha.status)}</span></td>
                <td className="text-cell" title={linha.modulo || ''}><span>{ehPresente ? valorDetalhe(linha.modulo) : '—'}</span></td>
                <td className="text-cell" title={linha.curso || ''}><span>{ehPresente ? valorDetalhe(linha.curso) : '—'}</span></td>
                <td className="text-cell" title={linha.motivo_falta || ''}><span>{ehFalta ? valorDetalhe(linha.motivo_falta) : '—'}</span></td>
                <td>{ehPresente && linha.read_ia_link ? <a className="read-ia-link compact" href={linha.read_ia_link} target="_blank" rel="noreferrer" title={linha.read_ia_link}>Abrir</a> : '—'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function RelatoriosMonitoria({ aluno, authHeaders }) {
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
    if (!aluno?.matricula) return;
    let cancelado = false;
    const carregar = async () => {
      setCarregando(true);
      setErro('');
      setMensagemAtualizacao('');
      try {
        const res = await axios.get(`${API_BASE_URL}/api/alunos/${encodeURIComponent(aluno.matricula)}/relatorios-monitoria`, { headers: authHeaders, timeout: 20000 });
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
  }, [aluno?.matricula, authHeaders]);

  const atualizarAgora = async () => {
    if (!aluno?.matricula || carregando || atualizando) return;
    setAtualizando(true);
    setCarregando(true);
    setErro('');
    setMensagemAtualizacao('');
    try {
      await axios.post(`${API_BASE_URL}/api/relatorios-monitoria/refresh`, {}, { headers: authHeaders, timeout: 12000 });
      const res = await axios.get(`${API_BASE_URL}/api/alunos/${encodeURIComponent(aluno.matricula)}/relatorios-monitoria`, { headers: authHeaders, timeout: 20000 });
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
            <ProfileField label="Data inicial" type="date" value={inicio} onChange={setInicio} />
            <ProfileField label="Data final" type="date" value={fim} onChange={setFim} />
            <ProfileSelect label="Status" value={status} onChange={setStatus} options={[['', 'Todos'], ...statusOptions.map((item) => [item, item])]} />
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
                          <DisplayItem label="Módulo" value={relatorio.modulo} compact />
                          <DisplayItem label="Curso" value={relatorio.curso} compact />
                          <DisplayItem label="READ IA" value={relatorio.read_ia_link ? <a className="read-ia-link" href={relatorio.read_ia_link} target="_blank" rel="noreferrer">Abrir READ IA</a> : ''} compact />
                        </div>
                        {!estaAberto && relatorio.relatorio && <p className="monitoring-preview">{resumoCurto(relatorio.relatorio)}</p>}
                      </>
                    )}

                    {ehFalta && (
                      <div className="monitoring-report-grid">
                        <DisplayItem label="Motivo da falta" value={relatorio.motivo_falta} compact />
                        {relatorio.outro_motivo && <DisplayItem label="Outro motivo" value={relatorio.outro_motivo} compact />}
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

function RelatoriosMonitoriaPlaceholder() {
  const placeholders = [
    'Presenças',
    'Faltas',
    'Última monitoria',
    'Observações',
  ];

  return (
    <section className="monitoring-reports" style={styles.section}>
      {/* Futuramente, esta aba deve consumir a aba "Relatórios Monitoria" da planilha Google via Google Sheets API. O Neon guarda dados estáveis dos alunos; relatórios recorrentes de formulários devem ser consultados ou sincronizados da planilha para evitar duplicação pesada. */}
      <div className="monitoring-empty-head">
        <ClipboardList size={22} />
        <div>
          <h3>Relatórios de Monitoria</h3>
          <p>Em breve, esta área exibirá presenças, faltas e informações registradas nas monitorias.</p>
        </div>
      </div>
      <div className="monitoring-placeholder-grid">
        {placeholders.map((titulo) => (
          <div key={titulo} className="monitoring-placeholder-card">
            <span>{titulo}</span>
            <strong>Em breve</strong>
          </div>
        ))}
      </div>
    </section>
  );
}
void RelatoriosMonitoriaPlaceholder;

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

function ProfileField({ label, value, onChange, disabled, type = 'text', autoComplete }) {
  return (
    <label style={{ display: 'block', marginTop: '10px' }}>
      <span style={styles.label}>{label}</span>
      <input type={type} style={styles.fieldInput} value={value || ''} disabled={disabled} onChange={(e) => onChange(e.target.value)} autoComplete={autoComplete} />
    </label>
  );
}

function ProfileSelect({ label, value, onChange, disabled, options, color }) {
  return (
    <label style={{ display: 'block', marginTop: '10px' }}>
      <span style={styles.label}>{label}</span>
      <select style={{ ...styles.fieldInput, color: color || 'var(--pd-text)', fontWeight: color ? 800 : 500 }} value={value} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
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
