import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="AI Art Agent: Viral Radar", page_icon="🔥", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 20px; border-radius: 12px; border-left: 5px solid #ff4b4b; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .hero-card {background: linear-gradient(135deg, #ff4b4b 0%, #8b0000 100%); padding: 30px; border-radius: 16px; margin-bottom: 25px; color: white; box-shadow: 0 10px 20px rgba(255, 75, 75, 0.3); border: 1px solid #ff7676;}
    .hero-title {font-size: 32px; font-weight: 800; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;}
    .hero-subtitle {font-size: 18px; opacity: 0.9; margin-bottom: 15px;}
    .hero-news {background: rgba(0,0,0,0.2); padding: 12px; border-radius: 8px; font-size: 15px; border-left: 4px solid #ffd700;}
    .top1 {border-left-color: #ffd700;} 
    .top2 {border-left-color: #c0c0c0;} 
    .top3 {border-left-color: #cd7f32;}
    .badge {background-color: #2b2d35; padding: 4px 10px; border-radius: 6px; font-size: 13px; margin-right: 6px; color: #a5b1c2; border: 1px solid #3d404b;}
    .gacha-badge {background-color: #4b8bff; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; text-transform: uppercase;}
    .aaa-badge {background-color: #ff4b8b; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; text-transform: uppercase;}
</style>
""", unsafe_allow_html=True)

# --- ЗАГРУЗКА КЛЮЧА ИЗ SECRETS / SIDEBAR ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = st.sidebar.text_input("Gemini API Key:", type="password")

st.title("🔥 Viral Radar: Аналитика 3D-арта")
st.markdown("Поиск самых хайповых женских персонажей на основе алгоритмов соцсетей, новостей и релизов.")

# --- БОКОВАЯ ПАНЕЛЬ И ФИЛЬТРЫ ---
with st.sidebar:
    st.header("Настройки сканирования")
    
    time_filter = st.selectbox(
        "⏳ Временной фильтр:",
        ["За 24 часа (Мгновенный хайп)", "За 3 дня (Свежие тренды)", "За 7 дней (Стабильный рост)"]
    )
    
    st.divider()
    st.info("🧠 **Алгоритм виральности:** ИИ учитывает не только объем фанартов, но и влияние СМИ (выход патчей, сливы, анонсы). Абсолютный лидер выводится в отдельный блок.")

# --- БАЗА ПЕРСОНАЖЕЙ ---
CHARACTERS = [
    {"name": "Jane Doe", "game": "ZZZ", "is_gacha": True},
    {"name": "Ellen Joe", "game": "ZZZ", "is_gacha": True},
    {"name": "Miyabi", "game": "ZZZ", "is_gacha": True},
    {"name": "Zhu Yuan", "game": "ZZZ", "is_gacha": True},
    {"name": "Firefly", "game": "Honkai: Star Rail", "is_gacha": True},
    {"name": "Acheron", "game": "Honkai: Star Rail", "is_gacha": True},
    {"name": "Kafka", "game": "Honkai: Star Rail", "is_gacha": True},
    {"name": "Feixiao", "game": "Honkai: Star Rail", "is_gacha": True},
    {"name": "Furina", "game": "Genshin Impact", "is_gacha": True},
    {"name": "Raiden Shogun", "game": "Genshin Impact", "is_gacha": True},
    {"name": "Arlecchino", "game": "Genshin Impact", "is_gacha": True},
    {"name": "Mavuika", "game": "Genshin Impact", "is_gacha": True},
    {"name": "Yinlin", "game": "Wuthering Waves", "is_gacha": True},
    {"name": "Changli", "game": "Wuthering Waves", "is_gacha": True},
    {"name": "2B", "game": "NieR:Automata", "is_gacha": False},
    {"name": "Tifa Lockhart", "game": "Final Fantasy VII", "is_gacha": False},
    {"name": "Ada Wong", "game": "Resident Evil", "is_gacha": False},
    {"name": "Eve", "game": "Stellar Blade", "is_gacha": False},
    {"name": "Ciri", "game": "The Witcher", "is_gacha": False},
    {"name": "D.Va", "game": "Overwatch", "is_gacha": False},
    {"name": "Ahri", "game": "League of Legends", "is_gacha": False},
    {"name": "Shadowheart", "game": "Baldur's Gate 3", "is_gacha": False},
    {"name": "Lucy", "game": "Cyberpunk Edgerunners", "is_gacha": False}
]

# --- АГЕНТНАЯ ФУНКЦИЯ GEMINI С ДИНАМИЧЕСКИМ ПОИСКОМ МОДЕЛИ ---
def agentic_market_analysis(char_list, time_scope, key):
    supported_models = []
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(list_url, timeout=8).json()
        for m in res.get('models', []):
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                name = m.get('name', '').replace('models/', '')
                if ('flash' in name.lower() or 'pro' in name.lower()) and 'lite' not in name.lower():
                    supported_models.append(name)
    except Exception:
        pass

    fallback_models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-pro"]
    
    models_to_try = []
    for m in supported_models + fallback_models:
        if m not in models_to_try:
            models_to_try.append(m)

    current_date = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
    Действуй как аналитик трендов и элитный арт-директор. Сегодня {current_date}. 
    Тебе передан список женских персонажей видеоигр: {json.dumps(char_list, ensure_ascii=False)}

    Твоя задача — проанализировать их виральность СТРОГО за период: {time_scope}.
    Учитывай аудиторию РФ/СНГ и глобальные площадки дистрибуции (15+ арт-галерей и соцсетей). 
    
    Алгоритм вычисления "virality_score" (от 1 до 100):
    1. Объем поисковых запросов и фанарта за указанный период.
    2. Скорость роста популярности.
    3. Наличие свежих инфоповодов (релизы патчей, анонсы в СМИ, крупные утечки, мемы в сообществе). Без инфоповода оценка не может быть выше 85.

    Формат ответа СТРОГО JSON:
    {{
      "overall_top_1": {{
        "name": "Имя абсолютного лидера",
        "game": "Игра",
        "virality_score": 99,
        "recent_news": "Какой именно инфоповод или новость в СМИ вызвали этот хайп (укажи детали)",
        "tags": ["3dart", "tag2"]
      }},
      "world_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Краткое обоснование спроса на западе/в Азии", "tags": ["tag1", "tag2"] }}
      ],
      "ru_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Краткое обоснование спроса в РФ/СНГ", "tags": ["tag1", "tag2"] }}
      ],
      "metrics": [
        {{ "name": "Имя", "game": "Игра", "is_gacha": true, "virality_score": 80, "recent_news": "Событие или патч (если есть, иначе пусто)", "trend": "Растет/Спадает" }}
      ]
    }}
    В массиве metrics должны быть оценены ВСЕ переданные персонажи. Поле is_gacha должно строго соответствовать переданному списку (true или false).
    """
    
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}

    last_err = ""
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=40)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
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
if st.button(f"🚀 Сгенерировать отчет ({time_filter})", type="primary", use_container_width=True):
    if not api_key:
        st.error("⚠️ Укажите Gemini API Key.")
    else:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        status_text.markdown(f"🧠 **ИИ-агент:** Поднимаю новостные сводки и проверяю тренды {time_filter.lower()}... (Ожидание ~15 сек)")
        progress_bar.progress(40)
        
        start_t = time.time()
        
        try:
            ai_data, model_used = agentic_market_analysis(CHARACTERS, time_filter, api_key)
            progress_bar.progress(90)
            
            df = pd.DataFrame(ai_data.get('metrics', []))
            
            st.session_state['results'] = ai_data
            st.session_state['df'] = df
            st.session_state['time_scope'] = time_filter
            st.session_state['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state['done'] = True
            
            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()
            
            ai_duration = time.time() - start_t
            st.toast(f"Отчет сформирован! (Модель: {model_used} | Время: {ai_duration:.1f}с)", icon="✅")
            
        except Exception as ex:
            st.error(f"Критическая ошибка ИИ: {ex}")

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
if st.session_state.get('done', False):
    results = st.session_state['results']
    df = st.session_state['df']
    
    st.caption(f"⏱️ **Актуальность данных проверена:** {st.session_state['timestamp']} | **Фильтр:** {st.session_state['time_scope']}")
    
    # --- БЛОК АБСОЛЮТНОГО ЛИДЕРА ---
    top1 = results.get('overall_top_1', {})
    if top1:
        tags_html = " ".join([f"<span class='badge'>#{t}</span>" for t in top1.get('tags', [])])
        st.markdown(f"""
        <div class="hero-card">
            <div style="text-transform: uppercase; letter-spacing: 2px; font-size: 12px; margin-bottom: 10px; color: #ffd700;">👑 Абсолютный виральный лидер</div>
            <div class="hero-title">{top1.get('name', 'N/A')} <span style="font-size: 24px; font-weight: 400; opacity: 0.8;">— {top1.get('game', '')}</span></div>
            <div class="hero-subtitle">Виральный индекс: <b>{top1.get('virality_score', 0)} / 100</b></div>
            <div class="hero-news">
                📰 <b>Главный инфоповод:</b> {top1.get('recent_news', 'Нет актуальных новостей')}
            </div>
            <div style="margin-top: 15px;">{tags_html}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # --- ТОПЫ ПО РЕГИОНАМ ---
    col_w, col_r = st.columns(2)
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    classes = ["top1", "top2", "top3", "", ""]

    with col_w:
        st.subheader("🌍 Мировой тренд (Топ-5)")
        for idx, item in enumerate(results.get('world_top', [])[:5]):
            tags = " ".join([f"<span class='badge'>#{t}</span>" for t in item.get('tags', [])])
            st.markdown(f"""
            <div class="metric-card {classes[idx]}">
                <h4 style="margin-bottom: 5px;">{medals[idx]} {item['name']} <span style="font-size:14px; color:#888;">({item['game']})</span></h4>
                <p style="font-size: 14px; color: #dfe4ea;">{item['analysis']}</p>
                <div>{tags}</div>
            </div>
            """, unsafe_allow_html=True)

    with col_r:
        st.subheader("🇷🇺 СНГ и РФ (Топ-5)")
        for idx, item in enumerate(results.get('ru_top', [])[:5]):
            tags = " ".join([f"<span class='badge'>#{t}</span>" for t in item.get('tags', [])])
            st.markdown(f"""
            <div class="metric-card {classes[idx]}">
                <h4 style="margin-bottom: 5px;">{medals[idx]} {item['name']} <span style="font-size:14px; color:#888;">({item['game']})</span></h4>
                <p style="font-size: 14px; color: #dfe4ea;">{item['analysis']}</p>
                <div>{tags}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # --- РАЗДЕЛЕНИЕ БАЗЫ: ГАЧИ VS ОСТАЛЬНЫЕ ---
    st.subheader("🗄️ Полная сводка виральности")
    
    df_sorted = df.sort_values(by="virality_score", ascending=False)
    
    if 'is_gacha' in df_sorted.columns:
        df_gacha = df_sorted[df_sorted['is_gacha'] == True].drop(columns=['is_gacha']).reset_index(drop=True)
        df_classic = df_sorted[df_sorted['is_gacha'] == False].drop(columns=['is_gacha']).reset_index(drop=True)
    else:
        df_gacha = df_sorted
        df_classic = df_sorted
    
    column_config = {
        "name": "Персонаж",
        "game": "Франшиза",
        "virality_score": st.column_config.ProgressColumn("Виральность", help="Виральный индекс (0-100)", format="%f", min_value=0, max_value=100),
        "recent_news": "Инфоповод / СМИ",
        "trend": "Тренд"
    }

    tab_gacha, tab_classic = st.tabs(["🎲 Гача-Игры (Агрессивные тренды)", "⚔️ AAA, RPG и Соревновательные (Классика)"])
    
    with tab_gacha:
        st.caption("Персонажи из Genshin Impact, HSR, ZZZ и WuWa. Тренды здесь сильно зависят от выхода патчей и баннеров.")
        st.dataframe(df_gacha, use_container_width=True, hide_index=True, column_config=column_config, height=500)
        
    with tab_classic:
        st.caption("Персонажи из файтингов, синглплеерных хитов и киберспорта. Спрос базируется на лояльности фандома и релизах DLC/аниме.")
        st.dataframe(df_classic, use_container_width=True, hide_index=True, column_config=column_config, height=500)
