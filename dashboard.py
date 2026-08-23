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
st.set_page_config(page_title="Omni-Channel Art Hype Radar Pro (Female Only)", page_icon="🔥", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 16px; border-radius: 12px; border-left: 5px solid #4b8bff; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .spicy-card {background-color: #25181e; padding: 16px; border-radius: 12px; border-left: 5px solid #ff4b8b; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(255, 75, 139, 0.15);}
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
nexus_key = st.secrets.get("NEXUSMODS_API_KEY", "") # НОВЫЙ КЛЮЧ

st.title("🔥 Omni-Channel Art Hype Radar: Velocity Edition")
st.markdown("Предиктивный радар виральности женских персонажей. Оптимизирован под мультиплатформенную публикацию 3D-ассетов.")

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Параметры Сбора")
    is_16_plus = st.toggle("🔞 Режим 16+ (Spicy / Фансервис / Моды)", value=True, help="Включает NexusMods и расширенный анализ фансервиса.")
    st.divider()
    st.header("📡 Состояние Каналов")
    st.write(f"🧠 Gemini Core: {'🟢 Активен' if gemini_key else '🔴 Нет ключа'}")
    st.write(f"🤖 Telegram Bot: {'🟢 Подключен' if tg_bot_token else '⚪ Выключен'}")
    st.write(f"🎨 Danbooru (Velocity): 🟢 Активен (24h)")
    st.write(f"🎨 Pixiv Daily (RSS): 🟢 Активен")
    st.write(f"🔍 Reddit Leaks (Velocity): 🟢 Активен (Hot/Rising)")
    st.write(f"🦋 Bluesky Stream: 🟢 Активен")
    st.write(f"📺 YouTube API (Targeted): {'🟢 Активен' if youtube_key else '⚪ Выключен'}")
    st.write(f"🎮 Steam & Twitch (Dynamics): {'🟢 Подключены' if (steam_key or twitch_id) else '🟡 Базовый режим'}")
    st.write(f"🛡️ NexusMods Trending: {'🟢 Активен' if nexus_key else '⚪ Выключен'}")
    st.write(f"📺 Bilibili Hot Search: 🟢 Активен")

# ==========================================
# ДИНАМИЧЕСКИЙ СПИСОК ИГР (STEAM + TWITCH)
# ==========================================
@st.cache_data(ttl=3600)
def get_dynamic_trending_games():
    games = ["Genshin", "Honkai", "Zenless", "Wuthering", "Nikke", "Snowbreak", "Resident Evil", "Cyberpunk", "Stellar Blade", "Final Fantasy"]
    # Парсим Twitch если есть ключи
    if twitch_id and twitch_secret:
        try:
            token_url = f"https://id.twitch.tv/oauth2/token?client_id={twitch_id}&client_secret={twitch_secret}&grant_type=client_credentials"
            token = requests.post(token_url, timeout=4).json().get('access_token', '')
            if token:
                res = requests.get("https://api.twitch.tv/helix/games/top?first=10", headers={"Client-ID": twitch_id, "Authorization": f"Bearer {token}"}, timeout=4)
                if res.status_code == 200:
                    for g in res.json().get('data', []):
                        name = g.get('name')
                        if name not in games and name not in ["Just Chatting", "Special Events"]:
                            games.append(name)
        except:
            pass
    return list(set(games))

# ==========================================
# СБОР ДАННЫХ ИЗ ПЕРВОИСТОЧНИКОВ
# ==========================================

def fetch_danbooru_velocity():
    """Сбор по метрике ускорения (Velocity) за последние 24 часа"""
    url = "https://danbooru.donmai.us/posts.json?limit=200&tags=age:<24h+1girl"
    results = []
    char_counts = Counter()
    try:
        res = requests.get(url, headers={'User-Agent': 'HypeRadarPro/5.0'}, timeout=5)
        if res.status_code == 200:
            for post in res.json():
                chars = post.get('tag_string_character', '').split()
                # Считаем частоту появления персонажа за последние 24 часа
                for char in chars:
                    if char and char not in ["original", "unknown", "comic"]:
                        char_counts[char] += 1
            for char, count in char_counts.most_common(20):
                if count > 2: # Минимум 3 арта за 24ч
                    clean_name = char.replace('_', ' ').title()
                    results.append(f"[Danbooru 24h Velocity]: {clean_name} (Свежих артов: {count})")
    except Exception:
        pass
    return results

def fetch_pixiv_daily_rss():
    # Рекомендуется заменить rsshub.app на свой self-hosted инстанс для стабильности
    url = "https://rsshub.app/pixiv/ranking/day"
    results = []
    try:
        res = requests.get(url, timeout=5)
        for entry in feedparser.parse(res.content).entries[:15]:
            results.append(f"[Pixiv Daily Top]: {entry.title}")
    except Exception:
        pass
    return results

def fetch_reddit_velocity():
    """Сбор Reddit через Hot/Rising с расчетом Velocity (Upvotes per Hour)"""
    subs = [
        "Genshin_Impact_Leaks", "HonkaiStarRail_Leaks", "Zenlesszonezero_leaks_", 
        "WutheringWavesLeaks", "NikkeMobile", "BlueArchive", "Snowbreak", "gaming"
    ]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) HypeRadar/5.0'}
    current_time = time.time()
    
    for sub in subs:
        try:
            # Используем rising/hot для перехвата тренда на взлете
            res = requests.get(f"https://www.reddit.com/r/{sub}/hot.json?limit=15", headers=headers, timeout=4)
            if res.status_code == 200:
                for p in res.json().get('data', {}).get('children', []):
                    data = p.get('data', {})
                    title = data.get('title', '')
                    ups = data.get('ups', 0)
                    created_utc = data.get('created_utc', current_time)
                    
                    age_hours = max((current_time - created_utc) / 3600, 0.5)
                    velocity = ups / age_hours
                    
                    if velocity > 10 and age_hours < 48: 
                        results.append(f"[Reddit r/{sub} Velocity (+{int(velocity)} upv/hr)]: {title}")
        except Exception:
            continue
    return results

