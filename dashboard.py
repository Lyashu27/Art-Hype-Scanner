import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime, timedelta
import feedparser
from concurrent.futures import ThreadPoolExecutor, as_completed
import telebot
import threading
import re

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="🔥 Waifu Art Hype Radar: Social Virality", page_icon="📈", layout="wide")

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
</style>
""", unsafe_allow_html=True)

# --- ЗАГРУЗКА КЛЮЧЕЙ ---
gemini_key = st.secrets.get("GEMINI_API_KEY", "")
youtube_key = st.secrets.get("YOUTUBE_API_KEY", "")
tg_bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN", "")

st.title("📈 Omni-Channel Art Hype Radar: Social Virality")
st.markdown("Поиск персонажей, которые прямо сейчас разрывают алгоритмы соцсетей. **Никаких архивов (Booru)** — только живые обсуждения, просмотры и мировые тренды.")

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Параметры Сбора")
    is_16_plus = st.toggle("🔞 Режим 16+ (Spicy / Виральные позы)", value=True)
    scan_depth = st.select_slider(
        "Глубина сбора соцсетей (логов):",
        options=[1000, 3000, 5000],
        value=3000,
        help="Количество страниц для парсинга Reddit, Bilibili, Bluesky и YouTube."
    )
    st.divider()
    st.header("📡 Источники (Social Only)")
    st.write(f"⚡ Gemini Flash Core: {'🟢 Активен' if gemini_key else '🔴 Нет ключа'}")
    st.write("🔍 Reddit Mega-Feeds (Hot, Top 24h, Rising): 🟢")
    st.write("📺 YouTube Hype (Трейлеры, Реакции): 🟢")
    st.write("📺 Bilibili (Азиатские тренды): 🟢")
    st.write("🦋 Bluesky Art Community: 🟢")
    st.write("📰 Gaming Media RSS: 🟢")

# ==========================================
# МНОГОПОТОЧНЫЕ СКРЕЙПЕРЫ СОЦСЕТЕЙ И ОБСУЖДЕНИЙ
# ==========================================

def fetch_reddit_social_hype(depth_multiplier):
    """Сбор массивного потока обсуждений с Reddit (Top 24h, Hot, Rising)"""
    # Разбиваем сабреддиты на смысловые кластеры для обхода лимитов
    clusters = [
        "Genshin_Impact+HonkaiStarRail+ZenlessZoneZero+WutheringWaves",
        "Genshin_Impact_Leaks+HonkaiStarRail_Leaks+Zenlesszonezero_leaks_+WutheringWavesLeaks",
        "NikkeMobile+BlueArchive+Snowbreak+gachagaming+FateGrandOrder+AzurLane",
        "gaming+games+pcgaming+ps5+NintendoSwitch",
        "cyberpunkgame+ResidentEvil+StellarBlade+FinalFantasy+Tekken+StreetFighter+BaldursGate3+MonsterHunter"
    ]
    feeds = ["top/.rss?t=day", "hot/.rss", "rising/.rss"]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # Ограничиваем количество комбинаций в зависимости от ползунка
    max_requests = 3 * depth_multiplier 
    requests_done = 0

    for cluster in clusters:
        for feed in feeds:
            if requests_done >= max_requests: break
            try:
                url = f"https://www.reddit.com/r/{cluster}/{feed}?limit=100"
                res = requests.get(url, headers=headers, timeout=10)
                if res.status_code == 200:
                    for entry in feedparser.parse(res.content).entries:
                        # Захватываем темы с обсуждением артов, косплея, новостей
                        if any(kw in entry.title.lower() for kw in ['art', 'cosplay', 'leak', 'drip', 'trailer', 'character', 'design', 'skin', 'mod', 'waifu', 'boss']):
                            results.append(f"[Reddit {feed.split('/')[0].upper()} Hype]: {entry.title}")
                requests_done += 1
                time.sleep(0.5)
            except Exception:
                continue
    return results

def fetch_bluesky_viral_art(depth_multiplier):
    """Глубокий поиск по Bluesky: что прямо сейчас лайкают и репостят художники"""
    queries = [
        "fanart", "character teaser", "drip marketing", "wip art", 
        "genshin fanart", "hsr fanart", "zzz fanart", "wuwa fanart", 
        "nikke", "stellar blade", "resident evil mod", "cyberpunk lucy", 
        "tifa fanart", "2b nier", "anime girl render"
    ]
    results = []
    limit_per_query = 20 * depth_multiplier
    
    for q in queries:
        try:
            # Bluesky API позволяет искать по ключевым словам
            res = requests.get(f"https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q={q}&limit={limit_per_query}", timeout=8)
            if res.status_code == 200:
                for p in res.json().get('posts', []):
                    text = p.get('record', {}).get('text', '').replace('\n', ' ')[:150]
                    likes = p.get('likeCount', 0)
                    reposts = p.get('repostCount', 0)
                    # Берем только то, что уже начало вируситься (хотя бы 1 лайк/репост)
                    if likes > 0 or reposts > 0:
                        results.append(f"[Bluesky Social (❤️{likes} 🔁{reposts})]: {text}")
        except Exception:
            pass
    return results

def fetch_youtube_hype(api_key, depth_multiplier):
    """Сбор трейлеров и реакций с YouTube для оценки просмотров"""
    if not api_key: return []
    time_limit = (datetime.utcnow() - timedelta(days=5)).isoformat() + "Z"
    
    # Расширенные запросы для Ютуба
    queries = [
        "Genshin Impact character trailer",
        "Honkai Star Rail trailer",
        "Zenless Zone Zero demo",
        "Wuthering Waves resonator",
        "Nikke animation",
        "Stellar Blade outfit",
        "Resident Evil mod showcase",
        "Upcoming gacha game trailer"
    ]
    
    results = []
    max_res = 10 * depth_multiplier
    
    for q in queries:
        params = {
            "part": "snippet", "q": q, "type": "video", 
            "videoCategoryId": "20", "publishedAfter": time_limit, 
            "maxResults": max_res, "order": "viewCount", "key": api_key
        }
        try:
            res = requests.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=10)
            if res.status_code == 200:
                for item in res.json().get('items', []):
                    results.append(f"[YouTube Trending]: {item['snippet']['title']}")
        except Exception:
            pass
    return results

def fetch_bilibili_hot_trends():
    """Сбор горячих поисковых запросов Китая (огромный рынок для гачи)"""
    url = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': 'https://www.bilibili.com/'
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json().get('data', {}).get('list', [])[:50] # Берем топ 50
            for item in data:
                title = item.get('title', '')
                desc = item.get('desc', '')
                # Ищем упоминания игровых франшиз
                if any(kw in title for kw in ['原神', '星穹铁道', '绝区零', '崩坏', '鸣潮', '明日方舟', '碧蓝航线', 'cosplay', '动画']):
                    results.append(f"[Bilibili Hot (CN)]: {title} - {desc[:50]}")
    except Exception:
        pass
    return results

def fetch_gaming_news_rss():
    """Свежие анонсы из СМИ, которые запустят волну фанарта завтра"""
    feeds = [
        "https://www.gematsu.com/feed",
        "https://www.siliconera.com/feed",
        "https://www.ign.com/rss/articles/feed",
        "https://www.gamespot.com/feeds/mashup/"
    ]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for u in feeds:
        try:
            res = requests.get(u, headers=headers, timeout=8)
            if res.status_code == 200:
                for entry in feedparser.parse(res.content).entries[:20]:
                    if any(kw in entry.title.lower() for kw in ['announce', 'reveal', 'trailer', 'character', 'dlc', 'update', 'leak']):
                        results.append(f"[Gaming Media Catalyst]: {entry.title}")
        except Exception:
            continue
    return results

# ==========================================
# ПАКЕТНЫЙ ЗАПУСК ДЛЯ СБОРА ТЫСЯЧ СИГНАЛОВ
# ==========================================
def run_massive_social_collection(target_count):
    feed = []
    depth_mult = max(1, int(target_count / 1000))
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(fetch_reddit_social_hype, depth_mult),
            executor.submit(fetch_bluesky_viral_art, depth_mult),
            executor.submit(fetch_youtube_hype, youtube_key, depth_mult),
            executor.submit(fetch_bilibili_hot_trends),
            executor.submit(fetch_gaming_news_rss)
        ]
        for f in as_completed(futures):
            feed.extend(f.result())
            
    # Чистим слишком короткие логи
    cleaned = [item for item in feed if len(item) > 10]
    return cleaned

# ==========================================
# ИИ-АНАЛИЗАТОР (FLASH NEXT-GEN С ТОП-10)
# ==========================================
def get_latest_flash_models(api_key):
    fallback = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest"]
    blacklisted = ["tts", "audio", "image", "imagen", "veo", "banana", "embed", "deep-research", "live", "translate", "vision"]
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

def analyze_massive_feed(feed_dump, key, nsfw_enabled):
    models_to_try = get_latest_flash_models(key)
    current_date = datetime.now().strftime("%Y-%m-%d")
    spicy_instruction = 'В массив "spicy_top" добавь от 6 до 10 ЖЕНСКИХ персонажей, которые прямо сейчас вызывают бурю эмоций, мемов и фанарта из-за откровенного дизайна (купальники, облегающая одежда, формы). Опиши, как это использовать для лайков.' if nsfw_enabled else 'Массив "spicy_top" оставь пустым.'

    # Защита от переполнения (Flash держит 1M токенов, но лучше не спамить больше 5000 логов за раз)
    sample_feed = feed_dump[:5000]

    prompt = f"""
    ТЫ — ГЛАВНЫЙ АРТ-ПРОДЮСЕР, АНАЛИТИК ТРЕНДОВ И ЭКСПЕРТ ПО АЛГОРИТМАМ СОЦСЕТЕЙ.
    Твоя задача — проанализировать огромный массив живых обсуждений, просмотров и новостей ({len(sample_feed)} постов) и сформировать рейтинги ЖЕНСКИХ персонажей видеоигр, фанарт по которым прямо сейчас (сегодня) гарантирует ВЗРЫВНОЙ ОХВАТ, МАССОВЫЕ ЛАЙКИ И НАБОР АУДИТОРИИ на платформах (Twitter/X, Pixiv, Reddit, TikTok, Instagram).
    Сегодня {current_date}.

    ВХОДНЫЕ СИГНАЛЫ (Живые обсуждения Reddit, тренды YouTube, Bluesky, СМИ):
    {json.dumps(sample_feed, ensure_ascii=False)}

    ЖЕЛЕЗНЫЕ ПРАВИЛА:
    1. ИСКЛЮЧИТЕЛЬНО ЖЕНСКИЕ ПЕРСОНАЖИ.
    2. РОВНО 10 ПЕРСОНАЖЕЙ в "gacha_top" (Genshin, Honkai, ZZZ, WuWa, Nikke, Blue Archive, FGO, Azur Lane, Arknights и др.).
    3. РОВНО 10 ПЕРСОНАЖЕЙ в "other_games_top" (AAA, PC, консоли, файтинги: Resident Evil, Cyberpunk, Stellar Blade, Final Fantasy, Tekken, SF6, NieR, Baldur's Gate и др.).
    4. ФОКУС НА АЛГОРИТМЫ (visual_hook): Опиши, какая именно поза, ракурс, деталь наряда или эмоция заставит пользователя остановиться при скроллинге ленты (scroll-stopper). 
    5. ПРИЧИНА ХАЙПА (reason): Почему аудитория обсуждает её именно сейчас? (Вышел трейлер, слили геймплей, споры о дизайне на Reddit).
    {spicy_instruction}

    ВЕРНИ ОТВЕТ СТРОГО В JSON:
    {{
      "absolute_leader": {{
        "name": "Имя героини",
        "game": "Игра",
        "virality_score": 99,
        "past_72h_event": "В чем заключается хайп (событие/новость)",
        "source_signal": "Где это обсуждают",
        "upcoming_catalyst": "Что будет дальше",
        "visual_hook": "Scroll-stopper: поза, ракурс, освещение, главная деталь, которая соберет ретвиты",
        "why_draw_today": "Почему публикация арта именно сегодня даст максимум подписчиков",
        "tags": ["fanart", "trending", "art"]
      }},
      "spicy_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "analysis": "Причина фансервис-хайпа", "visual_hook": "Специфика пикантного арта для алгоритмов", "source_signal": "Источник", "score": 96, "tags": ["spicy", "bikini"] }}
      ],
      "gacha_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "score": 98, "reach": 97, "likes": 98, "visual_hook": "Поза / ракурс / деталь, цепляющая глаз", "source_signal": "Источник хайпа", "reason": "Новый скин/Слив/Сюжет", "trend": "🔥" }}
      ],
      "other_games_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "score": 97, "reach": 95, "likes": 96, "visual_hook": "Поза / ракурс / деталь, цепляющая глаз", "source_signal": "Источник хайпа", "reason": "Анонс/Мод/Скандал", "trend": "⚔️" }}
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
                try: err_msg = resp.json().get('error', {}).get('message', resp.text[:100])
                except: err_msg = resp.text[:100]
                last_err = f"[{model_name}] {resp.status_code}: {err_msg}"
        except Exception as e:
            last_err = f"[{model_name}] {str(e)}"
            continue

    raise RuntimeError(f"Сбой Flash AI: {last_err}")

# ==========================================
# TELEGRAM БОТ
# ==========================================
@st.cache_resource
def start_telegram_bot(token):
    if not token: return None
    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['scan'])
    def handle_scan(message):
        bot.reply_to(message, "📈 Сканирую алгоритмы соцсетей, обсуждения Reddit и тренды YouTube...")
        try:
            raw_feed = run_massive_social_collection(3000)
            ai_res, model = analyze_massive_feed(raw_feed, gemini_key, is_16_plus)
            leader = ai_res.get('absolute_leader', {})
            msg = f"👑 *ТОП ДЛЯ ВИРУСНОГО ФАНАРТА:*\n*{leader.get('name', 'N/A')}* ({leader.get('game', 'N/A')})\n"
            msg += f"🎯 *Хук для соцсетей:* {leader.get('visual_hook', 'N/A')}\n"
            msg += f"📌 *Причина хайпа:* {leader.get('past_72h_event', 'N/A')}\n"
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    return bot

