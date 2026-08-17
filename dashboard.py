import streamlit as st
import pandas as pd
import requests
import json
import time
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor
import feedparser
import urllib.parse

# --- НАСТРОЙКА СТРАНИЦЫ ---
st.set_page_config(page_title="3D Art Hype Radar", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 20px; border-radius: 12px; border-left: 5px solid #ff4b4b; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .top1 {border-left-color: #ffd700;} 
    .top2 {border-left-color: #c0c0c0;} 
    .top3 {border-left-color: #cd7f32;}
    .badge {background-color: #2b2d35; padding: 4px 10px; border-radius: 6px; font-size: 13px; margin-right: 6px; color: #a5b1c2; border: 1px solid #3d404b;}
</style>
""", unsafe_allow_html=True)

# --- БЕЗОПАСНАЯ ЗАГРУЗКА СЕКРЕТОВ ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = st.sidebar.text_input("Gemini API Key:", type="password")

try:
    rapidapi_key = st.secrets["RAPIDAPI_KEY"]
except:
    rapidapi_key = st.sidebar.text_input("RapidAPI Key:", type="password")

st.title("⚡ AI Радар: Тренды 3D-арта из X (Twitter) & DeviantArt")
st.markdown("Предиктивная аналитика спроса на персонажей на основе живых данных соцсетей.")

with st.sidebar:
    if api_key and rapidapi_key:
        st.success("✅ Все API ключи подключены")
    elif api_key:
        st.warning("⚠️ Подключен только Gemini. Twitter отключен.")
    st.divider()

# --- БАЗА ПЕРСОНАЖЕЙ ДЛЯ МОНИТОРИНГА ---
CHARACTERS = [
    {"name": "Jane Doe", "query": "Jane Doe ZZZ art", "game": "ZZZ", "category": "ZZZ & WuWa"},
    {"name": "Ellen Joe", "query": "Ellen Joe ZZZ art", "game": "ZZZ", "category": "ZZZ & WuWa"},
    {"name": "Miyabi", "query": "Miyabi ZZZ art", "game": "ZZZ", "category": "ZZZ & WuWa"},
    {"name": "Firefly", "query": "Firefly Star Rail art", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    {"name": "Acheron", "query": "Acheron Star Rail art", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    {"name": "Kafka", "query": "Kafka Star Rail art", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    {"name": "Furina", "query": "Furina Genshin art", "game": "Genshin Impact", "category": "Genshin Impact"},
    {"name": "Raiden Shogun", "query": "Raiden Shogun art", "game": "Genshin Impact", "category": "Genshin Impact"},
    {"name": "2B", "query": "2B Nier art", "game": "NieR:Automata", "category": "Классика & AAA"},
    {"name": "Tifa Lockhart", "query": "Tifa Lockhart art", "game": "Final Fantasy VII", "category": "Классика & AAA"},
    {"name": "Eve", "query": "Eve Stellar Blade art", "game": "Stellar Blade", "category": "Классика & AAA"},
    {"name": "Ada Wong", "query": "Ada Wong art", "game": "Resident Evil", "category": "Классика & AAA"},
    {"name": "Ciri", "query": "Ciri Witcher art", "game": "The Witcher", "category": "Классика & AAA"},
    {"name": "D.Va", "query": "DVa Overwatch art", "game": "Overwatch", "category": "Соревновательные"},
    {"name": "Ahri", "query": "Ahri League of Legends art", "game": "League of Legends", "category": "Соревновательные"}
]

# --- ПАРСИНГ ПЛОЩАДОК ---

def fetch_deviantart_stats(query):
    """Сбор данных с открытого RSS DeviantArt"""
    try:
        encoded = urllib.parse.quote(query)
        feed = feedparser.parse(f"https://backend.deviantart.com/rss.xml?q=boost%3Apopular+{encoded}")
        count = len(feed.entries)
        return count, count * 20
    except:
        return 0, 0

def fetch_twitter_stats(query, key):
    """Сбор реальных твитов через The Old Bird API на RapidAPI"""
    if not key:
        return 0, 0
    url = "https://twitter154.p.rapidapi.com/search/search"
    querystring = {"query": query, "section": "top", "min_likes": "50", "limit": "20"}
    headers = {
        "x-rapidapi-key": key,
        "x-rapidapi-host": "twitter154.p.rapidapi.com"
    }
    try:
        res = requests.get(url, headers=headers, params=querystring, timeout=7)
        if res.status_code == 200:
            data = res.json()
            results = data.get('results', [])
            if isinstance(results, list) and len(results) > 0:
                likes = sum(int(t.get('favorite_count', 0)) for t in results)
                return len(results), likes
    except:
        pass
    return 0, 0

def collect_character_metrics(char):
    time.sleep(0.3)
    da_count, da_score = fetch_deviantart_stats(char['query'])
    tw_count, tw_score = fetch_twitter_stats(char['query'], rapidapi_key)
    
    total_posts = da_count + tw_count
    total_score = da_score + tw_score
    er = round(total_score / total_posts, 2) if total_posts > 0 else 0
    
    return {
        "Персонаж": char['name'],
        "Франшиза": char['game'],
        "Категория": char['category'],
        "X Твитов": tw_count,
        "DA Артов": da_count,
        "Суммарный хайп (Лайки)": total_score,
        "ER (Вовлеченность)": er
    }

# --- ИИ АНАЛИЗАТОР GEMINI ---

def analyze_with_gemini(metrics, key):
    supported = []
    try:
        res = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", timeout=8).json()
        for m in res.get('models', []):
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                name = m.get('name', '').replace('models/', '')
                if 'flash' in name.lower() and 'lite' not in name.lower():
                    supported.append(name)
    except:
        pass
        
    models_to_try = supported + ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-pro"]

    prompt = f"""
    Проанализируй реальные данные вовлеченности (ER) и объема обсуждений из X (Twitter) и DeviantArt:
    {json.dumps(metrics, ensure_ascii=False)}

    Определи ТОП-5 женских персонажей для создания качественного 3D-арта прямо сейчас.
    Сформируй две категории:
    1. world_top: Глобальный спрос на мировом рынке.
    2. ru_top: Спрос в СНГ (гачи + классика).

    Верни ответ СТРОГО в формате JSON:
    {{
      "world_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Обоснование спроса", "tags": ["3dart", "tag2", "tag3"] }}
      ],
      "ru_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Обоснование спроса", "tags": ["3dart", "tag2", "tag3"] }}
      ]
    }}
    """

    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}

    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
            resp = requests.post(url, headers=headers, json=payload, timeout=25)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                return json.loads(raw_text), model_name
        except:
            continue
    raise RuntimeError("Ошибка вызова Gemini API.")

# --- ИНТЕРФЕЙС ---

if st.button("🚀 Запустить мониторинг соцсетей", type="primary", use_container_width=True):
    if not api_key:
        st.error("⚠️ Укажите Gemini API Key.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        metrics_list = []
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            for idx, item in enumerate(executor.map(collect_character_metrics, CHARACTERS)):
                metrics_list.append(item)
                progress_bar.progress((idx + 1) / len(CHARACTERS))
                status_text.markdown(f"📡 Сбор метрик X & DA: **{idx + 1} / {len(CHARACTERS)}**")

        status_text.markdown("🧠 Обработка трендов через Gemini Flash...")
        try:
            ai_data, model_name = analyze_with_gemini(metrics_list, api_key)
            st.session_state['results'] = ai_data
            st.session_state['df'] = pd.DataFrame(metrics_list).sort_values(by="ER (Вовлеченность)", ascending=False)
            st.session_state['done'] = True
            progress_bar.empty()
            status_text.empty()
            st.toast("Анализ соцсетей завершен!", icon="✅")
        except Exception as e:
            st.error(f"Ошибка ИИ: {e}")

# --- ВЫВОД РЕЗУЛЬТАТОВ ---

if st.session_state.get('done', False):
    df = st.session_state['df']
    results = st.session_state['results']
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    classes = ["top1", "top2", "top3", "top4", "top5"]

    st.divider()
    
    # Графики
    col1, col2 = st.columns(2)
    with col1:
        fig_bar = px.bar(
            df.head(8), x="ER (Вовлеченность)", y="Персонаж", orientation="h",
            color="ER (Вовлеченность)", color_continuous_scale="Viridis",
            title="🔥 Топ по вовлеченности в X и DA", template="plotly_dark"
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col2:
        fig_bubble = px.scatter(
            df, x="DA Артов", y="X Твитов", size="Суммарный хайп (Лайки)",
            color="Категория", hover_name="Персонаж",
            title="Активность: DeviantArt vs X (Twitter)", template="plotly_dark", size_max=35
        )
        st.plotly_chart(fig_bubble, use_container_width=True)

    tab_w, tab_r, tab_all = st.tabs(["🌍 Глобальный ТОП", "🇷🇺 ТОП СНГ", "📊 Полная таблица соцсетей"])

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
