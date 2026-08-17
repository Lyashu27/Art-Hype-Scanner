import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime, timedelta
import feedparser
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

# --- КОНФИГУРАЦИЯ ---
st.set_page_config(page_title="AI Agent: Trend Discovery", page_icon="📡", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 20px; border-radius: 12px; border-left: 5px solid #4b8bff; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .hero-card {background: linear-gradient(135deg, #4b8bff 0%, #1a1c23 100%); padding: 30px; border-radius: 16px; margin-bottom: 25px; color: white; border: 1px solid #3d404b;}
    .badge {background-color: #2b2d35; padding: 4px 10px; border-radius: 6px; font-size: 13px; margin-right: 6px; color: #a5b1c2; border: 1px solid #3d404b;}
</style>
""", unsafe_allow_html=True)

# --- ЗАГРУЗКА КЛЮЧЕЙ ---
try:
    gemini_key = st.secrets["GEMINI_API_KEY"]
except:
    gemini_key = st.sidebar.text_input("Gemini API Key:", type="password")

try:
    youtube_key = st.secrets["YOUTUBE_API_KEY"]
except:
    youtube_key = st.sidebar.text_input("YouTube API Key:", type="password")

st.title("📡 Trend Discovery: Поиск скрытого хайпа")
st.markdown("Скрипт сканирует интернет (Reddit, СМИ, YouTube), а нейросеть сама находит в этом шуме самых обсуждаемых героинь для ваших 3D-артов.")

with st.sidebar:
    st.info("🔄 **Архитектура:** Сбор сырых текстовых данных из открытых источников -> Передача массива в Gemini -> ИИ-экстракция имен и оценка виральности.")

# --- ФУНКЦИИ СБОРА СЫРЫХ ДАННЫХ ---

def fetch_rss_news():
    """Сбор заголовков из игровых СМИ (Мир + СНГ)"""
    feeds = [
        "https://kotaku.com/rss", 
        "https://www.ign.com/feed.xml",
        "https://stopgame.ru/rss/news.xml"
    ]
    news_data = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for url in feeds:
        try:
            res = requests.get(url, headers=headers, timeout=5)
            feed = feedparser.parse(res.content)
            for entry in feed.entries[:10]: # Берем топ-10 свежих новостей с каждого сайта
                news_data.append(f"НОВОСТЬ: {entry.title}")
        except:
            continue
    return " | ".join(news_data)

def fetch_reddit_hot():
    """Сбор горячих тем с Reddit без авторизации (добавляем .json)"""
    subreddits = ["gaming", "gachagaming", "Genshin_Impact", "HonkaiStarRail"]
    reddit_data = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for sub in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                posts = res.json()['data']['children']
                for post in posts:
                    title = post['data'].get('title', '')
                    reddit_data.append(f"REDDIT ({sub}): {title}")
        except:
            continue
    return " | ".join(reddit_data)

def fetch_youtube_trends(api_key):
    """Поиск недавних трейлеров и видео с большим охватом"""
    if not api_key: return "YouTube API не подключен."
    
    # Ищем видео за последние 48 часов
    time_threshold = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": "character trailer OR game update",
        "type": "video",
        "publishedAfter": time_threshold,
        "relevanceLanguage": "en",
        "maxResults": 15,
        "key": api_key
    }
    
    yt_data = []
    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            items = res.json().get('items', [])
            for item in items:
                title = item['snippet']['title']
                channel = item['snippet']['channelTitle']
                yt_data.append(f"YOUTUBE ({channel}): {title}")
    except:
        pass
    return " | ".join(yt_data)

# --- ИИ-ЭКСТРАКТОР ---
def extract_trends_with_gemini(raw_text_dump, key):
    # Динамический поиск рабочих моделей
    supported_models = []
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(list_url, timeout=5).json()
        for m in res.get('models', []):
            name = m.get('name', '').replace('models/', '')
            if ('flash' in name.lower() or 'pro' in name.lower()) and 'lite' not in name.lower():
                supported_models.append(name)
    except:
        pass
    
    models_to_try = supported_models + ["gemini-2.0-flash", "gemini-1.5-flash"]
    
    prompt = f"""
    Действуй как аналитик игрового инфополя. Я передаю тебе сырой дамп данных за последние 24-48 часов (заголовки СМИ, Reddit, YouTube):
    
    ДАННЫЕ:
    {raw_text_dump}
    
    Твоя задача:
    1. Проанализировать этот текст.
    2. Найти упоминания видеоигр, свежих анонсов, патчей и скандалов.
    3. Выявить из этих трендов ЖЕНСКИХ персонажей, которые сейчас находятся на пике обсуждения.
    4. Сформировать подборку героинь, 3D-арт с которыми сейчас соберет максимальные охваты при веерной публикации на 15+ арт-платформах. Учитывай как глобальный интерес, так и аудиторию РФ/СНГ (например, любовь к СНГ-проектам или азиатским гачам).
    
    Верни ответ СТРОГО в JSON (без маркдауна):
    {{
      "global_trends": [
        {{ "name": "Имя героини", "game": "Игра", "source_event": "Событие из текста (например, вышел трейлер)", "virality": 95, "tags": ["tag1", "tag2"] }}
      ],
      "ru_cis_focus": [
        {{ "name": "Имя героини", "game": "Игра", "source_event": "Событие", "virality": 90, "tags": ["tag1", "tag2"] }}
      ]
    }}
    Если в сырых данных мало конкретных имен, используй свои знания о текущих трендах упомянутых в тексте игр.
    """
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2} # Низкая температура для точности извлечения
    }

    last_err = ""
    for model_name in set(models_to_try):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=40)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                if raw_text.startswith("```json"): raw_text = raw_text[7:]
                if raw_text.startswith("```"): raw_text = raw_text[3:]
                if raw_text.endswith("```"): raw_text = raw_text[:-3]
                return json.loads(raw_text.strip()), model_name
        except Exception as e:
            last_err = str(e)
            continue
    raise RuntimeError(f"Сбой ИИ: {last_err}")

# --- ИНТЕРФЕЙС ---
if st.button("🚀 Начать сбор и экстракцию трендов", type="primary", use_container_width=True):
    if not gemini_key:
        st.error("⚠️ Укажите Gemini API Key.")
    else:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        # 1. СБОР ИНФОПОЛЯ (Параллельно для скорости)
        status_text.markdown("📡 **Парсинг источников:** Опрашиваем Reddit, СМИ и YouTube...")
        raw_dump = ""
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_rss = executor.submit(fetch_rss_news)
            future_reddit = executor.submit(fetch_reddit_hot)
            future_yt = executor.submit(fetch_youtube_trends, youtube_key)
            
            # Собираем результаты
            results = [future_rss.result(), future_reddit.result(), future_yt.result()]
            raw_dump = " || ".join(results)
            progress_bar.progress(50)
            
        # 2. АНАЛИЗ ИИ
        status_text.markdown("🧠 **ИИ-Экстракция:** Gemini анализирует сырой текст и ищет виральных персонажей...")
        try:
            start_t = time.time()
            ai_data, model_used = extract_trends_with_gemini(raw_dump, gemini_key)
            
            st.session_state['results'] = ai_data
            st.session_state['raw_dump'] = raw_dump
            st.session_state['done'] = True
            
            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()
            st.toast(f"Готово! Модель: {model_used} | Время ИИ: {time.time() - start_t:.1f}с", icon="✅")
            
        except Exception as ex:
            st.error(f"Ошибка ИИ: {ex}")

# --- ВЫВОД ---
if st.session_state.get('done', False):
    data = st.session_state['results']
    
    st.markdown("""
    <div class="hero-card">
        <h2 style="margin-top:0;">Результаты сканирования инфополя</h2>
        <p>ИИ обработал новостные ленты, посты на Reddit и новые трейлеры, вычленив героинь, которые сейчас находятся на пике обсуждения. Это идеальные кандидаты для скорейшего рендера.</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌍 Мировые тренды (Глобальный хайп)")
        for item in data.get('global_trends', []):
            tags = " ".join([f"<span class='badge'>#{t}</span>" for t in item.get('tags', [])])
            st.markdown(f"""
            <div class="metric-card">
                <h4 style="margin-bottom: 5px;">{item['name']} <span style="font-size:14px; color:#888;">({item['game']})</span></h4>
                <p style="font-size: 14px; color: #ffd700; margin-bottom: 5px;">🔥 Индекс: {item['virality']}/100</p>
                <p style="font-size: 14px; color: #dfe4ea;"><b>Событие:</b> {item['source_event']}</p>
                <div>{tags}</div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.subheader("🇷🇺 Фокус на СНГ (Адаптация)")
        for item in data.get('ru_cis_focus', []):
            tags = " ".join([f"<span class='badge'>#{t}</span>" for t in item.get('tags', [])])
            st.markdown(f"""
            <div class="metric-card">
                <h4 style="margin-bottom: 5px;">{item['name']} <span style="font-size:14px; color:#888;">({item['game']})</span></h4>
                <p style="font-size: 14px; color: #ffd700; margin-bottom: 5px;">🔥 Индекс: {item['virality']}/100</p>
                <p style="font-size: 14px; color: #dfe4ea;"><b>Событие:</b> {item['source_event']}</p>
                <div>{tags}</div>
            </div>
            """, unsafe_allow_html=True)
            
    with st.expander("Посмотреть сырой дамп данных (Что читал ИИ)"):
        st.text_area("Сырой текст с Reddit, RSS и YouTube", st.session_state['raw_dump'], height=300)
