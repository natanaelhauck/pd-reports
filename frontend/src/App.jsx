import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { Save, X, LogIn, Moon, Sun, Eye, EyeOff } from 'lucide-react';
import pdLogo from './assets/pd-logo.svg';
import { AppHeader } from './components/AppHeader.jsx';
import { CourseHoursDashboard } from './components/CourseHoursDashboard.jsx';
import { MainNavigation } from './components/MainNavigation.jsx';
import { StudentSearchBar } from './components/StudentSearchBar.jsx';
import { StudentProfileShell } from './components/StudentProfileShell.jsx';
import { StudentMainDataTab } from './components/StudentMainDataTab.jsx';
import { StudentProfileDataTab } from './components/StudentProfileDataTab.jsx';
import { StudentHistoryTab } from './components/StudentHistoryTab.jsx';
import { StudentMonitoringReportsTab } from './components/StudentMonitoringReportsTab.jsx';
import { StudentConsumptionTab } from './components/StudentConsumptionTab.jsx';
import { UserManagementPanel } from './components/UserManagementPanel.jsx';
import { NewStudentPanel } from './components/NewStudentPanel.jsx';
import { useUsersManagement } from './hooks/useUsersManagement.js';
import { useAlunoSearch } from './hooks/useAlunoSearch.js';
import { useStudentHistory } from './hooks/useStudentHistory.js';
import { useStudentMainData } from './hooks/useStudentMainData.js';
import { useStudentProfileData } from './hooks/useStudentProfileData.js';
import { useNewStudentForm } from './hooks/useNewStudentForm.js';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:5000').replace(/\/$/, '');
const MONITORES = ['Alex', 'André', 'Douglas', 'Gabriel', 'Kellen', 'Natanael'];
const MONITORES_DASHBOARD = ['Alex', 'André', 'Douglas', 'Gabriel', 'Kellen', 'Natanael'];
const STATUS_OPTIONS = ['MANTER', 'EM ANÁLISE', 'REMOVIDO', 'DESLIGADO'];
const TABS = ['Dados principais', 'Perfil do aluno', 'Relatórios Monitoria', 'Consumo', 'Histórico'];
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
const PREFEITURA_MUNICIPAL_SCOPES = {
  prefeitura_itabira: {
    label: 'Itabira - Prefeitura',
    tipoMatricula: 'pdita',
    filtroLabel: 'Itabira - PDITA',
  },
  prefeitura_bom_despacho: {
    label: 'Bom Despacho - Prefeitura',
    tipoMatricula: 'pdbd',
    filtroLabel: 'Bom Despacho - PDBD',
  },
};

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
const CAMPOS_PERFIL_FORM = Object.keys(PERFIL_CADASTRO_INICIAL());

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

const normalizarPerfil = (perfil = {}) => {
  const normalizado = PERFIL_INICIAL(perfil.matricula);
  CAMPOS_PERFIL_FORM.forEach((campo) => {
    if (Object.prototype.hasOwnProperty.call(perfil, campo)) {
      normalizado[campo] = perfil[campo];
    }
  });
  return normalizado;
};

const montarPayloadPerfil = (perfil = {}, matricula = '') => {
  const normalizado = normalizarPerfil({ ...perfil, matricula });
  return {
    matricula: normalizado.matricula,
    ...Object.fromEntries(CAMPOS_PERFIL_FORM.map((campo) => [campo, normalizado[campo]])),
  };
};
const aguardar = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const erroDeConexao = (err) => (
  !err.response
  || err.code === 'ECONNABORTED'
  || err.code === 'ERR_NETWORK'
  || [502, 503, 504].includes(err.response?.status)
);

const mensagemErroApi = (err, fallback) => {
  return err.response?.data?.erro || fallback;
};

