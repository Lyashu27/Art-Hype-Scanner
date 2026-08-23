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
st.set_page_config(page_title="🔥 Waifu Art Hype Radar Pro (Massive Data)", page_icon="🎨", layout="wide")

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
tg_bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN", "")

st.title("🎨 Omni-Channel Waifu Hype Radar: Massive Feed Edition")
st.markdown("Предиктивный радар трендов фанарта на базе 300+ первоисточников. Фокус: охваты, виральные позы, фансервис.")

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Параметры Сбора")
    is_16_plus = st.toggle("🔞 Режим 16+ (Spicy / Фансервис / Бикини)", value=True)
    st.divider()
    st.header("📡 Подключенные Каналы")
    st.write(f"⚡ Gemini Flash: {'🟢 Активен' if gemini_key else '🔴 Нет ключа'}")
    st.write(f"🤖 Telegram Bot: {'🟢 Подключен' if tg_bot_token else '⚪ Выключен'}")
    st.write(f"📺 YouTube API: {'🟢 Активен' if youtube_key else '⚪ Выключен'}")
    st.write("🎨 Booru Стримы (Danbooru, Gelbooru, Yande.re, Konachan): 🟢")
    st.write("🔍 Reddit Mega-Feeds (Gacha + AAA/Gaming): 🟢")
    st.write("🦋 Bluesky Deep Search: 🟢")
    st.write("📰 Gaming Media & ArtStation Trending: 🟢")

# ==========================================
# МАКСИМАЛЬНЫЙ СБОР СЫРЫХ СИГНАЛОВ (300+ ЛОГОВ)
# ==========================================

def fetch_danbooru_velocity():
    url = "https://danbooru.donmai.us/posts.json?limit=200&tags=1girl"
    results = []
    char_counts = Counter()
    try:
        res = requests.get(url, headers={'User-Agent': 'WaifuRadarPro/9.0'}, timeout=12)
        if res.status_code == 200:
            for post in res.json():
                tags = post.get('tag_string', '')
                chars = post.get('tag_string_character', '').split()
                copyr = post.get('tag_string_copyright', '').split()
                score = post.get('score', 0)
                if 'comic' in tags or 'cartoon' in tags: continue
                weight = 1 + (score * 0.1) if score > 5 else 1
                for char in chars:
                    if char and char not in ["original", "unknown"]:
                        franchise = copyr[0] if copyr else "Game"
                        char_counts[f"{char} ({franchise})"] += weight
            for tag, score in char_counts.most_common(30):
                if score >= 2:
                    clean = tag.replace('_', ' ').title()
                    results.append(f"[Danbooru 24h Demand]: {clean} (Индекс: {math.floor(score)})")
    except Exception:
        pass
    return results

def fetch_gelbooru_hot():
    url = "https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&limit=100&tags=1girl+sort:score:desc"
    results = []
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=12)
        if res.status_code == 200:
            posts = res.json().get('post', [])
            char_counts = Counter()
            for post in posts:
                tags = post.get('tags', '').split()
                score = post.get('score', 0)
                for t in tags:
                    if len(t) > 3 and not any(c in t for c in ['dress', 'bikini', 'hair', 'eyes', 'panties', 'thighhighs', 'cleavage', 'gloves', 'skirt', 'weapon', 'sword', 'solo', '1girl']):
                        char_counts[t] += (1 + score * 0.05)
            for tag, score in char_counts.most_common(20):
                if score > 3:
                    results.append(f"[Gelbooru Top Score]: {tag.replace('_', ' ').title()}")
    except Exception:
        pass
    return results

def fetch_yandere_and_konachan():
    urls = ["https://yande.re/post.json?limit=80", "https://konachan.net/post.json?limit=80"]
    results = []
    for u in urls:
        try:
            res = requests.get(u, headers={'User-Agent': 'Mozilla/5.0'}, timeout=12)
            if res.status_code == 200:
                for post in res.json()[:25]:
                    tags = [t.replace('_', ' ').title() for t in post.get('tags', '').split() if len(t) > 3]
                    if tags:
                        results.append(f"[Anime Booru Stream]: {', '.join(tags[:3])}")
        except Exception:
            continue
    return results

def fetch_reddit_gacha_mega():
    subs = "Genshin_Impact_Leaks+HonkaiStarRail_Leaks+Zenlesszonezero_leaks_+WutheringWavesLeaks+NikkeMobile+BlueArchive+Snowbreak"
    url = f"https://www.reddit.com/r/{subs}/hot/.rss?limit=60"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    results = []
    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            for entry in feedparser.parse(res.content).entries:
                results.append(f"[Reddit Gacha Leaks]: {entry.title}")
    except Exception:
        pass
    return results

