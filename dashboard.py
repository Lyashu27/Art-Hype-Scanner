import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime, timedelta
import feedparser
from concurrent.futures import ThreadPoolExecutor
import plotly.express as px
import plotly.graph_objects as go

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="Omni-Channel Art Hype Radar", page_icon="🌐", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 20px; border-radius: 12px; border-left: 5px solid #4b8bff; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .spicy-card {background-color: #25181e; padding: 20px; border-radius: 12px; border-left: 5px solid #ff4b8b; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(255, 75, 139, 0.15);}
    .hero-card {background: linear-gradient(135deg, #4b8bff 0%, #1a1c23 100%); padding: 30px; border-radius: 16px; margin-bottom: 25px; color: white; border: 1px solid #3d404b; box-shadow: 0 10px 25px rgba(75, 139, 255, 0.2);}
    .hero-title {font-size: 32px; font-weight: 800; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;}
    .hero-news {background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; font-size: 15px; border-left: 4px solid #ffd700; margin-top: 10px;}
    .badge {background-color: #2b2d35; padding: 4px 10px; border-radius: 6px; font-size: 13px; margin-right: 6px; color: #a5b1c2; border: 1px solid #3d404b;}
    .spicy-badge {background-color: #3b1c28; color: #ff9ebf; border-color: #ff4b8b;}
    .top1 {border-left-color: #ffd700;} 
    .top2 {border-left-color: #c0c0c0;} 
    .top3 {border-left-color: #cd7f32;}
</style>
""", unsafe_allow_html=True)

# --- ЗАГРУЗКА КЛЮЧЕЙ ---
gemini_key = st.secrets.get("GEMINI_API_KEY", "")
youtube_key = st.secrets.get("YOUTUBE_API_KEY", "")
steam_key = st.secrets.get("STEAM_API_KEY", "")
twitch_id = st.secrets.get("TWITCH_CLIENT_ID", "")
twitch_secret = st.secrets.get("TWITCH_CLIENT_SECRET", "")

st.title("🌐 Omni-Channel Radar: Глобальный мониторинг трендов")
st.markdown("Сквозной сбор инфополя → AI-экстракция лидеров → Макро-аналитика Охватов и Лайков.")

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("Настройки Анализа")
    is_16_plus = st.toggle("🔞 Анализ 16+ (Spicy/Фансервис)", value=False, help="ИИ будет искать персонажей, популярных за счет откровенных нарядов, модов или физики.")
    
    st.divider()
    st.header("Статус каналов")
    st.write(f"🧠 Gemini Core: {'🟢 Подключен' if gemini_key else '🔴 Нет ключа'}")
    st.write(f"📺 YouTube API: {'🟢 Подключен' if youtube_key else '⚪ Выключен'}")
    st.write(f"🦋 Bluesky Public: 🟢 Активен")
    st.write(f"👾 Reddit Stream: 🟢 Активен")
    st.write(f"📰 Gaming News: 🟢 Активен")
    st.write(f"🎨 Booru/Art: 🟢 Активен")
    st.write(f"🎮 Steam Hub: {'🟢 API активен' if steam_key else '🟡 Открытый режим'}")
    st.write(f"🟣 Twitch / IGDB: {'🟢 Подключен' if (twitch_id and twitch_secret) else '⚪ Выключен'}")

# ==========================================
# МОДУЛИ СБОРА ДАННЫХ (Оставлены без изменений для надежности)
# ==========================================

def fetch_rss_news():
    feeds = ["https://kotaku.com/rss", "https://www.ign.com/feed.xml", "https://stopgame.ru/rss/news.xml", "https://www.gematsu.com/feed"]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for url in feeds:
        try:
            res = requests.get(url, headers=headers, timeout=4)
            for entry in feedparser.parse(res.content).entries[:6]:
                results.append(f"[СМИ/News]: {entry.title}")
        except: continue
    return results

def fetch_reddit_trends():
    subs = ["gaming", "gachagaming", "Genshin_Impact", "HonkaiStarRail", "ZenlessZoneZero", "leagueoflegends", "Overwatch"]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for sub in subs:
        try:
            res = requests.get(f"https://www.reddit.com/r/{sub}/hot.json?limit=6", headers=headers, timeout=4)
            if res.status_code == 200:
                for p in res.json().get('data', {}).get('children', []):
                    results.append(f"[Reddit r/{sub} (+{p.get('data', {}).get('ups', 0)})]: {p.get('data', {}).get('title', '')}")
        except: continue
    return results

def fetch_youtube_trailers(api_key):
    if not api_key: return []
    time_limit = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
    params = {"part": "snippet", "q": "character trailer OR gameplay trailer", "type": "video", "publishedAfter": time_limit, "maxResults": 10, "key": api_key}
    results = []
    try:
        res = requests.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=5)
        if res.status_code == 200:
            for item in res.json().get('items', []):
                results.append(f"[YouTube ({item['snippet']['channelTitle']})]: {item['snippet']['title']}")
    except: pass
    return results

def fetch_bluesky_trends():
    params = {"q": "fanart OR character art OR gacha update", "limit": 15}
    results = []
    try:
        res = requests.get("https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts", params=params, timeout=5)
        if res.status_code == 200:
            for p in res.json().get('posts', []):
                results.append(f"[Bluesky (+{p.get('likeCount', 0)}❤️)]: {p.get('record', {}).get('text', '').replace(chr(10), ' ')[:100]}")
    except: pass
    return results

def fetch_booru_hot_tags():
    results = []
    try:
        res = requests.get("https://danbooru.donmai.us/posts.json?limit=15&tags=order:rank", headers={'User-Agent': 'HypeRadar/1.0'}, timeout=5)
        if res.status_code == 200:
            for post in res.json():
                tags = post.get('tag_string_character', '')
                if tags: results.append(f"[Art-Boards Pop Tag]: {tags} (Score: {post.get('score', 0)})")
    except: pass
    return results

def fetch_steam_trends():
    results = []
    try:
        res = requests.get("https://store.steampowered.com/api/featuredcategories", timeout=5)
        if res.status_code == 200:
            for item in res.json().get('top_sellers', {}).get('items', [])[:8]:
                results.append(f"[Steam Top Seller]: {item.get('name', '')}")
    except: pass
    return results

def fetch_twitch_top_categories(c_id, c_secret):
    if not (c_id and c_secret): return []
    results = []
    try:
        auth_res = requests.post(f"https://id.twitch.tv/oauth2/token?client_id={c_id}&client_secret={c_secret}&grant_type=client_credentials", timeout=5).json()
        token = auth_res.get('access_token', '')
        if token:
            res = requests.get("https://api.twitch.tv/helix/games/top?first=10", headers={"Client-ID": c_id, "Authorization": f"Bearer {token}"}, timeout=5)
            if res.status_code == 200:
                for g in res.json().get('data', []):
                    results.append(f"[Twitch Top Streamed]: {g.get('name')}")
    except: pass
    return results

# ==========================================
# ИИ-АНАЛИЗАТОР С НОВЫМИ МЕТРИКАМИ И 16+
# ==========================================

def analyze_cross_platform_feed(feed_dump, key, nsfw_enabled):
    supported = []
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(list_url, timeout=6).json()
        for m in res.get('models', []):
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                name = m.get('name', '').replace('models/', '')
                if ('flash' in name.lower() or 'pro' in name.lower()) and 'lite' not in name.lower():
                    supported.append(name)
    except: pass

    models_to_try = supported + ["gemini-2.5-flash", "gemini-1.5-flash"]
    
    # Динамическая вставка промпта для 16+
    spicy_instruction = ""
    if nsfw_enabled:
        spicy_instruction = """
        ВНИМАНИЕ: Включен режим 16+. Проанализируй данные на предмет персонажей, которые вирусятся за счет фансервиса (купальники, откровенные наряды, физика, моды, NSFW-adjacent тренды). Выдели их в отдельный массив "spicy_top".
        """
    else:
        spicy_instruction = "Игнорируй откровенный NSFW контент. Массив 'spicy_top' оставь пустым."

    prompt = f"""
    Действуй как ведущий аналитик данных для 3D-художника. Сырые данные из 7 источников:
    {json.dumps(feed_dump, ensure_ascii=False)}

    {spicy_instruction}

    ТВОЯ ЗАДАЧА:
    Выделить Абсолютного Лидера, Топ-5 Мир, Топ-5 СНГ и (если включено) Топ-5 16+ Spicy.
    Затем сформировать ДВА макро-списка по 50 женских персонажей (Гачи и Остальные игры).
    
    Для КАЖДОГО персонажа в списках ТОП-50 рассчитай три метрики от 0 до 100:
    - score (Общий хайп)
    - reach (Охват: насколько часто имя мелькает в поиске/СМИ)
    - likes (Вовлеченность: насколько активно фанаты лайкают/рисуют арты)

    Формат ответа СТРОГО JSON:
    {{
      "absolute_leader": {{
        "name": "Имя", "game": "Игра", "virality_score": 98, "primary_trigger": "Событие", "tags": ["3dart"]
      }},
      "spicy_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Почему этот фансервис популярен", "score": 95, "tags": ["nsfw-adjacent"] }}
      ],
      "world_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Кратко", "score": 95, "tags": ["tag1"] }}
      ],
      "ru_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Кратко", "score": 92, "tags": ["tag1"] }}
      ],
      "gacha_top_50": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "score": 99, "reach": 95, "likes": 98, "trend": "🔥" }}
      ],
      "classic_top_50": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "score": 99, "reach": 90, "likes": 92, "trend": "📈" }}
      ]
    }}
    Убедись, что массивы gacha_top_50 и classic_top_50 содержат ровно по 50 объектов.
    """

    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}

    last_err = ""
    for model_name in models_to_try:
        try:
            resp = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}", headers=headers, json=payload, timeout=50)
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

if st.button("🚀 Начать глубокий скан (Охваты + Тренды)", type="primary", use_container_width=True):
    if not gemini_key: st.error("⚠️ Укажите GEMINI_API_KEY в Secrets.")
    else:
        progress = st.progress(0)
        status = st.empty()
        start_time = time.time()
        
        status.markdown("📡 **Сбор данных:** Опрос 7 каналов...")
        collected_feed = []
        with ThreadPoolExecutor(max_workers=7) as executor:
            for future in [
                executor.submit(fetch_rss_news), executor.submit(fetch_reddit_trends), 
                executor.submit(fetch_youtube_trailers, youtube_key), executor.submit(fetch_bluesky_trends), 
                executor.submit(fetch_booru_hot_tags), executor.submit(fetch_steam_trends), 
                executor.submit(fetch_twitch_top_categories, twitch_id, twitch_secret)
            ]:
                collected_feed.extend(future.result())
                
        progress.progress(50)
        status.markdown(f"🧠 **ИИ-анализ:** Генерация рейтингов с метриками охвата и лайков... (Ожидание ~20 сек)")
        
        try:
            ai_results, used_model = analyze_cross_platform_feed(collected_feed, gemini_key, is_16_plus)
            st.session_state.update({'omni_results': ai_results, 'raw_feed': collected_feed, 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'scan_done': True})
            progress.empty()
            status.empty()
            st.toast(f"Анализ завершен ({used_model})!", icon="✅")
        except Exception as e:
            st.error(f"Ошибка анализа: {e}")

# ==========================================
# ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ
# ==========================================

if st.session_state.get('scan_done', False):
    res = st.session_state['omni_results']
    st.caption(f"⏱️ **Актуально на:** {st.session_state['timestamp']}")
    
    # 1. АБСОЛЮТНЫЙ ЛИДЕР
    leader = res.get('absolute_leader', {})
    if leader:
        st.markdown(f"""
        <div class="hero-card">
            <div style="text-transform: uppercase; letter-spacing: 2px; font-size: 12px; margin-bottom: 8px; color: #ffd700;">👑 Главный инфоповод интернета</div>
            <div class="hero-title">{leader.get('name')} <span style="font-size:22px; font-weight:400; opacity:0.8;">— {leader.get('game')}</span></div>
            <div style="font-size: 16px; margin-top: 5px;">Индекс виральности: <b>{leader.get('virality_score')}/100</b></div>
            <div class="hero-news">🎯 <b>Триггер хайпа:</b> {leader.get('primary_trigger')}</div>
            <div style="margin-top: 15px;">{" ".join([f"<span class='badge'>#{t}</span>" for t in leader.get('tags', [])])}</div>
        </div>
        """, unsafe_allow_html=True)

    # 2. МИКРО-ТОПЫ И БЛОК 16+
    medals, classes = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"], ["top1", "top2", "top3", "", ""]
    
    if is_16_plus and res.get('spicy_top'):
        st.subheader("🔞 Тренды 16+ (Spicy & Фансервис)")
        spicy_cols = st.columns(3)
        for idx, item in enumerate(res.get('spicy_top', [])[:3]):
            with spicy_cols[idx]:
                st.markdown(f"""
                <div class="spicy-card">
                    <h4 style="margin-bottom: 5px; color: #ff9ebf;">{medals[idx]} {item['name']} <span style="font-size:14px; color:#a5b1c2;">({item['game']})</span></h4>
                    <p style="font-size: 13px; color: #dfe4ea;">{item['analysis']}</p>
                    <div>{" ".join([f"<span class='badge spicy-badge'>#{t}</span>" for t in item.get('tags', [])])}</div>
                </div>
                """, unsafe_allow_html=True)
        st.divider()

    col_w, col_r = st.columns(2)
    with col_w:
        st.subheader("🌍 Мировой тренд (Топ-5)")
        for idx, item in enumerate(res.get('world_top', [])[:5]):
            st.markdown(f"""<div class="metric-card {classes[idx]}"><h4 style="margin-bottom: 5px;">{medals[idx]} {item['name']} <span style="font-size:14px; color:#888;">({item['game']})</span></h4><p style="font-size: 14px; color: #dfe4ea;">{item['analysis']}</p></div>""", unsafe_allow_html=True)

    with col_r:
        st.subheader("🇷🇺 СНГ / РФ фокус (Топ-5)")
        for idx, item in enumerate(res.get('ru_top', [])[:5]):
            st.markdown(f"""<div class="metric-card {classes[idx]}"><h4 style="margin-bottom: 5px;">{medals[idx]} {item['name']} <span style="font-size:14px; color:#888;">({item['game']})</span></h4><p style="font-size: 14px; color: #dfe4ea;">{item['analysis']}</p></div>""", unsafe_allow_html=True)

    st.divider()

    # 3. ПОДГОТОВКА ДАННЫХ ДЛЯ ДИАГРАММ
    df_gacha = pd.DataFrame(res.get('gacha_top_50', []))
    df_classic = pd.DataFrame(res.get('classic_top_50', []))
    
    # 4. ПРОДВИНУТЫЕ ГРАФИКИ
    st.subheader("📊 Распределение Охватов и Вовлеченности (Топ-15)")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        if not df_gacha.empty:
            # Матрица вовлеченности (Bubble Chart)
            fig_g = px.scatter(
                df_gacha.head(15), x="reach", y="likes", size="score", color="game", 
                hover_name="name", text="name", size_max=40, template="plotly_dark",
                title="Гача: Охват (СМИ/Reddit) vs Лайки (Pixiv/X)",
                labels={"reach": "Охваты (Reach)", "likes": "Лайки (Engagement)"}
            )
            fig_g.update_traces(textposition='top center', textfont=dict(size=11))
            st.plotly_chart(fig_g, use_container_width=True)

    with col_chart2:
        if not df_classic.empty:
            # Улучшенный столбчатый график с цифрами
            fig_c = px.bar(
                df_classic.head(15).sort_values('score', ascending=True), 
                x='score', y='name', color='likes', orientation='h', text_auto=True,
                color_continuous_scale='Inferno', title="AAA и Соревновательные: Виральность", 
                template="plotly_dark", labels={"score": "Виральность", "name": ""}
            )
            fig_c.update_traces(textposition='outside')
            fig_c.update_layout(coloraxis_colorbar=dict(title="Лайки"))
            st.plotly_chart(fig_c, use_container_width=True)

    # 5. МАКРО-СПИСКИ ТОП-50
    st.subheader("🗄️ Макро-аналитика: ТОП-50 персонажей для 3D-арта")
    col_config = {
        "rank": st.column_config.NumberColumn("№", format="%d"),
        "name": "Персонаж", "game": "Игра", "trend": "Тренд",
        "score": st.column_config.ProgressColumn("Хайп", min_value=0, max_value=100),
        "reach": st.column_config.NumberColumn("Охват", format="%d"),
        "likes": st.column_config.NumberColumn("Лайки", format="%d")
    }
    
    col_tab1, col_tab2 = st.columns(2)
    with col_tab1:
        st.markdown("<h4 style='text-align: center; color: #4b8bff;'>🎲 Гача-Игры (Топ 50)</h4>", unsafe_allow_html=True)
        if not df_gacha.empty: st.dataframe(df_gacha, use_container_width=True, hide_index=True, column_config=col_config, height=600)
            
    with col_tab2:
        st.markdown("<h4 style='text-align: center; color: #ff4b4b;'>⚔️ Остальные игры (Топ 50)</h4>", unsafe_allow_html=True)
        if not df_classic.empty: st.dataframe(df_classic, use_container_width=True, hide_index=True, column_config=col_config, height=600)
