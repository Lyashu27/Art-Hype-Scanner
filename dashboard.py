import streamlit as st
import pandas as pd
import json
import time
from datetime import datetime, timedelta, timezone
from collections import Counter
import feedparser
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import cloudscraper
import requests
import random

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="🔥 Waifu Art Hype Radar PRO (Max Reach Edition)", page_icon="📈", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 16px; border-radius: 12px; border-left: 5px solid #4b8bff; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .spicy-card {background-color: #25181e; padding: 16px; border-radius: 12px; border-left: 5px solid #ff4b8b; margin-bottom: 12px; box-shadow: 0 4px 6px rgba(255, 75, 139, 0.15);}
    .hero-card {background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 26px; border-radius: 16px; margin-bottom: 20px; color: white; border: 1px solid #3b82f6; box-shadow: 0 10px 25px rgba(59, 130, 246, 0.25);}
    .hero-title {font-size: 28px; font-weight: 800; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 1px; color: #60a5fa;}
    .fact-box {background: rgba(15, 23, 42, 0.7); padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-top: 8px; border-left: 4px solid #38bdf8;}
    .hook-box {background: rgba(16, 185, 129, 0.12); padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-top: 8px; border-left: 4px solid #10b981; color: #d1fae5;}
    .badge {background-color: #1e293b; padding: 3px 8px; border-radius: 6px; font-size: 12px; margin-right: 5px; color: #93c5fd; border: 1px solid #334155; display: inline-block; margin-bottom: 4px;}
    .spicy-badge {background-color: #3b1c28; color: #ff9ebf; border-color: #ff4b8b;}
    .log-box {background-color: #000; color: #0f0; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 11px; max-height: 280px; overflow-y: auto;}
</style>
""", unsafe_allow_html=True)

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
gemini_key = st.secrets.get("GEMINI_API_KEY", "")
youtube_key = st.secrets.get("YOUTUBE_API_KEY", "")

st.title("📈 Omni-Channel Art Hype Radar PRO (Максимальные охваты)")
st.markdown("Точный поиск виральных героинь на основе **реальных метрик вовлеченности** (Danbooru, Pixiv, Reddit JSON, Bilibili, Bluesky, YouTube, Leaks).")

with st.sidebar:
    st.header("⚙️ Параметры Виральности")
    is_16_plus = st.toggle("🔞 Режим 16+ (Spicy / Фансервис-триггеры)", value=True)
    focus_mode = st.selectbox(
        "🎯 Стратегия охватов",
        [
            "🚀 Ранний перехват (Анонсы, сливы, первые 48ч — минимум конкуренции)",
            "🔥 Пиковый хайп (Максимальный трафик прямо сейчас)",
            "⚖️ Сбалансированный (Тренды + Новые анонсы)"
        ]
    )
    st.divider()
    st.header("📡 Активные Радары")
    st.write(f"⚡ Gemini Engine: {'🟢 Активен' if gemini_key else '🔴 Нет ключа'}")
    st.write(f"📺 YouTube Metrics API: {'🟢 Активен' if youtube_key else '⚪ Выключен'}")
    st.write("🎨 Danbooru & Pixiv Velocity: 🟢 Активны")
    st.write("🕵️ Leak & Design Hubs: 🟢 Активны")

# ==========================================
# ВЫСОКОТОЧНЫЕ ПАРСЕРЫ С РЕАЛЬНЫМИ МЕТРИКАМИ
# ==========================================

def fetch_danbooru_velocity():
    """Сбор самых быстрорастущих персонажей за 24ч через открытый API Danbooru Popular"""
    results = []
    headers = {'User-Agent': 'ArtHypeRadar/2.0 ( Analytics)'}
    char_counter = Counter()
    char_copyright = {}
    char_scores = Counter()

    try:
        url = "https://danbooru.donmai.us/explore/posts/popular.json?limit=100"
        res = requests.get(url, headers=headers, timeout=6)
        if res.status_code == 200:
            posts = res.json()
            for post in posts:
                chars = post.get('tag_string_character', '').split()
                copy_tags = post.get('tag_string_copyright', '').split()
                score = post.get('score', 0) + post.get('fav_count', 0)
                main_copy = copy_tags[0] if copy_tags else "unknown"
                for c in chars:
                    if c not in ["original", "custom_character"]:
                        char_counter[c] += 1
                        char_scores[c] += score
                        if c not in char_copyright:
                            char_copyright[c] = main_copy

            for char, count in char_counter.most_common(18):
                game = char_copyright.get(char, '')
                total_eng = char_scores[char]
                results.append(f"[Danbooru 24h Viral | 🎨 {count} top arts | ❤️Score: {total_eng}]: Character '{char}' from '{game}'")
    except Exception:
        pass
    return results


def fetch_pixiv_rankings(nsfw_enabled):
    """Сбор ежедневного чарта Pixiv (Япония/Азия) — главный индикатор азиатского трафика"""
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
        'Referer': 'https://www.pixiv.net/ranking.php'
    }
    modes = ["daily", "male"]  # 'male' идеально отражает спрос на женских персонажей (waifu)
    for mode in modes:
        try:
            url = f"https://www.pixiv.net/ranking.php?mode={mode}&content=illust&p=1&format=json"
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200:
                contents = res.json().get('contents', [])[:15]
                for item in contents:
                    title = item.get('title', '')
                    tags = ", ".join(item.get('tags', [])[:6])
                    views = item.get('view_count', 0)
                    bookmarks = item.get('rating_count', 0)
                    rank = item.get('rank', 0)
                    results.append(f"[Pixiv {mode.upper()} #{rank} | 👁️{views} ❤️{bookmarks}]: {title} (Tags: {tags})")
        except Exception:
            pass
    return list(dict.fromkeys(results))[:25]


def fetch_reddit_metrics():
    """Сбор Reddit через JSON с реальными апвоутами + сабреддиты сливов и дизайна"""
    results = []
    headers = {'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 RadarBot/{random.randint(1000,9999)}'}
    exclude_keywords = ["megathread", "daily question", "weekly", "troubleshooting", "maintenance", "giveaway", "mod post", "code"]

    # Включаем как общие хабы, так и главные источники ранних сливов и дизайна персонажей
    hubs = [
        "gachagaming", "TopCharacterDesigns", "AnimeART", "Games",
        "Genshin_Impact_Leaks", "HonkaiStarRail_leaks", "Zenlesszonezeroleaks_",
        "WutheringWavesLeaks", "StreetFighter", "Tekken", "cosplay"
    ]
    for hub in hubs:
        url = f"https://www.reddit.com/r/{hub}/top.json?t=day&limit=8"
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                children = res.json().get('data', {}).get('children', [])
                for post in children:
                    data = post.get('data', {})
                    title = data.get('title', '').strip()
                    ups = data.get('ups', 0)
                    comms = data.get('num_comments', 0)
                    if ups >= 150 and not any(ex in title.lower() for ex in exclude_keywords):
                        results.append(f"[Reddit r/{hub} | ⬆️{ups} 💬{comms}]: {title}")
        except Exception:
            pass
        time.sleep(0.1)

    # Глобальный поиск свежих анонсов и drip-маркетинга за 48ч
    discovery_queries = [
        'site:reddit.com/r/*+("drip marketing"+OR+"character reveal"+OR+"new playable"+OR+"character trailer"+OR+"new skin")+when:2d'
    ]
    for dq in discovery_queries:
        try:
            url = f"https://news.google.com/rss/search?q={dq}&hl=en-US&gl=US&ceid=US:en"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                feed = feedparser.parse(res.content)
                for entry in feed.entries[:10]:
                    title = entry.title.split(" - ")[0].strip()
                    if not any(ex in title.lower() for ex in exclude_keywords) and len(title) > 10:
                        results.append(f"[Reddit Global Drip/Reveal]: {title}")
        except Exception:
            pass

    return list(dict.fromkeys(results))[:45]


def fetch_bluesky_top():
    """Сбор ТОПОВЫХ постов Bluesky с сортировкой sort='top' и фильтром высокой виральности"""
    results = []
    queries = [
        "character reveal", "drip marketing", "fanart", "new skin",
        "waifu", "character design", "genshin", "star rail", "zzz", "wuthering waves"
    ]
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

    for q in queries:
        try:
            res = requests.get(
                "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
                params={"q": q, "sort": "top", "limit": 12},
                headers=headers,
                timeout=5
            )
            if res.status_code == 200:
                for p in res.json().get('posts', []):
                    record = p.get('record', {})
                    text = record.get('text', '').replace('\n', ' ').strip()
                    likes = p.get('likeCount', 0)
                    reposts = p.get('repostCount', 0)
                    if likes >= 80 and len(text) > 12:
                        results.append(f"[Bluesky Top | ❤️{likes} 🔁{reposts}]: {text[:140]}")
        except Exception:
            pass
        time.sleep(0.08)

    return list(dict.fromkeys(results))[:30]


def fetch_bilibili_dynamic():
    """Сбор трендов Bilibili (Китай) с просмотрами и комментариями"""
    results = []
    for rid in [4, 119, 17]:
        url = f"https://api.bilibili.com/x/web-interface/ranking/v2?rid={rid}&type=all"
        try:
            res = scraper.get(url, timeout=6)
            if res.status_code == 200:
                for item in res.json().get('data', {}).get('list', [])[:12]:
                    title = item.get('title', '')
                    views = item.get('stat', {}).get('view', 0)
                    likes = item.get('stat', {}).get('like', 0)
                    views_k = f"{views // 1000}k" if views > 1000 else str(views)
                    likes_k = f"{likes // 1000}k" if likes > 1000 else str(likes)
                    results.append(f"[Bilibili CN Hot | 👁️{views_k} 👍{likes_k}]: {title}")
        except Exception:
            pass
        time.sleep(0.1)
    return list(dict.fromkeys(results))[:30]


def fetch_gaming_media_dynamic():
    """Сбор профильных игровых и аниме-СМИ"""
    feeds = [
        "https://www.gematsu.com/feed",
        "https://www.siliconera.com/feed",
        "https://animecorner.me/feed/",
        "https://noisypixel.net/feed/",
        "https://automaton-media.com/en/feed/"
    ]
    results = []
    hype_markers = ["character", "trailer", "announce", "leak", "reveal", "skin", "update", "visual", "teaser", "outfit", "figure"]

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
    return list(dict.fromkeys(results))[:30]


def fetch_youtube_with_views(api_key):
    """Сбор YouTube с сортировкой по просмотрам (viewCount) и точным числом просмотров"""
    if not api_key:
        return []
    time_limit = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    queries = [
        "character trailer", "character demo", "character reveal", "drip marketing", "new skin showcase"
    ]
    video_ids = []
    snippets = {}

    for q in queries:
        params = {
            "part": "snippet", "q": q, "type": "video",
            "order": "viewCount", "videoCategoryId": "20",
            "publishedAfter": time_limit, "maxResults": 5, "key": api_key
        }
        try:
            res = scraper.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=6)
            if res.status_code == 200:
                for item in res.json().get('items', []):
                    vid = item['id']['videoId']
                    video_ids.append(vid)
                    snippets[vid] = item['snippet']['title']
        except Exception:
            pass

    results = []
    if video_ids:
        unique_ids = list(dict.fromkeys(video_ids))[:25]
        stats_params = {"part": "statistics", "id": ",".join(unique_ids), "key": api_key}
        try:
            stats_res = scraper.get("https://www.googleapis.com/youtube/v3/videos", params=stats_params, timeout=6)
            if stats_res.status_code == 200:
                for item in stats_res.json().get('items', []):
                    vid = item['id']
                    views = int(item.get('statistics', {}).get('viewCount', 0))
                    likes = int(item.get('statistics', {}).get('likeCount', 0))
                    if views >= 10000:
                        results.append(f"[YouTube 72h Viral | 👁️{views:,} 👍{likes:,}]: {snippets.get(vid, '')}")
        except Exception:
            for vid in unique_ids:
                results.append(f"[YouTube Trending]: {snippets.get(vid, '')}")

    return results[:20]


def run_all_sources(nsfw_enabled):
    feed = []
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = [
            executor.submit(fetch_danbooru_velocity),
            executor.submit(fetch_pixiv_rankings, nsfw_enabled),
            executor.submit(fetch_reddit_metrics),
            executor.submit(fetch_bluesky_top),
            executor.submit(fetch_bilibili_dynamic),
            executor.submit(fetch_gaming_media_dynamic),
            executor.submit(fetch_youtube_with_views, youtube_key)
        ]
        for f in as_completed(futures):
            try:
                feed.extend(f.result())
            except Exception:
                pass

    return list(dict.fromkeys([item for item in feed if len(item) > 8]))

# ==========================================
# ДИНАМИЧЕСКИЙ ПОДБОР МОДЕЛЕЙ (PRO -> FLASH)
# ==========================================
def get_prioritized_models(api_key):
    fallback_models = [
        "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"
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


def analyze_hype_feed(feed_dump, key, nsfw_enabled, strategy):
    models_to_try = get_prioritized_models(key)
    current_date = datetime.now().strftime("%Y-%m-%d")
    spicy_instruction = (
        'В массив "spicy_top" добавь от 3 до 6 ЖЕНСКИХ персонажей с максимальным потенциалом вирусного фансервиса (16+), опираясь ТОЛЬКО на сигналы.'
        if nsfw_enabled else 'Массив "spicy_top" оставь пустым.'
    )

    prompt = f"""
    ТЫ — ГЛАВНЫЙ АРТ-ПРОДЮСЕР И АНАЛИТИК ВИРАЛЬНЫХ АЛГОРИТМОВ (Pixiv, X/Twitter, LOFTER, Rednote/Xiaohongshu, Reddit, Bilibili).
    Сегодня {current_date}. Выбранная стратегия художника: "{strategy}".

    ВХОДНЫЕ СИГНАЛЫ С РЕАЛЬНЫМИ МЕТРИКАМИ (Danbooru, Pixiv, Reddit, Bilibili, Bluesky, YouTube, СМИ):
    {json.dumps(feed_dump, ensure_ascii=False)}

    🔥 АЛГОРИТМ ОЦЕНКИ ВИРАЛЬНОСТИ (СТРОГИЕ ПРАВИЛА):
    1. ЗАПРЕТ НА ГАЛЛЮЦИНАЦИИ: Бери ТОЛЬКО тех женских персонажей, которые явно присутствуют во входных сигналах.
    2. ФОРМУЛА МАКСИМАЛЬНОГО ОХВАТА:
       - Высший приоритет (Score 95-100): КРОСС-ПЛАТФОРМЕННЫЙ ВЗРЫВ (персонаж есть и в новостях/сливах/трейлерах Reddit/YouTube, И одновременно растет в Danbooru/Pixiv/Bilibili).
       - Высокий приоритет (Score 88-94): Свежий анонс / Drip Marketing / Слив нового скина или персонажа за последние 48 часов (эффект Первого Движения — спрос огромный, артов еще мало).
    3. ВИЗУАЛЬНЫЙ ТРИГГЕР (visual_hook): Обязательно укажи, ЧТО ИМЕННО нужно нарисовать для взрыва алгоритмов (конкретный новый костюм, мемная эмоция, поза из трейлера, контрастная деталь дизайна).
    4. МУЛЬТИЯЗЫЧНЫЕ ТЕГИ: Для публикации на 15+ площадках выдай точные теги на 3 языках: EN (для X/Reddit/Danbooru), JP (кандзи/катакана для Pixiv и JP X) и CN (для LOFTER, Rednote, Bilibili).
    {spicy_instruction}

    ВЕРНИ ОТВЕТ СТРОГО В JSON:
    {{
      "absolute_leader": {{
        "name": "Имя героини (EN / RU)",
        "game": "Название игры/франшизы",
        "virality_score": 99,
        "hype_phase": "🚀 Ранний взрыв (Голубой океан) ИЛИ 🔥 Пик трафика",
        "past_72h_event": "Точный инфоповод за последние 72 часа",
        "source_signal": "Конкретные сигналы и цифры (например: Reddit 4.2k ups + Pixiv Daily #3 + Danbooru 12 top arts)",
        "visual_hook": "Конкретное ТЗ для художника: какой образ/костюм/ракурс/эмоцию нарисовать сегодня для максимального CTR",
        "why_draw_today": "Почему публикация в ближайшие 24 часа даст максимальный охват",
        "tags_en": ["CharacterName", "GameName", "fanart"],
        "tags_jp": ["キャラ名", "ゲーム名"],
        "tags_cn": ["角色名", "游戏名"]
      }},
      "spicy_top": [
        {{
          "rank": 1,
          "name": "Персонаж",
          "game": "Игра",
          "score": 96,
          "analysis": "В чем заключается фансервис-триггер",
          "visual_hook": "Какой акцент/образ сделать на арте",
          "source_signal": "Источник и цифры",
          "tags_multi": ["#TagEN", "#タグJP", "#标签CN"]
        }}
      ],
      "gacha_top": [
        {{
          "rank": 1,
          "name": "Персонаж",
          "game": "Гача-игра",
          "score": 98,
          "reason": "Инфоповод",
          "visual_hook": "Идея для вирального арта",
          "source_signal": "Источник с метриками",
          "tags_multi": ["#TagEN", "#タグJP", "#标签CN"]
        }}
      ],
      "other_games_top": [
        {{
          "rank": 1,
          "name": "Персонаж",
          "game": "AAA / Fighting / MOBA / RPG",
          "score": 95,
          "reason": "Инфоповод",
          "visual_hook": "Идея для вирального арта",
          "source_signal": "Источник с метриками",
          "tags_multi": ["#TagEN", "#タグJP", "#标签CN"]
        }}
      ]
    }}
    """

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.15}
    }

    last_err = ""
    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
            resp = scraper.post(url, headers=headers, json=payload, timeout=75)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group()), model_name
                return json.loads(raw_text), model_name
            else:
                last_err = f"[{model_name}] {resp.status_code}: {resp.text[:100]}"
        except Exception as e:
            last_err = f"[{model_name}] Ошибка: {str(e)}"
            continue

    raise RuntimeError(f"Сбой ИИ-моделей: {last_err}")

# ==========================================
# ИНТЕРФЕЙС STREAMLIT
# ==========================================
if st.button("🚀 Запустить PRO Hype-Scan (Анализ метрик и арт-чартов)", type="primary", use_container_width=True):
    if not gemini_key:
        st.error("⚠️ Добавьте GEMINI_API_KEY в st.secrets.")
    else:
        status_container = st.status("📡 Сбор твердых метрик по 7 каналам индустрии...", expanded=True)
        try:
            status_container.write("1. 🎨 Сбор скорости появления артов в Danbooru Popular (24h)...")
            status_container.write("2. 🇯🇵 Сбор чартов Pixiv Daily & Male Ranking...")
            status_container.write("3. 🔥 Сбор Reddit JSON (реальные апвоуты + сабреддиты сливов и дизайна)...")
            status_container.write("4. 🦋 Сбор топовых постов Bluesky (sort=top) и трендов Bilibili CN...")
            status_container.write("5. 📺 Сбор YouTube-трейлеров по просмотрам и игровых СМИ...")

            raw_feed = run_all_sources(is_16_plus)

            if len(raw_feed) < 5:
                status_container.update(label="❌ Собрано слишком мало данных. Попробуйте еще раз через минуту.", state="error")
                st.stop()

            status_container.write(f"✅ Собрано {len(raw_feed)} верифицированных сигналов с метриками.")
            status_container.write("🧠 Кросс-платформенный анализ виральности через Gemini...")

            ai_results, used_model = analyze_hype_feed(raw_feed, gemini_key, is_16_plus, focus_mode)

            st.session_state.update({
                'omni_results': ai_results,
                'raw_feed': raw_feed,
                'used_model': used_model,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'scan_done': True
            })
            status_container.update(label=f"Анализ завершен! Модель: {used_model}", state="complete", expanded=False)
        except Exception as e:
            status_container.update(label="Ошибка сбора или анализа", state="error", expanded=True)
            st.error(e)

if st.session_state.get('scan_done', False):
    res = st.session_state['omni_results']
    st.caption(f"⏱️ **Срез:** {st.session_state['timestamp']} | 📊 **Сигналов с метриками:** {len(st.session_state.get('raw_feed', []))} | 🧠 **Модель:** `{st.session_state.get('used_model', 'N/A')}`")

    # 1. АБСОЛЮТНЫЙ ЛИДЕР
    leader = res.get('absolute_leader', {})
    if leader:
        en_tags = " ".join([f"<span class='badge'>🇺🇸 #{t}</span>" for t in leader.get('tags_en', [])])
        jp_tags = " ".join([f"<span class='badge'>🇯🇵 #{t}</span>" for t in leader.get('tags_jp', [])])
        cn_tags = " ".join([f"<span class='badge'>🇨🇳 #{t}</span>" for t in leader.get('tags_cn', [])])

        st.markdown(f"""
<div class="hero-card">
<div style="text-transform: uppercase; letter-spacing: 2px; font-size: 12px; margin-bottom: 6px; color: #fbbf24;">
👑 Абсолютный лидер охватов • {leader.get('hype_phase', 'Пик виральности')}
</div>
<div class="hero-title">{leader.get('name', 'Нет данных')} <span style="font-size:20px; font-weight:400; opacity:0.85; color:#cbd5e1;">— {leader.get('game', 'Нет данных')}</span></div>
<div style="font-size: 15px; margin: 4px 0 10px 0;">Индекс виральности: <b>{leader.get('virality_score', 0)}/100</b></div>
<div class="fact-box">📡 <b>Инфоповод (72ч):</b> {leader.get('past_72h_event', 'Отсутствует')}</div>
<div class="fact-box">📊 <b>Твердые метрики (Сигналы):</b> {leader.get('source_signal', 'Не указано')}</div>
<div class="hook-box">🎨 <b>ЧТО РИСОВАТЬ (Визуальный хук для алгоритмов):</b> {leader.get('visual_hook', 'Новый образ из анонса')}</div>
<div style="background: rgba(15, 23, 42, 0.7); padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-top: 8px; border-left: 4px solid #f59e0b;">
💡 <b>Почему даст максимум охватов сегодня:</b> {leader.get('why_draw_today', 'Пик внимания')}
</div>
<div style="margin-top: 14px;">{en_tags} {jp_tags} {cn_tags}</div>
</div>
        """, unsafe_allow_html=True)

    # 2. БЛОК 16+ SPICY
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    if is_16_plus and res.get('spicy_top'):
        st.subheader("🔞 Тренды 16+ (Виральный фансервис и высокий CTR)")
        spicy_items = res.get('spicy_top', [])
        spicy_cols = st.columns(min(3, len(spicy_items)) if len(spicy_items) > 0 else 1)

        for idx, item in enumerate(spicy_items[:3]):
            with spicy_cols[idx % 3]:
                st.markdown(f"""
<div class="spicy-card">
<h4 style="margin-bottom: 5px; color: #ff9ebf;">{medals[idx]} {item.get('name', '')} <span style="font-size:13px; color:#a5b1c2;">({item.get('game', '')}) — {item.get('score', 0)}/100</span></h4>
<p style="font-size: 13px; color: #f1f5f9; margin-bottom: 5px;"><b>Триггер:</b> {item.get('analysis', '')}</p>
<p style="font-size: 13px; color: #6ee7b7; margin-bottom: 5px;">🎨 <b>Хук:</b> {item.get('visual_hook', '')}</p>
<p style="font-size: 12px; color: #f472b6; margin-bottom: 8px;">📡 <b>Метрики:</b> {item.get('source_signal', '')}</p>
<div>{" ".join([f"<span class='badge spicy-badge'>{t}</span>" for t in item.get('tags_multi', [])])}</div>
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
<p style="font-size: 13px; color: #cbd5e1; margin-bottom: 4px;"><b>Инфоповод:</b> {item.get('reason', '')}</p>
<p style="font-size: 13px; color: #6ee7b7; margin-bottom: 4px;">🎨 <b>Что рисовать:</b> {item.get('visual_hook', '')}</p>
<p style="font-size: 12px; color: #38bdf8; margin-bottom: 6px;">📊 <b>Метрики:</b> {item.get('source_signal', '')}</p>
<div>{" ".join([f"<span class='badge'>{t}</span>" for t in item.get('tags_multi', [])])}</div>
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
<p style="font-size: 13px; color: #cbd5e1; margin-bottom: 4px;"><b>Инфоповод:</b> {item.get('reason', '')}</p>
<p style="font-size: 13px; color: #6ee7b7; margin-bottom: 4px;">🎨 <b>Что рисовать:</b> {item.get('visual_hook', '')}</p>
<p style="font-size: 12px; color: #f59e0b; margin-bottom: 6px;">📊 <b>Метрики:</b> {item.get('source_signal', '')}</p>
<div>{" ".join([f"<span class='badge'>{t}</span>" for t in item.get('tags_multi', [])])}</div>
</div>
            """, unsafe_allow_html=True)

    # 4. СЫРОЙ ПОТОК
    with st.expander(f"🔍 Лог собранных сигналов с метриками ({len(st.session_state.get('raw_feed', []))} записей)"):
        feed = st.session_state.get('raw_feed', [])
        st.markdown('<div class="log-box">' + "<br>".join(feed) + '</div>', unsafe_allow_html=True)
