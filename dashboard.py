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
st.set_page_config(page_title="🔥 Waifu Art Hype Radar (Audience Builder)", page_icon="📈", layout="wide")

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

st.title("📈 Omni-Channel Art Hype Radar: Audience Builder")
st.markdown("Поиск персонажей для вирального фанарта. Максимизация охватов, лайков и набора подписчиков.")

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Параметры Сбора")
    is_16_plus = st.toggle("🔞 Режим 16+ (Spicy / Виральные позы)", value=True)
    st.divider()
    st.header("📡 Состояние Каналов")
    st.write(f"⚡ Gemini Engine (Pro/Flash): {'🟢 Активен' if gemini_key else '🔴 Нет ключа'}")
    st.write(f"📺 YouTube API: {'🟢 Активен' if youtube_key else '⚪ Выключен'}")
    st.write("🔍 Reddit Hub: 🟢 Активен")
    st.write("🦋 Bluesky Social: 🟢 Активен")
    st.write("📺 Bilibili Trends: 🟢 Активен")
    st.write("📰 Gaming Media Feeds: 🟢 Активен")

# ==========================================
# СТАБИЛЬНЫЕ И СБАЛАНСИРОВАННЫЕ ПАРСЕРЫ
# ==========================================

def fetch_reddit_stable():
    """Сбор горячих тем Reddit с авто-переключением на RSS Gateway при блокировках"""
    subs = [
        "Genshin_Impact_Leaks", "HonkaiStarRail_Leaks", "Zenlesszonezero_leaks_",
        "WutheringWavesLeaks", "NikkeMobile", "BlueArchive", "gachagaming",
        "StellarBlade", "cyberpunkgame", "ResidentEvil"
    ]
    results = []
    headers = {'User-Agent': 'WaifuHypeBot/2.0 (Trend Research Tool)'}
    
    for sub in subs:
        url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                posts = res.json().get('data', {}).get('children', [])
                for p in posts:
                    data = p.get('data', {})
                    if not data.get('stickied'):
                        title = data.get('title', '')
                        ups = data.get('ups', 0)
                        results.append(f"[Reddit r/{sub} (🔥{ups})]: {title}")
            else:
                fallback_url = f"https://news.google.com/rss/search?q=site:reddit.com/r/{sub}+when:3d&hl=en-US&gl=US&ceid=US:en"
                fb_res = requests.get(fallback_url, timeout=5)
                if fb_res.status_code == 200:
                    feed = feedparser.parse(fb_res.content)
                    for entry in feed.entries[:5]:
                        clean_title = entry.title.split(" - ")[0]
                        results.append(f"[Reddit r/{sub}]: {clean_title}")
        except Exception:
            continue
        time.sleep(0.1)
    return results[:50]


def fetch_bluesky_stable():
    """Сбор трендов Bluesky с корректным URL-encoding"""
    queries = [
        "fanart", "character teaser", "drip marketing", 
        "genshin fanart", "hsr fanart", "zzz fanart", "wuwa fanart", 
        "nikke fanart", "stellar blade", "resident evil mod", "tifa fanart"
    ]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for q in queries:
        try:
            res = requests.get(
                "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
                params={"q": q, "limit": 10},
                headers=headers,
                timeout=6
            )
            if res.status_code == 200:
                for p in res.json().get('posts', []):
                    text = p.get('record', {}).get('text', '').replace('\n', ' ')[:110]
                    likes = p.get('likeCount', 0)
                    if likes >= 3:
                        results.append(f"[Bluesky (❤️{likes})]: {text}")
        except Exception:
            pass
        time.sleep(0.1)
    return results[:40]


def fetch_youtube_stable(api_key):
    """Сбор игровых видео с лимитом (макс. 5 записей на запрос)"""
    if not api_key: return []
    time_limit = (datetime.utcnow() - timedelta(days=3)).isoformat() + "Z"
    queries = [
        "Genshin character trailer", "Honkai Star Rail trailer",
        "Zenless Zone Zero demo", "Wuthering Waves resonator",
        "Nikke animation", "Stellar Blade", "Resident Evil mod"
    ]
    results = []
    for q in queries:
        params = {
            "part": "snippet", "q": q, "type": "video", 
            "videoCategoryId": "20", "publishedAfter": time_limit, 
            "maxResults": 5, "key": api_key
        }
        try:
            res = requests.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=6)
            if res.status_code == 200:
                for item in res.json().get('items', []):
                    results.append(f"[YouTube Trending]: {item['snippet']['title']}")
        except Exception:
            pass
    return results[:35]