start_telegram_bot(tg_bot_token)

# ==========================================
# ИНТЕРФЕЙС STREAMLIT
# ==========================================
if st.button(f"🚀 Запустить глубокий Social-Scan ({scan_depth} логов)", type="primary", use_container_width=True):
    if not gemini_key:
        st.error("⚠️ Добавьте GEMINI_API_KEY в Secrets.")
    else:
        status_container = st.status(f"📡 Массовый парсинг обсуждений и просмотров ({scan_depth} сигналов)...", expanded=True)
        try:
            status_container.write("1. Сканируем сотни сабреддитов (Top 24h, Hot, Rising) на предмет бурных обсуждений...")
            status_container.write("2. Проверяем YouTube трейлеры и китайские тренды Bilibili...")
            status_container.write("3. Анализируем арт-комьюнити в Bluesky (лайки и репосты)...")
            raw_feed = run_massive_social_collection(scan_depth)
            
            status_container.write(f"4. Синтез {len(raw_feed)} логов через Gemini Flash Core для поиска максимального хайпа...")
            ai_results, used_model = analyze_massive_feed(raw_feed, gemini_key, is_16_plus)
            
            st.session_state.update({
                'omni_results': ai_results,
                'raw_feed': raw_feed,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'scan_done': True
            })
            status_container.update(label=f"Анализ завершен! Собрано {len(raw_feed)} чистых логов из соцсетей. Модель: {used_model}", state="complete", expanded=False)
        except Exception as e:
            status_container.update(label="Ошибка анализа", state="error", expanded=True)
            st.error(e)

