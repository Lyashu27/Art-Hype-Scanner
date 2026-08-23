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
import math

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
nexus_key = st.secrets.get("NEXUSMODS_API_KEY", "")

st.title("🔥 Omni-Channel Art Hype Radar: Strict PRO Edition")
st.markdown("Предиктивный радар виральности женских персонажей. Исключительно текстовые Pro-модели.")

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("⚙️ Параметры Сбора")
    is_16_plus = st.toggle("🔞 Режим 16+ (Spicy / Фансервис / Моды)", value=True)
    scan_depth = st.slider("Глубина парсинга", min_value=1, max_value=3, value=2)
    st.divider()
    st.header("📡 Состояние Каналов")
    st.write(f"🧠 Gemini Core: {'🟢 Активен' if gemini_key else '🔴 Нет ключа'}")
    st.write(f"🤖 Telegram Bot: {'🟢 Подключен' if tg_bot_token else '⚪ Выключен'}")
    st.write(f"🛡️ NexusMods Trending: {'🟢 Активен' if nexus_key else '⚪ Выключен'}")

# ==========================================
# УТИЛИТЫ ДЛЯ СБОРА
# ==========================================
@st.cache_data(ttl=7200)
def get_dynamic_trending_games():
    games = ["Genshin", "Honkai Star Rail", "Zenless Zone Zero", "Wuthering Waves", "Nikke", "Snowbreak", "Resident Evil", "Cyberpunk", "Stellar Blade", "Final Fantasy", "Blue Archive", "Azur Lane"]
    if twitch_id and twitch_secret:
        try:
            token_url = f"https://id.twitch.tv/oauth2/token?client_id={twitch_id}&client_secret={twitch_secret}&grant_type=client_credentials"
            token = requests.post(token_url, timeout=5).json().get('access_token', '')
            if token:
                res = requests.get("https://api.twitch.tv/helix/games/top?first=15", headers={"Client-ID": twitch_id, "Authorization": f"Bearer {token}"}, timeout=8)
                if res.status_code == 200:
                    for g in res.json().get('data', []):
                        name = g.get('name')
                        if name not in games and name not in ["Just Chatting", "Special Events", "Music", "Art"]:
                            games.append(name)
        except:
            pass
    return list(set(games))

# ==========================================
# ФУНКЦИИ СБОРА ДАННЫХ
# ==========================================
def fetch_danbooru_velocity(depth):
    limit = 100 * depth
    url = f"https://danbooru.donmai.us/posts.json?limit={limit}&tags=1girl+age:<24h"
    results = []
    char_counts = Counter()
    try:
        res = requests.get(url, headers={'User-Agent': 'HypeRadarPro/7.0'}, timeout=15)
        if res.status_code == 200:
            for post in res.json():
                tags = post.get('tag_string', '')
                chars = post.get('tag_string_character', '').split()
                copyr = post.get('tag_string_copyright', '').split()
                score = post.get('score', 0)
                
                if 'comic' in tags or 'cartoon' in tags:
                    continue
                    
                weight = 1 + (score * 0.1) if score > 10 else 1
                
                for char in chars:
                    if char and char not in ["original", "unknown"]:
                        franchise = copyr[0] if copyr else "Unknown_Game"
                        full_tag = f"{char} ({franchise})"
                        char_counts[full_tag] += weight
                        
            for tag, score in char_counts.most_common(20):
                if score >= 3:
                    clean_name = tag.replace('_', ' ').title()
                    results.append(f"[Danbooru High Velocity]: {clean_name} (Индекс: {math.floor(score)})")
        else:
            results.append(f"[Danbooru Error]: Status {res.status_code}")
    except Exception as e:
        results.append(f"[Danbooru Exception]: {str(e)}")
    return results

