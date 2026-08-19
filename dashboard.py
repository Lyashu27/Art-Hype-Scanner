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
st.set_page_config(page_title="Omni-Channel Art Hype Radar Pro", page_icon="🔥", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 20px; border-radius: 12px; border-left: 5px solid #4b8bff; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .spicy-card {background-color: #25181e; padding: 20px; border-radius: 12px; border-left: 5px solid #ff4b8b; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(255, 75, 139, 0.15);}
    .hero-card {background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 30px; border-radius: 16px; margin-bottom: 25px; color: white; border: 1px solid #3b82f6; box-shadow: 0 10px 25px rgba(59, 130, 246, 0.25);}
    .hero-title {font-size: 32px; font-weight: 800; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px; color: #60a5fa;}
    .fact-box {background: rgba(15, 23, 42, 0.7); padding: 12px 16px; border-radius: 8px; font-size: 14px; margin-top: 8px; border-left: 4px solid #38bdf8;}
    .catalyst-box {background: rgba(15, 23, 42, 0.7); padding: 12px 16px; border-radius: 8px; font-size: 14px; margin-top: 8px; border-left: 4px solid #f59e0b;}
    .badge {background-color: #1e293b; padding: 4px 10px; border-radius: 6px; font-size: 13px; margin-right: 6px; color: #93c5fd; border: 1px solid #334155;}
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

st.title("🔥 Omni-Channel Radar: Предиктивный анализ хайпа")
st.markdown("Мониторинг событий за **последние 72 часа** + прогноз **ближайших инфоповодов** для максимальных охватов фан-арта.")

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("Настройки Анализа")
    is_16_plus = st.toggle("🔞 Анализ 16+ (Spicy / Фансервис)", value=True, help="Фокус на персонажах с виральными купальниками, откровенными скинами и модами.")
    
    st.divider()
    st.header("Статус каналов данных")
    st.write(f"🧠 Gemini Core: {'🟢 Активен' if gemini_key else '🔴 Нет ключа'}")
    st.write(f"📺 YouTube API (72h): {'🟢 Активен' if youtube_key else '⚪ Выключен'}")
    st.write(f"🦋 Bluesky Public: 🟢 Активен")
    st.write(f"👾 Reddit Gaming Hubs: 🟢 Активен")
    st.write(f"📰 Gaming News RSS: 🟢 Активен")
    st.write(f"🎨 Danbooru Trends: 🟢 Активен")
    st.write(f"🎮 Steam & Twitch: {'🟢 Подключены' if (steam_key or twitch_id) else '🟡 Открытый режим'}")

# ==========================================
# МОДУЛИ СБОРА СВЕЖИХ ДАННЫХ (ОКНО 72 ЧАСА)
# ==========================================

def fetch_rss_news():
    feeds = [
        "https://kotaku.com/rss", 
        "https://www.ign.com/feed.xml", 
        "https://stopgame.ru/rss/news.xml", 
        "https://www.gematsu.com/feed",
        "https://www.siliconera.com/feed/"
    ]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for url in feeds:
        try:
            res = requests.get(url, headers=headers, timeout=4)
            for entry in feedparser.parse(res.content).entries[:6]:
                results.append(f"[СМИ/News]: {entry.title}")
        except Exception:
            continue
    return results

def fetch_reddit_trends():
    subs = ["gaming", "gachagaming", "Genshin_Impact", "HonkaiStarRail", "ZenlessZoneZero", "WutheringWaves", "leagueoflegends", "Overwatch"]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for sub in subs:
        try:
            # Забираем горячее и топ за 3 дня
            res = requests.get(f"https://www.reddit.com/r/{sub}/hot.json?limit=6", headers=headers, timeout=4)
            if res.status_code == 200:
                for p in res.json().get('data', {}).get('children', []):
                    results.append(f"[Reddit r/{sub} (+{p.get('data', {}).get('ups', 0)})]: {p.get('data', {}).get('title', '')}")
        except Exception:
            continue
    return results

def fetch_youtube_trailers(api_key):
    if not api_key: 
        return []
    # Окно строго 72 часа назад
    time_limit = (datetime.utcnow() - timedelta(days=3)).isoformat() + "Z"
    params = {
        "part": "snippet", 
        "q": "character trailer OR teaser OR gameplay reveal OR banner preview", 
        "type": "video", 
        "publishedAfter": time_limit, 
        "maxResults": 12, 
        "key": api_key
    }
    results = []
    try:
        res = requests.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=5)
        if res.status_code == 200:
            for item in res.json().get('items', []):
                results.append(f"[YouTube ({item['snippet']['channelTitle']})]: {item['snippet']['title']}")
    except Exception:
        pass
    return results

def fetch_bluesky_trends():
    params = {"q": "fanart OR character design OR update OR leak", "limit": 15}
    results = []
    try:
        res = requests.get("https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts", params=params, timeout=5)
        if res.status_code == 200:
            for p in res.json().get('posts', []):
                text = p.get('record', {}).get('text', '').replace('\n', ' ')[:100]
                results.append(f"[Bluesky (+{p.get('likeCount', 0)}❤️)]: {text}")
    except Exception:
        pass
    return results

def fetch_booru_hot_tags():
    results = []
    try:
        res = requests.get("https://danbooru.donmai.us/posts.json?limit=15&tags=order:rank", headers={'User-Agent': 'HypeRadar/1.0'}, timeout=5)
        if res.status_code == 200:
            for post in res.json():
                tags = post.get('tag_string_character', '')
                if tags:
                    results.append(f"[Booru Tag]: {tags} (Score: {post.get('score', 0)})")
    except Exception:
        pass
    return results

def fetch_steam_twitch(steam_k, c_id, c_secret):
    results = []
    try:
        res_steam = requests.get("https://store.steampowered.com/api/featuredcategories", timeout=5)
        if res_steam.status_code == 200:
            for item in res_steam.json().get('top_sellers', {}).get('items', [])[:6]:
                results.append(f"[Steam Top Seller]: {item.get('name', '')}")
    except Exception:
        pass
    
    if c_id and c_secret:
        try:
            token = requests.post(f"https://id.twitch.tv/oauth2/token?client_id={c_id}&client_secret={c_secret}&grant_type=client_credentials", timeout=5).json().get('access_token', '')
            if token:
                res_twitch = requests.get("https://api.twitch.tv/helix/games/top?first=6", headers={"Client-ID": c_id, "Authorization": f"Bearer {token}"}, timeout=5)
                if res_twitch.status_code == 200:
                    for g in res_twitch.json().get('data', []):
                        results.append(f"[Twitch Top]: {g.get('name')}")
        except Exception:
            pass
    return results

# ==========================================
# ИИ-АНАЛИЗАТОР С ФИЛЬТРОМ ТОКСИЧНОСТИ И ПРОГНОЗОМ
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
    except Exception:
        pass

    models_to_try = supported + ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    current_date = datetime.now().strftime("%Y-%m-%d")

    spicy_block = ""
    if nsfw_enabled:
        spicy_block = """
        ВНИМАНИЕ: Включен режим 16+. Найди персонажей, вокруг которых хайп вызван фансервисом (новые летние скины, моды, физика, пикантные сюжетные сцены). Заполни массив "spicy_top".
        """

    prompt = f"""
    Ты ведущий аналитик данных и арт-директор для 3D-художника. Сегодня {current_date}.
    Художник создает высокодетализированный 3D-арт женских персонажей и публикует его в соцсетях.
    
    Вот свежие перехваченные события за последние 72 часа из СМИ, Reddit, YouTube, Bluesky, Danbooru, Steam и Twitch:
    {json.dumps(feed_dump, ensure_ascii=False)}

    {spicy_block}

    КРИТИЧЕСКИЕ ПРАВИЛА АНАЛИЗА:
    1. ФИЛЬТР ТОКСИЧНОСТИ: Исключи персонажей, чей хайп вызван только негативом/скандалами без эстетического спроса. Оставляй тех, кем аудитория восхищается (новый крутой дизайн, сюжетный пик, красивый трейлер).
    2. ВРЕМЕННОЙ СРЕЗ: Оценивай события строго за последние 72 часа И ближайшие инфоповоды на 1-7 дней вперед (анонсированные баннеры, выход трейлеров, патчи).
    3. КОНКРЕТИКА: В полях обоснования пиши ТОЧНУЮ причину (название патча, скина, ролика, суть мема). Не используй общие фразы.

    СФОРМИРУЙ СТРОГО JSON:
    {{
      "absolute_leader": {{
        "name": "Имя героини",
        "game": "Игра",
        "virality_score": 99,
        "past_72h_event": "Что конкретно произошло за последние 72 часа (трейлер, анонс, арт, стрим)",
        "upcoming_catalyst": "Какой инфоповод подогреет интерес в ближайшие дни (старт баннера, патч)",
        "why_draw_today": "Почему публикация вечером даст взрывной охват",
        "tags": ["3dart", "fanart", "tag3"]
      }},
      "spicy_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Точная причина фансервисного хайпа", "score": 95, "tags": ["spicy", "tag2"] }}
      ],
      "world_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Конкретный триггер мирового спроса", "score": 95, "tags": ["tag1"] }}
      ],
      "ru_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Конкретный триггер спроса в СНГ/РФ фандоме", "score": 92, "tags": ["tag1"] }}
      ],
      "gacha_top_50": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "score": 99, "reach": 95, "likes": 98, "reason": "Патч/баннер/инфоповод", "trend": "🔥" }}
      ],
      "classic_top_50": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "score": 99, "reach": 90, "likes": 92, "reason": "DLC/скин/лояльность фандома", "trend": "📈" }}
      ]
    }}
    Массивы gacha_top_50 и classic_top_50 должны содержать ровно по 50 записей.
    """

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.15}
    }

    last_err = ""
    for model_name in models_to_try:
        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}",
                headers=headers, json=payload, timeout=55
            )
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

if st.button("🚀 Запустить утренний аналитический скан (72h + Forecast)", type="primary", use_container_width=True):
    if not gemini_key:
        st.error("⚠️ Укажите GEMINI_API_KEY в Secrets.")
    else:
        progress = st.progress(0)
        status = st.empty()
        start_time = time.time()
        
        status.markdown("📡 **Сбор инфополя:** Опрашиваем Reddit, СМИ, YouTube (72h), Bluesky, Booru, Steam и Twitch...")
        collected_feed = []
        with ThreadPoolExecutor(max_workers=7) as executor:
            for future in [
                executor.submit(fetch_rss_news), executor.submit(fetch_reddit_trends), 
                executor.submit(fetch_youtube_trailers, youtube_key), executor.submit(fetch_bluesky_trends), 
                executor.submit(fetch_booru_hot_tags), executor.submit(fetch_steam_twitch, steam_key, twitch_id, twitch_secret)
            ]:
                collected_feed.extend(future.result())
                
        progress.progress(45)
        status.markdown(f"🧠 **ИИ-фильтрация:** Обработано **{len(collected_feed)}** событий. Отсекаем негатив, ищем катализаторы хайпа...")
        
        try:
            ai_results, used_model = analyze_cross_platform_feed(collected_feed, gemini_key, is_16_plus)
            st.session_state.update({
                'omni_results': ai_results, 
                'raw_feed': collected_feed, 
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                'scan_done': True
            })
            progress.empty()
            status.empty()
            st.toast(f"Аналитика готова ({used_model})!", icon="✅")
        except Exception as e:
            st.error(f"Ошибка анализа: {e}")

# ==========================================
# ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ
# ==========================================

if st.session_state.get('scan_done', False):
    res = st.session_state['omni_results']
    st.caption(f"⏱️ **Данные собраны и верифицированы:** {st.session_state['timestamp']}")
    
    # 1. КАРТОЧКА АБСОЛЮТНОГО ЛИДЕРА
    leader = res.get('absolute_leader', {})
    if leader:
        tags_html = " ".join([f"<span class='badge'>#{t}</span>" for t in leader.get('tags', [])])
        st.markdown(f"""
        <div class="hero-card">
            <div style="text-transform: uppercase; letter-spacing: 2px; font-size: 12px; margin-bottom: 6px; color: #fbbf24;">👑 Главная цель для вечернего рендера</div>
            <div class="hero-title">{leader.get('name')} <span style="font-size:22px; font-weight:400; opacity:0.85; color:#cbd5e1;">— {leader.get('game')}</span></div>
            <div style="font-size: 16px; margin: 4px 0 12px 0;">Индекс виральности: <b>{leader.get('virality_score')}/100</b></div>
            
            <div class="fact-box">
                📌 <b>Событие за последние 72ч:</b> {leader.get('past_72h_event')}
            </div>
            <div class="catalyst-box">
                ⏳ <b>Ближайший катализатор (1-7 дней):</b> {leader.get('upcoming_catalyst')}
            </div>
            <div style="margin-top: 10px; font-size: 14px; color: #94a3b8;">
                💡 <b>Почему рисовать сегодня:</b> {leader.get('why_draw_today')}
            </div>
            <div style="margin-top: 15px;">{tags_html}</div>
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
                    <p style="font-size: 13px; color: #f1f5f9; margin-bottom: 8px;">{item['analysis']}</p>
                    <div>{" ".join([f"<span class='badge spicy-badge'>#{t}</span>" for t in item.get('tags', [])])}</div>
                </div>
                """, unsafe_allow_html=True)
        st.divider()

    col_w, col_r = st.columns(2)
    with col_w:
        st.subheader("🌍 Мировой спрос (Топ-5)")
        for idx, item in enumerate(res.get('world_top', [])[:5]):
            st.markdown(f"""
            <div class="metric-card {classes[idx]}">
                <h4 style="margin-bottom: 5px;">{medals[idx]} {item['name']} <span style="font-size:14px; color:#888;">({item['game']})</span> — {item.get('score', 0)}/100</h4>
                <p style="font-size: 14px; color: #cbd5e1;">{item['analysis']}</p>
            </div>
            """, unsafe_allow_html=True)

    with col_r:
        st.subheader("🇷🇺 СНГ / РФ фокус (Топ-5)")
        for idx, item in enumerate(res.get('ru_top', [])[:5]):
            st.markdown(f"""
            <div class="metric-card {classes[idx]}">
                <h4 style="margin-bottom: 5px;">{medals[idx]} {item['name']} <span style="font-size:14px; color:#888;">({item['game']})</span> — {item.get('score', 0)}/100</h4>
                <p style="font-size: 14px; color: #cbd5e1;">{item['analysis']}</p>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # 3. ПОДГОТОВКА ДАННЫХ ДЛЯ ДИАГРАММ
    df_gacha = pd.DataFrame(res.get('gacha_top_50', []))
    df_classic = pd.DataFrame(res.get('classic_top_50', []))
    
    # 4. ПРОДВИНУТЫЕ ГРАФИКИ
    st.subheader("📊 Матрица спроса: Охват (СМИ/Reddit) vs Лайки фан-арта (Pixiv/X)")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        if not df_gacha.empty:
            fig_g = px.scatter(
                df_gacha.head(15), x="reach", y="likes", size="score", color="game", 
                hover_name="name", text="name", size_max=38, template="plotly_dark",
                title="Гача: Топ-15 кандидатов для рендера",
                labels={"reach": "Охват инфоповода (Reach)", "likes": "Вовлеченность фан-арта (Likes)"}
            )
            fig_g.update_traces(textposition='top center', textfont=dict(size=11))
            st.plotly_chart(fig_g, use_container_width=True)

    with col_chart2:
        if not df_classic.empty:
            fig_c = px.bar(
                df_classic.head(15).sort_values('score', ascending=True), 
                x='score', y='name', color='likes', orientation='h', text_auto=True,
                color_continuous_scale='Inferno', title="AAA и Соревновательные: Виральность", 
                template="plotly_dark", labels={"score": "Индекс хайпа", "name": ""}
            )
            fig_c.update_traces(textposition='outside')
            fig_c.update_layout(coloraxis_colorbar=dict(title="Лайки"))
            st.plotly_chart(fig_c, use_container_width=True)

    # 5. МАКРО-СПИСКИ ТОП-50 С ОБОСНОВАНИЯМИ
    st.subheader("🗄️ Макро-аналитика: ТОП-50 персонажей с контекстом")
    col_config = {
        "rank": st.column_config.NumberColumn("№", format="%d"),
        "name": "Персонаж",
        "game": "Игра",
        "trend": "Тренд",
        "score": st.column_config.ProgressColumn("Хайп", min_value=0, max_value=100),
        "reason": "Конкретная причина спроса (патч/скин/инфоповод)",
        "reach": st.column_config.NumberColumn("Охват", format="%d"),
        "likes": st.column_config.NumberColumn("Лайки", format="%d")
    }
    
    col_tab1, col_tab2 = st.columns(2)
    with col_tab1:
        st.markdown("<h4 style='text-align: center; color: #4b8bff;'>🎲 Гача-Игры (Топ 50)</h4>", unsafe_allow_html=True)
        if not df_gacha.empty:
            st.dataframe(df_gacha, use_container_width=True, hide_index=True, column_config=col_config, height=620)
            
    with col_tab2:
        st.markdown("<h4 style='text-align: center; color: #ff4b4b;'>⚔️ Остальные игры (Топ 50)</h4>", unsafe_allow_html=True)
        if not df_classic.empty:
            st.dataframe(df_classic, use_container_width=True, hide_index=True, column_config=col_config, height=620)
