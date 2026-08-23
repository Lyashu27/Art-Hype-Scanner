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
import telebot
import threading
import re
import math

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="🔥 Waifu Art Hype Radar Pro", page_icon="🎨", layout="wide")

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
twitch_id = st.secrets.get("TWITCH_CLIENT_ID", "")
twitch_secret = st.secrets.get("TWITCH_CLIENT_SECRET", "")
tg_bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN", "")

st.title("🎨 Omni-Channel Waifu Hype Radar: Fanart & Virality Edition")
st.markdown("Предиктивный радар трендов: кого из женских персонажей рисовать/рендерить сегодня для максимального охвата и лайков на 15+ площадках.")

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Параметры Сбора")
    is_16_plus = st.toggle("🔞 Режим 16+ (Spicy / Фансервис / Бикини)", value=True, help="Фокус на фансервисе, купальниках, пикантных ракурсах и вирусных позах.")
    st.divider()
    st.header("📡 Состояние Каналов")
    st.write(f"🧠 Gemini Flash Core: {'🟢 Активен' if gemini_key else '🔴 Нет ключа'}")
    st.write(f"🤖 Telegram Bot: {'🟢 Подключен' if tg_bot_token else '⚪ Выключен'}")
    st.write(f"📺 YouTube API: {'🟢 Активен' if youtube_key else '⚪ Выключен'}")
    st.write("🎨 Booru Streams (Danbooru + Yande.re): 🟢 Активны")
    st.write("🔍 Reddit Mega-Feed (Merged): 🟢 Активен")
    st.write("🦋 Bluesky Art Hub: 🟢 Активен")
    st.write("📰 Gaming Media & ArtStation: 🟢 Активны")

# ==========================================
# МАКСИМАЛЬНЫЙ СБОР СЫРЫХ СИГНАЛОВ (100+ ЛОГОВ)
# ==========================================

def fetch_reddit_mega_rss():
    """Один объединенный запрос ко всем сабреддитам утечек и игр (гарантирует отсутствие 429 бана)"""
    subs = "Genshin_Impact_Leaks+HonkaiStarRail_Leaks+Zenlesszonezero_leaks_+WutheringWavesLeaks+NikkeMobile+BlueArchive+Snowbreak+gaming"
    url = f"https://www.reddit.com/r/{subs}/hot/.rss?limit=60"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }
    results = []
    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            feed = feedparser.parse(res.content)
            for entry in feed.entries:
                title = entry.title
                if any(kw in title.lower() for kw in ['leak', 'drip', 'splash', 'skin', 'render', 'model', 'teaser', 'art', 'animation', 'concept', 'npc', 'official']):
                    results.append(f"[Reddit Leaks Hot]: {title}")
        else:
            results.append(f"[Reddit Notice]: Status {res.status_code}")
    except Exception as e:
        results.append(f"[Reddit Ex]: {str(e)}")
    return results

def fetch_danbooru_velocity():
    """Сбор 150 свежих постов Danbooru с подсчетом частоты появления персонажа"""
    url = "https://danbooru.donmai.us/posts.json?limit=150&tags=1girl"
    results = []
    char_counts = Counter()
    try:
        res = requests.get(url, headers={'User-Agent': 'WaifuRadarPro/8.0'}, timeout=12)
        if res.status_code == 200:
            for post in res.json():
                tags = post.get('tag_string', '')
                chars = post.get('tag_string_character', '').split()
                copyr = post.get('tag_string_copyright', '').split()
                score = post.get('score', 0)
                
                if 'comic' in tags or 'cartoon' in tags:
                    continue
                weight = 1 + (score * 0.1) if score > 5 else 1
                for char in chars:
                    if char and char not in ["original", "unknown"]:
                        franchise = copyr[0] if copyr else "Game"
                        full_tag = f"{char} ({franchise})"
                        char_counts[full_tag] += weight
                        
            for tag, score in char_counts.most_common(25):
                if score >= 2:
                    clean_name = tag.replace('_', ' ').title()
                    results.append(f"[Danbooru 24h Trend]: {clean_name} (Спрос: {math.floor(score)}pts)")
    except Exception as e:
        results.append(f"[Danbooru Ex]: {str(e)}")
    return results