def fetch_reddit_rss_fallback(depth):
    subs = [
        "Genshin_Impact_Leaks", "HonkaiStarRail_Leaks", "Zenlesszonezero_leaks_", 
        "WutheringWavesLeaks", "NikkeMobile", "BlueArchive", "Snowbreak", "gaming"
    ]
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    for sub in subs:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot/.rss"
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                feed = feedparser.parse(res.content)
                for entry in feed.entries[:5 + (depth*2)]:
                    title = entry.title
                    if any(kw in title.lower() for kw in ['leak', 'drip', 'model', 'render', 'banner', 'skin', 'art']):
                        results.append(f"[Reddit r/{sub} RSS]: {title}")
            else:
                results.append(f"[Reddit Error r/{sub}]: Status {res.status_code}")
        except Exception as e:
            results.append(f"[Reddit Exception r/{sub}]: {str(e)}")
        time.sleep(2.0)
    return results

def fetch_bilibili_hot():
    url = "https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=all"
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Referer': 'https://www.bilibili.com/'
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json().get('data', {}).get('list', [])[:20]
            for item in data:
                title = item.get('title', '')
                if any(kw in title for kw in ['原神', '星穹铁道', '绝区零', '崩坏', '鸣潮', '明日方舟', '碧蓝航线']):
                    results.append(f"[Bilibili Hot Trend (CN)]: {title}")
        else:
            results.append(f"[Bilibili Error]: Code {res.status_code}")
    except Exception as e:
        results.append(f"[Bilibili Exception]: {str(e)}")
    return results

def fetch_nexusmods_trending(api_key):
    if not api_key: 
        return ["[NexusMods]: API ключ не указан"]
    games = ["cyberpunk2077", "residentevil42023", "baldursgate3", "monsterhunterworld", "streetfighter6", "skyrimspecialedition"]
    results = []
    headers = {"accept": "application/json", "apikey": api_key, "User-Agent": "HypeRadar/7.0"}
    
    for game in games:
        try:
            res = requests.get(f"https://api.nexusmods.com/v1/games/{game}/mods/trending.json", headers=headers, timeout=10)
            if res.status_code == 200:
                mods = res.json()
                for mod in mods[:3]: 
                    name = mod.get('name', '')
                    summary = mod.get('summary', '')
                    if any(kw in name.lower() + summary.lower() for kw in ['outfit', 'body', 'hair', 'face', 'cbbe', 'girl', 'female', 'dress']):
                        results.append(f"[NexusMods {game} Top]: {name} - {summary}")
            elif res.status_code == 401:
                results.append("[NexusMods Error]: Неверный API ключ")
                break
        except Exception:
            pass
        time.sleep(0.5)
    return results

def fetch_youtube_targeted(api_key, depth):
    if not api_key: return ["[YouTube]: API ключ не указан"]
    time_limit = (datetime.utcnow() - timedelta(days=3)).isoformat() + "Z"
    dynamic_games = get_dynamic_trending_games()
    
    results = []
    queries = [
        " OR ".join(dynamic_games[:5]) + " (trailer OR teaser OR drip marketing OR female character)",
        " OR ".join(dynamic_games[5:10]) + " (trailer OR teaser OR female character)"
    ]
    
    for q_str in queries[:depth]:
        params = {
            "part": "snippet",
            "q": q_str,
            "type": "video",
            "videoCategoryId": "20",
            "publishedAfter": time_limit,
            "maxResults": 10,
            "key": api_key
        }
        try:
            res = requests.get("https://www.googleapis.com/youtube/v3/search", params=params, timeout=10)
            if res.status_code == 200:
                for item in res.json().get('items', []):
                    results.append(f"[YouTube Gaming]: {item['snippet']['title']}")
        except Exception as e:
            results.append(f"[YouTube Exception]: {str(e)}")
    return results

def fetch_bluesky_art(depth):
    queries = ["waifu fanart", "character leak splash", "new skin girl", "3dart character", "vtuber model 3d"]
    results = []
    for q in queries:
        try:
            res = requests.get(f"https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q={q}&limit={10 * depth}", timeout=10)
            if res.status_code == 200:
                for p in res.json().get('posts', []):
                    text = p.get('record', {}).get('text', '').replace('\n', ' ')[:150]
                    likes = p.get('likeCount', 0)
                    if likes >= 1: 
                        results.append(f"[Bluesky (+{likes}❤️)]: {text}")
        except Exception as e:
            results.append(f"[Bluesky Exception]: {str(e)}")
    return results

