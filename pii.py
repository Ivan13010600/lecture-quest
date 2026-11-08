import re
import spacy

# Загрузка легковесной предобученной модели русского языка
nlp = spacy.load("ru_core_news_sm")

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
    """Маскирование ПДн (FR-03): spaCy (ФИО) + Regex (контакты и документы)."""
    # 1. Номера, почта, документы
    text = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL]", text)
    text = re.sub(r"(?:\+7|8)[\s\-\(]*\d{3}[\s\-\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}", "[ТЕЛЕФОН]", text)
    text = re.sub(r"\b\d{4}\s+\d{6}\b", "[ПАСПОРТ]", text)
    text = re.sub(r"\b\d{3}-\d{3}-\d{3}\s+\d{2}\b", "[СНИЛС]", text)
    text = re.sub(r"\b\d{10}\b|\b\d{12}\b", "[ИНН]", text)

    # 2. Поиск и скрытие ФИО через библиотеку spaCy (тег PER = Person)
    doc = nlp(text)
    spans = [(ent.start_char, ent.end_char) for ent in doc.ents if ent.label_ == "PER"]

    # Замена с конца строки, чтобы не сбивались координаты символов
    for start, end in sorted(spans, key=lambda x: x[0], reverse=True):
        text = text[:start] + "[ФИО]" + text[end:]

    return text