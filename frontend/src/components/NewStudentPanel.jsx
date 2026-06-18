import { Briefcase, Calendar, GraduationCap, Save, ShieldCheck, User, Users, X } from 'lucide-react';
import {
  DIAS_MONITORIA,
  ENG_COLORS,
  MONITORES,
  PROG_COLORS,
  PSICOLOGOS,
  QTD_FILHOS,
  STATUS_OPTIONS,
  TURNOS,
  TURNOS_TRABALHO,
} from '../constants/studentProfileOptions.js';
import {
  ajustarQuantidadeFilhos,
  boolFromSelect,
  boolSelectValue,
  parseFilhos,
  pillColor,
  quantidadeFromFilhos,
  stringifyFilhos,
} from '../utils/studentProfileHelpers.js';

export function NewStudentPanel({
  novoAluno,
  novoAlunoPerfil,
  mostrarPerfilNovoAluno,
  salvandoNovoAluno,
  styles = {},
  onNovoAlunoChange,
  onNovoAlunoPerfilChange,
  onTogglePerfil,
  onSave,
  onCancel,
}) {
  return (
    <form className="admin-panel" onSubmit={onSave} style={styles.section}>
      <div className="panel-title-row">
        <h2>Novo aluno</h2>
        <button className="ui-button" type="button" onClick={onCancel} style={styles.secondaryBtn}><X size={17} /></button>
      </div>
      <div className="admin-grid">
        <ProfileField styles={styles} label="Nome *" value={novoAluno.nome} onChange={(value) => onNovoAlunoChange({ ...novoAluno, nome: value })} />
        <ProfileField styles={styles} label="Matrícula *" value={novoAluno.matricula} onChange={(value) => onNovoAlunoChange({ ...novoAluno, matricula: value })} />
        <ProfileField styles={styles} label="Telefone" value={novoAluno.telefone} onChange={(value) => onNovoAlunoChange({ ...novoAluno, telefone: value })} />
        <ProfileField styles={styles} label="E-mail" type="email" value={novoAluno.email} onChange={(value) => onNovoAlunoChange({ ...novoAluno, email: value })} />
        <ProfileField styles={styles} label="Nascimento" type="date" value={novoAluno.nascimento} onChange={(value) => onNovoAlunoChange({ ...novoAluno, nascimento: value })} />
        <ProfileField styles={styles} label="Patrimônio" value={novoAluno.patrimonio} onChange={(value) => onNovoAlunoChange({ ...novoAluno, patrimonio: value })} />
        <ProfileSelect styles={styles} label="Monitor" value={novoAluno.monitor} onChange={(value) => onNovoAlunoChange({ ...novoAluno, monitor: value })} options={[['', 'Selecione...'], ...MONITORES.map((monitor) => [monitor, monitor])]} />
        <ProfileSelect styles={styles} label="Status *" value={novoAluno.status} onChange={(value) => onNovoAlunoChange({ ...novoAluno, status: value })} options={STATUS_OPTIONS.map((status) => [status, status])} />
      </div>
      <div className="new-student-profile">
        <div className="new-student-profile-head">
          <div>
            <h3>Perfil do aluno</h3>
            <p>Preenchimento opcional no cadastro</p>
          </div>
          <button className="ui-button" type="button" onClick={onTogglePerfil} style={styles.secondaryBtn}>
            {mostrarPerfilNovoAluno ? 'Ocultar perfil' : 'Preencher perfil agora'}
          </button>
        </div>
        {mostrarPerfilNovoAluno && (
          <NewStudentProfileForm
            perfil={novoAlunoPerfil}
            setPerfil={onNovoAlunoPerfilChange}
            styles={styles}
          />
        )}
      </div>
      <button className="ui-button" type="submit" disabled={salvandoNovoAluno} style={{ ...styles.primaryBtn, marginTop: '14px' }}>
        <Save size={17} /> {salvandoNovoAluno ? 'Salvando...' : 'Cadastrar aluno'}
      </button>
    </form>
  );
}

