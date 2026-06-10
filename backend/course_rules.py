import re
import unicodedata


COURSE_CONSUMPTION_TOTAL_CERTIFIABLE = 22
EXCLUDED_CONSUMPTION_COURSE_KEYS = ("intensivao desenvolve",)


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
