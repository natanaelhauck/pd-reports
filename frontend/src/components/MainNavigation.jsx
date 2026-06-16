import { GraduationCap, Home, Plus, UserPlus, Users } from 'lucide-react';

const buttonProps = (activeSection, section) => {
  const active = activeSection === section;
  return {
    className: active ? 'ui-button main-action-button active' : 'ui-button main-action-button',
    'aria-current': active ? 'page' : undefined,
  };
};

export function MainNavigation({
  activeSection,
  canViewMonitores,
  canViewConsumo = true,
  canCreateAluno,
  canManageUsuarios,
  onHome,
  onMonitores,
  onConsumo,
  onNovoAluno,
  onUsuarios,
}) {
  return (
    <div className="main-actions">
      <button {...buttonProps(activeSection, 'inicio')} type="button" onClick={onHome}>
        <Home size={17} /> Início
      </button>
      {canViewMonitores && (
        <button {...buttonProps(activeSection, 'monitores')} type="button" onClick={onMonitores}>
          <Users size={17} /> Monitores
        </button>
      )}
      {canViewConsumo && (
        <button {...buttonProps(activeSection, 'consumo')} type="button" onClick={onConsumo}>
          <GraduationCap size={17} /> Consumo
        </button>
      )}
      {canCreateAluno && (
        <button {...buttonProps(activeSection, 'novo-aluno')} type="button" onClick={onNovoAluno}>
          <Plus size={17} /> Novo aluno
        </button>
      )}
      {canManageUsuarios && (
        <button {...buttonProps(activeSection, 'usuarios')} type="button" onClick={onUsuarios}>
          <UserPlus size={17} /> Usuários
        </button>
      )}
    </div>
  );
}
