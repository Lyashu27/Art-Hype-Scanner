import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime, timedelta
import feedparser
from concurrent.futures import ThreadPoolExecutor
import plotly.express as px
import telebot
import threading

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="Omni-Channel Art Hype Radar", page_icon="🌐", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 20px; border-radius: 12px; border-left: 5px solid #4b8bff; margin-bottom: 15px;}
    .spicy-card {background-color: #25181e; padding: 20px; border-radius: 12px; border-left: 5px solid #ff4b8b; margin-bottom: 15px;}
    .hero-card {background: linear-gradient(135deg, #4b8bff 0%, #1a1c23 100%); padding: 30px; border-radius: 16px; margin-bottom: 25px; color: white; border: 1px solid #3d404b;}
    .hero-title {font-size: 32px; font-weight: 800; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;}
    .hero-news {background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; font-size: 15px; border-left: 4px solid #ffd700; margin-top: 10px;}
    .badge {background-color: #2b2d35; padding: 4px 10px; border-radius: 6px; font-size: 13px; margin-right: 6px; color: #a5b1c2; border: 1px solid #3d404b;}
    .spicy-badge {background-color: #3b1c28; color: #ff9ebf; border-color: #ff4b8b;}
</style>
""", unsafe_allow_html=True)

# --- ЗАГРУЗКА КЛЮЧЕЙ ---
gemini_key = st.secrets.get("GEMINI_API_KEY", "")
youtube_key = st.secrets.get("YOUTUBE_API_KEY", "")
steam_key = st.secrets.get("STEAM_API_KEY", "")
twitch_id = st.secrets.get("TWITCH_CLIENT_ID", "")
twitch_secret = st.secrets.get("TWITCH_CLIENT_SECRET", "")
tg_bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN", "")

st.title("🌐 Omni-Channel Radar: Глобальный мониторинг трендов")

# --- БОКОВАЯ ПАНЕЛЬ ---
with st.sidebar:
    st.header("Настройки Анализа")
    is_16_plus = st.toggle("🔞 Анализ 16+ (Spicy/Фансервис)", value=True)
    
    st.divider()
    st.header("Статус каналов")
    st.write(f"🧠 Gemini Core: {'🟢' if gemini_key else '🔴'}")
    st.write(f"🤖 Telegram Bot: {'🟢 Подключен' if tg_bot_token else '⚪ Выключен'}")
    st.write(f"📺 YouTube API: {'🟢' if youtube_key else '⚪'}")
    st.write(f"🎮 Steam & Twitch: {'🟢' if twitch_id else '⚪'}")

# ==========================================
# ЯДРО СБОРА ДАННЫХ
# ==========================================

def fetch_rss_news():
    results = []
    try:
        for url in ["https://kotaku.com/rss", "https://www.ign.com/feed.xml", "https://stopgame.ru/rss/news.xml"]:
            for entry in feedparser.parse(requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=4).content).entries[:5]:
                results.append(f"[СМИ]: {entry.title}")
    except: pass
    return results

def fetch_reddit_trends():
    results = []
    try:
        for sub in ["gaming", "gachagaming", "Genshin_Impact", "HonkaiStarRail", "ZenlessZoneZero"]:
            res = requests.get(f"https://www.reddit.com/r/{sub}/hot.json?limit=5", headers={'User-Agent': 'Mozilla/5.0'}, timeout=4)
            if res.status_code == 200:
                for p in res.json().get('data', {}).get('children', []):
                    results.append(f"[Reddit r/{sub}]: {p.get('data', {}).get('title', '')}")
    except: pass
    return results

def fetch_youtube_trailers(api_key):
    if not api_key: return []
    results = []
    try:
        time_limit = (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z"
        res = requests.get("https://www.googleapis.com/youtube/v3/search", params={"part": "snippet", "q": "character trailer", "type": "video", "publishedAfter": time_limit, "maxResults": 10, "key": api_key}, timeout=5)
        if res.status_code == 200:
            for item in res.json().get('items', []):
                results.append(f"[YouTube]: {item['snippet']['title']}")
    except: pass
    return results

def fetch_bluesky_trends():
    results = []
    try:
        res = requests.get("https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts", params={"q": "fanart OR gacha update", "limit": 10}, timeout=5)
        if res.status_code == 200:
            for p in res.json().get('posts', []):
                results.append(f"[Bluesky]: {p.get('record', {}).get('text', '')[:80]}")
    except: pass
    return results

def fetch_booru_hot_tags():
    results = []
    try:
        res = requests.get("https://danbooru.donmai.us/posts.json?limit=10&tags=order:rank", headers={'User-Agent': 'HypeRadar/1.0'}, timeout=5)
        if res.status_code == 200:
            for post in res.json():
                if post.get('tag_string_character'): results.append(f"[Booru Tag]: {post.get('tag_string_character')}")
    except: pass
    return results

def fetch_steam_twitch(steam_k, c_id, c_secret):
    results = []
    try:
        res_steam = requests.get("https://store.steampowered.com/api/featuredcategories", timeout=5)
        if res_steam.status_code == 200:
            for item in res_steam.json().get('top_sellers', {}).get('items', [])[:5]:
                results.append(f"[Steam]: {item.get('name', '')}")
    except: pass
    
    if c_id and c_secret:
        try:
            token = requests.post(f"https://id.twitch.tv/oauth2/token?client_id={c_id}&client_secret={c_secret}&grant_type=client_credentials", timeout=5).json().get('access_token', '')
            res_twitch = requests.get("https://api.twitch.tv/helix/games/top?first=5", headers={"Client-ID": c_id, "Authorization": f"Bearer {token}"}, timeout=5)
            if res_twitch.status_code == 200:
                for g in res_twitch.json().get('data', []):
                    results.append(f"[Twitch]: {g.get('name')}")
        except: pass
    return results

# ==========================================
# ИИ-АНАЛИЗАТОР
# ==========================================

def analyze_feed(feed_dump, key, nsfw_enabled):
    models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash"]
    spicy_instruction = "Выдели персонажей с NSFW-adjacent трендами (моды, купальники) в массив 'spicy_top'." if nsfw_enabled else "Массив 'spicy_top' оставь пустым."

    prompt = f"""
    Данные из 7 источников: {json.dumps(feed_dump, ensure_ascii=False)}
    {spicy_instruction}
    Выдели Абсолютного Лидера, Топы (Мир, СНГ, Spicy) и сформируй списки gacha_top_50 и classic_top_50 (строго по 50 элементов). 
    Для Топ-50 рассчитай score, reach, likes (от 0 до 100).
    Ответь СТРОГО в JSON, ключи: absolute_leader, spicy_top, world_top, ru_top, gacha_top_50, classic_top_50.
    """
    
    for model_name in models_to_try:
        try:
            resp = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}", 
                                 headers={"Content-Type": "application/json"}, 
                                 json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}, 
                                 timeout=45)
            if resp.status_code == 200:
                raw = resp.json()['candidates'][0]['content']['parts'][0]['text']
                return json.loads(raw.replace("```json\n", "").replace("```", "").strip()), model_name
        except: continue
    raise RuntimeError("Сбой Gemini API")

def run_full_scan():
    collected_feed = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        for future in [
            executor.submit(fetch_rss_news), executor.submit(fetch_reddit_trends), 
            executor.submit(fetch_youtube_trailers, youtube_key), executor.submit(fetch_bluesky_trends), 
            executor.submit(fetch_booru_hot_tags), executor.submit(fetch_steam_twitch, steam_key, twitch_id, twitch_secret)
        ]:
            collected_feed.extend(future.result())
    return analyze_feed(collected_feed, gemini_key, is_16_plus)

# ==========================================
# ИНТЕГРАЦИЯ TELEGRAM БОТА (В ФОНЕ)
# ==========================================

@st.cache_resource
def start_telegram_bot(token):
    if not token: return None
    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        bot.reply_to(message, "Привет! Я *3D Art Hype Radar* 🤖\nНапиши /scan, чтобы я собрал самые актуальные тренды для твоих артов.", parse_mode="Markdown")

    @bot.message_handler(commands=['scan'])
    def handle_scan(message):
        bot.reply_to(message, "📡 Собираю данные с 7 платформ и анализирую ИИ... Подожди секунд 20-30.")
        try:
            ai_res, model = run_full_scan()
            data = ai_res[0]
            
            # Формирование красивого ответа для Телеграма
            leader = data.get('absolute_leader', {})
            msg = f"👑 *АБСОЛЮТНЫЙ ЛИДЕР:*\n*{leader.get('name')}* ({leader.get('game')})\n"
            msg += f"🔥 Виральность: {leader.get('virality_score')}/100\n"
            msg += f"🎯 Триггер: {leader.get('primary_trigger')}\n\n"
            
            msg += "🌍 *МИРОВОЙ ТОП-3:*\n"
            for i, itm in enumerate(data.get('world_top', [])[:3]):
                msg += f"{i+1}. {itm['name']} ({itm.get('score')}/100)\n"
                
            if data.get('spicy_top'):
                msg += "\n🔞 *SPICY 16+ ТРЕНДЫ:*\n"
                for i, itm in enumerate(data.get('spicy_top', [])[:3]):
                    msg += f"{i+1}. {itm['name']} ({itm.get('score')}/100)\n"
                    
            bot.send_message(message.chat.id, msg, parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Произошла ошибка сбора данных: {str(e)}")

    # Запускаем поллинг в отдельном потоке
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    return bot

# Инициализация бота при запуске дашборда
start_telegram_bot(tg_bot_token)

# ==========================================
# ИНТЕРФЕЙС STREAMLIT
# ==========================================

if st.button("🚀 Начать глубокий скан (Охваты + Тренды)", type="primary", use_container_width=True):
    if not gemini_key: st.error("⚠️ Укажите GEMINI_API_KEY в Secrets.")
    else:
        progress, status = st.progress(0), st.empty()
        status.markdown("📡 **Сбор данных и ИИ-анализ...**")
        progress.progress(50)
        try:
            ai_results, used_model = run_full_scan()
            st.session_state.update({'omni_results': ai_results, 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'scan_done': True})
            progress.empty(); status.empty()
            st.toast(f"Анализ завершен ({used_model})!", icon="✅")
        except Exception as e:
            st.error(f"Ошибка анализа: {e}")

if st.session_state.get('scan_done', False):
    res = st.session_state['omni_results']
    
    # АБСОЛЮТНЫЙ ЛИДЕР
    leader = res.get('absolute_leader', {})
    if leader:
        st.markdown(f"""
        <div class="hero-card">
            <div style="text-transform: uppercase; letter-spacing: 2px; font-size: 12px; margin-bottom: 8px; color: #ffd700;">👑 Главный инфоповод интернета</div>
            <div class="hero-title">{leader.get('name')} <span style="font-size:22px; font-weight:400; opacity:0.8;">— {leader.get('game')}</span></div>
            <div style="font-size: 16px; margin-top: 5px;">Индекс виральности: <b>{leader.get('virality_score')}/100</b></div>
            <div class="hero-news">🎯 <b>Триггер хайпа:</b> {leader.get('primary_trigger')}</div>
        </div>
        """, unsafe_allow_html=True)

    # ТОПЫ И 16+
    medals, classes = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"], ["top1", "top2", "top3", "", ""]
    if is_16_plus and res.get('spicy_top'):
        st.subheader("🔞 Тренды 16+ (Spicy & Фансервис)")
        spicy_cols = st.columns(3)
        for idx, item in enumerate(res.get('spicy_top', [])[:3]):
            with spicy_cols[idx]:
                st.markdown(f"""<div class="spicy-card"><h4 style="margin-bottom: 5px; color: #ff9ebf;">{medals[idx]} {item['name']}</h4><p style="font-size: 13px; color: #dfe4ea;">{item['analysis']}</p></div>""", unsafe_allow_html=True)
        st.divider()

    col_w, col_r = st.columns(2)
    with col_w:
        st.subheader("🌍 Мировой тренд (Топ-5)")
        for idx, item in enumerate(res.get('world_top', [])[:5]):
            st.markdown(f"""<div class="metric-card {classes[idx]}"><h4 style="margin-bottom: 5px;">{medals[idx]} {item['name']}</h4><p style="font-size: 14px;">{item['analysis']}</p></div>""", unsafe_allow_html=True)
    with col_r:
        st.subheader("🇷🇺 СНГ / РФ фокус (Топ-5)")
        for idx, item in enumerate(res.get('ru_top', [])[:5]):
            st.markdown(f"""<div class="metric-card {classes[idx]}"><h4 style="margin-bottom: 5px;">{medals[idx]} {item['name']}</h4><p style="font-size: 14px;">{item['analysis']}</p></div>""", unsafe_allow_html=True)

    st.divider()

    # ГРАФИКИ
    df_gacha, df_classic = pd.DataFrame(res.get('gacha_top_50', [])), pd.DataFrame(res.get('classic_top_50', []))
    st.subheader("📊 Распределение Охватов и Вовлеченности")
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        if not df_gacha.empty:
            fig_g = px.scatter(df_gacha.head(15), x="reach", y="likes", size="score", color="game", hover_name="name", text="name", size_max=40, template="plotly_dark", title="Гача: Охват vs Лайки")
            fig_g.update_traces(textposition='top center')
            st.plotly_chart(fig_g, use_container_width=True)
    with col_chart2:
        if not df_classic.empty:
            fig_c = px.bar(df_classic.head(15).sort_values('score', ascending=True), x='score', y='name', color='likes', orientation='h', text_auto=True, color_continuous_scale='Inferno', title="AAA и Соревновательные", template="plotly_dark")
            st.plotly_chart(fig_c, use_container_width=True)

    # ТАБЛИЦЫ ТОП-50
    col_config = {"rank": st.column_config.NumberColumn("№", format="%d"), "score": st.column_config.ProgressColumn("Хайп", min_value=0, max_value=100)}
    col_tab1, col_tab2 = st.columns(2)
    with col_tab1:
        st.markdown("<h4 style='text-align: center; color: #4b8bff;'>🎲 Гача-Игры (Топ 50)</h4>", unsafe_allow_html=True)
        if not df_gacha.empty: st.dataframe(df_gacha, use_container_width=True, hide_index=True, column_config=col_config, height=600)
    with col_tab2:
        st.markdown("<h4 style='text-align: center; color: #ff4b4b;'>⚔️ Остальные игры (Топ 50)</h4>", unsafe_allow_html=True)
        if not df_classic.empty: st.dataframe(df_classic, use_container_width=True, hide_index=True, column_config=col_config, height=600)
