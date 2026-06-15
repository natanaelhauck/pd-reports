import re
import unicodedata


COURSE_CONSUMPTION_TOTAL_CERTIFIABLE = 22
EXCLUDED_CONSUMPTION_COURSE_KEYS = ("intensivao desenvolve",)
OFFICIAL_COURSE_TRAIL_ORDER = (
    ("scratch", "scratch 1"),
    ("no code", "no code 1"),
    ("linux", "linux 1"),
    ("introducao a web",),
    ("python i", "python 1"),
    ("javascript", "javascript 1"),
    ("banco de dados", "banco de dados 1"),
    ("programacao orientada a objetos", "programacao orientada a objetos poo 1", "poo"),
    ("python ii", "python 2"),
    ("fundamentos de interface",),
    ("react js",),
    ("desenvolvimento de websites com mentalidade agil",),
    ("desenvolvimento de interfaces web frameworks front end",),
    ("programacao multiplataforma com react native",),
    ("programacao multiplataforma com flutter",),
    ("padrao de projeto de software",),
    ("desenvolvimento de apis restful",),
    ("desenvolvimento nativo para android",),
    ("banco de dados nao relacional",),
    ("framework full stack para web", "framework fullstack para web"),
    ("teste de software para web", "testes de software para web"),
    ("teste de software para mobile", "testes de software para mobile"),
)


def strip_accents(value):
    return "".join(
        char for char in unicodedata.normalize("NFD", str(value or ""))
        if unicodedata.category(char) != "Mn"
    )


def field_key(value):
    return re.sub(r"[^a-z0-9]+", " ", strip_accents(value).lower()).strip()


def course_name_is_excluded_from_consumption(course_name):
    key = field_key(course_name)
    return any(excluded in key for excluded in EXCLUDED_CONSUMPTION_COURSE_KEYS)


def official_course_order_index(*values):
    keys = [field_key(value) for value in values if field_key(value)]
    for index, aliases in enumerate(OFFICIAL_COURSE_TRAIL_ORDER):
        for alias in aliases:
            alias_key = field_key(alias)
            if any(alias_key == key for key in keys):
                return index
    return len(OFFICIAL_COURSE_TRAIL_ORDER)


def official_course_sort_key(course):
    if isinstance(course, dict):
        return (
            official_course_order_index(
                course.get("courseName"),
                course.get("curso"),
                course.get("courseId"),
            ),
            field_key(course.get("courseName") or course.get("curso")),
            field_key(course.get("courseId")),
        )
    return (official_course_order_index(course), field_key(course), "")
