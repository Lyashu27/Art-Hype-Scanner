import streamlit as st
import pandas as pd
import requests
import json
import time
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="3D Art Hype Scanner Pro", page_icon="🎨", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 20px; border-radius: 12px; border-left: 5px solid #ff4b4b; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .top1 {border-left-color: #ffd700;} 
    .top2 {border-left-color: #c0c0c0;} 
    .top3 {border-left-color: #cd7f32;}
    .badge {background-color: #2b2d35; padding: 4px 10px; border-radius: 6px; font-size: 13px; margin-right: 6px; color: #a5b1c2; border: 1px solid #3d404b;}
    .stat-row {display: flex; justify-content: space-between; margin-top: 10px; font-size: 14px; color: #d1d8e0;}
    .stTabs [data-baseweb="tab-list"] {gap: 8px;}
    .stTabs [data-baseweb="tab"] {background-color: #1e212b; border-radius: 4px 4px 0px 0px; padding: 10px 20px;}
</style>
""", unsafe_allow_html=True)

# --- БЕЗОПАСНАЯ ЗАГРУЗКА КЛЮЧА ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except (KeyError, FileNotFoundError):
    api_key = st.sidebar.text_input("Gemini API Key (Секрет не настроен):", type="password")

st.title("🎨 Аналитика 3D-арта: Глобальный радар хайпа")
st.markdown("Предиктивный отбор героинь для создания вирального контента и дистрибуции на 15+ арт-платформ.")

with st.sidebar:
    if api_key:
        st.success("✅ API Ключ подключен")
    st.divider()
    st.info("💡 **Архитектура сканирования:** Скрипт анализирует почти 100 персонажей, разбивая их на когорты. Гача-игры вынесены в отдельные пулы для точного отслеживания трендов.")

# --- МАССИВНАЯ БАЗА ПЕРСОНАЖЕЙ (Разбита по категориям) ---
CHARACTERS = [
    # --- Genshin Impact ---
    {"name": "Raiden Shogun", "tag": "raiden_shogun", "game": "Genshin Impact", "category": "Genshin Impact"},
    {"name": "Furina", "tag": "furina_(genshin_impact)", "game": "Genshin Impact", "category": "Genshin Impact"},
    {"name": "Hu Tao", "tag": "hu_tao_(genshin_impact)", "game": "Genshin Impact", "category": "Genshin Impact"},
    {"name": "Yelan", "tag": "yelan_(genshin_impact)", "game": "Genshin Impact", "category": "Genshin Impact"},
    {"name": "Navia", "tag": "navia_(genshin_impact)", "game": "Genshin Impact", "category": "Genshin Impact"},
    {"name": "Arlecchino", "tag": "arlecchino_(genshin_impact)", "game": "Genshin Impact", "category": "Genshin Impact"},
    {"name": "Ganyu", "tag": "ganyu_(genshin_impact)", "game": "Genshin Impact", "category": "Genshin Impact"},
    {"name": "Ayaka", "tag": "kamisato_ayaka", "game": "Genshin Impact", "category": "Genshin Impact"},
    {"name": "Yae Miko", "tag": "yae_miko", "game": "Genshin Impact", "category": "Genshin Impact"},
    {"name": "Nilou", "tag": "nilou_(genshin_impact)", "game": "Genshin Impact", "category": "Genshin Impact"},
    {"name": "Shenhe", "tag": "shenhe_(genshin_impact)", "game": "Genshin Impact", "category": "Genshin Impact"},
    {"name": "Clorinde", "tag": "clorinde_(genshin_impact)", "game": "Genshin Impact", "category": "Genshin Impact"},
    
    # --- Honkai: Star Rail ---
    {"name": "Firefly", "tag": "firefly_(honkai_star_rail)", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    {"name": "Acheron", "tag": "acheron_(honkai_star_rail)", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    {"name": "Kafka", "tag": "kafka_(honkai_star_rail)", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    {"name": "Black Swan", "tag": "black_swan_(honkai_star_rail)", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    {"name": "Ruan Mei", "tag": "ruan_mei_(honkai_star_rail)", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    {"name": "Sparkle", "tag": "sparkle_(honkai_star_rail)", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    {"name": "Jingliu", "tag": "jingliu_(honkai_star_rail)", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    {"name": "Topaz", "tag": "topaz_(honkai_star_rail)", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    {"name": "Robin", "tag": "robin_(honkai_star_rail)", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    {"name": "Feixiao", "tag": "feixiao_(honkai_star_rail)", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    {"name": "Yunli", "tag": "yunli_(honkai_star_rail)", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    {"name": "Jade", "tag": "jade_(honkai_star_rail)", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    
    # --- ZZZ & Wuthering Waves ---
    {"name": "Jane Doe", "tag": "jane_doe_(zenless_zone_zero)", "game": "ZZZ", "category": "ZZZ & WuWa"},
    {"name": "Ellen Joe", "tag": "ellen_joe_(zenless_zone_zero)", "game": "ZZZ", "category": "ZZZ & WuWa"},
    {"name": "Miyabi", "tag": "hoshimi_miyabi", "game": "ZZZ", "category": "ZZZ & WuWa"},
    {"name": "Zhu Yuan", "tag": "zhu_yuan_(zenless_zone_zero)", "game": "ZZZ", "category": "ZZZ & WuWa"},
    {"name": "Nicole Demara", "tag": "nicole_demara", "game": "ZZZ", "category": "ZZZ & WuWa"},
    {"name": "Grace Howard", "tag": "grace_howard", "game": "ZZZ", "category": "ZZZ & WuWa"},
    {"name": "Yinlin", "tag": "yinlin_(wuthering_waves)", "game": "Wuthering Waves", "category": "ZZZ & WuWa"},
    {"name": "Changli", "tag": "changli_(wuthering_waves)", "game": "Wuthering Waves", "category": "ZZZ & WuWa"},
    {"name": "Jinhsi", "tag": "jinhsi_(wuthering_waves)", "game": "Wuthering Waves", "category": "ZZZ & WuWa"},
    {"name": "Baizhi", "tag": "baizhi_(wuthering_waves)", "game": "Wuthering Waves", "category": "ZZZ & WuWa"},
    
    # --- Другие Гачи (Nikke, BA, Azur Lane, Arknights) ---
    {"name": "Rapi", "tag": "rapi_(nikke)", "game": "Goddess of Victory: Nikke", "category": "Другие Гачи"},
    {"name": "Viper", "tag": "viper_(nikke)", "game": "Goddess of Victory: Nikke", "category": "Другие Гачи"},
    {"name": "Alice", "tag": "alice_(nikke)", "game": "Goddess of Victory: Nikke", "category": "Другие Гачи"},
    {"name": "Shiroko", "tag": "sunaookami_shiroko", "game": "Blue Archive", "category": "Другие Гачи"},
    {"name": "Asuna", "tag": "ichinose_asuna", "game": "Blue Archive", "category": "Другие Гачи"},
    {"name": "Atago", "tag": "atago_(azur_lane)", "game": "Azur Lane", "category": "Другие Гачи"},
    {"name": "Taihou", "tag": "taihou_(azur_lane)", "game": "Azur Lane", "category": "Другие Гачи"},
    {"name": "Surtr", "tag": "surtr_(arknights)", "game": "Arknights", "category": "Другие Гачи"},
    
    # --- Классика AAA & RPG ---
    {"name": "2B", "tag": "yorha_no._2_type_b", "game": "NieR:Automata", "category": "Классика & AAA"},
    {"name": "Tifa Lockhart", "tag": "tifa_lockhart", "game": "Final Fantasy VII", "category": "Классика & AAA"},
    {"name": "Aerith Gainsborough", "tag": "aerith_gainsborough", "game": "Final Fantasy VII", "category": "Классика & AAA"},
    {"name": "Ada Wong", "tag": "ada_wong", "game": "Resident Evil", "category": "Классика & AAA"},
    {"name": "Jill Valentine", "tag": "jill_valentine", "game": "Resident Evil", "category": "Классика & AAA"},
    {"name": "Eve", "tag": "eve_(stellar_blade)", "game": "Stellar Blade", "category": "Классика & AAA"},
    {"name": "Lara Croft", "tag": "lara_croft", "game": "Tomb Raider", "category": "Классика & AAA"},
    {"name": "Ciri", "tag": "cirilla_fiona_elen_riannon", "game": "The Witcher", "category": "Классика & AAA"},
    {"name": "Yennefer", "tag": "yennefer_of_vengerberg", "game": "The Witcher", "category": "Классика & AAA"},
    {"name": "Shadowheart", "tag": "shadowheart_(baldurs_gate)", "game": "Baldur's Gate 3", "category": "Классика & AAA"},
    {"name": "Lucy", "tag": "lucyna_kushinada", "game": "Cyberpunk", "category": "Классика & AAA"},
    
    # --- Файтинги, Шутеры, Киберспорт ---
    {"name": "Chun-Li", "tag": "chun-li", "game": "Street Fighter", "category": "Соревновательные"},
    {"name": "Cammy White", "tag": "cammy_white", "game": "Street Fighter", "category": "Соревновательные"},
    {"name": "Juri Han", "tag": "juri_han", "game": "Street Fighter", "category": "Соревновательные"},
    {"name": "Mai Shiranui", "tag": "mai_shiranui", "game": "King of Fighters", "category": "Соревновательные"},
    {"name": "D.Va", "tag": "d.va_(overwatch)", "game": "Overwatch", "category": "Соревновательные"},
    {"name": "Widowmaker", "tag": "widowmaker_(overwatch)", "game": "Overwatch", "category": "Соревновательные"},
    {"name": "Kiriko", "tag": "kiriko_(overwatch)", "game": "Overwatch", "category": "Соревновательные"},
    {"name": "Ahri", "tag": "ahri_(league_of_legends)", "game": "League of Legends", "category": "Соревновательные"},
    {"name": "Jinx", "tag": "jinx_(league_of_legends)", "game": "League of Legends", "category": "Соревновательные"},
    {"name": "Viper", "tag": "viper_(valorant)", "game": "Valorant", "category": "Соревновательные"}
]

# --- ОПТИМИЗИРОВАННЫЙ СБОР ДАННЫХ ---
def fetch_art_stats(char):
    time.sleep(0.2) # Минимальная задержка для защиты от бана IP
    headers = {'User-Agent': 'ArtHypeScanner/3.0 (Analytics for 3D Artists)'}
    
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
                return {"Персонаж": char['name'], "Франшиза": char['game'], "Категория": char['category'], "Конкуренция (Новых работ)": count, "Суммарный скор": score, "ER (Вовлеченность)": er}
    except:
        pass

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
                return {"Персонаж": char['name'], "Франшиза": char['game'], "Категория": char['category'], "Конкуренция (Новых работ)": count, "Суммарный скор": score, "ER (Вовлеченность)": er}
    except:
        pass

    return {"Персонаж": char['name'], "Франшиза": char['game'], "Категория": char['category'], "Конкуренция (Новых работ)": 0, "Суммарный скор": 0, "ER (Вовлеченность)": 0}

# --- ИИ АНАЛИЗ (Ориентир на 3D арт и 15+ площадок) ---
def request_gemini_analysis(metrics, key):
    supported_models = []
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(list_url, timeout=8).json()
        for m in res.get('models', []):
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                name = m.get('name', '').replace('models/', '')
                if 'flash' in name.lower() and 'lite' not in name.lower():
                    supported_models.append(name)
    except Exception:
        pass

    fallback_models = ["gemini-2.5-flash", "gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-pro"]
    models_to_try = supported_models + [m for m in fallback_models if m not in supported_models]

    prompt = f"""
    Ты элитный арт-директор. Мы просканировали рынок и собрали точные метрики спроса (ER - вовлеченность, Конкуренция - объем новых работ) по десяткам героинь:
    {json.dumps(metrics, ensure_ascii=False)}

    Твоя задача — отобрать ТОП-7 женских персонажей для создания высококачественного 3D-арта.
    Учитывай главное правило: готовые работы будут системно публиковаться на 15+ арт-платформах и соцсетях. Нам нужны персонажи, которые пробивают алгоритмы и дают виральный охват прямо сейчас.

    Сформируй две выборки:
    1. world_top: Глобальный ТОП-7 (максимальный хайп на западных и азиатских площадках).
    2. ru_top: ТОП-7 с адаптацией под СНГ/РФ аудиторию (где традиционно сильны позиции гач, а также культовой классики).

    Формат ответа СТРОГО JSON:
    {{
      "world_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Профессиональное обоснование потенциала", "tags": ["tag1", "tag2"] }}
      ],
      "ru_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Профессиональное обоснование потенциала", "tags": ["tag1", "tag2"] }}
      ]
    }}
    """
    
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}

    last_err = ""
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=25)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                return json.loads(raw_text), model_name
            else:
                last_err = f"[{model_name}] {resp.status_code}: {resp.text}"
        except Exception as e:
            last_err = f"[{model_name}] {str(e)}"
            continue

    raise RuntimeError(f"Сбой API Gemini. Детали: {last_err}")

# --- ИНТЕРФЕЙС И ЗАПУСК ---
if st.button("🚀 Запустить нейросканирование рынка (100 героинь)", type="primary", use_container_width=True):
    if not api_key:
        st.error("⚠️ API Ключ не настроен.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        raw_metrics = []
        start_t = time.time()
        
        # Безопасный многопоточный сбор (6 потоков = оптимальный баланс скорости и обхода 429)
        with ThreadPoolExecutor(max_workers=6) as executor:
            for idx, result in enumerate(executor.map(fetch_art_stats, CHARACTERS)):
                raw_metrics.append(result)
                progress_bar.progress((idx + 1) / len(CHARACTERS))
                status_text.markdown(f"📡 Опрашиваем базы данных... Загружено: **{idx + 1} / {len(CHARACTERS)}**")
                
        status_text.markdown("🧠 Массив данных собран. Передаем матрицу в ИИ для анализа 3D-потенциала...")
        
        try:
            ai_start_t = time.time()
            ai_response, model_used = request_gemini_analysis(raw_metrics, api_key)
            
            st.session_state['ai_results'] = ai_response
            st.session_state['metrics_df'] = pd.DataFrame(raw_metrics).sort_values(by="ER (Вовлеченность)", ascending=False)
            st.session_state['scan_done'] = True
            
            status_text.empty()
            progress_bar.empty()
            fetch_time = time.time() - start_t
            st.toast(f"Сканирование успешно! (Модель: {model_used} | Время: {fetch_time:.1f}с)", icon="✅")
        except Exception as ex:
            st.error(f"Ошибка: {ex}")

# --- ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ, ГРАФИКОВ И КАТЕГОРИЙ ---
if st.session_state.get('scan_done', False):
    df = st.session_state['metrics_df']
    top_data = st.session_state['ai_results']
    
    st.divider()
    
    # Расширенные вкладки интерфейса
    tabs = st.tabs([
        "🌍 Глобальный ТОП ИИ", 
        "🇷🇺 СНГ ТОП ИИ", 
        "🔹 Genshin Impact", 
        "🚂 Honkai: Star Rail", 
        "📺 ZZZ & WuWa", 
        "🎲 Другие Гачи", 
        "⚔️ Классика & AAA", 
        "🎯 Соревновательные",
        "📊 Сводная матрица"
    ])

    # Функция рендера карточек ИИ
    def render_ai_cards(category_key):
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣"]
        for idx, item in enumerate(top_data.get(category_key, [])[:7]):
            tags = "".join([f"<span class='badge'>#{t}</span>" for t in item.get('tags', [])])
            css_class = f"top{idx+1}" if idx < 3 else "metric-card" # Подсветка только топ-3
            if idx >= 3: css_class = "metric-card"
            st.markdown(f"""
            <div class="metric-card {css_class if idx < 3 else ''}">
                <h3 style="margin-bottom: 5px;">{medals[idx]} {item['name']} <span style="font-size:16px; color:#a5b1c2; font-weight:normal;">— {item['game']}</span></h3>
                <p style="color: #dfe4ea; margin-bottom: 12px; font-size: 15px;">{item['analysis']}</p>
                <div>{tags}</div>
            </div>
            """, unsafe_allow_html=True)

    # Функция рендера аналитики по категориям (Игры)
    def render_category_analytics(category_name):
        cat_df = df[df['Категория'] == category_name]
        if not cat_df.empty:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.dataframe(cat_df[['Персонаж', 'ER (Вовлеченность)', 'Конкуренция (Новых работ)']], hide_index=True, use_container_width=True)
            with col2:
                fig = px.scatter(
                    cat_df, x="Конкуренция (Новых работ)", y="ER (Вовлеченность)", 
                    color="Персонаж", size="Суммарный скор", text="Персонаж",
                    title=f"Матрица спроса: {category_name}", 
                    template="plotly_dark", size_max=40
                )
                fig.update_traces(textposition='top center')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных по этой категории.")

    # Заполнение вкладок
    with tabs[0]: render_ai_cards('world_top')
    with tabs[1]: render_ai_cards('ru_top')
    with tabs[2]: render_category_analytics('Genshin Impact')
    with tabs[3]: render_category_analytics('Honkai: Star Rail')
    with tabs[4]: render_category_analytics('ZZZ & WuWa')
    with tabs[5]: render_category_analytics('Другие Гачи')
    with tabs[6]: render_category_analytics('Классика & AAA')
    with tabs[7]: render_category_analytics('Соревновательные')
    
    with tabs[8]:
        st.subheader("Глобальный срез: Все франшизы")
        fig_scatter = px.scatter(
            df, x="Конкуренция (Новых работ)", y="ER (Вовлеченность)", 
            color="Категория", size="Суммарный скор", hover_name="Персонаж",
            title="Сводная матрица: Конкуренция vs Вовлеченность", 
            template="plotly_dark", size_max=50, height=600
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