def fetch_bilibili_hot():
    """Азиатский первоисточник трендов"""
    url = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
    results = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json().get('data', {}).get('list', [])[:15]
            for item in data:
                title = item.get('title', '')
                # Фильтруем игровой контент по ключевикам
                if any(kw in title for kw in ['原神', '星穹铁道', '绝区零', '崩坏', '鸣潮']):
                    results.append(f"[Bilibili Hot Trend]: {title}")
    except:
        pass
    return results

def fetch_nexusmods_trending(api_key):
    """Анализ Spicy-модов и реплейсеров"""
    if not api_key: return []
    games = ["cyberpunk2077", "residentevil42023", "baldursgate3", "monsterhunterworld", "streetfighter6"]
    results = []
    headers = {"accept": "application/json", "apikey": api_key}
    
    for game in games:
        try:
            res = requests.get(f"https://api.nexusmods.com/v1/games/{game}/mods/trending.json", headers=headers, timeout=5)
            if res.status_code == 200:
                for mod in res.json()[:3]:
                    results.append(f"[NexusMods {game} Trending]: {mod.get('name')} - {mod.get('summary', '')}")
        except:
            continue
    return results

def fetch_youtube_targeted(api_key):
    if not api_key: return []
    time_limit = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
    dynamic_games = get_dynamic_trending_games()
    query_str = " OR ".join(dynamic_games[:6]) # Берем топ-6 игр для запроса
    
    params = {
        "part": "snippet",
        "q": f"({query_str}) (trailer OR drip marketing OR teaser OR demo OR female character)",
        "type": "video",
        "videoCategoryId": "20",
        "publishedAfter": time_limit,
        "maxResults": 15,
        "key": api_key
    }
    results = []
    try:
        res = requests.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=5)
        if res.status_code == 200:
            for item in res.json().get('items', []):
                results.append(f"[YouTube Gaming]: {item['snippet']['title']}")
    except:
        pass
    return results

