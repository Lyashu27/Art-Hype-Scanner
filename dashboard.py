import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime, timedelta
import feedparser
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import cloudscraper
import requests
import random
import urllib.parse

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="🔥 Waifu Art Hype Radar (Dynamic Discovery)", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 16px; border-radius: 12px; border-left: 5px solid #4b8bff; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .spicy-card {background-color: #25181e; padding: 16px; border-radius: 12px; border-left: 5px solid #ff4b8b; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(255, 75, 139, 0.15);}
    .hero-card {background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 26px; border-radius: 16px; margin-bottom: 20px; color: white; border: 1px solid #3b82f6; box-shadow: 0 10px 25px rgba(59, 130, 246, 0.25);}
    .hero-title {font-size: 28px; font-weight: 800; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 1px; color: #60a5fa;}
    .fact-box {background: rgba(15, 23, 42, 0.7); padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-top: 8px; border-left: 4px solid #38bdf8;}
    .badge {background-color: #1e293b; padding: 3px 8px; border-radius: 6px; font-size: 12px; margin-right: 5px; color: #93c5fd; border: 1px solid #334155; display: inline-block; margin-bottom: 3px;}
    .spicy-badge {background-color: #3b1c28; color: #ff9ebf; border-color: #ff4b8b;}
    .log-box {background-color: #000; color: #0f0; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 11px; max-height: 250px; overflow-y: auto;}
</style>
""", unsafe_allow_html=True)

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
gemini_key = st.secrets.get("GEMINI_API_KEY", "")
youtube_key = st.secrets.get("YOUTUBE_API_KEY", "")

st.title("📈 Omni-Channel Art Hype Radar (Динамический поиск)")
st.markdown("Поиск персонажей на основе глобальных трендов индустрии без ограничений по конкретным франшизам.")

with st.sidebar:
    st.header("⚙️ Параметры Сбора")
    is_16_plus = st.toggle("🔞 Режим 16+ (Spicy / Виральные тренды)", value=True)
    st.divider()
    st.header("📡 Состояние Каналов")
    st.write(f"⚡ Gemini Engine: {'🟢 Активен' if gemini_key else '🔴 Нет ключа'}")
    st.write(f"📺 YouTube API: {'🟢 Активен' if youtube_key else '⚪ Выключен'}")

# ==========================================
# ДИНАМИЧЕСКИЕ ПАРСЕРЫ (БЕЗ ЖЕСТКИХ ТЕГОВ ИГР)
# ==========================================

def fetch_reddit_dynamic():
    """Сбор Reddit через межпроектные хабы и динамические сквозные тренды"""
    results = []
    headers = {'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 HubTracker/{random.randint(100, 999)}'}
    exclude_keywords = ["megathread", "daily question", "weekly", "help", "troubleshooting", "maintenance", "giveaway", "mod post"]

    # 1. Общеигровые и арт-хабы
    general_hubs = ["gaming", "Games", "gachagaming", "pcgaming", "AnimeART", "CharacterDrawing", "DigitalArt", "cosplay"]
    for hub in general_hubs:
        url = f"https://www.reddit.com/r/{hub}/top.rss?t=day"
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                feed = feedparser.parse(res.content)
                for entry in feed.entries[:5]:
                    title = entry.title.strip()
                    if not any(ex in title.lower() for ex in exclude_keywords) and len(title) > 8:
                        results.append(f"[Reddit r/{hub} | 🔥 Top 24h]: {title}")
        except Exception:
            pass
        time.sleep(0.1)

    # 2. Сквозной поиск по всему Reddit на предмет горячих инфоповодов последних 48 часов
    discovery_queries = [
        'site:reddit.com/r/*+("character reveal"+OR+"drip marketing"+OR+"new character"+OR+"character trailer"+OR+"champion teaser")+when:2d',
        'site:reddit.com/r/*+("fanart"+OR+"cosplay")+("reveal"+OR+"teaser"+OR+"skin"+OR+"new")+when:2d'
    ]
    for dq in discovery_queries:
        try:
            url = f"https://news.google.com/rss/search?q={dq}&hl=en-US&gl=US&ceid=US:en"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                feed = feedparser.parse(res.content)
                for entry in feed.entries[:8]:
                    title = entry.title.split(" - ")[0].strip()
                    if not any(ex in title.lower() for ex in exclude_keywords) and len(title) > 10:
                        results.append(f"[Reddit Global Hype]: {title}")
        except Exception:
            pass
        time.sleep(0.1)

    return list(dict.fromkeys(results))[:50]


def fetch_bluesky_dynamic():
    """Сбор Bluesky по общевирусным арт- и игровым маркерам"""
    results = []
    queries = [
        "character reveal", "drip marketing", "character teaser",
        "new character", "game fanart", "waifu fanart", "concept art", "playable character"
    ]
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    # Прямой опрос API
    for q in queries:
        try:
            res = requests.get(
                "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
                params={"q": q, "limit": 15},
                headers=headers,
                timeout=5
            )
            if res.status_code == 200:
                for p in res.json().get('posts', []):
                    record = p.get('record', {})
                    text = record.get('text', '').replace('\n', ' ').strip()
                    likes = p.get('likeCount', 0)
                    if likes >= 10 and len(text) > 12:
                        results.append(f"[Bluesky | ❤️{likes}]: {text[:130]}")
        except Exception:
            pass
        time.sleep(0.1)

    # Зеркальный шлюз при лимитах
    if len(results) < 8:
        gw_queries = [
            "site:bsky.app+(" + "+OR+".join(["fanart", "character+reveal", "drip+marketing", "concept+art"]) + ")+when:3d"
        ]
        for gq in gw_queries:
            try:
                gw_url = f"https://news.google.com/rss/search?q={gq}&hl=en-US&gl=US&ceid=US:en"
                res = requests.get(gw_url, headers=headers, timeout=5)
                if res.status_code == 200:
                    for entry in feedparser.parse(res.content).entries[:10]:
                        title = entry.title.split(" - ")[0].strip()
                        if len(title) > 10:
                            results.append(f"[Bluesky Signal]: {title}")
            except Exception:
                pass

    return list(dict.fromkeys(results))[:40]


def fetch_bilibili_dynamic():
    """Сбор трендов Bilibili по всему игровому сектору (rid=4) без привязки к тайтлам"""
    results = []
    # Категории: 4 (Все игры), 119 (Мобильные), 17 (Синглплеер)
    for rid in [4, 119, 17]:
        url = f"https://api.bilibili.com/x/web-interface/ranking/v2?rid={rid}&type=all"
        try:
            res = scraper.get(url, timeout=6)
            if res.status_code == 200:
                for item in res.json().get('data', {}).get('list', [])[:12]:
                    title = item.get('title', '')
                    views = item.get('stat', {}).get('view', 0)
                    views_k = f"{views // 1000}k" if views > 1000 else str(views)
                    results.append(f"[Bilibili Hot (CN) | 👁️{views_k}]: {title}")
        except Exception:
            pass
        time.sleep(0.15)
        
    return list(dict.fromkeys(results))[:30]


def fetch_gaming_media_dynamic():
    """Сбор всех игровых новостей без фильтра по названиям игр"""
    feeds = [
        "https://www.gematsu.com/feed",
        "https://www.siliconera.com/feed",
        "https://animecorner.me/feed/",
        "https://noisypixel.net/feed/",
        "https://automaton-media.com/en/feed/"
    ]
    results = []
    hype_markers = ["character", "trailer", "announce", "leak", "reveal", "gameplay", "update", "visual", "teaser", "champion", "fighter"]
    
    for u in feeds:
        try:
            res = scraper.get(u, timeout=5)
            if res.status_code == 200:
                for entry in feedparser.parse(res.content).entries[:10]:
                    title = entry.title
                    if any(m in title.lower() for m in hype_markers):
                        results.append(f"[Gaming Media]: {title}")
        except Exception:
            continue
    return list(dict.fromkeys(results))[:40]


def fetch_youtube_dynamic(api_key):
    """Сбор YouTube по отраслевым маркерам трейлеров и анонсов"""
    if not api_key: return []
    time_limit = (datetime.utcnow() - timedelta(days=3)).isoformat() + "Z"
    queries = [
        "official character trailer", "character reveal trailer",
        "character demo", "new playable character showcase", "new champion teaser"
    ]
    results = []
    for q in queries:
        params = {
            "part": "snippet", "q": q, "type": "video", 
            "videoCategoryId": "20", "publishedAfter": time_limit, 
            "maxResults": 4, "key": api_key
        }
        try:
            res = scraper.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=6)
            if res.status_code == 200:
                for item in res.json().get('items', []):
                    results.append(f"[YouTube Trending]: {item['snippet']['title']}")
        except Exception:
            pass
    return results[:25]


def run_all_sources():
    feed = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(fetch_reddit_dynamic),
            executor.submit(fetch_bluesky_dynamic),
            executor.submit(fetch_bilibili_dynamic),
            executor.submit(fetch_gaming_media_dynamic),
            executor.submit(fetch_youtube_dynamic, youtube_key)
        ]
        for f in as_completed(futures):
            feed.extend(f.result())
            
    return list(set([item for item in feed if len(item) > 8]))

# ==========================================
# ДИНАМИЧЕСКИЙ ПОДБОР МОДЕЛЕЙ (PRO -> FLASH)
# ==========================================
def get_prioritized_models(api_key):
    fallback_models = [
        "gemini-2.5-pro", "gemini-2.0-pro-exp-02-05", "gemini-1.5-pro-latest", "gemini-1.5-pro",
        "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-flash"
    ]
    blacklisted = ["tts", "audio", "image", "imagen", "veo", "banana", "embed", "deep-research", "live", "translate"]
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res = scraper.get(url, timeout=8)
        if res.status_code == 200:
            models_data = res.json().get('models', [])
            pro_models, flash_models = [], []
            
            for m in models_data:
                name = m.get('name', '').replace('models/', '')
                methods = m.get('supportedGenerationMethods', [])
                if name.startswith('gemini-') and 'generateContent' in methods:
                    if not any(b in name.lower() for b in blacklisted):
                        if 'pro' in name.lower(): pro_models.append(name)
                        elif 'flash' in name.lower(): flash_models.append(name)
            
            def extract_ver(m_name):
                match = re.search(r'gemini-(\d+(?:\.\d+)?)', m_name)
                return float(match.group(1)) if match else 0.0

            pro_models.sort(key=extract_ver, reverse=True)
            flash_models.sort(key=extract_ver, reverse=True)
            
            discovered = pro_models + flash_models
            if discovered: return discovered
    except Exception:
        pass
    return fallback_models


def analyze_hype_feed(feed_dump, key, nsfw_enabled):
    models_to_try = get_prioritized_models(key)
    current_date = datetime.now().strftime("%Y-%m-%d")
    spicy_instruction = 'В массив "spicy_top" добавь от 3 до 8 ЖЕНСКИХ персонажей с вирусным фансервисом, опираясь ТОЛЬКО на предоставленные сигналы.' if nsfw_enabled else 'Массив "spicy_top" оставь пустым.'

    prompt = f"""
    ТЫ — ГЛАВНЫЙ АРТ-ПРОДЮСЕР, АНАЛИТИК ТРЕНДОВ И ЭКСПЕРТ ПО АЛГОРИТМАМ СОЦСЕТЕЙ.
    Сегодня {current_date}.
    Твоя задача — выявить САМЫХ ВИРАЛЬНЫХ ЖЕНСКИХ ПЕРСОНАЖЕЙ из любых игр (Gacha, AAA, MOBA, Fighting, Indie и др.) на основе предоставленных сырых данных.
    Фанарт будет публиковаться на 15+ платформах (включая LOFTER, Rednote, Pixiv, Twitter/X, Reddit).

    ВХОДНЫЕ СИГНАЛЫ (Reddit, Bluesky, Bilibili, YouTube, СМИ):
    {json.dumps(feed_dump, ensure_ascii=False)}

    🔥 ЖЕСТКИЕ ПРАВИЛА (ANTI-HALLUCINATION & GROUNDING):
    1. СТРОГАЯ ПРИВЯЗКА К СИГНАЛАМ: Анализируй ВСЕ игры, упомянутые во входных данных. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО выдумывать персонажей, если в сигналах нет инфоповода по ним.
    2. ТОЛЬКО ЖЕНСКИЕ ПЕРСОНАЖИ.
    3. РАЗДЕЛЕНИЕ ПО КАТЕГОРИЯМ:
       - "gacha_top": персонажи мобильных и сервисных гача-игр.
       - "other_games_top": персонажи любых других игр (League of Legends, Resident Evil, Fighting, RPG, PC/Консоли).
    4. ЕСЛИ ДАННЫХ НЕДОСТАТОЧНО: Верни ровно столько персонажей, сколько подтверждено сигналами. Не добавляй вымышленных для заполнения списка.
    {spicy_instruction}

    ВЕРНИ ОТВЕТ СТРОГО В JSON:
    {{
      "absolute_leader": {{
        "name": "Имя героини",
        "game": "Игра (любой проект)",
        "virality_score": 99,
        "past_72h_event": "В чем заключается хайп (анонс/слив/патч/трейлер)",
        "source_signal": "Точный источник из входных данных",
        "why_draw_today": "Почему публикация арта именно сегодня даст взрывной рост аудитории",
        "tags": ["trending", "waifu", "имяперсонажа"]
      }},
      "spicy_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "analysis": "Причина фансервис-хайпа", "source_signal": "Источник", "score": 96, "tags": ["spicy"] }}
      ],
      "gacha_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "score": 98, "source_signal": "Источник хайпа", "reason": "Причина" }}
      ],
      "other_games_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "score": 97, "source_signal": "Источник хайпа", "reason": "Причина" }}
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
            resp = scraper.post(url, headers=headers, json=payload, timeout=75)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match: return json.loads(json_match.group()), model_name
                else: return json.loads(raw_text), model_name
            else:
                last_err = f"[{model_name}] {resp.status_code}: {resp.text[:100]}"
        except Exception as e:
            last_err = f"[{model_name}] Ошибка: {str(e)}"
            continue

    raise RuntimeError(f"Сбой ИИ-моделей: {last_err}")

# ==========================================
# ИНТЕРФЕЙС STREAMLIT
# ==========================================
if st.button("🚀 Запустить Hype-Scan (Динамический сбор)", type="primary", use_container_width=True):
    if not gemini_key:
        st.error("⚠️ Добавьте GEMINI_API_KEY в конфигурацию.")
    else:
        status_container = st.status("📡 Динамический сбор по всем каналам индустрии...", expanded=True)
        try:
            status_container.write("1. 🟢 Сквозной сбор Reddit (Агрегаторы + Глобальный поиск)...")
            status_container.write("2. 🟢 Сбор Bluesky по открытым маркерам...")
            status_container.write("3. 🟢 Сбор трендов Bilibili Gaming...")
            status_container.write("4. 🟢 Сбор СМИ и YouTube анонсов...")
            
            raw_feed = run_all_sources()
            
            if len(raw_feed) < 5:
                status_container.update(label="❌ Собрано слишком мало данных. Попробуйте еще раз через минуту.", state="error")
                st.stop()
                
            status_container.write(f"✅ Успешно собрано {len(raw_feed)} уникальных сигналов индустрии.")
            status_container.write("🧠 Определение актуальной модели Gemini и запуск анализа...")
            
            ai_results, used_model = analyze_hype_feed(raw_feed, gemini_key, is_16_plus)
            
            st.session_state.update({
                'omni_results': ai_results,
                'raw_feed': raw_feed,
                'used_model': used_model,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'scan_done': True
            })
            status_container.update(label=f"Анализ завершен! Использована модель: {used_model}", state="complete", expanded=False)
        except Exception as e:
            status_container.update(label="Ошибка сбора или анализа", state="error", expanded=True)
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
<div style="text-transform: uppercase; letter-spacing: 2px; font-size: 12px; margin-bottom: 6px; color: #fbbf24;">👑 Максимальный виральный потенциал на сегодня</div>
<div class="hero-title">{leader.get('name', 'Нет данных')} <span style="font-size:20px; font-weight:400; opacity:0.85; color:#cbd5e1;">— {leader.get('game', 'Нет данных')}</span></div>
<div style="font-size: 15px; margin: 4px 0 10px 0;">Индекс виральности: <b>{leader.get('virality_score', 0)}/100</b></div>
<div class="fact-box">📡 <b>В чем суть хайпа:</b> {leader.get('past_72h_event', 'Отсутствует')}</div>
<div class="fact-box">📊 <b>Подтверждение (Сигнал):</b> {leader.get('source_signal', 'Не указано')}</div>
<div style="background: rgba(15, 23, 42, 0.7); padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-top: 8px; border-left: 4px solid #f59e0b;">
💡 <b>Стратегия роста:</b> {leader.get('why_draw_today', 'Пик внимания')}
</div>
<div style="margin-top: 14px;">{tags_html}</div>
</div>
        """, unsafe_allow_html=True)

    # 2. БЛОК 16+ SPICY
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    if is_16_plus and res.get('spicy_top'):
        st.subheader("🔞 Тренды 16+ (Виральный фансервис)")
        spicy_items = res.get('spicy_top', [])
        spicy_cols = st.columns(min(3, len(spicy_items)) if len(spicy_items) > 0 else 1)
        
        for idx, item in enumerate(spicy_items[:3]):
            with spicy_cols[idx]:
                st.markdown(f"""
<div class="spicy-card">
<h4 style="margin-bottom: 5px; color: #ff9ebf;">{medals[idx]} {item.get('name', '')} <span style="font-size:13px; color:#a5b1c2;">({item.get('game', '')})</span></h4>
<p style="font-size: 13px; color: #f1f5f9; margin-bottom: 6px;"><b>Хайп:</b> {item.get('analysis', '')}</p>
<p style="font-size: 12px; color: #f472b6; margin-bottom: 8px;">📡 <b>Сигнал:</b> {item.get('source_signal', '')}</p>
<div>{" ".join([f"<span class='badge spicy-badge'>#{t}</span>" for t in item.get('tags', [])])}</div>
</div>
                """, unsafe_allow_html=True)
        st.divider()

    # 3. ТОП ГАЧА VS ТОП ДРУГИЕ ИГРЫ
    col_gacha, col_other = st.columns(2)
    
    with col_gacha:
        gacha_list = res.get('gacha_top', [])
        st.subheader(f"🎲 Топ Гачи ({len(gacha_list)} подтвержденных)")
        for idx, item in enumerate(gacha_list):
            m_icon = medals[idx] if idx < len(medals) else f"{idx+1}."
            st.markdown(f"""
<div class="metric-card">
<h4 style="margin-bottom: 4px;">{m_icon} {item.get('name', '')} <span style="font-size:13px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 13px; color: #cbd5e1; margin-bottom: 4px;"><b>Событие:</b> {item.get('reason', '')}</p>
<p style="font-size: 12px; color: #38bdf8; margin: 0;">📊 <b>Сигнал:</b> {item.get('source_signal', '')}</p>
</div>
            """, unsafe_allow_html=True)

    with col_other:
        other_list = res.get('other_games_top', [])
        st.subheader(f"⚔️ Топ Другие Игры / AAA / MOBA ({len(other_list)} подтвержденных)")
        for idx, item in enumerate(other_list):
            m_icon = medals[idx] if idx < len(medals) else f"{idx+1}."
            st.markdown(f"""
<div class="metric-card">
<h4 style="margin-bottom: 4px;">{m_icon} {item.get('name', '')} <span style="font-size:13px; color:#888;">({item.get('game', '')})</span> — {item.get('score', 0)}/100</h4>
<p style="font-size: 13px; color: #cbd5e1; margin-bottom: 4px;"><b>Событие:</b> {item.get('reason', '')}</p>
<p style="font-size: 12px; color: #f59e0b; margin: 0;">📊 <b>Сигнал:</b> {item.get('source_signal', '')}</p>
</div>
            """, unsafe_allow_html=True)

    # 4. СЫРОЙ ПОТОК
    with st.expander(f"🔍 Лог собранных данных ({len(st.session_state.get('raw_feed', []))} записей)"):
        feed = st.session_state.get('raw_feed', [])
        st.markdown('<div class="log-box">' + "<br>".join(feed) + '</div>', unsafe_allow_html=True)