def fetch_reddit_aaa_mega():
    subs = "gaming+cyberpunkgame+ResidentEvil+StellarBlade+FinalFantasy+Tekken+StreetFighter+BaldursGate3+MonsterHunter"
    url = f"https://www.reddit.com/r/{subs}/hot/.rss?limit=60"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    results = []
    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            for entry in feedparser.parse(res.content).entries:
                if any(kw in entry.title.lower() for kw in ['art', 'cosplay', 'mod', 'skin', 'character', 'render', 'trailer', 'waifu', 'girl', 'photo']):
                    results.append(f"[Reddit AAA/Gaming]: {entry.title}")
    except Exception:
        pass
    return results

def fetch_bluesky_art_mega():
    queries = [
        "waifu fanart", "character leak", "drip marketing", "bikini fanart", 
        "anime girl render", "genshin fanart", "nikke fanart", "wuwa fanart", "stellar blade"
    ]
    results = []
    for q in queries:
        try:
            res = requests.get(f"https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q={q}&limit=12", timeout=8)
            if res.status_code == 200:
                for p in res.json().get('posts', []):
                    text = p.get('record', {}).get('text', '').replace('\n', ' ')[:130]
                    likes = p.get('likeCount', 0)
                    results.append(f"[Bluesky (+{likes}❤️)]: {text}")
        except Exception:
            pass
    return results

def fetch_artstation_and_news():
    feeds = [
        "https://www.artstation.com/artwork.rss?sorting=trending",
        "https://www.gematsu.com/feed",
        "https://www.siliconera.com/feed",
        "https://www.animenewsnetwork.com/all/rss.xml?ann-edition=w"
    ]
    results = []
    for u in feeds:
        try:
            res = requests.get(u, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
            if res.status_code == 200:
                for entry in feedparser.parse(res.content).entries[:12]:
                    results.append(f"[Art & Media Feed]: {entry.title}")
        except Exception:
            continue
    return results

def fetch_youtube_targeted(api_key):
    if not api_key: return []
    time_limit = (datetime.utcnow() - timedelta(days=3)).isoformat() + "Z"
    queries = [
        '(Genshin OR "Honkai Star Rail" OR "Zenless Zone Zero" OR "Wuthering Waves") (trailer OR demo OR teaser OR drip marketing)',
        '(Nikke OR "Blue Archive" OR "Stellar Blade" OR "Resident Evil" OR "Cyberpunk") (trailer OR animation OR teaser OR character)'
    ]
    results = []
    for q in queries:
        params = {
            "part": "snippet", "q": q, "type": "video", "videoCategoryId": "20",
            "publishedAfter": time_limit, "maxResults": 15, "key": api_key
        }
        try:
            res = requests.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=10)
            if res.status_code == 200:
                for item in res.json().get('items', []):
                    results.append(f"[YouTube Gaming]: {item['snippet']['title']}")
        except Exception:
            pass
    return results

# ==========================================
# ИИ-АНАЛИЗАТОР (FLASH NEXT-GEN С ТОП-10)
# ==========================================
def get_latest_flash_models(api_key):
    fallback = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest"]
    blacklisted = ["tts", "audio", "image", "imagen", "veo", "banana", "embed", "deep-research", "live"]
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            models_data = res.json().get('models', [])
            discovered = []
            for m in models_data:
                name = m.get('name', '').replace('models/', '')
                methods = m.get('supportedGenerationMethods', [])
                if name.startswith('gemini-') and 'flash' in name.lower() and 'generateContent' in methods:
                    if not any(b in name.lower() for b in blacklisted):
                        discovered.append(name)
            if discovered:
                def extract_ver(m_name):
                    match = re.search(r'gemini-(\d+(?:\.\d+)?)', m_name)
                    return float(match.group(1)) if match else 0.0
                discovered.sort(key=extract_ver, reverse=True)
                return discovered
    except Exception:
        pass
    return fallback