def fetch_bluesky_art():
    queries = ["waifu fanart", "character leak splash", "drip marketing female", "new skin girl", "3dart character"]
    results = []
    for q in queries:
        try:
            res = requests.get(f"https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q={q}&limit=5", timeout=4)
            if res.status_code == 200:
                for p in res.json().get('posts', []):
                    text = p.get('record', {}).get('text', '').replace('\n', ' ')[:120]
                    likes = p.get('likeCount', 0)
                    if likes > 10:
                        results.append(f"[Bluesky (+{likes}❤️)]: {text}")
        except:
            pass
    return results

# ==========================================
# ИИ-АНАЛИЗАТОР 
# ==========================================

def get_pro_gemini_models(api_key):
    pro_models = []
    flash_models = []
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            for m in res.json().get('models', []):
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    name = m.get('name', '').replace('models/', '')
                    if 'lite' in name.lower(): continue
                    if 'pro' in name.lower(): pro_models.append(name)
                    elif 'flash' in name.lower(): flash_models.append(name)
    except:
        pass

    ordered_models = pro_models + flash_models
    fallback = ["gemini-2.5-pro", "gemini-1.5-pro", "gemini-2.5-flash"]
    for f in fallback:
        if f not in ordered_models: ordered_models.append(f)
    return ordered_models

def analyze_cross_platform_feed(feed_dump, key, nsfw_enabled):
    models_to_try = get_pro_gemini_models(key)
    current_date = datetime.now().strftime("%Y-%m-%d")
    spicy_instruction = 'В массив "spicy_top" добавь от 5 до 10 ЖЕНСКИХ персонажей (особенно из NexusMods или Danbooru), сделав акцент на анатомии, фансервисных скинах и материалах для 3D.' if nsfw_enabled else 'Массив "spicy_top" оставь пустым.'

    prompt = f"""
    ТЫ — ГЛАВНЫЙ АРТ-ДИРЕКТОР И 3D-ЛИД. Твоя цель — проанализировать сырые данные и выдать точный список ТОЛЬКО ЖЕНСКИХ персонажей видеоигр.
    Данные будут использованы для создания 3D-моделей в Blender, настройки шейдеров/материалов в Unity 2022.3 LTS и последующей продажи/публикации на 15+ площадках. 
    Сегодня {current_date}.

    ВХОДНЫЕ СИГНАЛЫ (Velocity Danbooru, Reddit, Bilibili, NexusMods, YouTube):
    {json.dumps(feed_dump, ensure_ascii=False)}

    ЖЕЛЕЗНЫЕ ПРАВИЛА:
    1. ИСКЛЮЧИТЕЛЬНО ЖЕНСКИЕ ПЕРСОНАЖИ.
    2. Обосновывай популярность СТРОГО на основе входных сигналов. 
    3. ПРАКТИЧЕСКИЕ ВИЗУАЛЬНЫЕ ХУКИ (visual_hook):
       - Дай конкретные советы для 3D-скульпта, правильной топологии, работы с UV, настройки материалов в Eevee/Cycles или Unity (например, как избежать артефактов при запекании normal map для сложных тканей/fabric, как избежать Z-fighting на многослойной одежде).
    4. СПЕЦИФИКА RU/СНГ РЫНКА:
       - В блоке "ru_top" укажи персонажей, которые будут отлично продаваться на площадках, доступных из РФ (где можно регистрироваться без привязки крипто/иностранных кошельков, например Boosty, 3D Sky, VK Play и др.).
    {spicy_instruction}

    ВЕРНИ ОТВЕТ СТРОГО В ВИДЕ ВАЛИДНОГО JSON СЛЕДУЮЩЕЙ СТРУКТУРЫ:
    {{
      "absolute_leader": {{
        "name": "Имя героини",
        "game": "Игра",
        "virality_score": 99,
        "past_72h_event": "Точный факт/инфоповод",
        "source_signal": "Точная строка из логов",
        "upcoming_catalyst": "Что подогреет интерес",
        "visual_hook": "Детали для Blender (Eevee/Cycles), UV, запекания Normal Map без багов",
        "why_draw_today": "Почему это сработает на 15+ площадках",
        "tags": ["3dart", "blender", "unity"]
      }},
      "spicy_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "analysis": "Причина", "visual_hook": "Хук для 3D", "source_signal": "Источник", "score": 96, "tags": ["spicy"] }}
      ],
      "world_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "analysis": "Причина", "source_signal": "Источник", "score": 97, "tags": ["trend"] }}
      ],
      "ru_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "analysis": "Потенциал монетизации в РФ (Boosty, 3D Sky и т.д.)", "source_signal": "Источник", "score": 94, "tags": ["ru_fav"] }}
      ],
      "gacha_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "score": 98, "reach": 96, "likes": 97, "visual_hook": "Специфика Unity 2022.3 LTS", "source_signal": "Строка из логов", "reason": "Лик/Баннер", "trend": "🔥" }}
      ],
      "classic_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "score": 95, "reach": 91, "likes": 93, "visual_hook": "Шейдеры кожи / ткани", "source_signal": "Культ", "reason": "Культ/Скин", "trend": "📈" }}
      ]
    }}
    """

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}
    }

    last_err = ""
    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
            resp = requests.post(url, headers=headers, json=payload, timeout=75)
            
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match: return json.loads(json_match.group()), model_name
                else: return json.loads(raw_text), model_name
            else:
                last_err = f"[{model_name}] {resp.status_code}"
        except Exception as e:
            last_err = str(e)
            continue

    raise RuntimeError(f"Сбой Gemini API: {last_err}")

