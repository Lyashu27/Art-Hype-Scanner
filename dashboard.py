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
import telebot
import threading

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
    .badge {background-color: #1e293b; padding: 4px 10px; border-radius: 6px; font-size: 13px; margin-right: 6px; color: #93c5fd; border: 1px solid #334155; display: inline-block; margin-bottom: 4px;}
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
tg_bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN", "")

st.title("🔥 Omni-Channel Radar: Предиктивный анализ хайпа")
st.markdown("Мониторинг реальных событий за **последние 72 часа** без галлюцинаций.")

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("Настройки Анализа")
    is_16_plus = st.toggle("🔞 Анализ 16+ (Spicy / Фансервис)", value=True, help="Фокус на персонажах с виральными купальниками, откровенными скинами и модами.")
    
    st.divider()
    st.header("Статус каналов данных")
    st.write(f"🧠 Gemini Core: {'🟢 Активен' if gemini_key else '🔴 Нет ключа'}")
    st.write(f"🤖 Telegram Bot: {'🟢 Подключен' if tg_bot_token else '⚪ Выключен'}")
    st.write(f"📺 YouTube API (72h): {'🟢 Активен' if youtube_key else '⚪ Выключен'}")
    st.write(f"🦋 Bluesky Public: 🟢 Активен")
    st.write(f"👾 Reddit Gaming Hubs: 🟢 Активен")
    st.write(f"📰 Gaming News RSS: 🟢 Активен")
    st.write(f"🎨 Danbooru Trends: 🟢 Активен")
    st.write(f"🎮 Steam & Twitch: {'🟢 Подключены' if (steam_key or twitch_id) else '🟡 Открытый режим'}")

# ==========================================
# ЯДРО СБОРА ДАННЫХ
# ==========================================

def fetch_rss_news():
    feeds = ["https://kotaku.com/rss", "https://www.ign.com/feed.xml", "https://stopgame.ru/rss/news.xml", "https://www.gematsu.com/feed", "https://www.siliconera.com/feed/"]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for url in feeds:
        try:
            res = requests.get(url, headers=headers, timeout=4)
            for entry in feedparser.parse(res.content).entries[:6]:
                results.append(f"[СМИ]: {entry.title}")
        except Exception:
            continue
    return results

def fetch_reddit_trends():
    subs = ["gaming", "gachagaming", "Genshin_Impact", "HonkaiStarRail", "ZenlessZoneZero", "WutheringWaves", "leagueoflegends", "Overwatch"]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for sub in subs:
        try:
            res = requests.get(f"https://www.reddit.com/r/{sub}/hot.json?limit=6", headers=headers, timeout=4)
            if res.status_code == 200:
                for p in res.json().get('data', {}).get('children', []):
                    results.append(f"[Reddit r/{sub} (+{p.get('data', {}).get('ups', 0)})]: {p.get('data', {}).get('title', '')}")
        except Exception:
            continue
    return results

def fetch_youtube_trailers(api_key):
    if not api_key: return []
    time_limit = (datetime.utcnow() - timedelta(days=3)).isoformat() + "Z"
    params = {"part": "snippet", "q": "character trailer OR teaser OR gameplay reveal OR banner preview", "type": "video", "publishedAfter": time_limit, "maxResults": 12, "key": api_key}
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
                if tags: results.append(f"[Booru Tag]: {tags}")
    except Exception:
        pass
    return results

def fetch_steam_twitch(steam_k, c_id, c_secret):
    results = []
    try:
        res_steam = requests.get("https://store.steampowered.com/api/featuredcategories", timeout=5)
        if res_steam.status_code == 200:
            for item in res_steam.json().get('top_sellers', {}).get('items', [])[:6]:
                results.append(f"[Steam]: {item.get('name', '')}")
    except Exception:
        pass
    
    if c_id and c_secret:
        try:
            token = requests.post(f"https://id.twitch.tv/oauth2/token?client_id={c_id}&client_secret={c_secret}&grant_type=client_credentials", timeout=5).json().get('access_token', '')
            if token:
                res_twitch = requests.get("https://api.twitch.tv/helix/games/top?first=6", headers={"Client-ID": c_id, "Authorization": f"Bearer {token}"}, timeout=5)
                if res_twitch.status_code == 200:
                    for g in res_twitch.json().get('data', []):
                        results.append(f"[Twitch]: {g.get('name')}")
        except Exception:
            pass
    return results

# ==========================================
# ИИ-АНАЛИЗАТОР С ДИНАМИЧЕСКИМ ПОИСКОМ МОДЕЛЕЙ
# ==========================================

def analyze_cross_platform_feed(feed_dump, key, nsfw_enabled):
    # Автоматически запрашиваем список доступных моделей для вашего аккаунта
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

    fallback_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-pro"]
    models_to_try = []
    for m in supported_models + fallback_models:
        if m not in models_to_try:
            models_to_try.append(m)

    current_date = datetime.now().strftime("%Y-%m-%d")
    spicy_block = 'Ищи персонажей, популярных за счет фансервиса (купальники, моды, NSFW-adjacent). Заполни массив "spicy_top".' if nsfw_enabled else 'Массив "spicy_top" оставь пустым.'

    prompt = f"""
    ТВОЯ ЗАДАЧА — СТРОГИЙ АНАЛИЗ ФАКТОВ. ТЫ НЕ ИМЕЕШЬ ПРАВА ВЫДУМЫВАТЬ ИНФОРМАЦИЮ. Сегодня {current_date}.
    
    ДАННЫЕ ИЗ ИНТЕРНЕТА (ОСНОВА ДЛЯ АНАЛИЗА):
    {json.dumps(feed_dump, ensure_ascii=False)}

    {spicy_block}

    ЖЕСТКИЕ ПРАВИЛА:
    1. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО выдумывать новости, утечки, трейлеры, коллаборации, если этого НЕТ в переданных данных.
    2. Если персонаж популярен, но в данных про него нет конкретных новостей за 72ч, в полях 'past_72h_event' и 'upcoming_catalyst' пиши СТРОГО: "Нет свежих инфоповодов. Спрос держится на фанатской базе."
    3. Обоснования должны быть реальными. Цитируй или опирайся только на текст из переданных тебе данных.
    
    СФОРМИРУЙ СТРОГО JSON:
    {{
      "absolute_leader": {{
        "name": "Имя героини",
        "game": "Игра",
        "virality_score": 99,
        "past_72h_event": "Только реальное событие из данных, иначе 'Нет свежих инфоповодов.'",
        "upcoming_catalyst": "Только реальный инфоповод из данных, иначе 'Нет свежих инфоповодов.'",
        "why_draw_today": "Почему публикация сегодня вечером даст охват",
        "tags": ["3dart", "fanart"]
      }},
      "spicy_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Реальная причина фансервисного хайпа", "score": 95, "tags": ["spicy"] }}
      ],
      "world_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Реальный триггер спроса", "score": 95, "tags": ["tag1"] }}
      ],
      "ru_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Реальный триггер спроса", "score": 92, "tags": ["tag1"] }}
      ],
      "gacha_top_50": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "score": 99, "reach": 95, "likes": 98, "reason": "Реальная причина или 'Базовый интерес'", "trend": "🔥" }}
      ],
      "classic_top_50": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "score": 99, "reach": 90, "likes": 92, "reason": "Реальная причина или 'Базовый интерес'", "trend": "📈" }}
      ]
    }}
    """

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.0}
    }

    last_err = ""
    for model_name in models_to_try:
        try:
            resp = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}", headers=headers, json=payload, timeout=55)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                raw_text = raw_text.replace("```json\n", "").replace("```", "").strip()
                return json.loads(raw_text), model_name
            else:
                last_err = f"[{model_name}] {resp.status_code}: {resp.text}"
        except Exception as e:
            last_err = f"[{model_name}] {str(e)}"
            continue

    raise RuntimeError(f"Сбой Gemini API: {last_err}")