function NewStudentProfileForm({
  perfil,
  setPerfil,
  styles,
}) {
  const setCampo = (campo, valor) => setPerfil((atual) => ({ ...atual, [campo]: valor }));
  const filhosInfo = parseFilhos(perfil.filhos_descricao);
  const filhos = filhosInfo.filhos;
  const setFilhos = (novosFilhos) => setCampo('filhos_descricao', stringifyFilhos(novosFilhos));

  return (
    <div style={styles.profileGrid} className="profile-grid new-student-profile-grid">
      <section style={{ ...styles.section, gridColumn: '1 / -1' }}>
        <h3><User size={18} /> Breve análise de perfil</h3>
        <textarea style={styles.textarea} value={perfil.analise_perfil || ''} onChange={(event) => setCampo('analise_perfil', event.target.value)} />
      </section>
      <section style={styles.section}>
        <h3><Briefcase size={18} /> Trabalho e Estudos</h3>
        <ProfileSelect styles={styles} label="Trabalha?" value={boolSelectValue(perfil.trabalha)} onChange={(value) => {
          const trabalha = boolFromSelect(value);
          setPerfil((atual) => ({
            ...atual,
            trabalha,
            trabalho_descricao: trabalha === true ? atual.trabalho_descricao : '',
            turno_trabalho: trabalha === true ? atual.turno_trabalho : '',
          }));
        }} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
        {perfil.trabalha === true && (
          <>
            <ProfileField styles={styles} label="Com o que trabalha?" value={perfil.trabalho_descricao} onChange={(value) => setCampo('trabalho_descricao', value)} />
            <ProfileSelect styles={styles} label="Turno de trabalho" value={perfil.turno_trabalho || ''} onChange={(value) => setCampo('turno_trabalho', value)} options={[['', 'Não informado'], ...TURNOS_TRABALHO.map((turno) => [turno, turno])]} />
          </>
        )}
        <ProfileField styles={styles} label="Em qual área profissional pretende trabalhar futuramente?" value={perfil.area_profissional_interesse} onChange={(value) => setCampo('area_profissional_interesse', value)} />
        <ProfileSelect styles={styles} label="Estuda?" value={boolSelectValue(perfil.estuda)} onChange={(value) => setCampo('estuda', boolFromSelect(value))} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
        {perfil.estuda === true && (
          <>
            <ProfileField styles={styles} label="Onde estuda?" value={perfil.estudo_instituicao} onChange={(value) => setCampo('estudo_instituicao', value)} />
            <ProfileField styles={styles} label="Qual curso?" value={perfil.estudo_curso} onChange={(value) => setCampo('estudo_curso', value)} />
            <ProfileSelect styles={styles} label="Turno de estudo" value={perfil.turno_estudo || ''} onChange={(value) => setCampo('turno_estudo', value)} options={[['', 'Não informado'], ...TURNOS.map((turno) => [turno, turno])]} />
          </>
        )}
      </section>
      <section style={styles.section}>
        <h3><Users size={18} /> Família</h3>
        <ProfileSelect styles={styles} label="Tem filhos?" value={boolSelectValue(perfil.tem_filhos)} onChange={(value) => {
          const temFilhos = boolFromSelect(value);
          setPerfil((atual) => ({ ...atual, tem_filhos: temFilhos, filhos_descricao: temFilhos === true ? atual.filhos_descricao : '' }));
        }} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
        {perfil.tem_filhos === true && (
          <>
            <ProfileSelect
              styles={styles}
              label="Quantidade de filhos"
              value={quantidadeFromFilhos(filhos)}
              onChange={(value) => setFilhos(ajustarQuantidadeFilhos(value, filhos))}
              options={[['', 'Selecione...'], ...QTD_FILHOS.map((qtd) => [qtd, qtd])]}
            />
            <div className="children-editor">
              {filhos.map((filho, index) => (
                <div key={index} className="child-row">
                  <ProfileField styles={styles} label={`Nome do filho ${index + 1}`} value={filho.nome} onChange={(value) => {
                    const novos = [...filhos];
                    novos[index] = { ...novos[index], nome: value };
                    setFilhos(novos);
                  }} />
                  <ProfileField styles={styles} label="Idade" value={filho.idade} onChange={(value) => {
                    const novos = [...filhos];
                    novos[index] = { ...novos[index], idade: value };
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
        <ProfileSelect styles={styles} label="Nível de Engajamento" value={perfil.nivel_engajamento || ''} onChange={(value) => setCampo('nivel_engajamento', value)} options={[['', 'Não informado'], ['baixo', 'Baixo'], ['médio', 'Médio'], ['alto', 'Alto']]} color={pillColor(perfil.nivel_engajamento, ENG_COLORS)} />
        <ProfileSelect styles={styles} label="Nível de Conhecimento em Programação" value={perfil.nivel_programacao || ''} onChange={(value) => setCampo('nivel_programacao', value)} options={[['', 'Não informado'], ['básico', 'Básico'], ['intermediário', 'Intermediário'], ['avançado', 'Avançado']]} color={pillColor(perfil.nivel_programacao, PROG_COLORS)} />
      </section>
      <section style={styles.section}>
        <h3><Calendar size={18} /> Monitoria</h3>
        <ProfileSelect styles={styles} label="Dia da monitoria" value={perfil.dia_monitoria || ''} onChange={(value) => setCampo('dia_monitoria', value)} options={[['', 'Não informado'], ...DIAS_MONITORIA.map((dia) => [dia, dia])]} />
        <ProfileField styles={styles} label="Horário da monitoria" type="time" value={perfil.horario_monitoria} onChange={(value) => setCampo('horario_monitoria', value)} />
      </section>
      <section style={styles.section}>
        <h3><ShieldCheck size={18} /> Acompanhamento psicológico</h3>
        <ProfileSelect styles={styles} label="Faz acompanhamento?" value={boolSelectValue(perfil.acompanhamento_psicologico)} onChange={(value) => {
          const faz = boolFromSelect(value);
          setPerfil((atual) => ({ ...atual, acompanhamento_psicologico: faz, psicologo: faz === true ? atual.psicologo : '' }));
        }} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
        {perfil.acompanhamento_psicologico === true && (
          <ProfileSelect styles={styles} label="Psicólogo responsável" value={perfil.psicologo || ''} onChange={(value) => setCampo('psicologo', value)} options={[['', 'Selecione...'], ...PSICOLOGOS.map((nome) => [nome, nome])]} />
        )}
      </section>
    </div>
  );
}

function ProfileField({ styles, label, value, onChange, disabled, type = 'text', autoComplete }) {
  return (
    <label style={{ display: 'block', marginTop: '10px' }}>
      <span style={styles.label}>{label}</span>
      <input type={type} style={styles.fieldInput} value={value || ''} disabled={disabled} onChange={(event) => onChange(event.target.value)} autoComplete={autoComplete} />
    </label>
  );
}

function ProfileSelect({ styles, label, value, onChange, disabled, options, color }) {
  return (
    <label style={{ display: 'block', marginTop: '10px' }}>
      <span style={styles.label}>{label}</span>
      <select style={{ ...styles.fieldInput, color: color || 'var(--pd-text)', fontWeight: color ? 800 : 500 }} value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)}>
        {options.map(([optionValue, optionLabel]) => <option key={optionValue} value={optionValue}>{optionLabel}</option>)}
      </select>
    </label>
  );
}