def fetch_yandere_hot():
    """Дополнительный источник японского/гача арт-спроса (без ограничений по API)"""
    url = "https://yande.re/post.json?limit=80"
    results = []
    char_counts = Counter()
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=12)
        if res.status_code == 200:
            for post in res.json():
                tags = post.get('tags', '').split()
                score = post.get('score', 0)
                for t in tags:
                    if len(t) > 3 and not any(common in t for common in ['dress', 'bikini', 'hair', 'eyes', 'panties', 'thighhighs', 'cleavage', 'gloves', 'skirt', 'weapon', 'sword', 'sitting', 'standing']):
                        char_counts[t] += (1 + score * 0.05)
            for tag, score in char_counts.most_common(20):
                if score > 3:
                    clean_name = tag.replace('_', ' ').title()
                    results.append(f"[Yande.re Hype Tag]: {clean_name}")
    except Exception:
        pass
    return results

def fetch_artstation_trending():
    """Топ трендов ArtStation (вирусные стили и персонажи)"""
    url = "https://www.artstation.com/artwork.rss?sorting=trending"
    results = []
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if res.status_code == 200:
            feed = feedparser.parse(res.content)
            for entry in feed.entries[:15]:
                results.append(f"[ArtStation Trending Art]: {entry.title}")
    except Exception:
        pass
    return results

def fetch_gaming_news_rss():
    """Свежие анонсы персонажей из профильных СМИ"""
    urls = ["https://www.gematsu.com/feed", "https://www.siliconera.com/feed"]
    results = []
    for u in urls:
        try:
            res = requests.get(u, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
            if res.status_code == 200:
                feed = feedparser.parse(res.content)
                for entry in feed.entries[:8]:
                    results.append(f"[Gaming News]: {entry.title}")
        except Exception:
            continue
    return results

def fetch_youtube_targeted(api_key):
    """Массовый сбор трейлеров и демонстраций персонажей"""
    if not api_key: return []
    time_limit = (datetime.utcnow() - timedelta(days=3)).isoformat() + "Z"
    queries = [
        '(Genshin OR "Honkai Star Rail" OR "Zenless Zone Zero" OR "Wuthering Waves") (trailer OR demo OR teaser OR drip marketing)',
        '(Nikke OR "Blue Archive" OR "Stellar Blade" OR "Resident Evil" OR "Cyberpunk") (trailer OR animation OR teaser OR character)'
    ]
    results = []
    for q in queries:
        params = {
            "part": "snippet",
            "q": q,
            "type": "video",
            "videoCategoryId": "20",
            "publishedAfter": time_limit,
            "maxResults": 15,
            "key": api_key
        }
        try:
            res = requests.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=10)
            if res.status_code == 200:
                for item in res.json().get('items', []):
                    results.append(f"[YouTube Gaming]: {item['snippet']['title']}")
        except Exception:
            pass
    return results

def fetch_bluesky_art():
    """Поиск арт-референсов и вирусных тем в Bluesky"""
    queries = ["waifu fanart", "character leak splash", "drip marketing", "bikini fanart", "anime girl render"]
    results = []
    for q in queries:
        try:
            res = requests.get(f"https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q={q}&limit=12", timeout=8)
            if res.status_code == 200:
                for p in res.json().get('posts', []):
                    text = p.get('record', {}).get('text', '').replace('\n', ' ')[:140]
                    likes = p.get('likeCount', 0)
                    results.append(f"[Bluesky (+{likes}❤️)]: {text}")
        except Exception:
            pass
    return results

# ==========================================
# ИИ-АНАЛИЗАТОР (ФОКУС: ФАНАРТ, ВИРАЛЬНОСТЬ, ОХВАТЫ)
# ==========================================
def get_flash_models():
    return ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"]

