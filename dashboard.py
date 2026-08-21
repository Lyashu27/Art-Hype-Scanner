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

st.title("🔥 Omni-Channel Art Hype Radar: Female Characters Edition")
st.markdown("Предиктивный радар виральности женских персонажей из игр на базе первоисточников.")

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Параметры Сбора")
    is_16_plus = st.toggle("🔞 Режим 16+ (Spicy / Фансервис / Моды)", value=True, help="Фокус на купальниках, откровенных скинах, модах и фансервисных триггерах.")
    st.divider()
    st.header("📡 Состояние Каналов")
    st.write(f"🧠 Gemini Core: {'🟢 Активен (Pro Prioritized)' if gemini_key else '🔴 Нет ключа'}")
    st.write(f"🤖 Telegram Bot: {'🟢 Подключен' if tg_bot_token else '⚪ Выключен'}")
    st.write(f"🎨 Danbooru (1girl 72h): 🟢 Активен")
    st.write(f"🔍 Reddit Leaks Hubs: 🟢 Активен")
    st.write(f"🦋 Bluesky Stream: 🟢 Активен")
    st.write(f"📺 YouTube API: {'🟢 Активен' if youtube_key else '⚪ Выключен'}")
    st.write(f"🎮 Steam & Twitch: {'🟢 Подключены' if (steam_key or twitch_id) else '🟡 Базовый режим'}")

# ==========================================
# СБОР ДАННЫХ ИЗ ПЕРВОИСТОЧНИКОВ
# ==========================================

def fetch_danbooru_hot_72h():
    """Сбор взрывных женских персонажей по тегам за последние 72 часа"""
    url = "https://danbooru.donmai.us/posts.json?limit=60&tags=age:<3d+1girl+order:score"
    results = []
    char_counts = Counter()
    try:
        res = requests.get(url, headers={'User-Agent': 'HypeRadarPro/3.0'}, timeout=5)
        if res.status_code == 200:
            for post in res.json():
                chars = post.get('tag_string_character', '').split()
                score = post.get('score', 0)
                for char in chars:
                    if char and char not in ["original", "unknown", "comic"]:
                        char_counts[char] += (score + 2)
            for char, weight in char_counts.most_common(25):
                clean_name = char.replace('_', ' ').title()
                results.append(f"[Danbooru 72h Female Momentum (+{weight}pts)]: {clean_name}")
    except Exception:
        pass
    return results

def fetch_reddit_leaks_and_hubs():
    """Сбор утечек и дрип-маркетинга женских персонажей"""
    subs = [
        ("Genshin_Impact_Leaks", 12),
        ("HonkaiStarRail_Leaks", 12),
        ("Zenlesszonezero_leaks_", 12),
        ("WutheringWavesLeaks", 12),
        ("NikkeMobile", 10),
        ("BlueArchive", 10),
        ("AzurLane", 8),
        ("Snowbreak", 8),
        ("gachagaming", 8),
        ("Overwatch", 8),
        ("LeagueOfLegends", 8)
    ]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
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
    """Поиск виральных артов женских персонажей в Bluesky"""
    queries = ["waifu fanart", "character leak splash", "drip marketing female", "new skin girl", "3dart character"]
    results = []
    for q in queries:
        try:
            res = requests.get(f"https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q={q}&limit=10", timeout=4)
            if res.status_code == 200:
                for p in res.json().get('posts', []):
                    text = p.get('record', {}).get('text', '').replace('\n', ' ')[:120]
                    likes = p.get('likeCount', 0)
                    if likes > 5:
                        results.append(f"[Bluesky (+{likes}❤️)]: {text}")
        except Exception:
            pass
    return results

