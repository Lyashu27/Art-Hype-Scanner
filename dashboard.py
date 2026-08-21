import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime, timedelta
import feedparser
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go
import telebot
import threading
import re

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="Omni-Channel Art Hype Radar Pro v2", page_icon="🔥", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 18px; border-radius: 12px; border-left: 5px solid #4b8bff; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .spicy-card {background-color: #25181e; padding: 18px; border-radius: 12px; border-left: 5px solid #ff4b8b; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(255, 75, 139, 0.15);}
    .hero-card {background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 26px; border-radius: 16px; margin-bottom: 20px; color: white; border: 1px solid #3b82f6; box-shadow: 0 10px 25px rgba(59, 130, 246, 0.25);}
    .hero-title {font-size: 28px; font-weight: 800; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 1px; color: #60a5fa;}
    .fact-box {background: rgba(15, 23, 42, 0.7); padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-top: 8px; border-left: 4px solid #38bdf8;}
    .catalyst-box {background: rgba(15, 23, 42, 0.7); padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-top: 8px; border-left: 4px solid #f59e0b;}
    .badge {background-color: #1e293b; padding: 3px 8px; border-radius: 6px; font-size: 12px; margin-right: 5px; color: #93c5fd; border: 1px solid #334155; display: inline-block; margin-bottom: 3px;}
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

st.title("🔥 Omni-Channel Radar v2: High-Velocity Art Hype Engine")
st.markdown("Мониторинг первоисточников (Reddit Leaks, Danbooru 72h, Bluesky, Steam/Twitch) с динамическим анализом.")

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Параметры Сбора")
    is_16_plus = st.toggle("🔞 Режим 16+ (Spicy / Фансервис / Моды)", value=True, help="Фокус на купальниках, откровенных скинах, модах и фансервисных триггерах.")
    st.divider()
    st.header("📡 Состояние Каналов")
    st.write(f"🧠 Gemini Core: {'🟢 Активен' if gemini_key else '🔴 Нет ключа'}")
    st.write(f"🤖 Telegram Bot: {'🟢 Подключен' if tg_bot_token else '⚪ Выключен'}")
    st.write(f"🎨 Danbooru 72h: 🟢 Активен (age:<3d)")
    st.write(f"🔍 Reddit Leaks Hubs: 🟢 Активен (Top 7d)")
    st.write(f"🦋 Bluesky Stream: 🟢 Активен")
    st.write(f"📺 YouTube API: {'🟢 Активен' if youtube_key else '⚪ Выключен'}")
    st.write(f"🎮 Steam & Twitch: {'🟢 Подключены' if (steam_key or twitch_id) else '🟡 Базовый режим'}")

# ==========================================
# ЯДРО СБОРА ДАННЫХ ИЗ ПЕРВОИСТОЧНИКОВ
# ==========================================

def fetch_danbooru_hot_72h():
    """Сбор взрывных персонажей по тегам за последние 72 часа"""
    url = "https://danbooru.donmai.us/posts.json?limit=40&tags=age:<3d+order:score"
    results = []
    char_counts = Counter()
    try:
        res = requests.get(url, headers={'User-Agent': 'HypeRadarPro/2.0'}, timeout=5)
        if res.status_code == 200:
            for post in res.json():
                chars = post.get('tag_string_character', '').split()
                score = post.get('score', 0)
                for char in chars:
                    if char and char not in ["original", "unknown"]:
                        char_counts[char] += (score + 1)
            for char, weight in char_counts.most_common(12):
                clean_name = char.replace('_', ' ').title()
                results.append(f"[Danbooru 72h Momentum (+{weight}pts)]: {clean_name}")
    except Exception:
        pass
    return results

def fetch_reddit_leaks_and_hubs():
    """Сбор свежих утечек и хайпа из сабреддитов-первоисточников"""
    subs = [
        ("Genshin_Impact_Leaks", 8),
        ("HonkaiStarRail_Leaks", 8),
        ("Zenlesszonezero_leaks_", 8),
        ("WutheringWavesLeaks", 8),
        ("NikkeMobile", 6),
        ("BlueArchive", 6),
        ("gachagaming", 6),
        ("gaming", 6)
    ]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    for sub, limit in subs:
        try:
            res = requests.get(f"https://www.reddit.com/r/{sub}/top.json?t=week&limit={limit}", headers=headers, timeout=4)
            if res.status_code == 200:
                for p in res.json().get('data', {}).get('children', []):
                    data = p.get('data', {})
                    title = data.get('title', '')
                    ups = data.get('ups', 0)
                    results.append(f"[Reddit r/{sub} (+{ups}👍)]: {title}")
        except Exception:
            continue
    return results

def fetch_bluesky_art():
    """Поиск виральных персонажей в децентрализованной ленте Bluesky"""
    queries = ["fanart", "character design reveal", "drip marketing", "new skin"]
    results = []
    for q in queries[:2]:
        try:
            res = requests.get(f"https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q={q}&limit=8", timeout=4)
            if res.status_code == 200:
                for p in res.json().get('posts', []):
                    text = p.get('record', {}).get('text', '').replace('\n', ' ')[:110]
                    likes = p.get('likeCount', 0)
                    if likes > 5:
                        results.append(f"[Bluesky (+{likes}❤️)]: {text}")
        except Exception:
            pass
    return results

def fetch_youtube_trailers(api_key):
    if not api_key: return []
    time_limit = (datetime.utcnow() - timedelta(days=3)).isoformat() + "Z"
    params = {
        "part": "snippet",
        "q": "character trailer OR teaser OR drip marketing OR gameplay reveal OR skin preview",
        "type": "video",
        "publishedAfter": time_limit,
        "maxResults": 10,
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

def fetch_rss_news():
    feeds = [
        "https://www.gematsu.com/feed",
        "https://www.siliconera.com/feed/",
        "https://stopgame.ru/rss/news.xml",
        "https://kotaku.com/rss"
    ]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for url in feeds:
        try:
            res = requests.get(url, headers=headers, timeout=4)
            for entry in feedparser.parse(res.content).entries[:4]:
                results.append(f"[СМИ]: {entry.title}")
        except Exception:
            continue
    return results

def fetch_steam_twitch(steam_k, c_id, c_secret):
    results = []
    try:
        res_steam = requests.get("https://store.steampowered.com/api/featuredcategories", timeout=4)
        if res_steam.status_code == 200:
            for item in res_steam.json().get('top_sellers', {}).get('items', [])[:5]:
                results.append(f"[Steam Top Seller]: {item.get('name', '')}")
    except Exception:
        pass
    
    if c_id and c_secret:
        try:
            token = requests.post(f"https://id.twitch.tv/oauth2/token?client_id={c_id}&client_secret={c_secret}&grant_type=client_credentials", timeout=4).json().get('access_token', '')
            if token:
                res_twitch = requests.get("https://api.twitch.tv/helix/games/top?first=5", headers={"Client-ID": c_id, "Authorization": f"Bearer {token}"}, timeout=4)
                if res_twitch.status_code == 200:
                    for g in res_twitch.json().get('data', []):
                        results.append(f"[Twitch Top Streamed]: {g.get('name')}")
        except Exception:
            pass
    return results

# ==========================================
# ИИ-АНАЛИЗАТОР С АВТООПРЕДЕЛЕНИЕМ МОДЕЛЕЙ
# ==========================================

def get_available_gemini_models(api_key):
    """Динамический поиск активных моделей для конкретного API-ключа"""
    models = []
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            for m in res.json().get('models', []):
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    name = m.get('name', '').replace('models/', '')
                    # Приоритет быстрым Flash-моделям
                    if 'flash' in name.lower():
                        models.insert(0, name)
                    elif 'pro' in name.lower():
                        models.append(name)
    except Exception:
        pass

    # Надежные дефолтные имена актуальных версий
    fallback = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-1.5-pro", "gemini-2.0-flash-exp", "gemini-2.5-flash"]
    for f in fallback:
        if f not in models:
            models.append(f)
    return models

def analyze_cross_platform_feed(feed_dump, key, nsfw_enabled):
    models_to_try = get_available_gemini_models(key)
    current_date = datetime.now().strftime("%Y-%m-%d")
    spicy_instruction = 'Заполни массив "spicy_top" персонажами с фансервисом, купальниками, модами.' if nsfw_enabled else 'Оставь "spicy_top" пустым.'

    prompt = f"""
    ТЫ — АНАЛИТИК ХАЙПА ФАН-АРТА ДЛЯ ХУДОЖНИКОВ. Сегодня {current_date}.
    
    ВХОДНЫЕ ДАННЫЕ С ПЕРВОИСТОЧНИКОВ (Danbooru 72h, Reddit Leaks, Bluesky, YouTube, Steam/Twitch):
    {json.dumps(feed_dump, ensure_ascii=False)}

    ЗАДАЧА:
    Выдели персонажей с НАИБОЛЬШИМ ИМПУЛЬСОМ СПРОСА прямо сейчас на основе переданных фактов.
    {spicy_instruction}

    ПРАВИЛА:
    1. Не придумывай несуществующие события. Связывай персонажа строго с реальным триггером из ленты.
    2. В поле "visual_hook" укажи визуальную деталь для рендера (поза, купальник, оружие, подсветка, скин).
    3. Выстави реалистичный скоринг (0-100).
    
    ВЕРНИ СТРОГО JSON:
    {{
      "absolute_leader": {{
        "name": "Имя персонажа",
        "game": "Игра/Франшиза",
        "virality_score": 98,
        "past_72h_event": "Факт из данных",
        "upcoming_catalyst": "Что подогреет интерес в ближайшие дни",
        "visual_hook": "На какую деталь образа делать упор в арте",
        "why_draw_today": "Почему публикация сегодня даст охват",
        "tags": ["3dart", "fanart"]
      }},
      "spicy_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Причина фансервис-хайпа", "visual_hook": "Ключевой элемент костюма", "score": 95, "tags": ["spicy"] }}
      ],
      "world_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Основной глобальный триггер", "score": 96, "tags": ["global"] }}
      ],
      "ru_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Триггер для RU/CIS аудитории", "score": 93, "tags": ["ru_trend"] }}
      ],
      "gacha_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "score": 97, "reach": 94, "likes": 96, "visual_hook": "Деталь образа", "reason": "Реальный инфоповод", "trend": "🔥" }}
      ],
      "classic_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "score": 92, "reach": 88, "likes": 90, "visual_hook": "Деталь образа", "reason": "Реальный инфоповод", "trend": "📈" }}
      ]
    }}
    """

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.1
        }
    }

    last_err = ""
    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
            resp = requests.post(url, headers=headers, json=payload, timeout=45)
            
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                # Извлечение чистого JSON блока
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group()), model_name
                else:
                    return json.loads(raw_text), model_name
            else:
                last_err = f"[{model_name}] {resp.status_code}: {resp.text}"
        except Exception as e:
            last_err = f"[{model_name}] {str(e)}"
            continue

    raise RuntimeError(f"Сбой подключения к Gemini API. Последняя ошибка: {last_err}")

def run_full_scan():
    collected_feed = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [
            executor.submit(fetch_danbooru_hot_72h),
            executor.submit(fetch_reddit_leaks_and_hubs),
            executor.submit(fetch_bluesky_art),
            executor.submit(fetch_youtube_trailers, youtube_key),
            executor.submit(fetch_rss_news),
            executor.submit(fetch_steam_twitch, steam_key, twitch_id, twitch_secret)
        ]
        for f in futures:
            collected_feed.extend(f.result())
            
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
        bot.reply_to(message, "⚡ *Hype Radar Bot v2*\nКоманда /scan собирает свежие анонсы, лики и тренды Danbooru.", parse_mode="Markdown")

    @bot.message_handler(commands=['scan'])
    def handle_scan(message):
        bot.reply_to(message, "📡 Сканирую первоисточники (Reddit Leaks, Danbooru 72h, Bluesky)...")
        try:
            (ai_res, model), _ = run_full_scan()
            leader = ai_res.get('absolute_leader', {})
            msg = f"👑 *ТОП ЦЕЛЬ ДЛЯ АРТА:*\n*{leader.get('name', 'N/A')}* ({leader.get('game', 'N/A')})\n"
            msg += f"🎯 *Визуальный хук:* {leader.get('visual_hook', 'N/A')}\n"
            msg += f"📌 *Инфоповод:* {leader.get('past_72h_event', 'N/A')}\n\n"
            msg += "🌍 *ТОП-3 В МИРЕ:*\n"
            for i, itm in enumerate(ai_res.get('world_top', [])[:3]):
                msg += f"{i+1}. {itm['name']} ({itm.get('game')}) — {itm.get('score')}/100\n"
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    return bot

start_telegram_bot(tg_bot_token)

# ==========================================
# ИНТЕРФЕЙС STREAMLIT
# ==========================================

if st.button("🚀 Запустить глубокий скан первоисточников", type="primary", use_container_width=True):
    if not gemini_key:
        st.error("⚠️ Добавьте GEMINI_API_KEY в Secrets приложения.")
    else:
        status_container = st.status("📡 Сбор сигналов и синтез аналитики...", expanded=True)
        try:
            status_container.write("1. Проверяем Danbooru на взрывные теги за 72ч...")
            status_container.write("2. Парсим топ-посты в Reddit Leaks хабах...")
            status_container.write("3. Сканируем Bluesky, YouTube, Steam/Twitch...")
            status_container.write("4. Подключаем доступную модель Gemini и строим бэклог...")
            
            (ai_results, used_model), raw_feed = run_full_scan()
            
            st.session_state.update({
                'omni_results': ai_results,
                'raw_feed': raw_feed,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'scan_done': True
            })
            status_container.update(label=f"Готово! Модель: {used_model}", state="complete", expanded=False)
            st.toast("Анализ трендов успешно завершен!", icon="✨")
        except Exception as e:
            status_container.update(label="Ошибка сбора данных", state="error", expanded=True)
            st.error(f"Детали ошибки: {e}")

# ==========================================
# ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ
# ==========================================

if st.session_state.get('scan_done', False):
    res = st.session_state['omni_results']
    st.caption(f"⏱️ **Данные собраны и верифицированы:** {st.session_state['timestamp']}")
    
    # 1. ГЛАВНАЯ ЦЕЛЬ ДЛЯ АРТА
    leader = res.get('absolute_leader', {})
    if leader:
        tags_html = " ".join([f"<span class='badge'>#{t}</span>" for t in leader.get('tags', [])])
        st.markdown(f"""
<div class="hero-card">
<div style="text-transform: uppercase; letter-spacing: 2px; font-size: 12px; margin-bottom: 6px; color: #fbbf24;">👑 Главный объект внимания аудитории</div>
<div class="hero-title">{leader.get('name', 'Нет данных')} <span style="font-size:20px; font-weight:400; opacity:0.85; color:#cbd5e1;">— {leader.get('game', 'Нет данных')}</span></div>
<div style="font-size: 15px; margin: 4px 0 10px 0;">Индекс виральности: <b>{leader.get('virality_score', 0)}/100</b></div>
<div class="fact-box">🎯 <b>Визуальный фокус для рендера:</b> {leader.get('visual_hook', 'Детализированный костюм / фирменная поза')}</div>
<div class="fact-box">📌 <b>Событие за 72ч:</b> {leader.get('past_72h_event', 'Высокий интерес в фандоме')}</div>
<div class="catalyst-box">⏳ <b>Катализатор:</b> {leader.get('upcoming_catalyst', 'Ближайший баннер или релиз')}</div>
<div style="margin-top: 10px; font-size: 13px; color: #94a3b8;">💡 <b>Почему рисовать сегодня:</b> {leader.get('why_draw_today', 'Пик внимания к персонажу')}</div>
<div style="margin-top: 14px;">{tags_html}</div>
</div>
        """, unsafe_allow_html=True)

    # 2. БЛОК 16+ SPICY
    medals, classes = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"], ["top1", "top2", "top3", "", ""]
    
    if is_16_plus and res.get('spicy_top'):
        st.subheader("🔞 Тренды 16+ (Spicy / Фансервис / Скины)")
        spicy_cols = st.columns(min(3, len(res.get('spicy_top', []))))
        for idx, item in enumerate(res.get('spicy_top', [])[:3]):
            with spicy_cols[idx]:
                st.markdown(f"""
<div class="spicy-card">
<h4 style="margin-bottom: 5px; color: #ff9ebf;">{medals[idx]} {item.get('name', '')} <span style="font-size:13px; color:#a5b1c2;">({item.get('game', '')})</span></h4>
<p style="font-size: 13px; color: #f1f5f9; margin-bottom: 6px;"><b>Триггер:</b> {item.get('analysis', '')}</p>
<p style="font-size: 12px; color: #f472b6; margin-bottom: 8px;">👙 <b>Хук:</b> {item.get('visual_hook', 'Акцент на костюме')}</p>
<div>{" ".join([f"<span class='badge spicy-badge'>#{t}</span>" for t in item.get('tags', [])])}</div>
</div>
                """, unsafe_allow_html=True)
        st.divider()

    # 3. МИРОВОЙ И РЕГИОНАЛЬНЫЙ ТОП
    col_w, col_r = st.columns(2)
    with col_w:
        st.subheader("🌍 Мировой фокус (Топ-5)")
        for idx, item in enumerate(res.get('world_top', [])[:5]):
            st.markdown(f"""
<div class="metric-card {classes[idx]}">
<h4 style="margin-bottom: 4px;">{medals[idx]} {item.get('name', '')} <span style="font-size:13px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 13px; color: #cbd5e1; margin: 0;">{item.get('analysis', '')}</p>
</div>
            """, unsafe_allow_html=True)

    with col_r:
        st.subheader("🇷🇺 СНГ / RU интерес (Топ-5)")
        for idx, item in enumerate(res.get('ru_top', [])[:5]):
            st.markdown(f"""
<div class="metric-card {classes[idx]}">
<h4 style="margin-bottom: 4px;">{medals[idx]} {item.get('name', '')} <span style="font-size:13px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 13px; color: #cbd5e1; margin: 0;">{item.get('analysis', '')}</p>
</div>
            """, unsafe_allow_html=True)

    st.divider()

    # 4. ДИАГРАММЫ И МАТРИЦА
    df_gacha = pd.DataFrame(res.get('gacha_top', []))
    df_classic = pd.DataFrame(res.get('classic_top', []))
    
    st.subheader("📊 Матрица спроса: Охват инфоповода vs Вовлеченность аудитории")
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        if not df_gacha.empty and 'reach' in df_gacha.columns and 'likes' in df_gacha.columns:
            fig_g = px.scatter(
                df_gacha, x="reach", y="likes", size="score", color="game",
                hover_name="name", text="name", size_max=32, template="plotly_dark",
                title="Гача & Аниме: Карта вовлеченности",
                labels={"reach": "Охват инфоповода (Reddit/Media)", "likes": "Потенциал лайков (Booru/Bluesky)"}
            )
            fig_g.update_traces(textposition='top center', textfont=dict(size=11))
            st.plotly_chart(fig_g, use_container_width=True)

    with col_c2:
        if not df_classic.empty and 'score' in df_classic.columns and 'name' in df_classic.columns:
            fig_c = px.bar(
                df_classic.sort_values('score', ascending=True),
                x='score', y='name', color='likes' if 'likes' in df_classic.columns else None,
                orientation='h', text_auto=True,
                color_continuous_scale='Magma', title="AAA & Соревновательные: Индекс виральности",
                template="plotly_dark", labels={"score": "Индекс хайпа", "name": ""}
            )
            st.plotly_chart(fig_c, use_container_width=True)

    # 5. ТАБЛИЦЫ С ВИЗУАЛЬНЫМИ ХУКАМИ
    st.subheader("📋 Практический бэклог для создания артов")
    col_cfg = {
        "rank": st.column_config.NumberColumn("№", format="%d"),
        "name": "Персонаж",
        "game": "Игра",
        "trend": "Тренд",
        "score": st.column_config.ProgressColumn("Хайп", min_value=0, max_value=100),
        "visual_hook": "🎨 Визуальный хук для рендера",
        "reason": "Конкретная причина хайпа"
    }

    t1, t2 = st.columns(2)
    with t1:
        st.markdown("<h4 style='color: #4b8bff;'>🎲 Гача & Новые релизы</h4>", unsafe_allow_html=True)
        if not df_gacha.empty:
            st.dataframe(df_gacha, use_container_width=True, hide_index=True, column_config=col_cfg, height=380)

    with t2:
        st.markdown("<h4 style='color: #ff4b4b;'>⚔️ AAA, Соревновательные & Классика</h4>", unsafe_allow_html=True)
        if not df_classic.empty:
            st.dataframe(df_classic, use_container_width=True, hide_index=True, column_config=col_cfg, height=380)
            
    # 6. RAW FEED ДЛЯ САМОПРОВЕРКИ
    with st.expander("🔍 Посмотреть собранный сырой поток первоисточников"):
        st.write(st.session_state.get('raw_feed', []))
