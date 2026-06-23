import { Calendar, CheckCircle2, Edit2, GraduationCap, Hash, Laptop, Mail, Phone, Save, ShieldCheck, X } from 'lucide-react';

export function StudentMainDataTab({
  aluno,
  temp,
  editMode,
  somenteLeitura = false,
  salvando,
  corStatus,
  styles = {},
  statusOptions = [],
  monitores = [],
  statusDisplay,
  monitorDisplay,
  onEdit,
  onCancel,
  onSave,
  onFieldChange,
}) {
  const formatStatus = statusDisplay || ((status) => status || 'NÃO INFORMADO');
  const formatMonitor = monitorDisplay || ((monitor) => monitor || 'Não informado');

  return (
    <>
      {!somenteLeitura && (
        <div style={{ ...styles.actions, marginLeft: 0, marginBottom: '14px' }}>
          {editMode ? (
            <>
              <button className="ui-button" type="button" onClick={onSave} disabled={salvando} style={{ ...styles.primaryBtn, background: '#166534', opacity: salvando ? 0.75 : 1 }}><Save size={18} /> {salvando ? 'Salvando...' : 'Salvar'}</button>
              <button className="ui-button" type="button" onClick={onCancel} disabled={salvando} style={styles.secondaryBtn}><X size={18} /></button>
            </>
          ) : (
            <button className="ui-button" type="button" onClick={onEdit} style={styles.secondaryBtn}><Edit2 size={18} /> Editar</button>
          )}
        </div>
      )}
      <div className="student-grid" style={styles.grid}>
        <InfoItem styles={styles} icon={<Hash size={18} color={corStatus} />} label="Matrícula" value={aluno.matricula} />
        <FieldItem styles={styles} icon={<Phone size={18} color={corStatus} />} label="Telefone" editMode={editMode} value={temp.telefone} display={aluno.telefone} onChange={(value) => onFieldChange('telefone', value)} />
        <FieldItem styles={styles} icon={<Mail size={18} color={corStatus} />} label="E-mail" editMode={editMode} value={temp.email} display={aluno.email} onChange={(value) => onFieldChange('email', value)} />
        <div style={styles.infoItem}>
          <CheckCircle2 size={18} color={corStatus} />
          <div style={{ width: '100%', minWidth: 0 }}>
            <span style={styles.label}>Status</span>
            {editMode ? <select style={styles.fieldInput} value={temp.status || ''} onChange={(event) => onFieldChange('status', event.target.value)}><option value="">NÃO INFORMADO</option>{statusOptions.map((status) => <option key={status} value={status}>{status}</option>)}</select> : <span style={styles.val}>{formatStatus(aluno.status)}</span>}
          </div>
        </div>
        <InfoItem styles={styles} icon={<GraduationCap size={18} color={corStatus} />} label="Ingresso" value={aluno.ingresso_formatado || aluno.ingresso || aluno.dataEntradaCursoFormatada || 'Não informado'} />
        <FieldItem styles={styles} icon={<Calendar size={18} color={corStatus} />} label="Nascimento e Idade" type="date" editMode={editMode} value={temp.nascimento} display={`${aluno.nascimento_formatado} ${aluno.idade !== '-' ? `(${aluno.idade} anos)` : ''}`} onChange={(value) => onFieldChange('nascimento', value)} />
        <FieldItem styles={styles} icon={<Laptop size={18} color={corStatus} />} label="Patrimônio" editMode={editMode} value={temp.patrimonio} display={aluno.patrimonio || 'Não informado'} onChange={(value) => onFieldChange('patrimonio', value)} />
        <div style={styles.infoItem}>
          <ShieldCheck size={18} color={corStatus} />
          <div style={{ width: '100%', minWidth: 0 }}>
            <span style={styles.label}>Monitor Responsável</span>
            {editMode ? <select style={styles.fieldInput} value={temp.monitor || ''} onChange={(event) => onFieldChange('monitor', event.target.value)}><option value="">Selecione...</option>{monitores.map((monitor) => <option key={monitor} value={monitor}>{monitor}</option>)}</select> : <span style={styles.val}>{formatMonitor(aluno.monitor)}</span>}
          </div>
        </div>
      </div>
    </>
  );
}

function InfoItem({ styles, icon, label, value }) {
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

function FieldItem({ styles, icon, label, editMode, value, display, onChange, type = 'text', full = false }) {
  return (
    <div className={full ? 'full-row' : undefined} style={{ ...styles.infoItem, gridColumn: full ? '1 / -1' : undefined }}>
      {icon}
      <div style={{ width: '100%', minWidth: 0 }}>
        <span style={styles.label}>{label}</span>
        {editMode ? <input type={type} style={styles.fieldInput} value={value || ''} onChange={(event) => onChange(event.target.value)} /> : <span style={styles.val}>{display}</span>}
      </div>
    </div>
  );
}
