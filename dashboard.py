import streamlit as st
import pandas as pd
import requests
import json
import time
import plotly.express as px
from concurrent.futures import ThreadPoolExecutor
import feedparser
import urllib.parse

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="3D Art Hype Scanner Pro", page_icon="🎨", layout="wide")

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
    rapidapi_key = st.sidebar.text_input("RapidAPI Key (Для X и Pixiv):", type="password", help="Получить на rapidapi.com")

st.title("🎨 Аналитика 3D-арта: Real-Time Соцсети")
st.markdown("Предиктивный отбор героинь на основе данных DeviantArt, X (Twitter) и Pixiv.")

# --- БАЗА ПЕРСОНАЖЕЙ (Сокращенная для примера, можешь вернуть полный список) ---
CHARACTERS = [
    {"name": "Jane Doe", "tag": "jane doe zenless", "game": "ZZZ", "category": "ZZZ & WuWa"},
    {"name": "Firefly", "tag": "firefly honkai", "game": "Honkai Star Rail", "category": "Honkai: Star Rail"},
    {"name": "Furina", "tag": "furina genshin", "game": "Genshin Impact", "category": "Genshin Impact"},
    {"name": "2B", "tag": "2b nier", "game": "NieR:Automata", "category": "Классика & AAA"}
]

# --- ПАРСЕРЫ СОЦСЕТЕЙ ---

def fetch_deviantart(search_query):
    """Парсинг DeviantArt через открытый RSS (Работает без ключей)"""
    encoded_query = urllib.parse.quote(search_query)
    url = f"https://backend.deviantart.com/rss.xml?q=boost%3Apopular+in%3Adigitalart+{encoded_query}"
    try:
        feed = feedparser.parse(url)
        count = len(feed.entries)
        # Имитируем score на основе количества популярных артов в выдаче
        score = count * 15 
        return count, score
    except:
        return 0, 0

def fetch_x_twitter(search_query, key):
    """Парсинг X (Twitter) через RapidAPI (Требует ключ)"""
    if not key: return 0, 0
    # Пример использования популярного API "Twitter API v2" на RapidAPI
    url = "https://twitter-api45.p.rapidapi.com/search.php"
    querystring = {"query": search_query, "search_type":"Top"}
    headers = {
        "x-rapidapi-key": key,
        "x-rapidapi-host": "twitter-api45.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=5)
        data = response.json()
        count = len(data.get('timeline', []))
        score = sum(int(t.get('favorites', 0)) for t in data.get('timeline', []))
        return count, score
    except:
        return 0, 0

def fetch_pixiv(search_query, key):
    """Парсинг Pixiv через RapidAPI (Требует ключ)"""
    if not key: return 0, 0
    # Пример использования "Pixiv API" на RapidAPI
    url = "https://pixiv-api.p.rapidapi.com/search/illusts"
    querystring = {"word": search_query, "mode":"safe"}
    headers = {
        "x-rapidapi-key": key,
        "x-rapidapi-host": "pixiv-api.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=5)
        data = response.json()
        illusts = data.get('illusts', [])
        count = len(illusts)
        score = sum(int(i.get('total_bookmarks', 0)) for i in illusts)
        return count, score
    except:
        return 0, 0

def fetch_all_platforms(char):
    time.sleep(0.5) # Защита от спама
    
    da_count, da_score = fetch_deviantart(char['tag'])
    x_count, x_score = fetch_x_twitter(char['tag'], rapidapi_key)
    pixiv_count, pixiv_score = fetch_pixiv(char['tag'], rapidapi_key)
    
    total_count = da_count + x_count + pixiv_count
    total_score = da_score + x_score + pixiv_score
    er = round((total_score / total_count), 2) if total_count > 0 else 0
    
    return {
        "Персонаж": char['name'], 
        "Франшиза": char['game'], 
        "Категория": char['category'], 
        "DA Артов": da_count,
        "X/Pixiv Подключены": "Да" if rapidapi_key else "Нет",
        "Конкуренция (Новых работ)": total_count, 
        "Суммарный хайп": total_score, 
        "ER (Вовлеченность)": er
    }

# --- ИИ АНАЛИЗ (Ориентир на 3D арт) ---
def request_gemini_analysis(metrics, key):
    # Динамический поиск модели (Gemini Flash)
    supported_models = []
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(list_url, timeout=8).json()
        for m in res.get('models', []):
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                name = m.get('name', '').replace('models/', '')
                if 'flash' in name.lower() and 'lite' not in name.lower():
                    supported_models.append(name)
    except:
        pass

    fallback_models = ["gemini-2.5-flash", "gemini-1.5-flash-latest"]
    models_to_try = supported_models + [m for m in fallback_models if m not in supported_models]

    prompt = f"""
    Аналитика по вовлеченности (ER) собрана с DeviantArt, X и Pixiv:
    {json.dumps(metrics, ensure_ascii=False)}

    Опираясь на эти данные, отбери ТОП-5 женских персонажей для 3D-арта с максимальным виральным потенциалом.
    Верни JSON:
    {{
      "world_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Обоснование на основе соцсетей", "tags": ["tag1", "tag2"] }}
      ]
    }}
    """
    
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                return json.loads(raw_text), model_name
        except:
            continue
    raise RuntimeError("Сбой API Gemini")

# --- ИНТЕРФЕЙС И ЗАПУСК ---
if st.button("🚀 Сканировать Соцсети", type="primary", use_container_width=True):
    if not api_key:
        st.error("⚠️ Введи Gemini API Key.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        raw_metrics = []
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            for idx, result in enumerate(executor.map(fetch_all_platforms, CHARACTERS)):
                raw_metrics.append(result)
                progress_bar.progress((idx + 1) / len(CHARACTERS))
                status_text.markdown(f"📡 Опрашиваем соцсети... Загружено: **{idx + 1} / {len(CHARACTERS)}**")
                
        status_text.markdown("🧠 Анализ трендов через ИИ...")
        
        try:
            ai_response, model_used = request_gemini_analysis(raw_metrics, api_key)
            st.session_state['ai_results'] = ai_response
            st.session_state['metrics_df'] = pd.DataFrame(raw_metrics).sort_values(by="ER (Вовлеченность)", ascending=False)
            st.session_state['scan_done'] = True
            status_text.empty()
            progress_bar.empty()
            st.toast("Готово!", icon="✅")
        except Exception as ex:
            st.error(f"Ошибка: {ex}")

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
if st.session_state.get('scan_done', False):
    df = st.session_state['metrics_df']
    top_data = st.session_state['ai_results']
    
    st.divider()
    st.subheader("🌍 Глобальный ТОП ИИ (По данным соцсетей)")
    
    cols = st.columns(3)
    for idx, item in enumerate(top_data.get('world_top', [])[:3]):
        with cols[idx]:
            tags = "".join([f"<span class='badge'>#{t}</span>" for t in item.get('tags', [])])
            st.markdown(f"""
            <div class="metric-card top{idx+1}">
                <h3 style="margin-bottom: 5px;">{item['name']}</h3>
                <p style="color: #a5b1c2; margin-top:-5px; font-size: 14px;">{item['game']}</p>
                <p style="color: #dfe4ea; font-size: 14px;">{item['analysis']}</p>
                <div>{tags}</div>
            </div>
            """, unsafe_allow_html=True)
            
    st.subheader("📊 Сырые данные с платформ")
    st.dataframe(df, use_container_width=True, hide_index=True)
