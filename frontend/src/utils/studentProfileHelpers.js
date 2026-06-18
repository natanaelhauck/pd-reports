import { MONITORES, STATUS_COLORS } from '../constants/studentProfileOptions.js';

export const PERFIL_INICIAL = (matricula = '') => ({
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

export const NOVO_ALUNO_INICIAL = { nome: '', matricula: '', telefone: '', email: '', nascimento: '', patrimonio: '', monitor: '', status: 'MANTER' };

export const PERFIL_CADASTRO_INICIAL = () => {
  const perfil = PERFIL_INICIAL();
  delete perfil.matricula;
  return perfil;
};

export const CAMPOS_PERFIL_FORM = Object.keys(PERFIL_CADASTRO_INICIAL());

export const CAMPO_LABELS = {
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

export const semAcentos = (valor) => String(valor || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '');

export const valorVazio = (valor) => {
  const texto = String(valor ?? '').trim().toLowerCase();
  return !texto || ['-', 'nan', 'none', 'null', 'não informado', 'nao informado'].includes(texto);
};

export const normalizarStatus = (status) => {
  if (valorVazio(status)) return '';
  const chave = semAcentos(status).toUpperCase();
  if (['DESLIGAR', 'DESLIGADO', 'DESLIGADA', 'INATIVO', 'CANCELADO'].some((p) => chave.includes(p))) return 'DESLIGADO';
  if (['REMOVIDOS', 'REMOVIDO', 'REMOVER'].some((p) => chave.includes(p))) return 'REMOVIDO';
  if (['EM ANALISE', 'ANALISE'].some((p) => chave.includes(p))) return 'EM ANÁLISE';
  if (['MANTER', 'ATIVO', 'CURSANDO', 'CONTINUA', 'CONTINUAR'].some((p) => chave.includes(p))) return 'MANTER';
  return '';
};

export const normalizarMonitor = (monitor) => {
  if (valorVazio(monitor)) return '';
  const local = String(monitor).trim().split('@')[0].replace(/\d+/g, '');
  const chave = semAcentos(local).toLowerCase().replace(/[^a-z]/g, '');
  return MONITORES.find((m) => {
    const monitorChave = semAcentos(m).toLowerCase();
    return chave === monitorChave || chave.startsWith(monitorChave);
  }) || '';
};

export const monitorDisplay = (monitor) => normalizarMonitor(monitor) || 'Não informado';
export const statusDisplay = (status) => normalizarStatus(status) || 'NÃO INFORMADO';
export const getStatusColor = (status) => STATUS_COLORS[normalizarStatus(status)] || STATUS_COLORS[''];
export const pillColor = (valor, mapa) => mapa[semAcentos(valor).toLowerCase()] || '#64748b';

export const criarTempSeguro = (aluno = {}) => ({
  nome: aluno.nome ?? '',
  telefone: aluno.telefone ?? '',
  email: aluno.email ?? '',
  matricula: aluno.matricula ?? '',
  nascimento: aluno.nascimento ?? '',
  patrimonio: aluno.patrimonio ?? '',
  monitor: normalizarMonitor(aluno.monitor),
  status: normalizarStatus(aluno.status),
});

export const normalizarPerfil = (perfil = {}) => {
  const normalizado = PERFIL_INICIAL(perfil.matricula);
  CAMPOS_PERFIL_FORM.forEach((campo) => {
    if (Object.prototype.hasOwnProperty.call(perfil, campo)) {
      normalizado[campo] = perfil[campo];
    }
  });
  return normalizado;
};

export const montarPayloadPerfil = (perfil = {}, matricula = '') => {
  const normalizado = normalizarPerfil({ ...perfil, matricula });
  return {
    matricula: normalizado.matricula,
    ...Object.fromEntries(CAMPOS_PERFIL_FORM.map((campo) => [campo, normalizado[campo]])),
  };
};

export const boolSelectValue = (valor) => (valor === true ? 'sim' : valor === false ? 'nao' : '');
export const boolFromSelect = (valor) => (valor === 'sim' ? true : valor === 'nao' ? false : null);

export const parseFilhos = (valor) => {
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

export const stringifyFilhos = (filhos) => JSON.stringify(filhos.map((filho) => ({ nome: filho.nome || '', idade: filho.idade || '' })));

export const quantidadeFromFilhos = (filhos) => {
  if (!filhos.length) return '';
  return filhos.length >= 6 ? '6+' : String(filhos.length);
};

export const ajustarQuantidadeFilhos = (quantidade, filhosAtuais) => {
  const total = quantidade === '6+' ? 6 : Number(quantidade || 0);
  return Array.from({ length: total }, (_, index) => filhosAtuais[index] || { nome: '', idade: '' });
};

export const perfilCadastroTemDados = (perfil) => Object.values(perfil || {}).some((valor) => {
  if (typeof valor === 'boolean') return true;
  if (valor === null || valor === undefined) return false;
  return String(valor).trim() !== '';
});

export const filhosResumo = (valor) => {
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