def analyze_cross_platform_feed(feed_dump, key, nsfw_enabled):
    models_to_try = get_latest_flash_models(key)
    current_date = datetime.now().strftime("%Y-%m-%d")
    spicy_instruction = 'В массив "spicy_top" добавь от 6 до 10 ЖЕНСКИХ персонажей с вирусным фансервисом (купальники, открытые наряды, пикантные позы).' if nsfw_enabled else 'Массив "spicy_top" оставь пустым.'

    prompt = f"""
    ТЫ — ГЛАВНЫЙ АРТ-ДИРЕКТОР И ЭКСПЕРТ ПО ВИРАЛЬНОСТИ ФАНАРТА.
    Твоя цель — проанализировать огромный поток сырых сигналов интернета и составить списки ЖЕНСКИХ персонажей из видеоигр, фанарт по которым гарантирует ВЗРЫВНОЙ ОХВАТ, ЛАЙКИ И РЕПОСТЫ на 15+ площадках (Twitter/X, Pixiv, Bluesky, Reddit, Telegram, DeviantArt).
    Сегодня {current_date}.

    ВХОДНЫЕ СИГНАЛЫ (300+ логов из Booru, Reddit Leaks, Bluesky, ArtStation, YouTube):
    {json.dumps(feed_dump, ensure_ascii=False)}

    ЖЕЛЕЗНЫЕ ПРАВИЛА:
    1. ИСКЛЮЧИТЕЛЬНО ЖЕНСКИЕ ПЕРСОНАЖИ (Female Only).
    2. РОВНО 10 ПЕРСОНАЖЕЙ в "gacha_top" (Genshin, Honkai, ZZZ, WuWa, Nikke, Blue Archive, FGO, Azur Lane, Arknights и др.).
    3. РОВНО 10 ПЕРСОНАЖЕЙ в "other_games_top" (AAA, консольные, PC, файтинги, RPG: Resident Evil, Cyberpunk, Stellar Blade, Final Fantasy, Tekken, SF6, NieR, Witcher, Baldur's Gate и др.).
    4. ДЕТАЛЬНЫЕ ХУКИ (visual_hook): конкретная вирусная поза, ракурс, акцент в одежде/купальнике, эмоция, освещение.
    {spicy_instruction}

    ВЕРНИ ОТВЕТ СТРОГО В JSON СТРУКТУРЕ:
    {{
      "absolute_leader": {{
        "name": "Имя героини",
        "game": "Игра",
        "virality_score": 99,
        "past_72h_event": "Точный инфоповод из логов",
        "source_signal": "Строка из логов",
        "upcoming_catalyst": "Что подогреет интерес",
        "visual_hook": "Вирусная поза, ракурс, акцент в наряде и композиции",
        "why_draw_today": "Почему фанарт взорвет соцсети сегодня",
        "tags": ["fanart", "waifu", "art"]
      }},
      "spicy_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "analysis": "Причина фансервис-хайпа", "visual_hook": "Пикантный наряд / поза", "source_signal": "Источник", "score": 96, "tags": ["spicy", "bikini"] }}
      ],
      "gacha_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "score": 98, "reach": 97, "likes": 98, "visual_hook": "Поза / ракурс / детали", "source_signal": "Строка логов", "reason": "Слив/Баннер/Скин", "trend": "🔥" }}
      ],
      "other_games_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "score": 97, "reach": 95, "likes": 96, "visual_hook": "Поза / ракурс / детали", "source_signal": "Строка логов", "reason": "Мод/Трейлер/Культ", "trend": "⚔️" }}
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
            resp = requests.post(url, headers=headers, json=payload, timeout=65)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match: return json.loads(json_match.group()), model_name
                else: return json.loads(raw_text), model_name
            else:
                try: err_msg = resp.json().get('error', {}).get('message', resp.text[:100])
                except: err_msg = resp.text[:100]
                last_err = f"[{model_name}] {resp.status_code}: {err_msg}"
        except Exception as e:
            last_err = f"[{model_name}] {str(e)}"
            continue

    raise RuntimeError(f"Сбой Flash AI: {last_err}")

def run_full_scan():
    collected_feed = []
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = [
            executor.submit(fetch_danbooru_velocity),
            executor.submit(fetch_gelbooru_hot),
            executor.submit(fetch_yandere_and_konachan),
            executor.submit(fetch_reddit_gacha_mega),
            executor.submit(fetch_reddit_aaa_mega),
            executor.submit(fetch_bluesky_art_mega),
            executor.submit(fetch_artstation_and_news),
            executor.submit(fetch_youtube_targeted, youtube_key)
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
        bot.reply_to(message, "🎨 Сканирую 300+ первоисточников...")
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
# ИНТЕРФЕЙС STREAMLIT
# ==========================================
if st.button("🚀 Запустить глубокий поиск вирусных персонажей (300+ Signals)", type="primary", use_container_width=True):
    if not gemini_key:
        st.error("⚠️ Добавьте GEMINI_API_KEY в Secrets.")
    else:
        status_container = st.status("📡 Массовый сбор сигналов и синтез аналитики...", expanded=True)
        try:
            status_container.write("1. Парсинг Booru-платформ (Danbooru, Gelbooru, Yande.re, Konachan)...")
            status_container.write("2. Парсинг объединенных потоков Reddit (Гача + AAA)...")
            status_container.write("3. Сканирование Bluesky Deep Search, ArtStation и YouTube...")
            status_container.write("4. Структурирование Топ-10 Гачи и Топ-10 AAA через Flash Core...")
            
            (ai_results, used_model), raw_feed = run_full_scan()
            
            st.session_state.update({
                'omni_results': ai_results,
                'raw_feed': raw_feed,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'scan_done': True
            })
            status_container.update(label=f"Анализ завершен! Собрано {len(raw_feed)} сигналов. Модель: {used_model}", state="complete", expanded=False)
        except Exception as e:
            status_container.update(label="Ошибка анализа", state="error", expanded=True)
            st.error(e)

if st.session_state.get('scan_done', False):
    res = st.session_state['omni_results']
    st.caption(f"⏱️ **Данные собраны:** {st.session_state['timestamp']} | 📊 **Сигналов в базе:** {len(st.session_state.get('raw_feed', []))}")
    
    # 1. АБСОЛЮТНЫЙ ЛИДЕР
    leader = res.get('absolute_leader', {})
    if leader:
        tags_html = " ".join([f"<span class='badge'>#{t}</span>" for t in leader.get('tags', [])])
        st.markdown(f"""