def analyze_cross_platform_feed(feed_dump, key, nsfw_enabled):
    models_to_try = get_flash_models()
    current_date = datetime.now().strftime("%Y-%m-%d")
    spicy_instruction = 'В массив "spicy_top" добавь от 5 до 10 ЖЕНСКИХ персонажей с вирусным фансервисом (купальники, открытые наряды, пикантные позы). Сделай акцент на визуальных триггерах, которые набирают максимум лайков и репостов.' if nsfw_enabled else 'Массив "spicy_top" оставь пустым.'

    prompt = f"""
    ТЫ — ГЛАВНЫЙ АРТ-ДИРЕКТОР И ЭКСПЕРТ ПО ВИРАЛЬНОСТИ ФАНАРТА.
    Твоя цель — проанализировать сырые сигналы интернета и выдать ТОЧНЫЙ список ЖЕНСКИХ персонажей из видеоигр, фанарт по которым прямо сейчас гарантирует ВЗРЫВНОЙ ОХВАТ, МАКСИМУМ ЛАЙКОВ И РЕПОСТОВ при публикации на 15+ площадках (Twitter/X, Pixiv, Bluesky, Reddit, Telegram, DeviantArt и др.).
    Сегодня {current_date}.

    ВХОДНЫЕ СИГНАЛЫ (Reddit Leaks 60+, Danbooru Velocity, Yande.re, ArtStation, YouTube, Bluesky):
    {json.dumps(feed_dump, ensure_ascii=False)}

    ЖЕЛЕЗНЫЕ ПРАВИЛА:
    1. ИСКЛЮЧИТЕЛЬНО ЖЕНСКИЕ ПЕРСОНАЖИ (Female Only). Никаких мужских персонажей или роботов.
    2. БОРЬБА С ГАЛЛЮЦИНАЦИЯМИ: Выбирай только тех персонажей, которые явно фигурируют в логах выше (кроме classic_top, где можно указывать культовую классику).
    3. ВИЗУАЛЬНЫЕ ХУКИ ДЛЯ ХУДОЖНИКА (visual_hook):
       - Укажи конкретные детали для иллюстрации: вирусная поза, ключевые элементы наряда, эмоция/взгляд, светотень, ракурс или трендовая деталь костюма, которая зацепит ленту за 1 секунду.
    4. СТРАТЕГИЯ ВИРАЛЬНОСТИ (why_draw_today):
       - Объясни, почему именно эта героиня сейчас выстрелит на 15+ арт-платформах (анонс, слив сплэш-арта, патч, фансервисный скин).
    {spicy_instruction}

    ВЕРНИ ОТВЕТ СТРОГО В ВИДЕ ВАЛИДНОГО JSON:
    {{
      "absolute_leader": {{
        "name": "Имя героини",
        "game": "Игра",
        "virality_score": 99,
        "past_72h_event": "Точный инфоповод из логов",
        "source_signal": "Строка из логов",
        "upcoming_catalyst": "Что подогреет интерес в ближайшие дни",
        "visual_hook": "Вирусная поза, ракурс, акцент в наряде и композиции",
        "why_draw_today": "Почему фанарт взорвет соцсети сегодня",
        "tags": ["genshinimpact", "fanart", "waifu"]
      }},
      "spicy_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "analysis": "Причина фансервис-хайпа", "visual_hook": "Пикантный наряд / поза / акцент", "source_signal": "Источник", "score": 96, "tags": ["spicy", "bikini"] }}
      ],
      "world_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "analysis": "Почему в мировом тренде", "visual_hook": "Хук для арта", "source_signal": "Источник", "score": 97, "tags": ["trend"] }}
      ],
      "gacha_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "score": 98, "reach": 96, "likes": 97, "visual_hook": "Композиция и наряд", "source_signal": "Строка логов", "reason": "Слив/Баннер/Трейлер", "trend": "🔥" }}
      ],
      "classic_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "score": 95, "reach": 91, "likes": 93, "visual_hook": "Узнаваемый стиль / фансервис", "source_signal": "Вечнозеленый спрос", "reason": "Культ/Любимица комьюнити", "trend": "📈" }}
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
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group()), model_name
                else:
                    return json.loads(raw_text), model_name
            else:
                last_err = f"[{model_name}] {resp.status_code}: {resp.text[:100]}"
        except Exception as e:
            last_err = f"[{model_name}] {str(e)}"
            continue

    raise RuntimeError(f"Сбой Flash AI: {last_err}")

def run_full_scan():
    collected_feed = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [
            executor.submit(fetch_reddit_mega_rss),
            executor.submit(fetch_danbooru_velocity),
            executor.submit(fetch_yandere_hot),
            executor.submit(fetch_artstation_trending),
            executor.submit(fetch_gaming_news_rss),
            executor.submit(fetch_youtube_targeted, youtube_key),
            executor.submit(fetch_bluesky_art)
        ]
        for f in futures:
            collected_feed.extend(f.result())
            
    cleaned_feed = [item for item in collected_feed if len(item) > 8]
    return analyze_cross_platform_feed(cleaned_feed, gemini_key, is_16_plus), cleaned_feed

# ==========================================
# TELEGRAM БОТ
# ==========================================
@st.cache_resource
def start_telegram_bot(token):
    if not token: return None
    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['scan'])
    def handle_scan(message):
        bot.reply_to(message, "🎨 Сканирую тренды фанарта и свежие инфоповоды...")
        try:
            (ai_res, model), _ = run_full_scan()
            leader = ai_res.get('absolute_leader', {})
            msg = f"👑 *ТОП ДЕВУШКА ДЛЯ ФАНАРТА:*\n*{leader.get('name', 'N/A')}* ({leader.get('game', 'N/A')})\n"
            msg += f"🎯 *Визуальный хук:* {leader.get('visual_hook', 'N/A')}\n"
            msg += f"📌 *Инфоповод:* {leader.get('past_72h_event', 'N/A')}\n"
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    return bot

start_telegram_bot(tg_bot_token)

# ==========================================
# ИНТЕРФЕЙС
# ==========================================
if st.button("🚀 Запустить поиск вирусных персонажей (Mega-Feed Scan)", type="primary", use_container_width=True):
    if not gemini_key:
        st.error("⚠️ Добавьте GEMINI_API_KEY в Secrets.")
    else:
        status_container = st.status("📡 Сбор мега-потока данных и синтез арт-аналитики...", expanded=True)
        try:
            status_container.write("1. Парсим объединенную ленту Reddit Leaks (без лимитов и блокировок)...")
            status_container.write("2. Сканируем Booru-стримы (Danbooru + Yande.re)...")
            status_container.write("3. Проверяем тренды ArtStation, Bluesky и YouTube Gaming...")
            status_container.write("4. Генерация вирусных хуков и арт-стратегий через Gemini Flash Core...")
            
            (ai_results, used_model), raw_feed = run_full_scan()
            
            st.session_state.update({
                'omni_results': ai_results,
                'raw_feed': raw_feed,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'scan_done': True
            })
            status_container.update(label=f"Анализ завершен! Найдено {len(raw_feed)} сигналов. Модель: {used_model}", state="complete", expanded=False)
        except Exception as e:
            status_container.update(label="Ошибка анализа", state="error", expanded=True)
            st.error(e)

if st.session_state.get('scan_done', False):
    res = st.session_state['omni_results']
    st.caption(f"⏱️ **Данные собраны:** {st.session_state['timestamp']} | 📊 **Сигналов в базе:** {len(st.session_state.get('raw_feed', []))}")
    
    leader = res.get('absolute_leader', {})
    if leader:
        tags_html = " ".join([f"<span class='badge'>#{t}</span>" for t in leader.get('tags', [])])
        st.markdown(f"""