def fetch_gaming_media():
    """Расширенный сбор анонсов из игровых изданий"""
    feeds = [
        "https://www.gematsu.com/feed",
        "https://www.siliconera.com/feed",
        "https://automaton-media.com/en/feed/",
        "https://noisypixel.net/feed/",
        "https://animecorner.me/feed/",
        "https://www.animenewsnetwork.com/all/rss.xml?ann-edition=w"
    ]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for u in feeds:
        try:
            res = requests.get(u, headers=headers, timeout=6)
            if res.status_code == 200:
                for entry in feedparser.parse(res.content).entries[:8]:
                    results.append(f"[Gaming Media]: {entry.title}")
        except Exception:
            continue
    return results[:45]


def fetch_bilibili_stable():
    """Сбор трендов китайского региона по игровой секции"""
    url = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=4&type=all"
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.bilibili.com/'
    }
    try:
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            for item in res.json().get('data', {}).get('list', [])[:20]:
                title = item.get('title', '')
                results.append(f"[Bilibili Hot (CN)]: {title}")
    except Exception:
        pass
    return results[:20]


def run_all_sources():
    feed = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(fetch_reddit_stable),
            executor.submit(fetch_bluesky_stable),
            executor.submit(fetch_youtube_stable, youtube_key),
            executor.submit(fetch_bilibili_stable),
            executor.submit(fetch_gaming_media)
        ]
        for f in as_completed(futures):
            feed.extend(f.result())
            
    cleaned = [item for item in feed if len(item) > 10]
    return cleaned

# ==========================================
# ИИ-АНАЛИЗАТОР (PRO С ФОЛЛБЭКОМ НА FLASH)
# ==========================================
def get_prioritized_models(api_key):
    """
    Динамический поиск моделей с сортировкой:
    1. Gemini Pro (по убыванию версии)
    2. Gemini Flash (по убыванию версии)
    """
    fallback_models = [
        "gemini-2.5-pro", "gemini-2.0-pro", "gemini-1.5-pro-latest", "gemini-1.5-pro",
        "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-flash"
    ]
    blacklisted = ["tts", "audio", "image", "imagen", "veo", "banana", "embed", "deep-research", "live", "translate"]
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            models_data = res.json().get('models', [])
            pro_models = []
            flash_models = []
            
            for m in models_data:
                name = m.get('name', '').replace('models/', '')
                methods = m.get('supportedGenerationMethods', [])
                
                if name.startswith('gemini-') and 'generateContent' in methods:
                    if not any(b in name.lower() for b in blacklisted):
                        if 'pro' in name.lower():
                            pro_models.append(name)
                        elif 'flash' in name.lower():
                            flash_models.append(name)
            
            def extract_ver(m_name):
                match = re.search(r'gemini-(\d+(?:\.\d+)?)', m_name)
                return float(match.group(1)) if match else 0.0

            pro_models.sort(key=extract_ver, reverse=True)
            flash_models.sort(key=extract_ver, reverse=True)
            
            discovered = pro_models + flash_models
            if discovered:
                return discovered
    except Exception:
        pass
    return fallback_models


