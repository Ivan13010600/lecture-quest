import os
import streamlit as st
from datetime import datetime
import requests
from dotenv import load_dotenv

from ocr import read_uploaded_file
from pii import contains_forbidden_docs, mask_pii
from llm import generate_validated_quiz, get_api_key

load_dotenv()

# Базовая конфигурация страницы
st.set_page_config(page_title="Lecture Quest", page_icon="🎓", layout="wide")

# Фирменный стиль интерфейса
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #A0AABF;
        margin-bottom: 2rem;
    }
    .card {
        background-color: #161B26;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #262C3D;
        margin-bottom: 20px;
    }
    .quote-box {
        background-color: #1A2234;
        border-left: 4px solid #FF5500;
        padding: 12px 16px;
        border-radius: 4px;
        font-size: 0.95rem;
        color: #D1D5DB;
        margin-top: 10px;
    }
    div.stButton > button:first-child {
        background-color: #FF5500;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 600;
        width: 100%;
        transition: background-color 0.2s;
    }
    div.stButton > button:first-child:hover {
        background-color: #FF7733;
        color: white;
    }
    .disclaimer {
        font-size: 0.8rem;
        color: #6B7280;
        text-align: center;
        margin-top: 40px;
    }
</style>
""", unsafe_allow_html=True)

# Инициализация переменных сессии
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}


def log_complaint(question_id: int, question_text: str, reason: str):
    """Логирование замечаний к вопросам в журнал complaints.log (FR-12)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] Вопрос #{question_id}: '{question_text}' | Причина: {reason}\n"

    with open("complaints.log", "a", encoding="utf-8") as f:
        f.write(log_line)

    tg_token = os.getenv("TG_BOT_TOKEN") or (st.secrets.get("TG_BOT_TOKEN") if hasattr(st, "secrets") else None)
    tg_chat = os.getenv("TG_CHAT_ID") or (st.secrets.get("TG_CHAT_ID") if hasattr(st, "secrets") else None)
    if tg_token and tg_chat:
        try:
            tg_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
            requests.post(tg_url, json={"chat_id": tg_chat, "text": f"⚠️ Замечание к вопросу:\n{log_line}"}, timeout=5)
        except Exception:
            pass


# Боковая панель
with st.sidebar:
    st.markdown("### 🎓 Lecture Quest")
    st.caption("ИИ-генератор вопросов по учебным материалам")
    st.markdown("---")

    q_count = st.slider("Количество вопросов:", min_value=10, max_value=20, value=10, step=1)

    st.markdown("---")
    st.markdown("#### 🔒 Безопасность и правила")
    st.markdown("""
    - Форматы: **PDF, DOCX, TXT, PNG, JPG**
    - Размер файла: **до 10 МБ**
    - Объём текста: **от 500 до 18 000 символов**
    - Паспорта и справки **запрещены**
    - ФИО и контакты **маскируются**
    """)
    st.markdown("---")
    st.markdown(
        "<div class='disclaimer'>Проект ВятГУ<br>Кафедра ЭВМ, Шибаев И.Н.<br>2026</div>",
        unsafe_allow_html=True
    )

# Главный экран
st.markdown("<div class='main-header'>Генератор вопросов для подготовки</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='sub-header'>Загрузите конспект, методичку или фото страниц для создания теста для самопроверки</div>",
    unsafe_allow_html=True)