if st.session_state.get('scan_done', False):
    res = st.session_state['omni_results']
    st.caption(f"⏱️ **Данные собраны:** {st.session_state['timestamp']} | 📊 **Обсуждений и трендов в базе:** {len(st.session_state.get('raw_feed', []))}")
    
    # 1. АБСОЛЮТНЫЙ ЛИДЕР
    leader = res.get('absolute_leader', {})
    if leader:
        tags_html = " ".join([f"<span class='badge'>#{t}</span>" for t in leader.get('tags', [])])
        st.markdown(f"""
<div class="hero-card">
<div style="text-transform: uppercase; letter-spacing: 2px; font-size: 12px; margin-bottom: 6px; color: #fbbf24;">👑 Максимальный виральный потенциал (Рисовать прямо сейчас)</div>
<div class="hero-title">{leader.get('name', 'Нет данных')} <span style="font-size:20px; font-weight:400; opacity:0.85; color:#cbd5e1;">— {leader.get('game', 'Нет данных')}</span></div>
<div style="font-size: 15px; margin: 4px 0 10px 0;">Индекс виральности: <b>{leader.get('virality_score', 0)}/100</b></div>
<div class="fact-box">🎯 <b>Хук для алгоритмов (поза / ракурс / деталь):</b> {leader.get('visual_hook', 'Особые детали')}</div>
<div class="fact-box">📡 <b>В чем суть хайпа:</b> {leader.get('past_72h_event', 'Отсутствует')} ({leader.get('source_signal', 'Сигнал')})</div>
<div class="catalyst-box">💡 <b>Зачем публиковать сегодня:</b> {leader.get('why_draw_today', 'Пик внимания к персонажу')}</div>
<div style="margin-top: 14px;">{tags_html}</div>
</div>
        """, unsafe_allow_html=True)

    # 2. БЛОК 16+ SPICY
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    if is_16_plus and res.get('spicy_top'):
        st.subheader("🔞 Тренды 16+ (Виральный фансервис для набора аудитории)")
        spicy_items = res.get('spicy_top', [])
        spicy_cols = st.columns(min(3, len(spicy_items)))
        for idx, item in enumerate(spicy_items[:3]):
            with spicy_cols[idx]:
                st.markdown(f"""
<div class="spicy-card">
<h4 style="margin-bottom: 5px; color: #ff9ebf;">{medals[idx]} {item.get('name', '')} <span style="font-size:13px; color:#a5b1c2;">({item.get('game', '')})</span></h4>
<p style="font-size: 13px; color: #f1f5f9; margin-bottom: 6px;"><b>Хайп:</b> {item.get('analysis', '')}</p>
<p style="font-size: 12px; color: #f472b6; margin-bottom: 8px;">👙 <b>Scroll-stopper:</b> {item.get('visual_hook', '')}</p>
<div>{" ".join([f"<span class='badge spicy-badge'>#{t}</span>" for t in item.get('tags', [])])}</div>
</div>
                """, unsafe_allow_html=True)
        st.divider()

    # 3. ТОП 10 ГАЧА VS ТОП 10 ДРУГИЕ ИГРЫ
    col_gacha, col_other = st.columns(2)
    
    with col_gacha:
        st.subheader("🎲 Топ-10 Гачи (Максимальное обсуждение: Genshin, HSR, WuWa...)")
        for idx, item in enumerate(res.get('gacha_top', [])[:10]):
            m_icon = medals[idx] if idx < len(medals) else f"{idx+1}."
            st.markdown(f"""
<div class="metric-card">
<h4 style="margin-bottom: 4px;">{m_icon} {item.get('name', '')} <span style="font-size:13px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 13px; color: #cbd5e1; margin-bottom: 4px;"><b>Повод:</b> {item.get('reason', '')}</p>
<p style="font-size: 12px; color: #38bdf8; margin: 0;">🎯 <b>Хук для соцсетей:</b> {item.get('visual_hook', '')}</p>
</div>
            """, unsafe_allow_html=True)

    with col_other:
        st.subheader("⚔️ Топ-10 AAA & PC (Мировой хайп: RE, Cyberpunk, Stellar Blade...)")
        for idx, item in enumerate(res.get('other_games_top', [])[:10]):
            m_icon = medals[idx] if idx < len(medals) else f"{idx+1}."
            st.markdown(f"""
<div class="metric-card">
<h4 style="margin-bottom: 4px;">{m_icon} {item.get('name', '')} <span style="font-size:13px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 13px; color: #cbd5e1; margin-bottom: 4px;"><b>Повод:</b> {item.get('reason', '')}</p>
<p style="font-size: 12px; color: #f59e0b; margin: 0;">🎯 <b>Хук для соцсетей:</b> {item.get('visual_hook', '')}</p>
</div>
            """, unsafe_allow_html=True)

    # 4. СЫРОЙ ПОТОК (ВЕСЬ МАССИВ)
    with st.expander(f"🔍 Посмотреть весь массив живых обсуждений и трендов ({len(st.session_state.get('raw_feed', []))} записей)"):
        st.write(st.session_state.get('raw_feed', []))
