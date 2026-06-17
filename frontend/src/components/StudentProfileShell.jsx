import { User, X } from 'lucide-react';

export function StudentProfileShell({
  aluno,
  activeTab,
  tabs,
  onTabChange,
  onClose,
  cardRef,
  statusLabel,
  statusColor,
  editMode,
  nameValue,
  onNameChange,
  styles = {},
  children,
}) {
  return (
    <div
      ref={cardRef}
      className="student-card"
      style={{ ...styles.card, '--student-status-color': statusColor, borderLeft: `8px solid ${statusColor}`, marginBottom: '18px' }}
    >
      <button className="ui-button card-close" type="button" onClick={onClose} aria-label="Fechar aluno selecionado" style={styles.iconBtn}>
        <X size={17} />
      </button>
      <div className="student-card-header" style={styles.cardHeader}>
        <div style={{ ...styles.avatar, backgroundColor: `${statusColor}18` }}>
          <User size={30} color={statusColor} />
        </div>
        <div style={styles.headerInfo}>
          {editMode ? (
            <input style={styles.editInputName} value={nameValue || ''} onChange={(event) => onNameChange(event.target.value)} />
          ) : (
            <h2 style={styles.nome}>{aluno.nome}</h2>
          )}
          <span style={{ ...styles.badge, color: statusColor, backgroundColor: `${statusColor}12`, border: `1px solid ${statusColor}35` }}>{statusLabel}</span>
        </div>
      </div>

      <div style={styles.tabs}>
        {tabs.map((tab) => (
          <button
            key={tab}
            className="ui-button"
            type="button"
            onClick={() => onTabChange(tab)}
            style={{
              ...styles.tab,
              background: activeTab === tab ? 'var(--pd-surface)' : 'transparent',
              color: activeTab === tab ? 'var(--pd-title)' : 'var(--pd-muted)',
              boxShadow: activeTab === tab ? 'var(--pd-tab-shadow)' : 'none',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {children}
    </div>
  );
}