def fetch_youtube_trailers(api_key):
    if not api_key: return []
    time_limit = (datetime.utcnow() - timedelta(days=4)).isoformat() + "Z"
    params = {
        "part": "snippet",
        "q": "female character trailer OR drip marketing reveal OR banner teaser OR new skin preview",
        "type": "video",
        "publishedAfter": time_limit,
        "maxResults": 15,
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
            for entry in feedparser.parse(res.content).entries[:5]:
                results.append(f"[СМИ]: {entry.title}")
        except Exception:
            continue
    return results

def fetch_steam_twitch(steam_k, c_id, c_secret):
    results = []
    try:
        res_steam = requests.get("https://store.steampowered.com/api/featuredcategories", timeout=4)
        if res_steam.status_code == 200:
            for item in res_steam.json().get('top_sellers', {}).get('items', [])[:6]:
                results.append(f"[Steam Top Seller]: {item.get('name', '')}")
    except Exception:
        pass
    
    if c_id and c_secret:
        try:
            token = requests.post(f"https://id.twitch.tv/oauth2/token?client_id={c_id}&client_secret={c_secret}&grant_type=client_credentials", timeout=4).json().get('access_token', '')
            if token:
                res_twitch = requests.get("https://api.twitch.tv/helix/games/top?first=6", headers={"Client-ID": c_id, "Authorization": f"Bearer {token}"}, timeout=4)
                if res_twitch.status_code == 200:
                    for g in res_twitch.json().get('data', []):
                        results.append(f"[Twitch Top Game]: {g.get('name')}")
        except Exception:
            pass
    return results

# ==========================================
# ИИ-АНАЛИЗАТОР (ВЫБОР PRO-МОДЕЛЕЙ И СТРОГИЙ ПРОМПТ)
# ==========================================

def get_pro_gemini_models(api_key):
    """Выбор лучших Pro моделей без Flash-Lite"""
    pro_models = []
    flash_models = []
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            for m in res.json().get('models', []):
                if 'generateContent' in m.get('supportedGenerationMethods', []):
                    name = m.get('name', '').replace('models/', '')
                    # Исключаем легковесные и урезанные модели
                    if 'lite' in name.lower():
                        continue
                    if 'pro' in name.lower():
                        pro_models.append(name)
                    elif 'flash' in name.lower():
                        flash_models.append(name)
    except Exception:
        pass

    # Приоритет отдаем лучшим Pro-моделям
    ordered_models = pro_models + flash_models
    fallback = [
        "gemini-1.5-pro",
        "gemini-2.5-pro",
        "gemini-2.0-pro-exp-02-05",
        "gemini-1.5-pro-latest",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ]
    for f in fallback:
        if f not in ordered_models:
            ordered_models.append(f)
            
    return ordered_models

def analyze_cross_platform_feed(feed_dump, key, nsfw_enabled):
    models_to_try = get_pro_gemini_models(key)
    current_date = datetime.now().strftime("%Y-%m-%d")
    spicy_instruction = 'В массив "spicy_top" добавь от 6 до 10 ЖЕНСКИХ персонажей с виральным фансервисом, купальниками, модами, чулками или открытыми нарядами.' if nsfw_enabled else 'Массив "spicy_top" оставь пустым.'

    prompt = f"""
    ТЫ — ГЛАВНЫЙ АРТ-АНАЛИТИК И ЛИД-КОНЦЕПТЕР. Твоя цель — выдать максимально точный, объективный и объемный список ЖЕНСКИХ персонажей видеоигр, создание 3D/2D фан-арта по которым сегодня гарантирует максимальный охват и вовлеченность. Сегодня {current_date}.

    ВХОДНЫЕ СВЕЖИЕ СИГНАЛЫ (Danbooru 72h 1girl, Reddit Leaks, Bluesky, YouTube, Steam/Twitch):
    {json.dumps(feed_dump, ensure_ascii=False)}

    ЖЕЛЕЗНЫЕ ПРАВИЛА ФИЛЬТРАЦИИ И ГЕНЕРАЦИИ:
    1. СТРОГО ИСКЛЮЧИТЕЛЬНО ЖЕНСКИЕ ПЕРСОНАЖИ (Female Only).
       - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО включать мужских персонажей (никаких Kratos, Wise, Dante, Aether, FL4K, Zhongli и т.д.).
       - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО включать негуманоидных монстров, роботов без женского гендера и технику.
    2. ОБЪЕМ ВЫБОРКИ (НЕ УРЕЗАТЬ!):
       - "gacha_top": ОБЯЗАТЕЛЬНО сформируй список ровно из 15-20 самых хайповых женских персонажей (Genshin, Honkai Star Rail, Zenless Zone Zero, Wuthering Waves, Nikke, Blue Archive, Azur Lane, Snowbreak, Fate и др.).
       - "classic_top": ОБЯЗАТЕЛЬНО сформируй список ровно из 15-20 самых востребованных женских персонажей из AAA/соревновательных/классических игр (League of Legends, Overwatch, Resident Evil, Final Fantasy, Valorant, NieR, Cyberpunk, Baldur's Gate 3, Tekken, Street Fighter, Stellar Blade и др.).
       - "world_top": ровно 5 женских топ-лидеров.
       - "ru_top": ровно 5 женских фаворитов для СНГ/РФ.
    3. СТРОГАЯ ПРИВЯЗКА К РЕАЛЬНОСТИ:
       - Опирайся на реальные инфоповоды из ленты: свежие утечки внешности (Leaks), дрип-маркетинг, анонсы баннеров, новые скины, бум артов на Danbooru за 72ч.
       - Если для популярного персонажа нет события за 72ч, пиши причину: "Стабильный культовый спрос / фансервис".
    4. ПРАКТИЧЕСКИЕ ВИЗУАЛЬНЫЕ ХУКИ (visual_hook):
       - Для каждой героини укажи точную визуальную зацепку для художника: ракурс, элемент костюма (чулки, вырез, декольте, купальник, мокрый эффект), освещение, оружие или вирусная поза.
    {spicy_instruction}

    ВЕРНИ ОТВЕТ СТРОГО В ВИДЕ ВАЛИДНОГО JSON СЛЕДУЮЩЕЙ СТРУКТУРЫ:
    {{
      "absolute_leader": {{
        "name": "Имя героини",
        "game": "Игра",
        "virality_score": 99,
        "past_72h_event": "Точный факт/инфоповод",
        "upcoming_catalyst": "Что подогреет интерес в ближайшие дни",
        "visual_hook": "Точный визуальный акцент и ракурс для 3D/2D",
        "why_draw_today": "Почему именно она принесет максимальный охват прямо сейчас",
        "tags": ["3dart", "character", "waifu"]
      }},
      "spicy_top": [
        {{ "rank": 1, "name": "Женский персонаж", "game": "Игра", "analysis": "Причина спайси-хайпа", "visual_hook": "Деталь откровенного костюма/позы", "score": 96, "tags": ["spicy", "bikini"] }}
      ],
      "world_top": [
        {{ "rank": 1, "name": "Женский персонаж", "game": "Игра", "analysis": "Причина мирового спроса", "score": 97, "tags": ["trend"] }}
      ],
      "ru_top": [
        {{ "rank": 1, "name": "Женский персонаж", "game": "Игра", "analysis": "Причина популярности в СНГ/РФ", "score": 94, "tags": ["ru_fav"] }}
      ],
      "gacha_top": [
        {{ "rank": 1, "name": "Женский персонаж 1", "game": "Игра", "score": 98, "reach": 96, "likes": 97, "visual_hook": "Визуальный хук", "reason": "Инфоповод/Лик/Баннер", "trend": "🔥" }}
      ],
      "classic_top": [
        {{ "rank": 1, "name": "Женский персонаж 1", "game": "Игра", "score": 95, "reach": 91, "likes": 93, "visual_hook": "Визуальный хук", "reason": "Инфоповод/Культ/Скин", "trend": "📈" }}
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
            resp = requests.post(url, headers=headers, json=payload, timeout=75)
            
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
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

    raise RuntimeError(f"Сбой подключения к Gemini API: {last_err}")

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
        bot.reply_to(message, "⚡ *Hype Radar Bot (Female Characters Edition)*\nКоманда /scan собирает свежие женские тренды из первоисточников.", parse_mode="Markdown")

    @bot.message_handler(commands=['scan'])
    def handle_scan(message):
        bot.reply_to(message, "📡 Сканирую первоисточники и запускаю Pro-анализ женских персонажей...")
        try:
            (ai_res, model), _ = run_full_scan()
            leader = ai_res.get('absolute_leader', {})
            msg = f"👑 *ТОП ЖЕНСКИЙ ПЕРСОНАЖ:*\n*{leader.get('name', 'N/A')}* ({leader.get('game', 'N/A')})\n"
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

if st.button("🚀 Запустить глубокий скан (Female Only / Pro Engine)", type="primary", use_container_width=True):
    if not gemini_key:
        st.error("⚠️ Добавьте GEMINI_API_KEY в Secrets приложения.")
    else:
        status_container = st.status("📡 Сбор сигналов и синтез аналитики...", expanded=True)
        try:
            status_container.write("1. Проверяем Danbooru на женские теги (1girl, 72h momentum)...")
            status_container.write("2. Парсим хабы утечек и анонсов (Genshin, HSR, ZZZ, WuWa, Nikke, BA)...")
            status_container.write("3. Сканируем Bluesky, YouTube трейлеры, Steam/Twitch...")
            status_container.write("4. Подключаем флагманскую модель Gemini Pro и формируем полные списки...")
            
            (ai_results, used_model), raw_feed = run_full_scan()
            
            st.session_state.update({
                'omni_results': ai_results,
                'raw_feed': raw_feed,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'scan_done': True
            })
            status_container.update(label=f"Анализ завершен! Модель: {used_model}", state="complete", expanded=False)
            st.toast("Полный бэклог женских персонажей сформирован!", icon="✨")
        except Exception as e:
            status_container.update(label="Ошибка анализа данных", state="error", expanded=True)
            st.error(f"Детали ошибки: {e}")

# ==========================================
# ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ
# ==========================================

if st.session_state.get('scan_done', False):
    res = st.session_state['omni_results']
    st.caption(f"⏱️ **Данные собраны и верифицированы:** {st.session_state['timestamp']}")
    
    # 1. ГЛАВНАЯ ЦЕЛЬ
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
    medals, classes = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣"], ["top1", "top2", "top3", "", "", ""]
    
    if is_16_plus and res.get('spicy_top'):
        st.subheader("🔞 Тренды 16+ (Spicy / Фансервис / Скины)")
        spicy_items = res.get('spicy_top', [])
        spicy_cols = st.columns(min(3, len(spicy_items)))
        for idx, item in enumerate(spicy_items[:3]):
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
                hover_name="name", text="name", size_max=28, template="plotly_dark",
                title="Гача & Аниме Героини: Карта вовлеченности",
                labels={"reach": "Охват инфоповода (Reddit/Media)", "likes": "Потенциал лайков (Booru/Bluesky)"}
            )
            fig_g.update_traces(textposition='top center', textfont=dict(size=10))
            st.plotly_chart(fig_g, use_container_width=True)

    with col_c2:
        if not df_classic.empty and 'score' in df_classic.columns and 'name' in df_classic.columns:
            fig_c = px.bar(
                df_classic.sort_values('score', ascending=True),
                x='score', y='name', color='likes' if 'likes' in df_classic.columns else None,
                orientation='h', text_auto=True,
                color_continuous_scale='Magma', title="AAA & Классика: Индекс виральности",
                template="plotly_dark", labels={"score": "Индекс хайпа", "name": ""}
            )
            st.plotly_chart(fig_c, use_container_width=True)

    # 5. ПОЛНЫЕ ТАБЛИЦЫ С ВИЗУАЛЬНЫМИ ХУКАМИ
    st.subheader("📋 Практический бэклог для создания артов (Полные списки)")
    col_cfg = {
        "rank": st.column_config.NumberColumn("№", format="%d"),
        "name": "Героиня",
        "game": "Игра",
        "trend": "Тренд",
        "score": st.column_config.ProgressColumn("Хайп", min_value=0, max_value=100),
        "visual_hook": "🎨 Визуальный хук для рендера",
        "reason": "Конкретная причина хайпа / лика",
        "reach": st.column_config.NumberColumn("Reach", format="%d"),
        "likes": st.column_config.NumberColumn("Likes", format="%d")
    }

    t1, t2 = st.columns(2)
    with t1:
        st.markdown(f"<h4 style='color: #4b8bff;'>🎲 Гача-Героини ({len(df_gacha)} персонажей)</h4>", unsafe_allow_html=True)
        if not df_gacha.empty:
            st.dataframe(df_gacha, use_container_width=True, hide_index=True, column_config=col_cfg, height=580)

    with t2:
        st.markdown(f"<h4 style='color: #ff4b4b;'>⚔️ AAA & Классические Героини ({len(df_classic)} персонажей)</h4>", unsafe_allow_html=True)
        if not df_classic.empty:
            st.dataframe(df_classic, use_container_width=True, hide_index=True, column_config=col_cfg, height=580)
            
    # 6. RAW FEED ДЛЯ САМОПРОВЕРКИ
    with st.expander("🔍 Посмотреть собранный сырой поток первоисточников"):
        st.write(st.session_state.get('raw_feed', []))