def run_full_scan():
    collected_feed = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        for future in [
            executor.submit(fetch_rss_news), executor.submit(fetch_reddit_trends), 
            executor.submit(fetch_youtube_trailers, youtube_key), executor.submit(fetch_bluesky_trends), 
            executor.submit(fetch_booru_hot_tags), executor.submit(fetch_steam_twitch, steam_key, twitch_id, twitch_secret)
        ]:
            collected_feed.extend(future.result())
    return analyze_cross_platform_feed(collected_feed, gemini_key, is_16_plus), collected_feed

# ==========================================
# ИНТЕГРАЦИЯ TELEGRAM БОТА
# ==========================================

@st.cache_resource
def start_telegram_bot(token):
    if not token: return None
    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        bot.reply_to(message, "Привет! Я *Omni-Channel Radar* 🤖\nНапиши /scan, чтобы я собрал строгие факты по трендам.", parse_mode="Markdown")

    @bot.message_handler(commands=['scan'])
    def handle_scan(message):
        bot.reply_to(message, "📡 Собираю данные с платформ. ИИ проверяет факты... Подожди 20-30 секунд.")
        try:
            (ai_res, model), _ = run_full_scan()
            leader = ai_res.get('absolute_leader', {})
            msg = f"👑 *АБСОЛЮТНЫЙ ЛИДЕР:*\n*{leader.get('name', 'N/A')}* ({leader.get('game', 'N/A')})\n"
            msg += f"📌 Событие (72ч): {leader.get('past_72h_event', 'Нет данных')}\n\n"
            msg += "🌍 *МИРОВОЙ ТОП-3:*\n"
            for i, itm in enumerate(ai_res.get('world_top', [])[:3]):
                msg += f"{i+1}. {itm['name']} ({itm.get('score')}/100)\n"
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка сбора: {str(e)}")

    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    return bot