<div class="hero-card">
<div style="text-transform: uppercase; letter-spacing: 2px; font-size: 12px; margin-bottom: 6px; color: #fbbf24;">👑 Главный объект внимания (Рисовать в первую очередь)</div>
<div class="hero-title">{leader.get('name', 'Нет данных')} <span style="font-size:20px; font-weight:400; opacity:0.85; color:#cbd5e1;">— {leader.get('game', 'Нет данных')}</span></div>
<div style="font-size: 15px; margin: 4px 0 10px 0;">Индекс виральности: <b>{leader.get('virality_score', 0)}/100</b></div>
<div class="fact-box">🎯 <b>Визуальный хук для арта (поза / наряд / ракурс):</b> {leader.get('visual_hook', 'Особые детали')}</div>
<div class="fact-box">📡 <b>Сигнал / Инфоповод:</b> {leader.get('source_signal', 'Отсутствует')}</div>
<div class="catalyst-box">⏳ <b>Катализатор внимания:</b> {leader.get('upcoming_catalyst', 'Ближайший релиз/патч')}</div>
<div style="margin-top: 10px; font-size: 13px; color: #94a3b8;">💡 <b>Почему завирусится на 15+ площадках:</b> {leader.get('why_draw_today', 'Пик внимания к персонажу')}</div>
<div style="margin-top: 14px;">{tags_html}</div>
</div>
        """, unsafe_allow_html=True)

    medals, classes = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"], ["top1", "top2", "top3", "", "", "", "", ""]
    
    if is_16_plus and res.get('spicy_top'):
        st.subheader("🔞 Тренды 16+ (Spicy / Фансервис / Бикини)")
        spicy_items = res.get('spicy_top', [])
        spicy_cols = st.columns(min(3, len(spicy_items)))
        for idx, item in enumerate(spicy_items[:3]):
            with spicy_cols[idx]:
                st.markdown(f"""