def run_full_scan():
    collected_feed = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(fetch_danbooru_velocity),
            executor.submit(fetch_reddit_velocity),
            executor.submit(fetch_bilibili_hot),
            executor.submit(fetch_nexusmods_trending, nexus_key),
            executor.submit(fetch_bluesky_art),
            executor.submit(fetch_youtube_targeted, youtube_key),
            executor.submit(fetch_pixiv_daily_rss)
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

    @bot.message_handler(commands=['scan'])
    def handle_scan(message):
        bot.reply_to(message, "📡 Собираю Velocity-сигналы и запускаю пайплайн (Blender/Unity)...")
        try:
            (ai_res, model), _ = run_full_scan()
            leader = ai_res.get('absolute_leader', {})
            msg = f"👑 *ТОП ЖЕНСКИЙ ПЕРСОНАЖ:*
*{leader.get('name', 'N/A')}* ({leader.get('game', 'N/A')})
"
            msg += f"🎯 *Визуальный хук (3D):* {leader.get('visual_hook', 'N/A')}
"
            msg += f"📌 *Инфоповод:* {leader.get('past_72h_event', 'N/A')}
"
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    return bot

start_telegram_bot(tg_bot_token)

# ==========================================
# ИНТЕРФЕЙС STREAMLIT
# ==========================================
if st.button("🚀 Запустить Velocity Scan (Blender & Unity Pipeline)", type="primary", use_container_width=True):
    if not gemini_key:
        st.error("⚠️ Добавьте GEMINI_API_KEY в Secrets.")
    else:
        status_container = st.status("📡 Сбор Velocity-сигналов и метрик ускорения...", expanded=True)
        try:
            status_container.write("1. Замеряем Velocity (ускорение публикаций) на Reddit и Danbooru...")
            status_container.write("2. Сканируем китайские тренды (Bilibili)...")
            status_container.write("3. Проверяем новые откровенные моды на NexusMods...")
            status_container.write("4. Синтез архитектуры мешей и шейдеров через Gemini AI...")
            
            (ai_results, used_model), raw_feed = run_full_scan()
            
            st.session_state.update({
                'omni_results': ai_results,
                'raw_feed': raw_feed,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'scan_done': True
            })
            status_container.update(label=f"Успешно! (Модель: {used_model})", state="complete", expanded=False)
        except Exception as e:
            status_container.update(label="Ошибка", state="error", expanded=True)
            st.error(e)

