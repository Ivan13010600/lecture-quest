import streamlit as st
import time

# ==========================================
# 1. НАСТРОЙКА СТРАНИЦЫ И СТИЛЕЙ (CSS)
# ==========================================
st.set_page_config(
    page_title="Lecture Quest — Генератор вопросов",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"  # Удобно для мобильных
)

# Стили: Тёмная тема + Адаптивность под смартфоны
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    section[data-testid="stSidebar"] { background-color: #161B22; }

    /* Оранжевые кнопки */
    div.stButton > button:first-child {
        background-color: #FF5500;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        width: 100%;
    }
    div.stButton > button:first-child:hover { background-color: #FF7733; color: white; }

    /* Карточки шагов */
    .info-step {
        background-color: #161B22;
        border-radius: 8px;
        padding: 10px 15px;
        margin-bottom: 8px;
        border-left: 4px solid #FF5500;
    }

    /* Адаптивность для мобильных */
    @media (max-width: 768px) {
        .stApp { padding: 5px; }
    }
    </style>
""", unsafe_allow_html=True)

# Инициализация состояний
if 'generated' not in st.session_state:
    st.session_state.generated = False
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'answered' not in st.session_state:
    st.session_state.answered = {}

# ==========================================
# 2. БОКОВАЯ ПАНЕЛЬ (SIDEBAR)
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: #FF5500;'>LQ LECTURE QUEST</h2>", unsafe_allow_html=True)
    st.caption("Твои лекции — наши вопросы")
    st.divider()

    st.radio("Навигация", ["🏠 Главная", "📁 Мои лекции", "🕒 История", "⚙️ Настройки"], label_visibility="collapsed")
    st.divider()

    # Требование ТЗ: Ограничение/Предупреждение об ИИ
    st.warning("⚠️ **Внимание:** Вопросы генерируются ИИ (DeepSeek API). Проверяйте точность ответов.")
    st.info("👤 Студент: Шибаев И.Н. (ИВТб-2301)")

# ==========================================
# 3. ОСНОВНАЯ ОБЛАСТЬ (MAIN CONTENT)
# ==========================================

st.title("⚡ ГЕНЕРАТОР ВОПРОСОВ ПО ФОТО ЛЕКЦИИ")
st.write("Загрузи фото с лекции, и ИИ автоматически сгенерирует тест для самопроверки.")

# Двухколоночный макет
col_left, col_right = st.columns([1, 1], gap="large")

# ------------------------------------------
# ЛЕВАЯ КОЛОНКА: Загрузка
# ------------------------------------------
with col_left:
    st.subheader("1. Загрузка лекции")
    uploaded_file = st.file_uploader(
        "Выберите или перетащите фото лекции",
        type=["jpg", "png", "jpeg", "heic"],
        help="Максимальный размер: 10 МБ"
    )

    if uploaded_file is not None:
        st.success(f"Файл `{uploaded_file.name}` загружен!")
        st.image(uploaded_file, caption="Предпросмотр лекции", use_container_width=True)
    else:
        st.info("📌 Загрузите четкое фото рукописного или печатного конспекта.")

    st.subheader("2. Алгоритм работы")
    st.markdown("""
        <div class="info-step"><b>1. OCR-сканирование:</b> Распознавание текста (OpenCV + Tesseract)</div>
        <div class="info-step"><b>2. Анализ ИИ:</b> Выделение ключевых смыслов (DeepSeek API)</div>
        <div class="info-step"><b>3. Тестирование:</b> Генерация 10–20 вопросов с ответами</div>
    """, unsafe_allow_html=True)

    st.write("")
    if st.button("⚡ Сгенерировать вопросы"):
        if uploaded_file is None:
            st.error("Сначала загрузите фото лекции!")
        else:
            with st.spinner('Анализ изображения и генерация вопросов (< 30 сек)...'):
                time.sleep(2.0)  # Имитация работы алгоритма по ТЗ
                st.session_state.generated = True
                st.session_state.score = 0
                st.session_state.answered = {}
                st.toast("Вопросы успешно сгенерированы!", icon="🎉")

# ------------------------------------------
# ПРАВАЯ КОЛОНКА: Вопросы (Демо-данные по ТЗ)
# ------------------------------------------
with col_right:
    st.subheader("Сгенерированный тест 📋")

    dummy_questions = [
        {
            "id": 1,
            "q": "Что описывает Второй закон Ньютона?",
            "options": ["А) Зависимость ускорения от силы и массы", "В) Закон сохранения энергии", "С) Притяжение тел"],
            "correct": "А) Зависимость ускорения от силы и массы"
        },
        {
            "id": 2,
            "q": "В каких единицах измеряется сила в системе СИ?",
            "options": ["А) Джоуль", "В) Ньютон", "С) Паскаль"],
            "correct": "В) Ньютон"
        },
        {
            "id": 3,
            "q": "Как изменится кинетическая энергия при увеличении скорости в 2 раза?",
            "options": ["А) Увеличится в 2 раза", "В) Увеличится в 4 раза", "С) Не изменится"],
            "correct": "В) Увеличится в 4 раза"
        }
    ]

    if st.session_state.generated:
        st.caption(f"Сгенерировано вопросов: **{len(dummy_questions)}**")

        for idx, q in enumerate(dummy_questions):
            with st.expander(f"Вопрос {q['id']}: {q['q']}", expanded=(idx == 0)):
                user_choice = st.radio("Варианты ответа:", q['options'], key=f"q_{q['id']}")

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button(f"Ответить #{q['id']}", key=f"check_{q['id']}"):
                        if user_choice == q['correct']:
                            st.success("Верно! 🎉")
                            st.session_state.answered[q['id']] = True
                        else:
                            st.error(f"Неверно. Правильно: {q['correct']}")
                            st.session_state.answered[q['id']] = False

                # Требование ТЗ (FR-007): Кнопка «Пожаловаться»
                with col_btn2:
                    if st.button(f"🚨 Ошибка в вопросе", key=f"rep_{q['id']}"):
                        st.toast(f"Жалоба на вопрос #{q['id']} отправлена!", icon="📩")

        # Требование ТЗ (FR-006): Расчет итогового результата
        if len(st.session_state.answered) == len(dummy_questions):
            correct_cnt = sum(1 for v in st.session_state.answered.values() if v)
            st.divider()
            st.subheader(f"📊 Итоговый результат: {correct_cnt} / {len(dummy_questions)}")
    else:
        st.info("👈 Загрузите фото лекции слева и нажмите **«Сгенерировать вопросы»**.")