const mensagemErroAbrirAluno = (err) => {
  if (err?.code === 'ECONNABORTED') {
    return 'Não foi possível abrir o aluno selecionado. O servidor demorou para responder.';
  }
  return err?.response?.data?.erro || 'Não foi possível abrir o aluno selecionado. Tente novamente em instantes.';
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
  ['prefeitura_itabira', 'Itabira - Prefeitura'],
  ['prefeitura_bom_despacho', 'Bom Despacho - Prefeitura'],
];

const prefeituraMunicipalScope = (usuario) => PREFEITURA_MUNICIPAL_SCOPES[usuario?.role] || null;

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
  const prefeitura = prefeituraMunicipalScope(usuario);
  if (prefeitura) return nome || prefeitura.label;
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
  const prefeitura = prefeituraMunicipalScope(usuario);
  if (prefeitura) return prefeitura.label;
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
  modalOverlay: { position: 'fixed', inset: 0, zIndex: 40, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '18px', background: 'rgba(15, 23, 42, 0.55)', backdropFilter: 'blur(2px)' },
  modalCard: { width: 'min(100%, 520px)', background: 'var(--pd-surface)', border: '1px solid var(--pd-border)', borderRadius: '14px', padding: '18px', boxShadow: '0 18px 50px rgba(15, 23, 42, 0.22)', textAlign: 'left' },
  modalHead: { display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px', marginBottom: '14px' },
  modalTitle: { margin: 0, color: 'var(--pd-title)', fontSize: '18px', fontWeight: '850', lineHeight: 1.2 },
  modalSubtitle: { marginTop: '4px', color: 'var(--pd-muted)', fontSize: '13px' },
  modalGrid: { display: 'grid', gap: '10px' },
  modalActions: { display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '10px', marginTop: '16px', flexWrap: 'wrap' },
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
  const [aluno, setAluno] = useState(null);
  const [activeTab, setActiveTab] = useState('Dados principais');
  const [mensagem, setMensagem] = useState(null);
  const [mostrarNovoAluno, setMostrarNovoAluno] = useState(false);
  const [mostrarUsuarios, setMostrarUsuarios] = useState(false);
  const [mostrarMonitores, setMostrarMonitores] = useState(false);
  const [mostrarIntegralizacao, setMostrarIntegralizacao] = useState(false);
  const [voltarParaListaConsumo, setVoltarParaListaConsumo] = useState(false);
  const [mostrarAlterarSenha, setMostrarAlterarSenha] = useState(false);
  const [alterandoMinhaSenha, setAlterandoMinhaSenha] = useState(false);
  const cardRef = useRef(null);
  const atualizarAlunoNosResultadosRef = useRef(() => {});
  const isAdmin = usuario?.role === 'admin';
  const isPrefeituraMunicipal = Boolean(prefeituraMunicipalScope(usuario));
  const autenticado = Boolean(usuario?.token);
  const authHeaders = useMemo(() => (
    usuario?.token ? { Authorization: `Bearer ${usuario.token}` } : {}
  ), [usuario]);
  const authConfig = (config = {}) => ({
    ...config,
    headers: { ...(config.headers || {}), ...authHeaders },
  });
  const usersManagement = useUsersManagement({
    apiBaseUrl: API_BASE_URL,
    authHeaders,
    isAdmin,
    setMensagem,
    getErrorMessage: mensagemErroApi,
  });
  const studentHistory = useStudentHistory({
    apiBaseUrl: API_BASE_URL,
    authHeaders,
    mensagemErroApi,
    setMensagem,
  });
  const profileData = useStudentProfileData({
    aluno,
    apiBaseUrl: API_BASE_URL,
    authHeaders,
    mensagemErroApi,
    setMensagem,
    perfilInicial: PERFIL_INICIAL,
    normalizarPerfil,
    montarPayloadPerfil,
    carregarHistorico: studentHistory.carregarHistorico,
    activeTab,
  });
  const atualizarAlunoNosResultados = useCallback((atualizado) => {
    atualizarAlunoNosResultadosRef.current(atualizado);
  }, []);
  const mainData = useStudentMainData({
    aluno,
    setAluno,
    apiBaseUrl: API_BASE_URL,
    authHeaders,
    mensagemErroApi,
    setMensagem,
    criarTempSeguro,
    normalizarMonitor,
    normalizarStatus,
    atualizarAlunoNosResultados,
  });
  const alunoSearch = useAlunoSearch({
    apiBaseUrl: API_BASE_URL,
    authHeaders,
    aluno,
    setAluno,
    setActiveTab,
    limparHistorico: studentHistory.limparHistorico,
    setMensagem,
    setVoltarParaListaConsumo,
    setMostrarNovoAluno,
    setMostrarUsuarios,
    setMostrarMonitores,
    setMostrarIntegralizacao,
    prepararDadosPrincipais: mainData.sincronizarComAluno,
    resetarDadosPrincipais: mainData.resetarDadosPrincipais,
    prepararPerfilInicial: profileData.prepararPerfilInicial,
    limparPerfil: profileData.limparPerfil,
    mensagemErroApi,
    mensagemErroAbrirAluno,
    cardRef,
  });
  useEffect(() => {
    atualizarAlunoNosResultadosRef.current = alunoSearch.atualizarAlunoNosResultados;
  }, [alunoSearch.atualizarAlunoNosResultados]);
  const { adicionarAlunoAResultados } = alunoSearch;
  const { sincronizarComAluno } = mainData;
  const { sincronizarPerfil } = profileData;
  const fecharNovoAluno = useCallback(() => {
    setMostrarNovoAluno(false);
  }, []);
  const handleNovoAlunoCriado = useCallback((dadosCriacao) => {
    const criado = dadosCriacao.aluno;
    adicionarAlunoAResultados(criado);
    setAluno(criado);
    sincronizarComAluno(criado);
    if (dadosCriacao.perfil) {
      const perfilCriado = normalizarPerfil(dadosCriacao.perfil);
      sincronizarPerfil(perfilCriado);
    } else {
      const perfilInicial = PERFIL_INICIAL(criado.matricula);
      sincronizarPerfil(perfilInicial);
    }
  }, [
    adicionarAlunoAResultados,
    sincronizarComAluno,
    sincronizarPerfil,
  ]);
  const newStudentForm = useNewStudentForm({
    apiBaseUrl: API_BASE_URL,
    authHeaders,
    isAdmin,
    setMensagem,
    mensagemErroApi,
    novoAlunoInicial: NOVO_ALUNO_INICIAL,
    perfilCadastroInicial: PERFIL_CADASTRO_INICIAL,
    perfilCadastroTemDados,
    normalizarMonitor,
    normalizarStatus,
    onCreated: handleNovoAlunoCriado,
    onClose: fecharNovoAluno,
  });
  const temaEscuro = tema === 'dark';
  const tabsVisiveis = useMemo(() => (
    isPrefeituraMunicipal ? TABS.filter((tab) => tab !== 'Relatórios Monitoria' && tab !== 'Histórico') : TABS
  ), [isPrefeituraMunicipal]);

  const estiloMensagem = mensagem?.tipo === 'sucesso'
    ? { background: '#ecfdf5', color: '#166534', border: '1px solid #bbf7d0' }
    : mensagem?.tipo === 'aviso'
      ? { background: '#fffbeb', color: '#92400e', border: '1px solid #fde68a' }
      : { background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca' };

  const limparEstadoAplicacao = () => {
    alunoSearch.resetBuscaGeral();
    setAluno(null);
    mainData.resetarDadosPrincipais();
    setActiveTab('Dados principais');
    profileData.limparPerfil();
    setMensagem(null);
    studentHistory.limparHistorico();
    setMostrarNovoAluno(false);
    setMostrarUsuarios(false);
    setMostrarMonitores(false);
    setMostrarIntegralizacao(false);
    setVoltarParaListaConsumo(false);
    newStudentForm.limparNovoAluno();
    usersManagement.limparGestaoUsuarios();
    setMostrarAlterarSenha(false);
    setAlterandoMinhaSenha(false);
  };

  const voltarParaInicio = () => {
    alunoSearch.resetBuscaGeral();
    setAluno(null);
    mainData.resetarDadosPrincipais();
    setActiveTab('Dados principais');
    profileData.limparPerfil();
    setMensagem(null);
    studentHistory.limparHistorico();
    setMostrarNovoAluno(false);
    setMostrarUsuarios(false);
    setMostrarMonitores(false);
    setMostrarIntegralizacao(false);
    setVoltarParaListaConsumo(false);
    newStudentForm.limparNovoAluno();
    usersManagement.limparGestaoUsuarios();
    setMostrarAlterarSenha(false);
    setAlterandoMinhaSenha(false);
  };

  const selecionarTab = (tab) => {
    if (!tabsVisiveis.includes(tab)) return;
    setActiveTab(tab);
    if (tab === 'Perfil do aluno' && aluno) profileData.carregarPerfilAluno(aluno.matricula);
    if (tab === 'Histórico' && aluno && !isPrefeituraMunicipal) studentHistory.carregarHistorico(aluno.matricula);
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
    setMostrarAlterarSenha(false);
    setAlterandoMinhaSenha(false);
  };

  const abrirNovoAluno = () => {
    alunoSearch.fecharAlunoSelecionado();
    setMostrarMonitores(false);
    setMostrarUsuarios(false);
    setMostrarIntegralizacao(false);
    setMostrarNovoAluno(true);
    newStudentForm.prepararNovoAluno();
    setMensagem(null);
  };

  const abrirUsuarios = async () => {
    alunoSearch.fecharAlunoSelecionado();
    setMostrarMonitores(false);
    setMostrarIntegralizacao(false);
    setMostrarNovoAluno(false);
    usersManagement.resetarFormularioUsuarios();
    const carregou = await usersManagement.carregarUsuarios();
    if (carregou) setMostrarUsuarios(true);
  };

  const abrirMonitores = () => {
    alunoSearch.fecharAlunoSelecionado();
    setMostrarNovoAluno(false);
    setMostrarUsuarios(false);
    setMostrarIntegralizacao(false);
    setMostrarMonitores(true);
    setMensagem(null);
  };

  const abrirConsumo = () => {
    alunoSearch.fecharAlunoSelecionado();
    setMostrarNovoAluno(false);
    setMostrarUsuarios(false);
    setMostrarMonitores(false);
    setMostrarIntegralizacao(true);
    setVoltarParaListaConsumo(false);
    setMensagem(null);
  };

  const alterarMinhaSenha = async ({ senhaAtual, novaSenha, confirmacaoNovaSenha }) => {
    if (alterandoMinhaSenha) return;
    setAlterandoMinhaSenha(true);
    setMensagem(null);
    try {
      const res = await axios.post(`${API_BASE_URL}/api/usuarios/me/password`, {
        senha_atual: senhaAtual,
        nova_senha: novaSenha,
        confirmacao_nova_senha: confirmacaoNovaSenha,
      }, authConfig({ timeout: 12000 }));
      setMostrarAlterarSenha(false);
      setMensagem({ tipo: 'sucesso', texto: res.data.mensagem || 'Senha alterada com sucesso.' });
    } catch (err) {
      setMensagem({ tipo: 'erro', texto: mensagemErroApi(err, 'Erro ao alterar a própria senha.') });
    } finally {
      setAlterandoMinhaSenha(false);
    }
  };

  const activeSection = useMemo(() => {
    if (mostrarMonitores) return 'monitores';
    if (mostrarIntegralizacao || (voltarParaListaConsumo && activeTab === 'Consumo')) return 'consumo';
    if (mostrarNovoAluno) return 'novo-aluno';
    if (mostrarUsuarios) return 'usuarios';

    const telaInicialLimpa = !mostrarMonitores
      && !mostrarIntegralizacao
      && !mostrarNovoAluno
      && !mostrarUsuarios
      && !aluno
      && !alunoSearch.busca
      && !alunoSearch.buscaRealizada
      && alunoSearch.alunos.length === 0;

    return telaInicialLimpa ? 'inicio' : null;
  }, [
    mostrarMonitores,
    mostrarIntegralizacao,
    mostrarNovoAluno,
    mostrarUsuarios,
    aluno,
    alunoSearch.busca,
    alunoSearch.buscaRealizada,
    alunoSearch.alunos.length,
    voltarParaListaConsumo,
    activeTab,
  ]);

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

  const statusAtual = mainData.editMode ? mainData.temp.status : aluno?.status;
  const corStatus = getStatusColor(statusAtual);

  return (
    <div className={temaEscuro ? 'theme-dark app-shell' : 'theme-light app-shell'} style={(mostrarMonitores || mostrarIntegralizacao) ? { ...styles.container, maxWidth: '1500px' } : styles.container}>
      <AppHeader
        userLabel={formatarUsuario(usuario)}
        isDarkTheme={temaEscuro}
        onHome={voltarParaInicio}
        onToggleTheme={alternarTema}
        onLogout={sair}
        onOpenPasswordModal={() => setMostrarAlterarSenha(true)}
        styles={styles}
      />

      <MainNavigation
        activeSection={activeSection}
        canViewMonitores={!isPrefeituraMunicipal}
        canViewConsumo
        canCreateAluno={isAdmin}
        canManageUsuarios={isAdmin}
        onHome={voltarParaInicio}
        onMonitores={abrirMonitores}
        onConsumo={abrirConsumo}
        onNovoAluno={abrirNovoAluno}
        onUsuarios={abrirUsuarios}
      />

      <StudentSearchBar
        value={alunoSearch.busca}
        onChange={alunoSearch.setBusca}
        onSubmit={alunoSearch.buscarAlunos}
        onClear={() => alunoSearch.limparBuscaGeral()}
        loading={alunoSearch.buscando}
        styles={styles}
      />

      {mensagem && <div style={{ ...styles.message, ...estiloMensagem }}>{mensagem.texto}</div>}

      {mostrarAlterarSenha && (
        <AlterarSenhaPropriaModal
          aberto={mostrarAlterarSenha}
          carregando={alterandoMinhaSenha}
          onClose={() => setMostrarAlterarSenha(false)}
          onSubmit={alterarMinhaSenha}
        />
      )}

      {mostrarMonitores && (
        <MonitoresDashboard usuario={usuario} authHeaders={authHeaders} />
      )}

      {mostrarIntegralizacao && (
        <CourseHoursDashboard
          apiBaseUrl={API_BASE_URL}
          authHeaders={authHeaders}
          usuario={usuario}
          onSelectStudent={alunoSearch.selecionarAlunoConsumo}
        />
      )}

      {isAdmin && mostrarNovoAluno && (
        <NewStudentPanel
          novoAluno={newStudentForm.novoAluno}
          novoAlunoPerfil={newStudentForm.novoAlunoPerfil}
          mostrarPerfilNovoAluno={newStudentForm.mostrarPerfilNovoAluno}
          salvandoNovoAluno={newStudentForm.salvandoNovoAluno}
          styles={styles}
          statusOptions={STATUS_OPTIONS}
          monitores={MONITORES}
          turnos={TURNOS}
          turnosTrabalho={TURNOS_TRABALHO}
          diasMonitoria={DIAS_MONITORIA}
          qtdFilhos={QTD_FILHOS}
          psicologos={PSICOLOGOS}
          engColors={ENG_COLORS}
          progColors={PROG_COLORS}
          boolSelectValue={boolSelectValue}
          boolFromSelect={boolFromSelect}
          parseFilhos={parseFilhos}
          stringifyFilhos={stringifyFilhos}
          quantidadeFromFilhos={quantidadeFromFilhos}
          ajustarQuantidadeFilhos={ajustarQuantidadeFilhos}
          pillColor={pillColor}
          onNovoAlunoChange={newStudentForm.setNovoAluno}
          onNovoAlunoPerfilChange={newStudentForm.setNovoAlunoPerfil}
          onTogglePerfil={newStudentForm.alternarPerfilNovoAluno}
          onSave={newStudentForm.cadastrarAluno}
          onCancel={newStudentForm.cancelarNovoAluno}
        />
      )}

      {isAdmin && mostrarUsuarios && (
        <UserManagementPanel
          usuarios={usersManagement.usuarios}
          novoUsuario={usersManagement.novoUsuario}
          usuarioTemp={usersManagement.usuarioTemp}
          usuarioEditando={usersManagement.usuarioEditando}
          senhaUsuarioEditando={usersManagement.senhaUsuarioEditando}
          novaSenhaUsuario={usersManagement.novaSenhaUsuario}
          mostrarSenhaUsuario={usersManagement.mostrarSenhaUsuario}
          perfisUsuario={PERFIS_USUARIO}
          salvandoUsuario={usersManagement.salvandoUsuario}
          salvandoUsuarioEditando={usersManagement.salvandoUsuarioEditando}
          salvandoSenhaUsuario={usersManagement.salvandoSenhaUsuario}
          styles={styles}
          formatarUsuario={formatarUsuario}
          rotuloPerfilUsuario={rotuloPerfilUsuario}
          onClose={() => setMostrarUsuarios(false)}
          onSubmitNovoUsuario={usersManagement.cadastrarUsuario}
          onNovoUsuarioChange={usersManagement.setNovoUsuario}
          onUsuarioTempChange={usersManagement.setUsuarioTemp}
          onEditarUsuario={usersManagement.editarUsuario}
          onCancelarEdicaoUsuario={usersManagement.cancelarEdicaoUsuario}
          onSalvarUsuario={usersManagement.salvarUsuario}
          onIniciarEdicaoSenha={usersManagement.iniciarEdicaoSenha}
          onCancelarEdicaoSenha={usersManagement.cancelarEdicaoSenha}
          onNovaSenhaUsuarioChange={usersManagement.setNovaSenhaUsuario}
          onToggleMostrarSenhaUsuario={usersManagement.alternarMostrarSenhaUsuario}
          onSalvarSenhaUsuario={usersManagement.salvarSenhaUsuario}
        />
      )}

      {aluno && (
        <StudentProfileShell
          aluno={aluno}
          activeTab={activeTab}
          tabs={tabsVisiveis}
          onTabChange={selecionarTab}
          onClose={alunoSearch.fecharAlunoSelecionado}
          cardRef={cardRef}
          statusLabel={statusDisplay(statusAtual)}
          statusColor={corStatus}
          editMode={mainData.editMode}
          nameValue={mainData.temp.nome}
          onNameChange={(nome) => mainData.setCampoTemp('nome', nome)}
          styles={styles}
        >
          {activeTab === 'Dados principais' && (
            <StudentMainDataTab
              aluno={aluno}
              temp={mainData.temp}
              editMode={mainData.editMode}
              onEdit={mainData.iniciarEdicao}
              onSave={mainData.salvarEdicao}
              onCancel={mainData.cancelarEdicao}
              onFieldChange={mainData.setCampoTemp}
              salvando={mainData.salvando}
              corStatus={corStatus}
              somenteLeitura={isPrefeituraMunicipal}
              styles={styles}
              statusOptions={STATUS_OPTIONS}
              monitores={MONITORES}
              statusDisplay={statusDisplay}
              monitorDisplay={monitorDisplay}
            />
          )}
          {activeTab === 'Perfil do aluno' && (
            <StudentProfileDataTab
              perfil={profileData.perfil}
              perfilTemp={profileData.perfilTemp}
              editPerfil={profileData.editPerfil}
              somenteLeitura={isPrefeituraMunicipal}
              salvandoPerfil={profileData.salvandoPerfil}
              styles={styles}
              turnos={TURNOS}
              turnosTrabalho={TURNOS_TRABALHO}
              diasMonitoria={DIAS_MONITORIA}
              qtdFilhos={QTD_FILHOS}
              psicologos={PSICOLOGOS}
              engColors={ENG_COLORS}
              progColors={PROG_COLORS}
              boolSelectValue={boolSelectValue}
              boolFromSelect={boolFromSelect}
              parseFilhos={parseFilhos}
              stringifyFilhos={stringifyFilhos}
              filhosResumo={filhosResumo}
              quantidadeFromFilhos={quantidadeFromFilhos}
              ajustarQuantidadeFilhos={ajustarQuantidadeFilhos}
              pillColor={pillColor}
              onEdit={profileData.iniciarEdicaoPerfil}
              onCancel={profileData.cancelarEdicaoPerfil}
              onSave={profileData.salvarPerfil}
              setPerfilTemp={profileData.setPerfilTemp}
            />
          )}

          {activeTab === 'Histórico' && (
            <StudentHistoryTab
              historico={studentHistory.historico}
              carregandoHistorico={studentHistory.carregandoHistorico}
              styles={styles}
              rotuloCampoHistorico={rotuloCampoHistorico}
              formatarUsuarioHistorico={formatarUsuarioHistorico}
              formatarData={formatarData}
            />
          )}

          {activeTab === 'Relatórios Monitoria' && (
            <StudentMonitoringReportsTab
              aluno={aluno}
              authHeaders={authHeaders}
              apiBaseUrl={API_BASE_URL}
              styles={styles}
              mensagemErroApi={mensagemErroApi}
              formatarDataIso={formatarDataIso}
              statusMonitoriaClass={statusMonitoriaClass}
              statusMonitoriaLabel={statusMonitoriaLabel}
              resumoCurto={resumoCurto}
            />
          )}

          {activeTab === 'Consumo' && (
            <StudentConsumptionTab
              aluno={aluno}
              apiBaseUrl={API_BASE_URL}
              authHeaders={authHeaders}
              showBackToList={voltarParaListaConsumo}
              onBackToList={alunoSearch.voltarParaConsumoGeral}
            />
          )}
        </StudentProfileShell>
      )}

      {!mostrarMonitores && !mostrarIntegralizacao && alunoSearch.buscaRealizada && alunoSearch.resultadosVisiveis.length > 0 && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--pd-title)', margin: 0 }}>Resultados</h2>
            <span style={{ fontSize: '13px', color: 'var(--pd-muted)', fontWeight: 700 }}>{alunoSearch.alunosOrdenados.length} aluno(s)</span>
          </div>
          <div style={styles.results}>
            {alunoSearch.resultadosVisiveis.map((item) => {
              const selecionado = aluno?.matricula === item.matricula;
              const itemColor = getStatusColor(item.status);
              return (
                <button className={`result-button${selecionado ? ' selected' : ''}`} type="button" key={item.matricula || item.id} style={{ ...styles.resultBtn, borderColor: selecionado ? itemColor : 'var(--pd-border)', backgroundColor: selecionado ? `${itemColor}0d` : 'var(--pd-surface)' }} onClick={() => alunoSearch.selecionarAluno(item)}>
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
  const prefeituraScope = prefeituraMunicipalScope(usuario);
  const isPrefeituraMunicipal = Boolean(prefeituraScope);
  const monitorUsuario = monitorDoUsuario(usuario);
  const monitorEfetivo = usuario?.role === 'monitor' ? monitorUsuario : (isAdmin ? monitorFiltro : '');
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
      tipo_matricula: prefeituraScope?.tipoMatricula || tipoMatriculaFiltro,
    };
    if (periodoFiltroEfetivo === 'dia') params.data_periodo = dataPeriodoEfetiva;
    return params;
  }, [mes, monitorEfetivo, statusFiltro, periodoFiltroEfetivo, tipoMatriculaFiltro, dataPeriodoEfetiva, prefeituraScope]);

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
          ) : isPrefeituraMunicipal ? (
            <ProfileField label="Monitor" value="Todos" disabled onChange={() => {}} />
          ) : (
            <ProfileField label="Monitor" value={monitorUsuario || 'Monitor'} disabled onChange={() => {}} />
          )}
          <ProfileSelect label="Status" value={statusFiltro} onChange={setStatusFiltro} options={STATUS_MONITORIA_FILTROS} />
          <ProfileSelect label="Período" value={periodoFiltroEfetivo} onChange={setPeriodoFiltro} options={periodoOptions} />
          {periodoFiltroEfetivo === 'dia' && <ProfileField label="Data" type="date" value={dataPeriodoEfetiva} onChange={setDataPeriodo} />}
          {isPrefeituraMunicipal ? (
            <ProfileField label="Cidade - Matrícula" value={prefeituraScope?.filtroLabel || ''} disabled onChange={() => {}} />
          ) : (
            <ProfileSelect label="Cidade - Matrícula" value={tipoMatriculaFiltro} onChange={setTipoMatriculaFiltro} options={TIPO_MATRICULA_FILTROS} />
          )}
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

function AlterarSenhaPropriaModal({ aberto, carregando, onClose, onSubmit }) {
  const [senhaAtual, setSenhaAtual] = useState('');
  const [novaSenha, setNovaSenha] = useState('');
  const [confirmacaoNovaSenha, setConfirmacaoNovaSenha] = useState('');

  useEffect(() => {
    if (!aberto) return undefined;
    const aoPressionarTecla = (event) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', aoPressionarTecla);
    return () => window.removeEventListener('keydown', aoPressionarTecla);
  }, [aberto, onClose]);

  if (!aberto) return null;

  const enviar = (event) => {
    event.preventDefault();
    onSubmit({
      senhaAtual,
      novaSenha,
      confirmacaoNovaSenha,
    });
  };

  return (
    <div
      role="presentation"
      style={styles.modalOverlay}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <form role="dialog" aria-modal="true" aria-label="Alterar minha senha" onSubmit={enviar} style={styles.modalCard}>
        <div style={styles.modalHead}>
          <div>
            <h2 style={styles.modalTitle}>Alterar minha senha</h2>
            <p style={styles.modalSubtitle}>A mudança vale só para o usuário logado.</p>
          </div>
          <button className="ui-button" type="button" aria-label="Fechar" title="Fechar" onClick={onClose} style={styles.iconBtn}>
            <X size={17} />
          </button>
        </div>

        <div style={styles.modalGrid}>
          <ProfileField label="Senha atual" type="password" value={senhaAtual} onChange={setSenhaAtual} autoComplete="current-password" />
          <ProfileField label="Nova senha" type="password" value={novaSenha} onChange={setNovaSenha} autoComplete="new-password" />
          <ProfileField label="Confirmar nova senha" type="password" value={confirmacaoNovaSenha} onChange={setConfirmacaoNovaSenha} autoComplete="new-password" />
        </div>

        <div style={styles.modalActions}>
          <button className="ui-button" type="submit" disabled={carregando} style={styles.primaryBtn}>
            <Save size={17} /> {carregando ? 'Salvando...' : 'Salvar senha'}
          </button>
          <button className="ui-button" type="button" disabled={carregando} onClick={onClose} style={styles.secondaryBtn}>
            Cancelar
          </button>
        </div>
      </form>
    </div>
  );
}
