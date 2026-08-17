import streamlit as st
import pandas as pd
import requests
import json
import time

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="3D Art Hype Scanner", page_icon="🎨", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 18px; border-radius: 8px; border-left: 5px solid #ff4b4b; margin-bottom: 12px;}
    .top1 {border-left-color: #ffd700;} 
    .top2 {border-left-color: #c0c0c0;} 
    .top3 {border-left-color: #cd7f32;}
    .top4 {border-left-color: #4b8bff;}
    .top5 {border-left-color: #ff4b8b;}
    .badge {background-color: #262730; padding: 3px 8px; border-radius: 4px; font-size: 12px; margin-right: 5px;}
</style>
""", unsafe_allow_html=True)

st.title("🎨 Аналитика спроса: 3D-арт женских персонажей")
st.markdown("Предиктивный отбор самых востребованных героинь для моделирования и рендеров.")

with st.sidebar:
    st.header("Настройки")
    api_key = st.text_input("Gemini API Key:", type="password")
    st.divider()
    st.info("💡 **Как работает сбор:** Система последовательно опрашивает открытые API с официальным User-Agent, что исключает блокировки и зависания.")

# --- БАЗА ТЕГОВ ---
CHARACTERS = [
    {"name": "Jane Doe", "tag": "jane_doe_(zenless_zone_zero)", "game": "ZZZ"},
    {"name": "Ellen Joe", "tag": "ellen_joe_(zenless_zone_zero)", "game": "ZZZ"},
    {"name": "Miyabi", "tag": "hoshimi_miyabi", "game": "ZZZ"},
    {"name": "Zhu Yuan", "tag": "zhu_yuan_(zenless_zone_zero)", "game": "ZZZ"},
    {"name": "Nicole Demara", "tag": "nicole_demara", "game": "ZZZ"},
    
    {"name": "Firefly", "tag": "firefly_(honkai_star_rail)", "game": "Honkai Star Rail"},
    {"name": "Acheron", "tag": "acheron_(honkai_star_rail)", "game": "Honkai Star Rail"},
    {"name": "Kafka", "tag": "kafka_(honkai_star_rail)", "game": "Honkai Star Rail"},
    {"name": "Black Swan", "tag": "black_swan_(honkai_star_rail)", "game": "Honkai Star Rail"},
    {"name": "Ruan Mei", "tag": "ruan_mei_(honkai_star_rail)", "game": "Honkai Star Rail"},
    {"name": "Sparkle", "tag": "sparkle_(honkai_star_rail)", "game": "Honkai Star Rail"},
    {"name": "Jingliu", "tag": "jingliu_(honkai_star_rail)", "game": "Honkai Star Rail"},
    
    {"name": "Furina", "tag": "furina_(genshin_impact)", "game": "Genshin Impact"},
    {"name": "Raiden Shogun", "tag": "raiden_shogun", "game": "Genshin Impact"},
    {"name": "Yelan", "tag": "yelan_(genshin_impact)", "game": "Genshin Impact"},
    {"name": "Navia", "tag": "navia_(genshin_impact)", "game": "Genshin Impact"},
    {"name": "Arlecchino", "tag": "arlecchino_(genshin_impact)", "game": "Genshin Impact"},
    {"name": "Hu Tao", "tag": "hu_tao_(genshin_impact)", "game": "Genshin Impact"},
    
    {"name": "Tifa Lockhart", "tag": "tifa_lockhart", "game": "Final Fantasy VII"},
    {"name": "Aerith Gainsborough", "tag": "aerith_gainsborough", "game": "Final Fantasy VII"},
    {"name": "2B", "tag": "yorha_no._2_type_b", "game": "NieR:Automata"},
    {"name": "Ada Wong", "tag": "ada_wong", "game": "Resident Evil"},
    {"name": "Eve", "tag": "eve_(stellar_blade)", "game": "Stellar Blade"},
    {"name": "Lara Croft", "tag": "lara_croft", "game": "Tomb Raider"},
    
    {"name": "Chun-Li", "tag": "chun-li", "game": "Street Fighter"},
    {"name": "Cammy White", "tag": "cammy_white", "game": "Street Fighter"},
    {"name": "Juri Han", "tag": "juri_han", "game": "Street Fighter"},
    
    {"name": "Ciri", "tag": "cirilla_fiona_elen_riannon", "game": "The Witcher"},
    {"name": "Yennefer", "tag": "yennefer_of_vengerberg", "game": "The Witcher"},
    {"name": "Lucy", "tag": "lucyna_kushinada", "game": "Cyberpunk"},
    {"name": "D.Va", "tag": "d.va_(overwatch)", "game": "Overwatch"},
    {"name": "Ahri", "tag": "ahri_(league_of_legends)", "game": "League of Legends"},
    {"name": "Jinx", "tag": "jinx_(league_of_legends)", "game": "League of Legends"}
]

# --- НАДЕЖНЫЙ СБОР ДАННЫХ ---

def fetch_art_stats(char):
    # Кастомный User-Agent, чтобы Danbooru не банил запрос как ботнет
    headers = {'User-Agent': 'ArtHypeScanner/1.0 (project for 3d artists)'}
    
    # 1. Попытка через Danbooru (Самая точная база по новым играм)
    try:
        url = "https://danbooru.donmai.us/posts.json"
        params = {"limit": 40, "tags": char['tag']}
        res = requests.get(url, params=params, headers=headers, timeout=5)
        
        if res.status_code == 200:
            posts = res.json()
            if isinstance(posts, list) and len(posts) > 0:
                score = sum(int(p.get('score', 0)) + int(p.get('up_score', 0)) for p in posts)
                count = len(posts)
                er = round((score / count), 2) if count > 0 else 0
                return {"Персонаж": char['name'], "Франшиза": char['game'], "Новых работ": count, "Суммарный скор": score, "ER (Вовлеченность)": er}
    except Exception:
        pass

    # 2. Резерв через Safebooru
    try:
        url = "https://safebooru.org/index.php"
        params = {"page": "dapi", "s": "post", "q": "index", "json": 1, "limit": 40, "tags": char['tag']}
        res = requests.get(url, params=params, headers=headers, timeout=5)
        
        if res.status_code == 200:
            posts = res.json()
            if isinstance(posts, list) and len(posts) > 0:
                score = sum(int(p.get('score', 0)) for p in posts)
                count = len(posts)
                er = round((score / count), 2) if count > 0 else 0
                return {"Персонаж": char['name'], "Франшиза": char['game'], "Новых работ": count, "Суммарный скор": score, "ER (Вовлеченность)": er}
    except Exception:
        pass

    return {"Персонаж": char['name'], "Франшиза": char['game'], "Новых работ": 0, "Суммарный скор": 0, "ER (Вовлеченность)": 0}

# --- ВЫЗОВ GEMINI API ---

def request_gemini_analysis(metrics, key):
    dynamic_models = []
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(list_url, timeout=6).json()
        for m in res.get('models', []):
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                dynamic_models.append(m['name'].replace('models/', ''))
    except:
        pass

    fallback_pool = [
        "gemini-2.0-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash"
    ]

    models_to_try = []
    for model in dynamic_models + fallback_pool:
        if "flash" in model.lower() and "lite" not in model.lower() and model not in models_to_try:
            models_to_try.append(model)

    prompt = f"""
    Проанализируй эти точные метрики спроса (ER - вовлеченность, Новых работ - конкуренция):
    {json.dumps(metrics, ensure_ascii=False)}

    Твоя задача — отобрать ТОП-5 женских персонажей для создания качественного 3D-арта. 
    Учитывай, что готовые работы будут активно публиковаться на 15+ различных арт-площадках и соцсетях. Нам нужны персонажи, которые дадут максимальный охват прямо сейчас.

    Сформируй две выборки:
    1. world_top: ТОП-5 по мировому тренду (высокий ER, глобальный интерес).
    2. ru_top: ТОП-5 с учетом предпочтений СНГ/РФ аудитории (гачи + классика).

    Формат ответа СТРОГО JSON:
    {{
      "world_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Четкое обоснование выбора", "tags": ["3dart", "tag2", "tag3"] }}
      ],
      "ru_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Четкое обоснование выбора", "tags": ["3dart", "tag2", "tag3"] }}
      ]
    }}
    """

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    last_err = ""
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                result_json = resp.json()
                raw_text = result_json['candidates'][0]['content']['parts'][0]['text']
                return json.loads(raw_text), model_name
            else:
                last_err = resp.text
        except Exception as e:
            last_err = str(e)
            continue

    raise RuntimeError(f"Сбой моделей Gemini. Ошибка: {last_err}")

# --- ИНТЕРФЕЙС И ЗАПУСК ---

col_btn, col_status = st.columns([1, 3])

with col_btn:
    start_scan = st.button("🚀 Запустить глубокий скан рынка", type="primary", use_container_width=True)

if start_scan:
    if not api_key:
        st.error("⚠️ Укажите Gemini API Key в левой панели.")
    else:
        # Контейнеры для отображения процесса
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        raw_metrics = []
        start_t = time.time()
        
        # Последовательный сбор данных с паузами (без зависаний потоков)
        for idx, char in enumerate(CHARACTERS):
            status_text.markdown(f"📡 Сканирование баз данных: **{char['name']}** ({char['game']})...")
            
            stats = fetch_art_stats(char)
            raw_metrics.append(stats)
            
            # Обновляем полосу загрузки
            progress = (idx + 1) / len(CHARACTERS)
            progress_bar.progress(progress)
            
            time.sleep(0.3) # Пауза, чтобы сервер не принял нас за спамеров
            
        fetch_duration = time.time() - start_t
        status_text.markdown("✅ Данные собраны! Анализ через нейросеть Gemini...")
        
        try:
            ai_start_t = time.time()
            ai_response, model_used = request_gemini_analysis(raw_metrics, api_key)
            ai_duration = time.time() - ai_start_t
            
            st.session_state['ai_results'] = ai_response
            st.session_state['metrics_df'] = pd.DataFrame(raw_metrics).sort_values(by="ER (Вовлеченность)", ascending=False)
            st.session_state['scan_done'] = True
            
            status_text.empty()
            progress_bar.empty()
            st.success(f"Анализ завершен ({model_used}). Сбор: {fetch_duration:.1f}с | ИИ: {ai_duration:.1f}с")
        except Exception as ex:
            st.error(f"Ошибка при анализе: {ex}")

# --- ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ ---

if st.session_state.get('scan_done', False):
    st.divider()
    tab_world, tab_ru, tab_all = st.tabs([
        "🌍 ТОП-5 Мировой тренд", 
        "🇷🇺 ТОП-5 СНГ и РФ", 
        "💯 Полный рейтинг"
    ])
    
    top_data = st.session_state['ai_results']
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    classes = ["top1", "top2", "top3", "top4", "top5"]

    with tab_world:
        st.subheader("Лидеры глобального спроса")
        for idx, item in enumerate(top_data.get('world_top', [])[:5]):
            tags = " ".join([f"<span class='badge'>#{t}</span>" for t in item.get('tags', [])])
            st.markdown(f"""
            <div class="metric-card {classes[idx]}">
                <h3>{medals[idx]} {item['name']} <span style="font-size:15px; color:#888;">({item['game']})</span></h3>
                <p><b>Обоснование:</b> {item['analysis']}</p>
                <div>{tags}</div>
            </div>
            """, unsafe_allow_html=True)

    with tab_ru:
        st.subheader("Лидеры спроса в СНГ / РФ")
        for idx, item in enumerate(top_data.get('ru_top', [])[:5]):
            tags = " ".join([f"<span class='badge'>#{t}</span>" for t in item.get('tags', [])])
            st.markdown(f"""
            <div class="metric-card {classes[idx]}">
                <h3>{medals[idx]} {item['name']} <span style="font-size:15px; color:#888;">({item['game']})</span></h3>
                <p><b>Обоснование:</b> {item['analysis']}</p>
                <div>{tags}</div>
            </div>
            """, unsafe_allow_html=True)

    with tab_all:
        st.subheader("Сводная таблица вовлеченности (ER)")
        st.dataframe(st.session_state['metrics_df'], use_container_width=True, hide_index=True)
