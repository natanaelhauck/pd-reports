import { Briefcase, Calendar, Edit2, GraduationCap, Save, ShieldCheck, User, Users, X } from 'lucide-react';

export function StudentProfileDataTab({
  perfil,
  perfilTemp,
  editPerfil,
  somenteLeitura = false,
  salvandoPerfil,
  styles = {},
  turnos = [],
  turnosTrabalho = [],
  diasMonitoria = [],
  qtdFilhos = [],
  psicologos = [],
  engColors = {},
  progColors = {},
  boolSelectValue,
  boolFromSelect,
  parseFilhos,
  stringifyFilhos,
  filhosResumo,
  quantidadeFromFilhos,
  ajustarQuantidadeFilhos,
  pillColor,
  onEdit,
  onCancel,
  onSave,
  setPerfilTemp,
}) {
  const p = editPerfil && !somenteLeitura ? perfilTemp : perfil;
  const setCampo = (campo, valor) => setPerfilTemp({ ...perfilTemp, [campo]: valor });
  const filhosInfo = parseFilhos(p.filhos_descricao);
  const filhos = filhosInfo.filhos;
  const setFilhos = (novosFilhos) => setCampo('filhos_descricao', stringifyFilhos(novosFilhos));

  if (!editPerfil || somenteLeitura) {
    return (
      <>
        {!somenteLeitura && (
          <div style={{ ...styles.actions, marginLeft: 0, marginBottom: '14px' }}>
            <button className="ui-button" type="button" onClick={onEdit} style={styles.secondaryBtn}><Edit2 size={18} /> Editar perfil</button>
          </div>
        )}
        <div style={styles.profileGrid} className="profile-grid">
          <section style={{ ...styles.section, gridColumn: '1 / -1' }}>
            <h3><User size={18} /> Breve análise de perfil</h3>
            <p className="profile-text">{p.analise_perfil || 'Não informado'}</p>
          </section>
          <section style={styles.section}>
            <h3><Briefcase size={18} /> Trabalho e Estudos</h3>
            <DisplayItem styles={styles} label="Trabalha?" value={p.trabalha === true ? 'Sim' : p.trabalha === false ? 'Não' : 'Não informado'} />
            {p.trabalha === true && (
              <>
                <DisplayItem styles={styles} label="Com o que trabalha?" value={p.trabalho_descricao} />
                <DisplayItem styles={styles} label="Turno de trabalho" value={p.turno_trabalho} />
              </>
            )}
            <DisplayItem styles={styles} label="Em qual área profissional pretende trabalhar futuramente?" value={p.area_profissional_interesse} />
            <DisplayItem styles={styles} label="Estuda?" value={p.estuda === true ? 'Sim' : p.estuda === false ? 'Não' : 'Não informado'} />
            {p.estuda === true && (
              <>
                <DisplayItem styles={styles} label="Onde estuda?" value={p.estudo_instituicao} />
                <DisplayItem styles={styles} label="Qual curso?" value={p.estudo_curso} />
                <DisplayItem styles={styles} label="Turno de estudo" value={p.turno_estudo} />
              </>
            )}
          </section>
          <section style={styles.section}>
            <h3><Users size={18} /> Família</h3>
            <DisplayItem styles={styles} label="Tem filhos?" value={p.tem_filhos === true ? 'Sim' : p.tem_filhos === false ? 'Não' : 'Não informado'} />
            {p.tem_filhos === true && (
              <div className="children-list">
                {filhosResumo(p.filhos_descricao).map((linha) => <strong key={linha}>{linha}</strong>)}
              </div>
            )}
          </section>
          <section style={styles.section}>
            <h3><GraduationCap size={18} /> Curso</h3>
            <div className="profile-badge-row">
              <ProfileBadge styles={styles} label="Nível de Engajamento" value={p.nivel_engajamento} color={pillColor(p.nivel_engajamento, engColors)} />
              <ProfileBadge styles={styles} label="Nível de Conhecimento em Programação" value={p.nivel_programacao} color={pillColor(p.nivel_programacao, progColors)} />
            </div>
          </section>
          <section style={styles.section}>
            <h3><Calendar size={18} /> Monitoria</h3>
            <div className="mini-card-row">
              <DisplayItem styles={styles} label="Dia da monitoria" value={p.dia_monitoria} compact />
              <DisplayItem styles={styles} label="Horário da monitoria" value={p.horario_monitoria} compact />
            </div>
          </section>
          <section style={styles.section}>
            <h3><ShieldCheck size={18} /> Acompanhamento psicológico</h3>
            <DisplayItem styles={styles} label="Faz acompanhamento?" value={p.acompanhamento_psicologico === true ? 'Sim' : p.acompanhamento_psicologico === false ? 'Não' : 'Não informado'} />
            {p.acompanhamento_psicologico === true && <DisplayItem styles={styles} label="Psicólogo responsável" value={p.psicologo} />}
          </section>
        </div>
      </>
    );
  }

  return (
    <>
      <div style={{ ...styles.actions, marginLeft: 0, marginBottom: '14px' }}>
        <button className="ui-button" type="button" onClick={onSave} disabled={salvandoPerfil} style={{ ...styles.primaryBtn, background: '#166534', opacity: salvandoPerfil ? 0.75 : 1 }}><Save size={18} /> {salvandoPerfil ? 'Salvando...' : 'Salvar perfil'}</button>
        <button className="ui-button" type="button" onClick={onCancel} disabled={salvandoPerfil} style={styles.secondaryBtn}><X size={18} /></button>
      </div>
      <div style={styles.profileGrid} className="profile-grid">
        <section style={{ ...styles.section, gridColumn: '1 / -1' }}>
          <h3><User size={18} /> Breve análise de perfil</h3>
          <textarea style={styles.textarea} value={p.analise_perfil || ''} onChange={(event) => setCampo('analise_perfil', event.target.value)} />
        </section>
        <section style={styles.section}>
          <h3><Briefcase size={18} /> Trabalho e Estudos</h3>
          <ProfileSelect styles={styles} label="Trabalha?" value={boolSelectValue(p.trabalha)} disabled={!editPerfil} onChange={(value) => {
            const trabalha = boolFromSelect(value);
            setPerfilTemp({
              ...perfilTemp,
              trabalha,
              trabalho_descricao: trabalha === true ? perfilTemp.trabalho_descricao : '',
              turno_trabalho: trabalha === true ? perfilTemp.turno_trabalho : '',
            });
          }} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
          {p.trabalha === true && (
            <>
              <ProfileField styles={styles} label="Com o que trabalha?" value={p.trabalho_descricao} disabled={!editPerfil} onChange={(value) => setCampo('trabalho_descricao', value)} />
              <ProfileSelect styles={styles} label="Turno de trabalho" value={p.turno_trabalho || ''} disabled={!editPerfil} onChange={(value) => setCampo('turno_trabalho', value)} options={[['', 'Não informado'], ...turnosTrabalho.map((turno) => [turno, turno])]} />
            </>
          )}
          <ProfileField styles={styles} label="Em qual área profissional pretende trabalhar futuramente?" value={p.area_profissional_interesse} disabled={!editPerfil} onChange={(value) => setCampo('area_profissional_interesse', value)} />
          <ProfileSelect styles={styles} label="Estuda?" value={boolSelectValue(p.estuda)} disabled={!editPerfil} onChange={(value) => setCampo('estuda', boolFromSelect(value))} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
          {p.estuda === true && (
            <>
              <ProfileField styles={styles} label="Onde estuda?" value={p.estudo_instituicao} disabled={!editPerfil} onChange={(value) => setCampo('estudo_instituicao', value)} />
              <ProfileField styles={styles} label="Qual curso?" value={p.estudo_curso} disabled={!editPerfil} onChange={(value) => setCampo('estudo_curso', value)} />
              <ProfileSelect styles={styles} label="Turno de estudo" value={p.turno_estudo || ''} disabled={!editPerfil} onChange={(value) => setCampo('turno_estudo', value)} options={[['', 'Não informado'], ...turnos.map((turno) => [turno, turno])]} />
            </>
          )}
        </section>
        <section style={styles.section}>
          <h3><Users size={18} /> Família</h3>
          <ProfileSelect styles={styles} label="Tem filhos?" value={boolSelectValue(p.tem_filhos)} disabled={!editPerfil} onChange={(value) => {
            const temFilhos = boolFromSelect(value);
            setPerfilTemp({ ...perfilTemp, tem_filhos: temFilhos, filhos_descricao: temFilhos === true ? perfilTemp.filhos_descricao : '' });
          }} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
          {p.tem_filhos === true && (
            <>
              <ProfileSelect
                styles={styles}
                label="Quantidade de filhos"
                value={quantidadeFromFilhos(filhos)}
                disabled={!editPerfil}
                onChange={(value) => setFilhos(ajustarQuantidadeFilhos(value, filhos))}
                options={[['', 'Selecione...'], ...qtdFilhos.map((qtd) => [qtd, qtd])]}
              />
              <div className="children-editor">
                {filhos.map((filho, index) => (
                  <div key={index} className="child-row">
                    <ProfileField styles={styles} label={`Nome do filho ${index + 1}`} value={filho.nome} disabled={!editPerfil} onChange={(value) => {
                      const novos = [...filhos];
                      novos[index] = { ...novos[index], nome: value };
                      setFilhos(novos);
                    }} />
                    <ProfileField styles={styles} label="Idade" value={filho.idade} disabled={!editPerfil} onChange={(value) => {
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
          <ProfileSelect styles={styles} label="Nível de Engajamento" value={p.nivel_engajamento || ''} disabled={!editPerfil} onChange={(value) => setCampo('nivel_engajamento', value)} options={[['', 'Não informado'], ['baixo', 'Baixo'], ['médio', 'Médio'], ['alto', 'Alto']]} color={pillColor(p.nivel_engajamento, engColors)} />
          <ProfileSelect styles={styles} label="Nível de Conhecimento em Programação" value={p.nivel_programacao || ''} disabled={!editPerfil} onChange={(value) => setCampo('nivel_programacao', value)} options={[['', 'Não informado'], ['básico', 'Básico'], ['intermediário', 'Intermediário'], ['avançado', 'Avançado']]} color={pillColor(p.nivel_programacao, progColors)} />
        </section>
        <section style={styles.section}>
          <h3><Calendar size={18} /> Monitoria</h3>
          <ProfileSelect styles={styles} label="Dia da monitoria" value={p.dia_monitoria || ''} disabled={!editPerfil} onChange={(value) => setCampo('dia_monitoria', value)} options={[['', 'Não informado'], ...diasMonitoria.map((dia) => [dia, dia])]} />
          <ProfileField styles={styles} label="Horário da monitoria" type="time" value={p.horario_monitoria} disabled={!editPerfil} onChange={(value) => setCampo('horario_monitoria', value)} />
        </section>
        <section style={styles.section}>
          <h3><ShieldCheck size={18} /> Acompanhamento psicológico</h3>
          <ProfileSelect styles={styles} label="Faz acompanhamento?" value={boolSelectValue(p.acompanhamento_psicologico)} disabled={!editPerfil} onChange={(value) => {
            const faz = boolFromSelect(value);
            setPerfilTemp({ ...perfilTemp, acompanhamento_psicologico: faz, psicologo: faz === true ? perfilTemp.psicologo : '' });
          }} options={[['', 'Não informado'], ['sim', 'Sim'], ['nao', 'Não']]} />
          {p.acompanhamento_psicologico === true && (
            <ProfileSelect styles={styles} label="Psicólogo responsável" value={p.psicologo || ''} disabled={!editPerfil} onChange={(value) => setCampo('psicologo', value)} options={[['', 'Selecione...'], ...psicologos.map((nome) => [nome, nome])]} />
          )}
        </section>
      </div>
    </>
  );
}

function DisplayItem({ styles, label, value, compact = false }) {
  return (
    <div className={compact ? 'display-item compact' : 'display-item'}>
      <span style={styles.label}>{label}</span>
      <strong>{value || 'Não informado'}</strong>
    </div>
  );
}

function ProfileBadge({ styles, label, value, color }) {
  return (
    <div className="profile-badge">
      <span style={styles.label}>{label}</span>
      <strong style={{ color, backgroundColor: `${color}14`, borderColor: `${color}35` }}>{value || 'Não informado'}</strong>
    </div>
  );
}

function ProfileField({ styles, label, value, onChange, disabled, type = 'text' }) {
  return (
    <label style={{ display: 'block', marginTop: '10px' }}>
      <span style={styles.label}>{label}</span>
      <input type={type} style={styles.fieldInput} value={value || ''} disabled={disabled} onChange={(event) => onChange(event.target.value)} />
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
