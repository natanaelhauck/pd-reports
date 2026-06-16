import { Search, X } from 'lucide-react';

export function StudentSearchBar({
  value,
  onChange,
  onSubmit,
  onClear,
  loading,
  placeholder = 'Buscar por nome, matrícula, e-mail ou telefone...',
  styles = {},
}) {
  return (
    <form className="search-form" onSubmit={onSubmit} style={styles.searchBox}>
      <Search className="search-icon" size={20} color="#64748b" />
      <div className="search-input-wrap">
        <input
          style={styles.searchInput}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete="off"
        />
        {value && (
          <button
            className="search-clear-button"
            type="button"
            aria-label="Limpar busca"
            title="Limpar busca"
            onClick={onClear}
          >
            <X size={16} />
          </button>
        )}
      </div>
      <button className="ui-button" type="submit" disabled={loading} style={{ ...styles.primaryBtn, opacity: loading ? 0.75 : 1 }}>
        {loading ? 'Buscando...' : 'Buscar'}
      </button>
    </form>
  );
}