<div class="hero-card">
<div style="text-transform: uppercase; letter-spacing: 2px; font-size: 12px; margin-bottom: 6px; color: #fbbf24;">👑 Главный объект внимания (Рисовать сегодня в 1 очередь)</div>
<div class="hero-title">{leader.get('name', 'Нет данных')} <span style="font-size:20px; font-weight:400; opacity:0.85; color:#cbd5e1;">— {leader.get('game', 'Нет данных')}</span></div>
<div style="font-size: 15px; margin: 4px 0 10px 0;">Индекс виральности: <b>{leader.get('virality_score', 0)}/100</b></div>
<div class="fact-box">🎯 <b>Визуальный хук (поза / наряд / ракурс):</b> {leader.get('visual_hook', 'Особые детали')}</div>
<div class="fact-box">📡 <b>Сигнал / Инфоповод:</b> {leader.get('source_signal', 'Отсутствует')}</div>
<div class="catalyst-box">⏳ <b>Катализатор внимания:</b> {leader.get('upcoming_catalyst', 'Ближайший релиз/патч')}</div>
<div style="margin-top: 10px; font-size: 13px; color: #94a3b8;">💡 <b>Почему фанарт завирусится:</b> {leader.get('why_draw_today', 'Пик внимания к персонажу')}</div>
<div style="margin-top: 14px;">{tags_html}</div>
</div>
        """, unsafe_allow_html=True)

    # 2. БЛОК 16+ SPICY
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
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

    # 3. ТОП 10 ГАЧА VS ТОП 10 ДРУГИЕ ИГРЫ
    col_gacha, col_other = st.columns(2)
    
    with col_gacha:
        st.subheader("🎲 Топ-10: Гача-Героини (Genshin, HSR, WuWa, Nikke...)")
        for idx, item in enumerate(res.get('gacha_top', [])[:10]):
            m_icon = medals[idx] if idx < len(medals) else f"{idx+1}."
            st.markdown(f"""
<div class="metric-card">
<h4 style="margin-bottom: 4px;">{m_icon} {item.get('name', '')} <span style="font-size:13px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 12px; color: #38bdf8; margin-bottom: 4px;">🎯 <b>Хук:</b> {item.get('visual_hook', '')}</p>
<p style="font-size: 12px; color: #64748b; margin-bottom: 4px;">📡 {item.get('source_signal', '')}</p>
<p style="font-size: 13px; color: #cbd5e1; margin: 0;">{item.get('reason', '')}</p>
</div>
            """, unsafe_allow_html=True)

    with col_other:
        st.subheader("⚔️ Топ-10: AAA & Другие Игры (Resident Evil, Cyberpunk, Stellar Blade...)")
        for idx, item in enumerate(res.get('other_games_top', [])[:10]):
            m_icon = medals[idx] if idx < len(medals) else f"{idx+1}."
            st.markdown(f"""
<div class="metric-card">
<h4 style="margin-bottom: 4px;">{m_icon} {item.get('name', '')} <span style="font-size:13px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 12px; color: #f59e0b; margin-bottom: 4px;">🎯 <b>Хук:</b> {item.get('visual_hook', '')}</p>
<p style="font-size: 12px; color: #64748b; margin-bottom: 4px;">📡 {item.get('source_signal', '')}</p>
<p style="font-size: 13px; color: #cbd5e1; margin: 0;">{item.get('reason', '')}</p>
</div>
            """, unsafe_allow_html=True)

    # 4. СЫРОЙ ПОТОК
    with st.expander("🔍 Посмотреть весь массив собранных логов"):
        st.write(st.session_state.get('raw_feed', []))