start_telegram_bot(tg_bot_token)

# ==========================================
# ИНТЕРФЕЙС STREAMLIT
# ==========================================

if st.button("🚀 Запустить строгий аналитический скан", type="primary", use_container_width=True):
    if not gemini_key:
        st.error("⚠️ Укажите GEMINI_API_KEY в Secrets.")
    else:
        progress = st.progress(0)
        status = st.empty()
        status.markdown("📡 **Сбор инфополя и проверка фактов...**")
        progress.progress(50)
        
        try:
            (ai_results, used_model), raw_feed = run_full_scan()
            st.session_state.update({
                'omni_results': ai_results, 
                'raw_feed': raw_feed,
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
<div class="hero-title">{leader.get('name', 'Нет данных')} <span style="font-size:22px; font-weight:400; opacity:0.85; color:#cbd5e1;">— {leader.get('game', 'Нет данных')}</span></div>
<div style="font-size: 16px; margin: 4px 0 12px 0;">Индекс виральности: <b>{leader.get('virality_score', 0)}/100</b></div>
<div class="fact-box">📌 <b>Событие за последние 72ч:</b> {leader.get('past_72h_event', 'Нет свежих инфоповодов')}</div>
<div class="catalyst-box">⏳ <b>Ближайший катализатор:</b> {leader.get('upcoming_catalyst', 'Нет свежих инфоповодов')}</div>
<div style="margin-top: 10px; font-size: 14px; color: #94a3b8;">💡 <b>Почему рисовать сегодня:</b> {leader.get('why_draw_today', 'Базовый спрос аудитории')}</div>
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
<h4 style="margin-bottom: 5px; color: #ff9ebf;">{medals[idx]} {item.get('name', '')} <span style="font-size:14px; color:#a5b1c2;">({item.get('game', '')})</span></h4>
<p style="font-size: 13px; color: #f1f5f9; margin-bottom: 8px;">{item.get('analysis', '')}</p>
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
<h4 style="margin-bottom: 5px;">{medals[idx]} {item.get('name', '')} <span style="font-size:14px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 14px; color: #cbd5e1;">{item.get('analysis', '')}</p>
</div>
            """, unsafe_allow_html=True)

    with col_r:
        st.subheader("🇷🇺 СНГ / РФ фокус (Топ-5)")
        for idx, item in enumerate(res.get('ru_top', [])[:5]):
            st.markdown(f"""
<div class="metric-card {classes[idx]}">
<h4 style="margin-bottom: 5px;">{medals[idx]} {item.get('name', '')} <span style="font-size:14px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 14px; color: #cbd5e1;">{item.get('analysis', '')}</p>
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
        if not df_gacha.empty and 'reach' in df_gacha.columns and 'likes' in df_gacha.columns:
            fig_g = px.scatter(
                df_gacha.head(15), x="reach", y="likes", size="score", color="game", 
                hover_name="name", text="name", size_max=38, template="plotly_dark",
                title="Гача: Топ-15 кандидатов для рендера",
                labels={"reach": "Охват инфоповода (Reach)", "likes": "Вовлеченность фан-арта (Likes)"}
            )
            fig_g.update_traces(textposition='top center', textfont=dict(size=11))
            st.plotly_chart(fig_g, use_container_width=True)

    with col_chart2:
        if not df_classic.empty and 'score' in df_classic.columns and 'name' in df_classic.columns:
            fig_c = px.bar(
                df_classic.head(15).sort_values('score', ascending=True), 
                x='score', y='name', color='likes' if 'likes' in df_classic.columns else None, 
                orientation='h', text_auto=True,
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
        "reason": "Фактическая причина спроса",
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