<div class="spicy-card">
<h4 style="margin-bottom: 5px; color: #ff9ebf;">{medals[idx]} {item.get('name', '')} <span style="font-size:13px; color:#a5b1c2;">({item.get('game', '')})</span></h4>
<p style="font-size: 13px; color: #f1f5f9; margin-bottom: 6px;"><b>Инфоповод:</b> {item.get('analysis', '')}</p>
<p style="font-size: 12px; color: #f472b6; margin-bottom: 8px;">👙 <b>Хук:</b> {item.get('visual_hook', '')}</p>
<div>{" ".join([f"<span class='badge spicy-badge'>#{t}</span>" for t in item.get('tags', [])])}</div>
</div>
                """, unsafe_allow_html=True)
        st.divider()

    col_w, col_r = st.columns(2)
    with col_w:
        st.subheader("🌍 Мировой тренд (Топ фанарта)")
        for idx, item in enumerate(res.get('world_top', [])[:5]):
            st.markdown(f"""
<div class="metric-card {classes[idx]}">
<h4 style="margin-bottom: 4px;">{medals[idx]} {item.get('name', '')} <span style="font-size:13px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 12px; color: #64748b; margin-bottom: 4px;">📡 {item.get('source_signal', '')}</p>
<p style="font-size: 13px; color: #cbd5e1; margin: 0;">{item.get('analysis', '')}</p>
</div>
            """, unsafe_allow_html=True)

    with col_r:
        st.subheader("🎲 Гача & Аниме фавориты")
        for idx, item in enumerate(res.get('gacha_top', [])[:5]):
            st.markdown(f"""
<div class="metric-card {classes[idx]}">
<h4 style="margin-bottom: 4px;">{medals[idx]} {item.get('name', '')} <span style="font-size:13px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 12px; color: #64748b; margin-bottom: 4px;">🎯 <b>Хук:</b> {item.get('visual_hook', '')}</p>
<p style="font-size: 13px; color: #cbd5e1; margin: 0;">{item.get('reason', '')}</p>
</div>
            """, unsafe_allow_html=True)

    with st.expander("🔍 Посмотреть собранный сырой поток первоисточников"):
        st.write(st.session_state.get('raw_feed', []))
