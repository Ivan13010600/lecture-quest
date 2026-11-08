import re

FORBIDDEN_KEYWORDS = [
    r"паспорт\s+гражданина",
    r"водительское\s+удостоверение",
    r"медицинская\s+справка",
    r"история\s+болезни",
    r"листок\s+нетрудоспособности",
    r"диагноз\s*:",
    r"врачебная\s+тайна"
]


def contains_forbidden_docs(text: str) -> bool:
    """Проверка FR-04: запрет на паспорта и медсправки."""
    lower_text = text.lower()
    for pattern in FORBIDDEN_KEYWORDS:
        if re.search(pattern, lower_text):
            return True
    return False


def mask_pii(text: str) -> str:
    """Маскирование ПДн (FR-03): скрытие контактов, документов и ФИО."""
    # 1. Почта, телефоны, документы
    text = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL]", text)
    text = re.sub(r"(?:\+7|8)[\s\-\(]*\d{3}[\s\-\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}", "[ТЕЛЕФОН]", text)
    text = re.sub(r"\b\d{4}\s+\d{6}\b", "[ПАСПОРТ]", text)
    text = re.sub(r"\b\d{3}-\d{3}-\d{3}\s+\d{2}\b", "[СНИЛС]", text)
    text = re.sub(r"\b\d{10}\b|\b\d{12}\b", "[ИНН]", text)

    # 2. ФИО (поиск конструкций: Иванов И.И. или Иванов Иван Иванович)
    fio_initials = r"\b[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ]\.\s*[А-ЯЁ]\.)\b"
    fio_full = r"\b[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2}\b"

    text = re.sub(fio_initials, "[ФИО]", text)
    text = re.sub(fio_full, "[ФИО]", text)

    return text