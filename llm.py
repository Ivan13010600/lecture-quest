import os
import json
import random
import re
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def get_api_key() -> str:
    """Получение ключа: сначала из secrets Streamlit Cloud, затем из локального .env."""
    if hasattr(st, "secrets") and "DEEPSEEK_API_KEY" in st.secrets:
        return st.secrets["DEEPSEEK_API_KEY"]
    return os.getenv("DEEPSEEK_API_KEY", "")

def get_client() -> OpenAI:
    api_key = get_api_key()
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY не задан! Задайте его в .env или в панели Streamlit Secrets.")
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

def _normalize_text(text: str) -> str:
    """Нормализация пробелов и регистра для надёжной сверки цитаты."""
    return re.sub(r"\s+", " ", text).strip().lower()

def is_quote_in_text(quote: str, source_text: str) -> bool:
    """Проверка FR-07: точная цитата обязательно должна быть в тексте источника."""
    return _normalize_text(quote) in _normalize_text(source_text)

SYSTEM_PROMPT = """Ты — академический эксперт по созданию тестов для самопроверки студентов.
Твоя задача: составить качественные тесты с одним правильным ответом на основе предоставленного учебного материала.

ПРАВИЛА:
1. Формируй вопросы СТРОГО по предоставленному тексту.
2. Вопрос должен иметь ровно 4 варианта ответа, из которых строго 1 правильный.
3. Поле "quote" ОБЯЗАНО содержать ДОСЛОВНУЮ цитату (1-3 предложения) из текста, подтверждающую верный ответ.
4. Ответ верни СТРОГО в формате JSON по следующей схеме:
{
  "questions": [
    {
      "id": 1,
      "question": "Текст вопроса?",
      "options": ["Вариант 1", "Вариант 2", "Вариант 3", "Вариант 4"],
      "correct_answer": "Вариант 1",
      "quote": "Дословный фрагмент исходного текста."
    }
  ]
}
Никакого пояснительного текста или markdown-разметки вокруг JSON, только чистый JSON.
"""

def generate_questions_raw(client: OpenAI, text: str, count: int) -> list:
    user_prompt = f"Сгенерируй ровно {count} тестовых вопросов по следующему учебному материалу:\n\n{text}"
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    content = response.choices[0].message.content
    data = json.loads(content)
    return data.get("questions", [])

def generate_validated_quiz(text: str, target_count: int = 10) -> list:
    """Генерация вопросов, отбор с точными цитатами и перемешивание вариантов."""
    client = get_client()
    raw_questions = generate_questions_raw(client, text, target_count)

    valid_questions = []
    for q in raw_questions:
        quote = q.get("quote", "")
        # Проверка FR-07 (дословная цитата)
        if quote and is_quote_in_text(quote, text):
            opts = q.get("options", [])
            correct = q.get("correct_answer", "")
            if correct in opts and len(opts) == 4:
                random.shuffle(opts)
                q["options"] = opts
                valid_questions.append(q)

    # Если после валидации осталось мало вопросов, делаем 1 дозапрос (FR-016)
    if len(valid_questions) < 10 and len(valid_questions) < target_count:
        needed = target_count - len(valid_questions)
        try:
            extra_raw = generate_questions_raw(client, text, needed + 3)
            for q in extra_raw:
                quote = q.get("quote", "")
                if quote and is_quote_in_text(quote, text):
                    opts = q.get("options", [])
                    correct = q.get("correct_answer", "")
                    if correct in opts and len(opts) == 4:
                        random.shuffle(opts)
                        q["options"] = opts
                        valid_questions.append(q)
                if len(valid_questions) >= target_count:
                    break
        except Exception:
            pass

    for idx, q in enumerate(valid_questions, start=1):
        q["id"] = idx

    return valid_questions