# ==========================================
# ИИ-АНАЛИЗАТОР (ЧИСТЫЕ TEXT PRO МОДЕЛИ)
# ==========================================
def get_clean_pro_models(api_key):
    """
    Возвращает ТОЛЬКО текстовые Pro-модели.
    Исключены любые TTS, Audio, Vision-only и Experimental с нулевой квотой.
    """
    allowed_pro_whitelist = [
        "gemini-1.5-pro-latest",
        "gemini-1.5-pro-002",
        "gemini-1.5-pro-001",
        "gemini-1.5-pro",
        "gemini-2.0-pro-exp-02-05",
        "gemini-pro"
    ]
    
    # Жесткий черный список любых медиа-суффиксов
    forbidden = ["tts", "audio", "voice", "speech", "image", "imagen", "veo", "lyria", "chirp", "deep-research", "embed", "aqa"]
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        res = requests.get(url, timeout=10)
        
        if res.status_code == 200:
            models_data = res.json().get('models', [])
            available_clean = []
            
            for m in models_data:
                name = m.get('name', '').replace('models/', '')
                methods = m.get('supportedGenerationMethods', [])
                
                # Должен поддерживать генерацию текста и содержать 'pro'
                if 'generateContent' in methods and 'pro' in name.lower():
                    # Проверяем на отсутствие запрещенных медиа-тегов
                    if not any(f in name.lower() for f in forbidden):
                        if 'flash' not in name.lower() and 'lite' not in name.lower():
                            available_clean.append(name)
            
            # Приоритезируем по нашему белому списку
            final_list = [m for m in allowed_pro_whitelist if m in available_clean]
            for m in available_clean:
                if m not in final_list:
                    final_list.append(m)
                    
            if final_list:
                return final_list
    except Exception:
        pass
        
    return allowed_pro_whitelist