def analyze_hype_feed(feed_dump, key, nsfw_enabled):
    models_to_try = get_prioritized_models(key)
    current_date = datetime.now().strftime("%Y-%m-%d")
    spicy_instruction = 'В массив "spicy_top" добавь от 6 до 10 ЖЕНСКИХ персонажей с вирусным фансервисом (купальники, открытые наряды, пикантные позы). Сделай акцент на визуальных триггерах для набора аудитории.' if nsfw_enabled else 'Массив "spicy_top" оставь пустым.'

    prompt = f"""
    ТЫ — ГЛАВНЫЙ АРТ-ПРОДЮСЕР, АНАЛИТИК ТРЕНДОВ И ЭКСПЕРТ ПО АЛГОРИТМАМ СОЦСЕТЕЙ.
    Твоя задача — проанализировать {len(feed_dump)} свежих обсуждений и сформировать рейтинги ЖЕНСКИХ персонажей видеоигр.
    Цель пользователя — сделать виральный 3D-фанарт, который соберет МАКСИМУМ ЛАЙКОВ, РЕПОСТОВ И ПОДПИСЧИКОВ на 15+ платформах (Twitter/X, Pixiv, Reddit, Bluesky, DeviantArt, Instagram).
    Сегодня {current_date}.

    ВХОДНЫЕ СИГНАЛЫ (Живые обсуждения Reddit, тренды YouTube, Bluesky, Bilibili, Gaming Media):
    {json.dumps(feed_dump, ensure_ascii=False)}

    ЖЕЛЕЗНЫЕ ПРАВИЛА:
    1. ИСКЛЮЧИТЕЛЬНО ЖЕНСКИЕ ПЕРСОНАЖИ.
    2. НИКАКИХ ПРОДАЖ И АССЕТОВ: Цель — только фанарт, просмотры, хайп и удержание аудитории.
    3. РОВНО 10 ПЕРСОНАЖЕЙ в "gacha_top" (Genshin, Honkai, ZZZ, WuWa, Nikke, Blue Archive, FGO, Azur Lane и др.).
    4. РОВНО 10 ПЕРСОНАЖЕЙ в "other_games_top" (AAA, PC, консоли: Resident Evil, Cyberpunk, Stellar Blade, Final Fantasy, Tekken и др.).
    5. ФОКУС НА 3D-ВИРАЛЬНОСТЬ (visual_hook): Опиши, какая именно динамичная поза, ракурс камеры в Blender, освещение или деталь наряда заставит пользователя остановиться при скроллинге ленты (scroll-stopper). 
    {spicy_instruction}

    ВЕРНИ ОТВЕТ СТРОГО В JSON:
    {{
      "absolute_leader": {{
        "name": "Имя героини",
        "game": "Игра",
        "virality_score": 99,
        "past_72h_event": "В чем заключается хайп (событие/новость/слив)",
        "source_signal": "Где это активно обсуждают",
        "upcoming_catalyst": "Что подогреет хайп дальше",
        "visual_hook": "Scroll-stopper для 3D: поза, ракурс камеры, свет, акцент",
        "why_draw_today": "Почему публикация 3D-арта сегодня даст максимум подписчиков",
        "tags": ["3dfanart", "trending", "waifu"]
      }},
      "spicy_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "analysis": "Причина фансервис-хайпа", "visual_hook": "Специфика пикантного 3D-рендера для алгоритмов", "source_signal": "Источник", "score": 96, "tags": ["spicy", "nsfw"] }}
      ],
      "gacha_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "score": 98, "reach": 97, "likes": 98, "visual_hook": "Ракурс камеры / свет в Blender", "source_signal": "Источник хайпа", "reason": "Новый скин/Слив/Сюжет", "trend": "🔥" }}
      ],
      "other_games_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "score": 97, "reach": 95, "likes": 96, "visual_hook": "Ракурс камеры / свет в Blender", "source_signal": "Источник хайпа", "reason": "Анонс/Мод/Хайп", "trend": "⚔️" }}
      ]
    }}
    """

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}
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

    raise RuntimeError(f"Сбой ИИ-моделей: {last_err}")

# ==========================================
# TELEGRAM БОТ
# ==========================================
@st.cache_resource
def start_telegram_bot(token):
    if not token: return None
    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['scan'])
    def handle_scan(message):
        bot.reply_to(message, "📈 Сканирую тренды (Reddit, Bluesky, YouTube, СМИ, Bilibili)...")
        try:
            raw_feed = run_all_sources()
            ai_res, model = analyze_hype_feed(raw_feed, gemini_key, is_16_plus)
            leader = ai_res.get('absolute_leader', {})
            msg = f"👑 *ТОП ДЛЯ ВИРУСНОГО 3D-РЕНДЕРА ({model}):*\n*{leader.get('name', 'N/A')}* ({leader.get('game', 'N/A')})\n"
            msg += f"🎯 *Хук (Ракурс/Свет):* {leader.get('visual_hook', 'N/A')}\n"
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
if st.button("🚀 Запустить Hype-Scan (Все каналы)", type="primary", use_container_width=True):
    if not gemini_key:
        st.error("⚠️ Добавьте GEMINI_API_KEY в Secrets.")
    else:
        status_container = st.status("📡 Сбор данных по всем каналам...", expanded=True)
        try:
            status_container.write("1. Парсинг Reddit Hot & Leaks...")
            status_container.write("2. Сканирование Bluesky постов...")
            status_container.write("3. Сбор трейлеров YouTube & Bilibili Gaming...")
            status_container.write("4. Получение свежих релизов из Gaming Media RSS...")
            raw_feed = run_all_sources()
            
            status_container.write(f"5. Анализ {len(raw_feed)} сбалансированных сигналов через Gemini Pro/Flash...")
            ai_results, used_model = analyze_hype_feed(raw_feed, gemini_key, is_16_plus)
            
            st.session_state.update({
                'omni_results': ai_results,
                'raw_feed': raw_feed,
                'used_model': used_model,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'scan_done': True
            })
            status_container.update(label=f"Анализ завершен! Собрано {len(raw_feed)} сигналов. Модель: {used_model}", state="complete", expanded=False)
        except Exception as e:
            status_container.update(label="Ошибка анализа", state="error", expanded=True)
            st.error(e)

