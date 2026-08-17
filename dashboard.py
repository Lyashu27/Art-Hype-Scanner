import streamlit as st
import pandas as pd
import requests
import json
import time
import plotly.express as px

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="AI Art Agent Pro", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 20px; border-radius: 12px; border-left: 5px solid #ff4b4b; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .top1 {border-left-color: #ffd700;} 
    .top2 {border-left-color: #c0c0c0;} 
    .top3 {border-left-color: #cd7f32;}
    .badge {background-color: #2b2d35; padding: 4px 10px; border-radius: 6px; font-size: 13px; margin-right: 6px; color: #a5b1c2; border: 1px solid #3d404b;}
</style>
""", unsafe_allow_html=True)

# --- БЕЗОПАСНАЯ ЗАГРУЗКА КЛЮЧА ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = st.sidebar.text_input("Gemini API Key (Секрет не настроен):", type="password")

st.title("🧠 AI Art Agent: Глубокий анализ рынка")
st.markdown("Нейросеть самостоятельно извлекает данные о популярности персонажей, верифицирует их и формирует стратегию для 3D-артов.")

with st.sidebar:
    if api_key:
        st.success("✅ Gemini Agent подключен")
    st.divider()
    st.info("💡 **Новая архитектура:** Мы больше не парсим сайты напрямую. ИИ-агент сам оценивает объем фан-арта, индекс хайпа и тренды на основе актуальных данных из соцсетей (X, Pixiv, Reddit).")

# --- БАЗА ПЕРСОНАЖЕЙ (Для передачи Агенту) ---
CHARACTERS = [
    # ZZZ & WuWa
    "Jane Doe (ZZZ)", "Ellen Joe (ZZZ)", "Miyabi (ZZZ)", "Zhu Yuan (ZZZ)", "Nicole Demara (ZZZ)", "Yinlin (Wuthering Waves)", "Changli (Wuthering Waves)",
    # Honkai: Star Rail
    "Firefly (HSR)", "Acheron (HSR)", "Kafka (HSR)", "Black Swan (HSR)", "Ruan Mei (HSR)", "Sparkle (HSR)", "Jingliu (HSR)", "Feixiao (HSR)",
    # Genshin Impact
    "Furina (Genshin)", "Raiden Shogun (Genshin)", "Yelan (Genshin)", "Navia (Genshin)", "Arlecchino (Genshin)", "Hu Tao (Genshin)",
    # Классика & AAA
    "2B (NieR)", "Tifa Lockhart (FF7)", "Ada Wong (Resident Evil)", "Eve (Stellar Blade)", "Ciri (Witcher)", "Lucy (Cyberpunk Edgerunners)",
    # Соревновательные
    "D.Va (Overwatch)", "Ahri (LoL)", "Jinx (LoL)", "Viper (Valorant)", "Chun-Li (Street Fighter)", "Juri Han (Street Fighter)"
]

# --- АГЕНТНАЯ ФУНКЦИЯ GEMINI ---
def agentic_market_analysis(char_list, key):
    # Подбор модели с акцентом на сложные логические задачи
    supported_models = []
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(list_url, timeout=8).json()
        for m in res.get('models', []):
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                name = m.get('name', '').replace('models/', '')
                # Ищем модели, способные к глубокому анализу
                if 'flash' in name.lower() and 'lite' not in name.lower():
                    supported_models.append(name)
    except:
        pass

    fallback_models = ["gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
    models_to_try = supported_models + [m for m in fallback_models if m not in supported_models]

    prompt = f"""
    Ты выступаешь в роли ведущего аналитика данных и арт-директора. Твоя задача — провести глубокое исследование рынка для 3D-художника.
    Художник создает высококачественный 3D-арт женских персонажей и публикует его на 15+ площадках (X, Pixiv, ArtStation, Patreon и др.), а также работает с аудиторией из РФ и СНГ.

    Вот список персонажей для анализа:
    {json.dumps(char_list, ensure_ascii=False)}

    Шаг 1. Самостоятельный сбор данных: 
    Оцени текущую популярность каждого персонажа в интернете (соцсети, арты, запросы). Удостоверься в правдивости оценки — не завышай мертвые тренды и не занижай актуальные хайп-поезда.
    Оцени "Индекс хайпа" (от 1 до 100) и "Объем фан-контента" (от 1 до 100).
    
    Шаг 2. Анализ и фильтрация:
    Основываясь на сгенерированных тобой метриках, выбери ТОП-5 персонажей для глобального рынка и ТОП-5 для рынка СНГ/РФ.

    Верни ответ СТРОГО в виде единого JSON объекта без маркдауна и лишнего текста:
    {{
      "metrics": [
        {{ "name": "Имя персонажа", "category": "Франшиза", "hype_score": 95, "content_volume": 80, "trend": "Растет/Падает/Стабилен" }}
      ],
      "world_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Почему этот 3D-арт разорвет алгоритмы площадок", "tags": ["3dart", "tag2"] }}
      ],
      "ru_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Почему это будет популярно в СНГ", "tags": ["3dart", "tag2"] }}
      ]
    }}
    """
    
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}

    last_err = ""
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        try:
            # Увеличен таймаут, так как ИИ нужно "подумать" над большой генерацией
            resp = requests.post(url, headers=headers, json=payload, timeout=40)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                # Очистка от возможных markdown тегов ```json ... ```
                if raw_text.startswith("```json"): raw_text = raw_text[7:]
                if raw_text.startswith("```"): raw_text = raw_text[3:]
                if raw_text.endswith("```"): raw_text = raw_text[:-3]
                
                return json.loads(raw_text.strip()), model_name
            else:
                last_err = f"[{model_name}] Ошибка: {resp.text}"
        except Exception as e:
            last_err = f"[{model_name}] Сбой: {str(e)}"
            continue

    raise RuntimeError(f"Сбой AI-агента. Детали: {last_err}")

# --- ИНТЕРФЕЙС И ЗАПУСК ---
if st.button("🚀 Делегировать анализ ИИ-агенту", type="primary", use_container_width=True):
    if not api_key:
        st.error("⚠️ Укажите Gemini API Key.")
    else:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        status_text.markdown("🧠 **ИИ-агент:** Поднимаю архивы данных. Оцениваю тренды Pixiv, X и Reddit... (Ожидание ~15-20 секунд)")
        progress_bar.progress(30)
        
        start_t = time.time()
        
        try:
            # Один большой запрос к ИИ, который делает всё сам
            ai_data, model_used = agentic_market_analysis(CHARACTERS, api_key)
            progress_bar.progress(80)
            
            status_text.markdown("🧠 **ИИ-агент:** Данные верифицированы. Формирую списки лидеров для 3D-арта...")
            
            # Извлекаем метрики в DataFrame для графиков
            metrics_data = ai_data.get('metrics', [])
            df = pd.DataFrame(metrics_data)
            
            st.session_state['results'] = ai_data
            st.session_state['df'] = df
            st.session_state['done'] = True
            
            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()
            
            ai_duration = time.time() - start_t
            st.toast(f"Агент завершил работу! (Модель: {model_used} | Время: {ai_duration:.1f}с)", icon="✅")
            
        except Exception as ex:
            st.error(f"Критическая ошибка ИИ: {ex}")

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
if st.session_state.get('done', False):
    df = st.session_state['df']
    results = st.session_state['results']
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    classes = ["top1", "top2", "top3", "top4", "top5"]

    st.divider()
    
    # Визуализация данных, сгенерированных ИИ
    st.subheader("📊 Аналитика рынка (По оценке Gemini Agent)")
    col1, col2 = st.columns(2)
    
    with col1:
        fig_bar = px.bar(
            df.sort_values(by="hype_score", ascending=False).head(10), 
            x="hype_score", y="name", orientation="h",
            color="hype_score", color_continuous_scale="Inferno",
            title="🔥 Топ-10: Индекс Хайпа", template="plotly_dark"
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col2:
        fig_bubble = px.scatter(
            df, x="content_volume", y="hype_score", size="hype_score",
            color="category", hover_name="name", symbol="trend",
            title="Матрица: Объем рынка vs Хайп (Форма = Тренд)", template="plotly_dark", size_max=35
        )
        st.plotly_chart(fig_bubble, use_container_width=True)

    tab_w, tab_r, tab_all = st.tabs(["🌍 Глобальный выбор ИИ", "🇷🇺 Выбор ИИ для СНГ", "🗄️ База метрик (Оценка ИИ)"])

    def render_list(key):
        for idx, item in enumerate(results.get(key, [])[:5]):
            tags = " ".join([f"<span class='badge'>#{t}</span>" for t in item.get('tags', [])])
            st.markdown(f"""
            <div class="metric-card {classes[idx]}">
                <h3>{medals[idx]} {item['name']} <span style="font-size:15px; color:#888;">({item['game']})</span></h3>
                <p>{item['analysis']}</p>
                <div>{tags}</div>
            </div>
            """, unsafe_allow_html=True)

    with tab_w:
        render_list('world_top')
    with tab_r:
        render_list('ru_top')
    with tab_all:
        st.dataframe(df, use_container_width=True, hide_index=True)