# 1. Загрузка файла
if st.session_state.quiz_data is None:
    st.markdown("<div class='card'>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Выберите файл документа или фотографию конспекта",
        type=["pdf", "docx", "txt", "png", "jpg", "jpeg"]
    )

    consent = st.checkbox("Я подтверждаю согласие на учебную обработку материалов (FR-05)")

    generate_btn = st.button("Сгенерировать тест")
    st.markdown("</div>", unsafe_allow_html=True)

    if generate_btn:
        if not uploaded_file:
            st.error("Пожалуйста, прикрепите файл перед началом генерации.")
        elif not consent:
            st.error("Для генерации необходимо дать согласие на обработку материала.")
        elif uploaded_file.size > 10 * 1024 * 1024:
            st.error("Размер файла превышает лимит 10 МБ.")
        else:
            with st.spinner("1/3 Извлечение и оптическое распознавание текста..."):
                try:
                    file_bytes = uploaded_file.read()
                    raw_text = read_uploaded_file(uploaded_file.name, file_bytes)
                except Exception as e:
                    st.error(f"Ошибка при чтении файла: {e}")
                    st.stop()

            char_count = len(raw_text)
            if char_count < 500:
                st.error(f"Извлечено слишком мало текста ({char_count} симв.). Минимальный объём — 500 символов.")
                st.stop()
            if char_count > 18000:
                st.error(f"Файл слишком велик ({char_count} симв.). Допустимый лимит — 18 000 символов (~10-12 стр.).")
                st.stop()

            with st.spinner("2/3 Проверка на конфиденциальность и маскирование ПДн..."):
                if contains_forbidden_docs(raw_text):
                    st.error("Загрузка отменена: обнаружены признаки паспорта или медицинских документов (FR-04).")
                    st.stop()
                safe_text = mask_pii(raw_text)

            with st.spinner("3/3 DeepSeek AI формирует вопросы и сопоставляет цитаты..."):
                try:
                    questions = generate_validated_quiz(safe_text, target_count=q_count)
                    if len(questions) < 5:
                        st.error(
                            "Не удалось сформировать достаточное количество вопросов с подтверждёнными цитатами. Попробуйте другой фрагмент текста.")
                        st.stop()

                    st.session_state.quiz_data = questions
                    st.session_state.quiz_submitted = False
                    st.session_state.user_answers = {}
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка генерации теста: {e}")

# 2. Прохождение теста
else:
    questions = st.session_state.quiz_data

    if not st.session_state.quiz_submitted:
        st.info(f"Сформировано вопросов: {len(questions)}. Ответьте на вопросы и нажмите «Завершить тест».")

        with st.form("quiz_form"):
            for q in questions:
                st.markdown(f"**Вопрос {q['id']}:** {q['question']}")
                chosen = st.radio(
                    f"Варианты к вопросу {q['id']}:",
                    options=q["options"],
                    key=f"q_{q['id']}",
                    label_visibility="collapsed"
                )
                st.session_state.user_answers[q["id"]] = chosen
                st.markdown("---")

            submit_test = st.form_submit_button("Завершить тест и проверить результат")
            if submit_test:
                st.session_state.quiz_submitted = True
                st.rerun()

    # 3. Результаты теста и разбор ошибок
    else:
        score = 0
        mistakes = []

        for q in questions:
            user_ans = st.session_state.user_answers.get(q["id"])
            if user_ans == q["correct_answer"]:
                score += 1
            else:
                mistakes.append(q)

        total = len(questions)
        pct = int((score / total) * 100)

        st.markdown(f"""
        <div class='card' style='text-align: center;'>
            <h2>Ваш результат: {score} из {total} ({pct}%)</h2>
            <p>{'Отличный результат! Материал усвоен превосходно.' if pct >= 80 else 'Рекомендуется повторить отмеченные ниже темы.'}</p>
        </div>
        """, unsafe_allow_html=True)

        if mistakes:
            st.markdown("### 🔍 Подробный разбор допущенных ошибок:")
            for m in mistakes:
                with st.expander(f"Вопрос #{m['id']}: {m['question']}", expanded=True):
                    st.write(f"❌ **Ваш ответ:** {st.session_state.user_answers.get(m['id'])}")
                    st.write(f"✅ **Правильный ответ:** {m['correct_answer']}")

                    st.markdown("**Подтверждающая цитата из первоисточника:**")
                    st.markdown(f"<div class='quote-box'>«{m['quote']}»</div>", unsafe_allow_html=True)

                    col1, col2 = st.columns([3, 1])
                    with col1:
                        reason = st.text_input(f"Нашли неточность в вопросе #{m['id']}?",
                                               key=f"complaint_text_{m['id']}")
                    with col2:
                        st.write("")
                        st.write("")
                        if st.button("Пожаловаться", key=f"btn_comp_{m['id']}"):
                            if reason.strip():
                                log_complaint(m["id"], m["question"], reason.strip())
                                st.success("Жалоба записана в журнал аудита!")
                            else:
                                st.warning("Укажите причину.")
        else:
            st.balloons()
            st.success("Идеально! Ни одной ошибки!")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Пройти тест по новому материалу"):
            st.session_state.quiz_data = None
            st.session_state.quiz_submitted = False
            st.session_state.user_answers = {}
            st.rerun()

# Предупреждение об ИИ (FR-11, CON-03)
st.markdown(
    "<div class='disclaimer'>⚠️ Внимание: вопросы и цитаты сгенерированы искусственным интеллектом DeepSeek и могут содержать неточности. Всегда сверяйтесь с официальными учебниками.</div>",
    unsafe_allow_html=True
)