if st.session_state.get('scan_done', False):
    res = st.session_state['omni_results']
    st.caption(f"⏱️ **Данные собраны:** {st.session_state['timestamp']} | 📊 **Сигналов в базе:** {len(st.session_state.get('raw_feed', []))} | 🧠 **Модель:** `{st.session_state.get('used_model', 'N/A')}`")
    
    # 1. АБСОЛЮТНЫЙ ЛИДЕР
    leader = res.get('absolute_leader', {})
    if leader:
        tags_html = " ".join([f"<span class='badge'>#{t}</span>" for t in leader.get('tags', [])])
        st.markdown(f"""
<div class="hero-card">
<div style="text-transform: uppercase; letter-spacing: 2px; font-size: 12px; margin-bottom: 6px; color: #fbbf24;">👑 Максимальный виральный потенциал (Рендерить прямо сейчас)</div>
<div class="hero-title">{leader.get('name', 'Нет данных')} <span style="font-size:20px; font-weight:400; opacity:0.85; color:#cbd5e1;">— {leader.get('game', 'Нет данных')}</span></div>
<div style="font-size: 15px; margin: 4px 0 10px 0;">Индекс виральности: <b>{leader.get('virality_score', 0)}/100</b></div>
<div class="fact-box">🎯 <b>Хук для 3D (свет / поза / ракурс):</b> {leader.get('visual_hook', 'Особые детали')}</div>
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
        st.subheader("🎲 Топ-10 Гачи (Genshin, HSR, WuWa, Nikke...)")
        for idx, item in enumerate(res.get('gacha_top', [])[:10]):
            m_icon = medals[idx] if idx < len(medals) else f"{idx+1}."
            st.markdown(f"""
<div class="metric-card">
<h4 style="margin-bottom: 4px;">{m_icon} {item.get('name', '')} <span style="font-size:13px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 13px; color: #cbd5e1; margin-bottom: 4px;"><b>Повод:</b> {item.get('reason', '')}</p>
<p style="font-size: 12px; color: #38bdf8; margin: 0;">🎯 <b>Хук для 3D:</b> {item.get('visual_hook', '')}</p>
</div>
            """, unsafe_allow_html=True)

    with col_other:
        st.subheader("⚔️ Топ-10 AAA & PC (Resident Evil, Cyberpunk, Stellar Blade...)")
        for idx, item in enumerate(res.get('other_games_top', [])[:10]):
            m_icon = medals[idx] if idx < len(medals) else f"{idx+1}."
            st.markdown(f"""
<div class="metric-card">
<h4 style="margin-bottom: 4px;">{m_icon} {item.get('name', '')} <span style="font-size:13px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 13px; color: #cbd5e1; margin-bottom: 4px;"><b>Повод:</b> {item.get('reason', '')}</p>
<p style="font-size: 12px; color: #f59e0b; margin: 0;">🎯 <b>Хук для 3D:</b> {item.get('visual_hook', '')}</p>
</div>
            """, unsafe_allow_html=True)

    # 4. СЫРОЙ ПОТОК
    with st.expander(f"🔍 Посмотреть собранный массив обсуждений ({len(st.session_state.get('raw_feed', []))} записей)"):
        st.write(st.session_state.get('raw_feed', []))
