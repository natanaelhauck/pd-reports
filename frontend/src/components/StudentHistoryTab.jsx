export function StudentHistoryTab({
  historico = [],
  carregandoHistorico,
  styles = {},
  rotuloCampoHistorico,
  formatarUsuarioHistorico,
  formatarData,
}) {
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
