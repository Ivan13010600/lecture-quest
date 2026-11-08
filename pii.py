import re
from natasha import (
    Segmenter, MorphVocab, NewsEmbedding,
    NewsMorphTagger, NewsSyntaxParser, NewsNERTagger,
    NamesExtractor, Doc
)

segmenter = Segmenter()
morph_vocab = MorphVocab()
emb = NewsEmbedding()
morph_tagger = NewsMorphTagger(emb)
syntax_parser = NewsSyntaxParser(emb)
ner_tagger = NewsNERTagger(emb)
names_extractor = NamesExtractor(morph_vocab)

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
    """Проверка FR-04: запрет на обработку паспортов и медицинских документов."""
    lower_text = text.lower()
    for pattern in FORBIDDEN_KEYWORDS:
        if re.search(pattern, lower_text):
            return True
    return False

def mask_pii(text: str) -> str:
    """Маскирование ПДн (FR-03): Regex + Natasha (ФИО, почты, телефоны, СНИЛС, ИНН)."""
    # Электронная почта
    text = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL]", text)
    # Номера телефонов
    text = re.sub(r"(?:\+7|8)[\s\-\(]*\d{3}[\s\-\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}", "[ТЕЛЕФОН]", text)
    # Серия и номер паспорта
    text = re.sub(r"\b\d{4}\s+\d{6}\b", "[ПАСПОРТ]", text)
    # СНИЛС
    text = re.sub(r"\b\d{3}-\d{3}-\d{3}\s+\d{2}\b", "[СНИЛС]", text)
    # ИНН
    text = re.sub(r"\b\d{10}\b|\b\d{12}\b", "[ИНН]", text)

    # Поиск и скрытие ФИО через Natasha
    doc = Doc(text)
    doc.segment(segmenter)
    doc.tag_morph(morph_tagger)
    doc.tag_ner(ner_tagger)

    spans_to_replace = []
    for span in doc.spans:
        if span.type == "PER":
            spans_to_replace.append((span.start, span.stop))

    # Замена с конца строки для сохранения смещений символов
    for start, stop in sorted(spans_to_replace, key=lambda x: x[0], reverse=True):
        text = text[:start] + "[ФИО]" + text[stop:]

    return text