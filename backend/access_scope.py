import re
import unicodedata


CITY_SCOPE_BY_ROLE = {
    'prefeitura_itabira': {
        'city': 'itabira',
        'prefixes': ('PDITA',),
        'primary_prefix': 'PDITA',
    },
    'prefeitura_bom_despacho': {
        'city': 'bom_despacho',
        'prefixes': ('PDBD',),
        'primary_prefix': 'PDBD',
    },
}


def sem_acentos(valor):
    return ''.join(
        ch for ch in unicodedata.normalize('NFD', str(valor or ''))
        if unicodedata.category(ch) != 'Mn'
    )


def normalizar_matricula(valor):
    return re.sub(r'[^A-Z0-9]', '', sem_acentos(valor).upper())


def normalizar_texto(valor):
    return re.sub(r'\s+', ' ', sem_acentos(valor or '').strip()).lower()


def get_user_city_scope(user):
    role = (user or {}).get('role')
    scope = CITY_SCOPE_BY_ROLE.get(role)
    if not scope:
        return {
            'role': role,
            'restricted': False,
            'city': None,
            'prefixes': (),
            'primary_prefix': None,
        }
    return {
        'role': role,
        'restricted': True,
        **scope,
    }


def matricula_matches_scope(matricula, scope):
    scope = scope or {}
    prefixes = scope.get('prefixes') or ()
    if not prefixes:
        return True
    matricula_normalizada = normalizar_matricula(matricula)
    return any(matricula_normalizada.startswith(prefix) for prefix in prefixes)


def apply_student_scope_filter(user, items, get_student_matricula=None):
    scope = get_user_city_scope(user)
    if not scope.get('restricted'):
        return items

    if get_student_matricula is None:
        get_student_matricula = lambda item: (
            (item or {}).get('matricula')
            or ((item or {}).get('alunoPd') or {}).get('matricula')
            or (item or {}).get('pdita')
            or ''
        )

    if items is None:
        return []

    if isinstance(items, list):
        return [item for item in items if matricula_matches_scope(get_student_matricula(item), scope)]

    if isinstance(items, tuple):
        return tuple(item for item in items if matricula_matches_scope(get_student_matricula(item), scope))

    if isinstance(items, set):
        return {item for item in items if matricula_matches_scope(get_student_matricula(item), scope)}

    return items


def can_access_student(user, student, monitor_name_resolver=None, enforce_monitor_scope=False):
    role = (user or {}).get('role')
    if role in {'owner_admin', 'admin', 'psicologa', 'gestor_tk', 'ed_viewer'}:
        return True

    scope = get_user_city_scope(user)
    if scope.get('restricted') and not matricula_matches_scope(
        (student or {}).get('matricula')
        or ((student or {}).get('alunoPd') or {}).get('matricula')
        or (student or {}).get('pdita'),
        scope,
    ):
        return False

    if role == 'monitor' and enforce_monitor_scope:
        monitor_resolvido = monitor_name_resolver(user) if callable(monitor_name_resolver) else (user or {}).get('monitor')
        if not monitor_resolvido:
            return False
        monitor_aluno = (student or {}).get('monitor') or ((student or {}).get('alunoPd') or {}).get('monitor')
        if not monitor_aluno:
            return False
        return normalizar_texto(monitor_aluno) == normalizar_texto(monitor_resolvido)

    if role == 'monitor':
        return True

    return scope.get('restricted')
