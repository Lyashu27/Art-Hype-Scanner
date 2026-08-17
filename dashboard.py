import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime, timedelta
import feedparser
from concurrent.futures import ThreadPoolExecutor
import plotly.express as px

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="Omni-Channel Art Hype Radar", page_icon="🌐", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 20px; border-radius: 12px; border-left: 5px solid #4b8bff; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .hero-card {background: linear-gradient(135deg, #4b8bff 0%, #1a1c23 100%); padding: 30px; border-radius: 16px; margin-bottom: 25px; color: white; border: 1px solid #3d404b; box-shadow: 0 10px 25px rgba(75, 139, 255, 0.2);}
    .hero-title {font-size: 32px; font-weight: 800; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;}
    .hero-news {background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; font-size: 15px; border-left: 4px solid #ffd700; margin-top: 10px;}
    .badge {background-color: #2b2d35; padding: 4px 10px; border-radius: 6px; font-size: 13px; margin-right: 6px; color: #a5b1c2; border: 1px solid #3d404b;}
    .top1 {border-left-color: #ffd700;} 
    .top2 {border-left-color: #c0c0c0;} 
    .top3 {border-left-color: #cd7f32;}
</style>
""", unsafe_allow_html=True)

# --- АВТОМАТИЧЕСКАЯ ЗАГРУЗКА КЛЮЧЕЙ ИЗ SECRETS ---
gemini_key = st.secrets.get("GEMINI_API_KEY", "")
youtube_key = st.secrets.get("YOUTUBE_API_KEY", "")
steam_key = st.secrets.get("STEAM_API_KEY", "")
twitch_id = st.secrets.get("TWITCH_CLIENT_ID", "")
twitch_secret = st.secrets.get("TWITCH_CLIENT_SECRET", "")

st.title("🌐 Omni-Channel Radar: Глобальный мониторинг трендов")
st.markdown("Сквозной сбор инфополя: **СМИ + Reddit + YouTube + Bluesky + Danbooru + Steam + Twitch** → AI-экстракция самых востребованных героинь для 3D-арта.")

# Индикаторы подключенных каналов
with st.sidebar:
    st.header("Статус каналов данных")
    st.write(f"🧠 Gemini Core: {'🟢 Подключен' if gemini_key else '🔴 Нет ключа'}")
    st.write(f"📺 YouTube API: {'🟢 Подключен' if youtube_key else '⚪ Выключен'}")
    st.write(f"🦋 Bluesky Public API: 🟢 Активен")
    st.write(f"👾 Reddit Stream: 🟢 Активен")
    st.write(f"📰 Gaming News RSS: 🟢 Активен")
    st.write(f"🎨 Booru/Art Trends: 🟢 Активен")
    st.write(f"🎮 Steam Hub: {'🟢 API активен' if steam_key else '🟡 Открытый режим'}")
    st.write(f"🟣 Twitch / IGDB: {'🟢 Подключен' if (twitch_id and twitch_secret) else '⚪ Выключен'}")
    st.divider()

# ==========================================
# МОДУЛИ СБОРА ДАННЫХ
# ==========================================

def fetch_rss_news():
    """1. Игровые СМИ (Запад + СНГ)"""
    feeds = [
        "https://kotaku.com/rss", 
        "https://www.ign.com/feed.xml",
        "https://stopgame.ru/rss/news.xml",
        "https://www.gematsu.com/feed"
    ]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for url in feeds:
        try:
            res = requests.get(url, headers=headers, timeout=4)
            feed = feedparser.parse(res.content)
            for entry in feed.entries[:6]:
                results.append(f"[СМИ/News]: {entry.title}")
        except Exception:
            continue
    return results

def fetch_reddit_trends():
    """2. Сообщества Reddit (Открытые JSON-эндпоинты)"""
    subs = ["gaming", "gachagaming", "Genshin_Impact", "HonkaiStarRail", "ZenlessZoneZero"]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for sub in subs:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=6"
            res = requests.get(url, headers=headers, timeout=4)
            if res.status_code == 200:
                posts = res.json().get('data', {}).get('children', [])
                for p in posts:
                    title = p.get('data', {}).get('title', '')
                    ups = p.get('data', {}).get('ups', 0)
                    results.append(f"[Reddit r/{sub} (+{ups})]: {title}")
        except Exception:
            continue
    return results

def fetch_youtube_trailers(api_key):
    """3. YouTube Data API v3 (Трейлеры за последние 48 часов)"""
    if not api_key:
        return []
    time_limit = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": "character trailer OR gameplay trailer",
        "type": "video",
        "publishedAfter": time_limit,
        "maxResults": 10,
        "key": api_key
    }
    results = []
    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            for item in res.json().get('items', []):
                title = item['snippet']['title']
                channel = item['snippet']['channelTitle']
                results.append(f"[YouTube ({channel})]: {title}")
    except Exception:
        pass
    return results

def fetch_bluesky_trends():
    """4. Bluesky AT Protocol (Публичный поиск по арт-трендам)"""
    url = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
    params = {"q": "fanart OR character art OR gacha update", "limit": 15}
    results = []
    try:
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            posts = res.json().get('posts', [])
            for p in posts:
                text = p.get('record', {}).get('text', '').replace('\n', ' ')[:100]
                likes = p.get('likeCount', 0)
                results.append(f"[Bluesky (+{likes}❤️)]: {text}")
    except Exception:
        pass
    return results

def fetch_booru_hot_tags():
    """5. Арт-борды (Danbooru / Safebooru популярные теги)"""
    results = []
    try:
        url = "https://danbooru.donmai.us/posts.json?limit=15&tags=order:rank"
        res = requests.get(url, headers={'User-Agent': 'HypeRadar/1.0'}, timeout=5)
        if res.status_code == 200:
            for post in res.json():
                char_tags = post.get('tag_string_character', '')
                if char_tags:
                    results.append(f"[Art-Boards Pop Tag]: {char_tags} (Score: {post.get('score', 0)})")
    except Exception:
        pass
    return results

def fetch_steam_trends():
    """6. Steam (Трендовые релизы и апдейты)"""
    results = []
    try:
        # Получаем список популярных новинок Steam
        url = "https://store.steampowered.com/api/featuredcategories"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            top_sellers = res.json().get('top_sellers', {}).get('items', [])[:8]
            for item in top_sellers:
                name = item.get('name', '')
                results.append(f"[Steam Top Seller]: {name}")
    except Exception:
        pass
    return results

def fetch_twitch_top_categories(c_id, c_secret):
    """7. Twitch Helix API (Категории с максимальным числом зрителей)"""
    if not (c_id and c_secret):
        return []
    results = []
    try:
        # Авторизация OAuth
        auth_url = f"https://id.twitch.tv/oauth2/token?client_id={c_id}&client_secret={c_secret}&grant_type=client_credentials"
        auth_res = requests.post(auth_url, timeout=5).json()
        token = auth_res.get('access_token', '')
        
        if token:
            headers = {"Client-ID": c_id, "Authorization": f"Bearer {token}"}
            games_url = "https://api.twitch.tv/helix/games/top?first=10"
            res = requests.get(games_url, headers=headers, timeout=5)
            if res.status_code == 200:
                for g in res.json().get('data', []):
                    results.append(f"[Twitch Top Streamed]: {g.get('name')}")
    except Exception:
        pass
    return results

# ==========================================
# ИИ-АНАЛИЗАТОР (GEMINI)
# ==========================================

def analyze_cross_platform_feed(feed_dump, key):
    supported = []
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(list_url, timeout=6).json()
        for m in res.get('models', []):
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                name = m.get('name', '').replace('models/', '')
                if ('flash' in name.lower() or 'pro' in name.lower()) and 'lite' not in name.lower():
                    supported.append(name)
    except Exception:
        pass

    models_to_try = supported + ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"]

    prompt = f"""
    Действуй как ведущий игровой аналитик и арт-директор. Перед тобой массив данных, собранный в реальном времени из 7 ключевых источников (СМИ, Reddit, YouTube, Bluesky, Danbooru, Steam, Twitch):

    ДАННЫЕ МОНИТОРИНГА:
    {json.dumps(feed_dump, ensure_ascii=False)}

    ТВОЯ ЗАДАЧА:
    1. Изучить сводку инфоповодов (новые трейлеры, патчи, споры на Reddit, топовые стримы и популярные теги).
    2. Выделить из этого массива конкретных ЖЕНСКИХ персонажей, вокруг которых сейчас идет максимальная концентрация внимания.
    3. Определить Абсолютного Лидера (#1) и сформировать рейтинги для создания 3D-арта.

    Формат ответа СТРОГО JSON:
    {{
      "absolute_leader": {{
        "name": "Имя героини",
        "game": "Игра",
        "virality_score": 98,
        "primary_trigger": "Из какого источника/события идет главный хайп",
        "tags": ["3dart", "tag2", "tag3"]
      }},
      "world_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Почему будет высокий спрос на международных площадках", "score": 95, "tags": ["tag1", "tag2"] }}
      ],
      "ru_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Почему зайдет в СНГ/РФ фандоме", "score": 92, "tags": ["tag1", "tag2"] }}
      ]
    }}
    Выдай по 5 персонажей в world_top и ru_top.
    """

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}
    }

    last_err = ""
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=35)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                if raw_text.startswith("```json"): raw_text = raw_text[7:]
                if raw_text.startswith("```"): raw_text = raw_text[3:]
                if raw_text.endswith("```"): raw_text = raw_text[:-3]
                return json.loads(raw_text.strip()), model_name
            else:
                last_err = f"[{model_name}] {resp.status_code}: {resp.text}"
        except Exception as e:
            last_err = f"[{model_name}] {str(e)}"
            continue

    raise RuntimeError(f"Сбой Gemini API: {last_err}")

# ==========================================
# ИНТЕРФЕЙС И ЗАПУСК
# ==========================================

if st.button("🚀 Запустить сквозной мультиплатформенный скан", type="primary", use_container_width=True):
    if not gemini_key:
        st.error("⚠️ Укажите GEMINI_API_KEY в Secrets.")
    else:
        progress = st.progress(0)
        status = st.empty()
        start_time = time.time()
        
        status.markdown("📡 **Сбор данных:** Параллельный опрос СМИ, Reddit, YouTube, Bluesky, Booru, Steam и Twitch...")
        
        # Параллельный сбор со всех источников
        collected_feed = []
        with ThreadPoolExecutor(max_workers=7) as executor:
            f_rss = executor.submit(fetch_rss_news)
            f_reddit = executor.submit(fetch_reddit_trends)
            f_yt = executor.submit(fetch_youtube_trailers, youtube_key)
            f_bsky = executor.submit(fetch_bluesky_trends)
            f_booru = executor.submit(fetch_booru_hot_tags)
            f_steam = executor.submit(fetch_steam_trends)
            f_twitch = executor.submit(fetch_twitch_top_categories, twitch_id, twitch_secret)
            
            for future in [f_rss, f_reddit, f_yt, f_bsky, f_booru, f_steam, f_twitch]:
                collected_feed.extend(future.result())
                
        progress.progress(60)
        status.markdown(f"🧠 **ИИ-анализ:** Собрано **{len(collected_feed)}** фактов инфополя. Gemini вычисляет лидеров...")
        
        try:
            ai_results, used_model = analyze_cross_platform_feed(collected_feed, gemini_key)
            
            st.session_state['omni_results'] = ai_results
            st.session_state['raw_feed'] = collected_feed
            st.session_state['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state['scan_done'] = True
            
            progress.empty()
            status.empty()
            st.toast(f"Анализ завершен через {used_model}! (Сбор: {time.time()-start_time:.1f}с)", icon="✅")
        except Exception as e:
            st.error(f"Ошибка анализа: {e}")

# ==========================================
# ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ
# ==========================================

if st.session_state.get('scan_done', False):
    res = st.session_state['omni_results']
    raw = st.session_state['raw_feed']
    
    st.caption(f"⏱️ **Данные актуальны на:** {st.session_state['timestamp']} | Обработано источников: **{len(raw)}**")
    
    # Блок абсолютного лидера
    leader = res.get('absolute_leader', {})
    if leader:
        tags_str = " ".join([f"<span class='badge'>#{t}</span>" for t in leader.get('tags', [])])
        st.markdown(f"""
        <div class="hero-card">
            <div style="text-transform: uppercase; letter-spacing: 2px; font-size: 12px; margin-bottom: 8px; color: #ffd700;">👑 Главный инфоповод интернета прямо сейчас</div>
            <div class="hero-title">{leader.get('name')} <span style="font-size:22px; font-weight:400; opacity:0.8;">— {leader.get('game')}</span></div>
            <div style="font-size: 16px; margin-top: 5px;">Индекс виральности: <b>{leader.get('virality_score')}/100</b></div>
            <div class="hero-news">
                🎯 <b>Триггер хайпа:</b> {leader.get('primary_trigger')}
            </div>
            <div style="margin-top: 15px;">{tags_str}</div>
        </div>
        """, unsafe_allow_html=True)

    col_w, col_r = st.columns(2)
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    classes = ["top1", "top2", "top3", "", ""]

    with col_w:
        st.subheader("🌍 Мировой тренд (Топ-5)")
        for idx, item in enumerate(res.get('world_top', [])[:5]):
            tags = " ".join([f"<span class='badge'>#{t}</span>" for t in item.get('tags', [])])
            st.markdown(f"""
            <div class="metric-card {classes[idx]}">
                <h4 style="margin-bottom: 5px;">{medals[idx]} {item['name']} <span style="font-size:14px; color:#888;">({item['game']})</span> — {item.get('score', 0)}/100</h4>
                <p style="font-size: 14px; color: #dfe4ea;">{item['analysis']}</p>
                <div>{tags}</div>
            </div>
            """, unsafe_allow_html=True)

    with col_r:
        st.subheader("🇷🇺 СНГ / РФ фокус (Топ-5)")
        for idx, item in enumerate(res.get('ru_top', [])[:5]):
            tags = " ".join([f"<span class='badge'>#{t}</span>" for t in item.get('tags', [])])
            st.markdown(f"""
            <div class="metric-card {classes[idx]}">
                <h4 style="margin-bottom: 5px;">{medals[idx]} {item['name']} <span style="font-size:14px; color:#888;">({item['game']})</span> — {item.get('score', 0)}/100</h4>
                <p style="font-size: 14px; color: #dfe4ea;">{item['analysis']}</p>
                <div>{tags}</div>
            </div>
            """, unsafe_allow_html=True)

    with st.expander("🔍 Посмотреть сырой поток перехваченных данных"):
        st.write(f"Всего событий собрано: {len(raw)}")
        st.json(raw)