def analyze_cross_platform_feed(feed_dump, key, nsfw_enabled):
    models_to_try = get_clean_pro_models(key)
    current_date = datetime.now().strftime("%Y-%m-%d")
    spicy_instruction = 'В массив "spicy_top" добавь от 5 до 10 ЖЕНСКИХ персонажей (опираясь на NexusMods и Danbooru). Сделай акцент на топологии для откровенных нарядов (body mesh, cloth physics).' if nsfw_enabled else 'Массив "spicy_top" оставь пустым.'

    prompt = f"""
    ТЫ — ГЛАВНЫЙ АРТ-ДИРЕКТОР И 3D-ЛИД. Твоя задача — извлечь МАКСИМАЛЬНО ТОЧНЫЙ список ТОЛЬКО ЖЕНСКИХ персонажей видеоигр из предоставленных сырых логов.
    Пользователь (3D-художник из РФ) будет использовать эти данные для моделирования в Blender, настройки материалов в Unity (Eevee/Cycles/URP) и монетизации ассетов на 15+ площадках.
    Сегодня {current_date}.

    ВХОДНЫЕ СИГНАЛЫ (Сырые логи сканеров):
    {json.dumps(feed_dump, ensure_ascii=False)}

    ЖЕЛЕЗНЫЕ ПРАВИЛА:
    1. ИСКЛЮЧИТЕЛЬНО ЖЕНСКИЕ ПЕРСОНАЖИ.
    2. НИКАКИХ ГАЛЛЮЦИНАЦИЙ: Базируй выбор строго на входных сигналах (кроме блока "classic_top", где можно брать культовую классику). 
    3. ИНСТРУКЦИИ ДЛЯ 3D (visual_hook):
       - Указывай технические советы: запекание Normal/AO, избегание артефактов (например, при fabric normals), настройка Z-fighting для слоистой одежды в Unity.
    {spicy_instruction}

    ВЕРНИ ОТВЕТ СТРОГО В ВИДЕ ВАЛИДНОГО JSON:
    {{
      "absolute_leader": {{
        "name": "Имя героини",
        "game": "Игра",
        "virality_score": 99,
        "past_72h_event": "Точный факт/инфоповод",
        "source_signal": "Точная строка из логов",
        "upcoming_catalyst": "Что подогреет интерес",
        "visual_hook": "Детали для Blender (Eevee/Cycles), UV, запекания Normal Map без багов, Unity Eevee/URP",
        "why_draw_today": "Почему сработает на 15+ площадках",
        "tags": ["3dart", "blender", "unity"]
      }},
      "spicy_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "analysis": "Причина", "visual_hook": "Хук для 3D/Топологии", "source_signal": "Источник", "score": 96, "tags": ["spicy"] }}
      ],
      "world_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "analysis": "Причина", "source_signal": "Источник", "score": 97, "tags": ["trend"] }}
      ],
      "ru_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "analysis": "Как монетизировать в РФ (Boosty, 3D Sky, CGTrader)", "source_signal": "Источник", "score": 94, "tags": ["ru_fav"] }}
      ],
      "gacha_top": [
        {{ "rank": 1, "name": "Персонаж", "game": "Игра", "score": 98, "reach": 96, "likes": 97, "visual_hook": "Специфика Unity/Blender", "source_signal": "Строка из логов", "reason": "Лик/Баннер", "trend": "🔥" }}
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
            resp = requests.post(url, headers=headers, json=payload, timeout=90) 
            
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match: 
                    return json.loads(json_match.group()), model_name
                else: 
                    return json.loads(raw_text), model_name
            else:
                try:
                    err_msg = resp.json().get('error', {}).get('message', resp.text[:100])
                except:
                    err_msg = resp.text[:100]
                last_err = f"[{model_name}] Code {resp.status_code}: {err_msg}"
                # Продолжаем цикл для поиска доступной Pro модели
                continue

        except Exception as e:
            last_err = f"[{model_name}] {str(e)}"
            continue

    raise RuntimeError(f"Все PRO-модели вернули ошибку. Последняя: {last_err}")

def run_full_scan(depth):
    collected_feed = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(fetch_danbooru_velocity, depth),
            executor.submit(fetch_reddit_rss_fallback, depth),
            executor.submit(fetch_bilibili_hot),
            executor.submit(fetch_nexusmods_trending, nexus_key),
            executor.submit(fetch_bluesky_art, depth),
            executor.submit(fetch_youtube_targeted, youtube_key, depth)
        ]
        for f in futures:
            collected_feed.extend(f.result())
            
    cleaned_feed = [item for item in collected_feed if len(item) > 10]
    return analyze_cross_platform_feed(cleaned_feed, gemini_key, is_16_plus), cleaned_feed

# ==========================================
# ИНТЕГРАЦИЯ TELEGRAM БОТА
# ==========================================
@st.cache_resource
def start_telegram_bot(token):
    if not token: return None
    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['scan'])
    def handle_scan(message):
        bot.reply_to(message, "📡 Запущен глубокий парсинг источников (Pro Engine)...")
        try:
            (ai_res, model), _ = run_full_scan(depth=2)
            leader = ai_res.get('absolute_leader', {})
            msg = f"👑 *ТОП ЖЕНСКИЙ ПЕРСОНАЖ:*\n*{leader.get('name', 'N/A')}* ({leader.get('game', 'N/A')})\n"
            msg += f"🎯 *3D Хук (Blender/Unity):* {leader.get('visual_hook', 'N/A')}\n"
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
if st.button("🚀 Запустить Ultra-Precision Scan", type="primary", use_container_width=True):
    if not gemini_key:
        st.error("⚠️ Добавьте GEMINI_API_KEY в Secrets.")
    else:
        status_container = st.status(f"📡 Сбор данных (Глубина: {scan_depth})...", expanded=True)
        try:
            status_container.write("1. Парсинг RSS-лент Reddit...")
            status_container.write("2. Сканирование Bilibili...")
            status_container.write("3. Анализ NexusMods и Danbooru...")
            status_container.write("4. Синтез архитектуры мешей и шейдеров через Gemini Pro...")
            
            (ai_results, used_model), raw_feed = run_full_scan(scan_depth)
            
            st.session_state.update({
                'omni_results': ai_results,
                'raw_feed': raw_feed,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'scan_done': True
            })
            status_container.update(label=f"Успешно! (Использована PRO-модель: {used_model})", state="complete", expanded=False)
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
        st.subheader("🇷🇺 СНГ рынок (Монетизация РФ)")
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
