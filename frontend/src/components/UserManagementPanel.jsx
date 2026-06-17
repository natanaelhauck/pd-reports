import { Fragment } from 'react';
import { Edit2, Eye, EyeOff, Save, X } from 'lucide-react';

export function UserManagementPanel({
  usuarios,
  novoUsuario,
  usuarioTemp,
  usuarioEditando,
  senhaUsuarioEditando,
  novaSenhaUsuario,
  mostrarSenhaUsuario,
  perfisUsuario,
  salvandoUsuario,
  salvandoUsuarioEditando,
  salvandoSenhaUsuario,
  styles = {},
  formatarUsuario,
  rotuloPerfilUsuario,
  onClose,
  onSubmitNovoUsuario,
  onNovoUsuarioChange,
  onUsuarioTempChange,
  onEditarUsuario,
  onCancelarEdicaoUsuario,
  onSalvarUsuario,
  onIniciarEdicaoSenha,
  onCancelarEdicaoSenha,
  onNovaSenhaUsuarioChange,
  onToggleMostrarSenhaUsuario,
  onSalvarSenhaUsuario,
}) {
  return (
    <section className="admin-panel" style={styles.section}>
      <div className="panel-title-row">
        <h2>Usuários</h2>
        <button className="ui-button" type="button" onClick={onClose} style={styles.secondaryBtn}><X size={17} /></button>
      </div>
      <form onSubmit={onSubmitNovoUsuario} className="admin-grid" autoComplete="off">
        <ProfileField styles={styles} label="Nome" value={novoUsuario.nome} onChange={(value) => onNovoUsuarioChange({ ...novoUsuario, nome: value })} />
        <ProfileField styles={styles} label="E-mail" type="email" value={novoUsuario.email} onChange={(value) => onNovoUsuarioChange({ ...novoUsuario, email: value })} autoComplete="new-email" />
        <ProfileField styles={styles} label="Senha" type="password" value={novoUsuario.senha} onChange={(value) => onNovoUsuarioChange({ ...novoUsuario, senha: value })} autoComplete="new-password" />
        <ProfileSelect styles={styles} label="Perfil" value={novoUsuario.role} onChange={(value) => onNovoUsuarioChange({ ...novoUsuario, role: value })} options={perfisUsuario} />
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
            {usuarios.map((usuario) => (
              <Fragment key={usuario.id || usuario.email}>
                <tr>
                  <td>{formatarUsuario(usuario)}</td>
                  <td>{usuario.email}</td>
                  <td>{rotuloPerfilUsuario(usuario)}</td>
                  <td>
                    <div style={{ ...styles.actions, marginLeft: 0 }}>
                      <button className="ui-button" type="button" style={styles.secondaryBtn} onClick={() => onEditarUsuario(usuario)}>
                        <Edit2 size={16} /> Editar
                      </button>
                      <button className="ui-button" type="button" style={styles.secondaryBtn} onClick={() => onIniciarEdicaoSenha(usuario)}>
                        Alterar senha
                      </button>
                    </div>
                  </td>
                </tr>
                {usuarioEditando === usuario.id && (
                  <tr className="password-row">
                    <td colSpan="4">
                      <div className="password-inline-form">
                        <ProfileField styles={styles} label="Nome" value={usuarioTemp.nome} onChange={(value) => onUsuarioTempChange({ ...usuarioTemp, nome: value })} />
                        <ProfileField styles={styles} label="E-mail" type="email" value={usuarioTemp.email} onChange={(value) => onUsuarioTempChange({ ...usuarioTemp, email: value })} autoComplete="off" />
                        <ProfileSelect styles={styles} label="Perfil" value={usuarioTemp.role} onChange={(value) => onUsuarioTempChange({ ...usuarioTemp, role: value })} options={perfisUsuario} />
                        <button className="ui-button" type="button" disabled={salvandoUsuarioEditando} style={styles.primaryBtn} onClick={() => onSalvarUsuario(usuario)}>
                          {salvandoUsuarioEditando ? 'Salvando...' : 'Salvar'}
                        </button>
                        <button className="ui-button" type="button" style={styles.secondaryBtn} onClick={onCancelarEdicaoUsuario}>
                          Cancelar
                        </button>
                      </div>
                    </td>
                  </tr>
                )}
                {senhaUsuarioEditando === usuario.id && (
                  <tr className="password-row">
                    <td colSpan="4">
                      <div className="password-inline-form">
                        <label style={{ display: 'block', marginTop: '10px' }}>
                          <span style={styles.label}>Nova senha</span>
                          <div style={{ ...styles.passwordWrap, marginBottom: 0 }}>
                            <input type={mostrarSenhaUsuario ? 'text' : 'password'} style={{ ...styles.fieldInput, paddingRight: '48px' }} value={novaSenhaUsuario} onChange={(event) => onNovaSenhaUsuarioChange(event.target.value)} autoComplete="new-password" />
                            <button
                              className="ui-button"
                              type="button"
                              aria-label={mostrarSenhaUsuario ? 'Ocultar senha' : 'Mostrar senha'}
                              title={mostrarSenhaUsuario ? 'Ocultar senha' : 'Mostrar senha'}
                              onClick={onToggleMostrarSenhaUsuario}
                              style={styles.passwordToggle}
                            >
                              {mostrarSenhaUsuario ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                          </div>
                        </label>
                        <button className="ui-button" type="button" disabled={salvandoSenhaUsuario} style={styles.primaryBtn} onClick={() => onSalvarSenhaUsuario(usuario)}>
                          {salvandoSenhaUsuario ? 'Salvando...' : 'Salvar senha'}
                        </button>
                        <button className="ui-button" type="button" style={styles.secondaryBtn} onClick={onCancelarEdicaoSenha}>
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