if st.session_state.get('scan_done', False):
    res = st.session_state['omni_results']
    st.caption(f"⏱️ **Данные собраны:** {st.session_state['timestamp']}")
    
    leader = res.get('absolute_leader', {})
    if leader:
        tags_html = " ".join([f"<span class='badge'>#{t}</span>" for t in leader.get('tags', [])])
        st.markdown(f"""
<div class="hero-card">
<div style="text-transform: uppercase; letter-spacing: 2px; font-size: 12px; margin-bottom: 6px; color: #fbbf24;">👑 Главный объект внимания аудитории</div>
<div class="hero-title">{leader.get('name', 'Нет данных')} <span style="font-size:20px; font-weight:400; opacity:0.85; color:#cbd5e1;">— {leader.get('game', 'Нет данных')}</span></div>
<div style="font-size: 15px; margin: 4px 0 10px 0;">Индекс виральности: <b>{leader.get('virality_score', 0)}/100</b></div>
<div class="fact-box">🎨 <b>3D Pipeline (Blender/Unity):</b> {leader.get('visual_hook', 'Особые детали')}</div>
<div class="fact-box">📡 <b>Сигнал:</b> {leader.get('source_signal', 'Отсутствует')}</div>
<div class="catalyst-box">💡 <b>Стратегия дистрибуции (15+ площадок):</b> {leader.get('why_draw_today', 'Пик внимания к персонажу')}</div>
<div style="margin-top: 14px;">{tags_html}</div>
</div>
        """, unsafe_allow_html=True)

    medals, classes = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"], ["top1", "top2", "top3", "", "", "", "", ""]
    
    if is_16_plus and res.get('spicy_top'):
        st.subheader("🔞 Тренды 16+ (NexusMods / Фансервис)")
        spicy_items = res.get('spicy_top', [])
        spicy_cols = st.columns(min(3, len(spicy_items)))
        for idx, item in enumerate(spicy_items[:3]):
            with spicy_cols[idx]:
                st.markdown(f"""
<div class="spicy-card">
<h4 style="margin-bottom: 5px; color: #ff9ebf;">{medals[idx]} {item.get('name', '')} <span style="font-size:13px; color:#a5b1c2;">({item.get('game', '')})</span></h4>
<p style="font-size: 13px; color: #f1f5f9; margin-bottom: 6px;"><b>Сигнал:</b> {item.get('source_signal', '')}</p>
<p style="font-size: 12px; color: #f472b6; margin-bottom: 8px;">👙 <b>Хук для 3D:</b> {item.get('visual_hook', '')}</p>
<div>{" ".join([f"<span class='badge spicy-badge'>#{t}</span>" for t in item.get('tags', [])])}</div>
</div>
                """, unsafe_allow_html=True)
        st.divider()

    col_w, col_r = st.columns(2)
    with col_w:
        st.subheader("🌍 Мировой фокус (Топ-5)")
        for idx, item in enumerate(res.get('world_top', [])[:5]):
            st.markdown(f"""
<div class="metric-card {classes[idx]}">
<h4 style="margin-bottom: 4px;">{medals[idx]} {item.get('name', '')} <span style="font-size:13px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 12px; color: #64748b; margin-bottom: 4px;">📡 {item.get('source_signal', '')}</p>
<p style="font-size: 13px; color: #cbd5e1; margin: 0;">{item.get('analysis', '')}</p>
</div>
            """, unsafe_allow_html=True)

    with col_r:
        st.subheader("🇷🇺 СНГ рынок (Под площадки без крипто-регистрации)")
        for idx, item in enumerate(res.get('ru_top', [])[:5]):
            st.markdown(f"""
<div class="metric-card {classes[idx]}">
<h4 style="margin-bottom: 4px;">{medals[idx]} {item.get('name', '')} <span style="font-size:13px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 12px; color: #64748b; margin-bottom: 4px;">📡 {item.get('source_signal', '')}</p>
<p style="font-size: 13px; color: #cbd5e1; margin: 0;">{item.get('analysis', '')}</p>
</div>
            """, unsafe_allow_html=True)

    with st.expander("🔍 Посмотреть собранный сырой поток первоисточников"):
        st.write(st.session_state.get('raw_feed', []))
