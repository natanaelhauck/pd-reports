import { KeyRound, Moon, Sun } from 'lucide-react';
import pdLogo from '../assets/pd-logo.svg';

export function AppHeader({
  userLabel,
  isDarkTheme,
  onHome,
  onToggleTheme,
  onLogout,
  onOpenPasswordModal,
  styles = {},
}) {
  return (
    <header className="app-header" style={styles.header}>
      <div className="header-user">
        <span className="user-chip">{userLabel}</span>
      </div>
      <button className="brand-block brand-home-button" type="button" onClick={onHome} aria-label="Voltar para o início">
        <img src={pdLogo} alt="PD Reports" className="pd-logo" style={styles.logo} />
        <h1 style={styles.title}>PD Reports</h1>
        <p style={styles.subtitle}>Gestão de Alunos</p>
      </button>
      <div className="header-controls">
        <button className="ui-button icon-button" type="button" title="Alterar minha senha" aria-label="Alterar minha senha" onClick={onOpenPasswordModal} style={styles.iconBtn}>
          <KeyRound size={18} />
        </button>
        <button className="ui-button icon-button" type="button" title="Alternar tema" aria-label="Alternar tema" onClick={onToggleTheme} style={styles.iconBtn}>
          {isDarkTheme ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <button className="ui-button logout-button" type="button" onClick={onLogout} style={styles.neutralBtn}>Sair</button>
      </div>
    </header>
  );
}
