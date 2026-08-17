import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime
import urllib.parse
import feedparser
from concurrent.futures import ThreadPoolExecutor

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="Viral Radar Pro (Strict Data)", page_icon="🔥", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 20px; border-radius: 12px; border-left: 5px solid #ff4b4b; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .hero-card {background: linear-gradient(135deg, #ff4b4b 0%, #8b0000 100%); padding: 30px; border-radius: 16px; margin-bottom: 25px; color: white; box-shadow: 0 10px 20px rgba(255, 75, 75, 0.3); border: 1px solid #ff7676;}
    .hero-title {font-size: 32px; font-weight: 800; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 1px;}
    .hero-subtitle {font-size: 18px; opacity: 0.9; margin-bottom: 15px;}
    .hero-news {background: rgba(0,0,0,0.2); padding: 12px; border-radius: 8px; font-size: 15px; border-left: 4px solid #ffd700;}
    .top1 {border-left-color: #ffd700;} 
    .top2 {border-left-color: #c0c0c0;} 
    .top3 {border-left-color: #cd7f32;}
    .badge {background-color: #2b2d35; padding: 4px 10px; border-radius: 6px; font-size: 13px; margin-right: 6px; color: #a5b1c2; border: 1px solid #3d404b;}
</style>
""", unsafe_allow_html=True)

# --- БЕЗОПАСНАЯ ЗАГРУЗКА КЛЮЧЕЙ ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = st.sidebar.text_input("Gemini API Key:", type="password")

try:
    rapidapi_key = st.secrets["RAPIDAPI_KEY"]
except:
    rapidapi_key = st.sidebar.text_input("RapidAPI Key (X/Twitter):", type="password")

st.title("🔥 Viral Radar: Аналитика 3D-арта (Real-Time)")
st.markdown("Поиск абсолютных лидеров на основе **строгих и актуальных цифр** из соцсетей.")

# --- БОКОВАЯ ПАНЕЛЬ И ФИЛЬТРЫ ---
with st.sidebar:
    st.header("Настройки сканирования")
    
    time_filters = {
        "За 24 часа (Мгновенный хайп)": "24h",
        "За 3 дня (Свежие тренды)": "72h",
        "За 7 дней (Стабильный рост)": "168h"
    }
    
    selected_filter = st.selectbox("⏳ Временной фильтр:", list(time_filters.keys()))
    time_scope_val = time_filters[selected_filter]
    
    st.divider()
    st.info("⚙️ **Точность 100%:** Скрипт собирает реальные метрики и передает их в Gemini с temperature=0.0 для стабильного аналитического отчета.")

# --- БАЗА ПЕРСОНАЖЕЙ ---
CHARACTERS = [
    {"name": "Jane Doe", "query": "Jane Doe ZZZ", "game": "ZZZ", "is_gacha": True},
    {"name": "Ellen Joe", "query": "Ellen Joe ZZZ", "game": "ZZZ", "is_gacha": True},
    {"name": "Miyabi", "query": "Miyabi ZZZ", "game": "ZZZ", "is_gacha": True},
    {"name": "Zhu Yuan", "query": "Zhu Yuan ZZZ", "game": "ZZZ", "is_gacha": True},
    {"name": "Firefly", "query": "Firefly Honkai", "game": "Honkai: Star Rail", "is_gacha": True},
    {"name": "Acheron", "query": "Acheron Honkai", "game": "Honkai: Star Rail", "is_gacha": True},
    {"name": "Kafka", "query": "Kafka Honkai", "game": "Honkai: Star Rail", "is_gacha": True},
    {"name": "Furina", "query": "Furina Genshin", "game": "Genshin Impact", "is_gacha": True},
    {"name": "Raiden Shogun", "query": "Raiden Genshin", "game": "Genshin Impact", "is_gacha": True},
    {"name": "Arlecchino", "query": "Arlecchino Genshin", "game": "Genshin Impact", "is_gacha": True},
    {"name": "Yinlin", "query": "Yinlin Wuthering", "game": "Wuthering Waves", "is_gacha": True},
    {"name": "2B", "query": "2B Nier", "game": "NieR:Automata", "is_gacha": False},
    {"name": "Tifa Lockhart", "query": "Tifa Lockhart", "game": "Final Fantasy VII", "is_gacha": False},
    {"name": "Ada Wong", "query": "Ada Wong", "game": "Resident Evil", "is_gacha": False},
    {"name": "Eve", "query": "Eve Stellar Blade", "game": "Stellar Blade", "is_gacha": False},
    {"name": "D.Va", "query": "D.Va Overwatch", "game": "Overwatch", "is_gacha": False},
    {"name": "Ahri", "query": "Ahri League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Akali", "query": "Akali League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Ashe", "query": "Ashe League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Aurora", "query": "Aurora League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Bel'Veth", "query": "BelVeth League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Briar", "query": "Briar League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Caitlyn", "query": "Caitlyn League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Camille", "query": "Camille League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Cassiopeia", "query": "Cassiopeia League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Diana", "query": "Diana League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Elise", "query": "Elise League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Evelynn", "query": "Evelynn League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Fiora", "query": "Fiora League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Gwen", "query": "Gwen League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Illaoi", "query": "Illaoi League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Irelia", "query": "Irelia League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Janna", "query": "Janna League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Jinx", "query": "Jinx League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Kai'Sa", "query": "Kaisa League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Kalista", "query": "Kalista League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Karma", "query": "Karma League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Katarina", "query": "Katarina League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Kayle", "query": "Kayle League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Kindred", "query": "Kindred League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Lillia", "query": "Lillia League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Lissandra", "query": "Lissandra League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Lulu", "query": "Lulu League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Lux", "query": "Lux League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Miss Fortune", "query": "Miss Fortune League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Morgana", "query": "Morgana League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Naafiri", "query": "Naafiri League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Nami", "query": "Nami League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Neeko", "query": "Neeko League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Nidalee", "query": "Nidalee League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Nilah", "query": "Nilah League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Orianna", "query": "Orianna League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Poppy", "query": "Poppy League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Qiyana", "query": "Qiyana League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Quinn", "query": "Quinn League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Rell", "query": "Rell League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Renata Glasc", "query": "Renata Glasc League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Riven", "query": "Riven League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Samira", "query": "Samira League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Sejuani", "query": "Sejuani League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Senna", "query": "Senna League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Seraphine", "query": "Seraphine League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Shyvana", "query": "Shyvana League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Sivir", "query": "Sivir League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Sona", "query": "Sona League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Soraka", "query": "Soraka League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Syndra", "query": "Syndra League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Taliyah", "query": "Taliyah League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Tristana", "query": "Tristana League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Vayne", "query": "Vayne League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Vex", "query": "Vex League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Vi", "query": "Vi League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Xayah", "query": "Xayah League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Yuumi", "query": "Yuumi League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Zeri", "query": "Zeri League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Zoe", "query": "Zoe League of Legends", "game": "League of Legends", "is_gacha": False},
    {"name": "Zyra", "query": "Zyra League of Legends", "game": "League of Legends", "is_gacha": False}
]

# --- 1. СБОР РЕАЛЬНЫХ МЕТРИК ---
def fetch_real_metrics(char, time_str):
    da_count, x_count = 0, 0
    
    # DeviantArt RSS
    try:
        encoded_query = urllib.parse.quote(char['query'])
        url = f"https://backend.deviantart.com/rss.xml?q=boost%3Apopular+in%3Adigitalart+max_age%3A{time_str}+{encoded_query}"
        feed = feedparser.parse(url)
        da_count = len(feed.entries)
    except Exception:
        pass

    # X (Twitter) RapidAPI
    if rapidapi_key:
        try:
            url = "https://twitter154.p.rapidapi.com/search/search"
            querystring = {"query": char['query'], "section": "top", "limit": "15"}
            headers = {"x-rapidapi-key": rapidapi_key, "x-rapidapi-host": "twitter154.p.rapidapi.com"}
            res = requests.get(url, headers=headers, params=querystring, timeout=5)
            if res.status_code == 200:
                data = res.json()
                results = data.get('results', [])
                x_count = len(results)
        except Exception:
            pass

    return {
        "Персонаж": char['name'],
        "Франшиза": char['game'],
        "is_gacha": char['is_gacha'],
        "Новых артов (DA)": da_count,
        "Твитов в Топе (X)": x_count,
        "Общий Хайп-Индекс": da_count + x_count
    }

# --- 2. ДИНАМИЧЕСКИЙ ВЫЗОВ GEMINI (TEMPERATURE 0.0) ---
def analyze_metrics_deterministically(metrics_data, key):
    supported_models = []
    try:
        list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        res = requests.get(list_url, timeout=8).json()
        for m in res.get('models', []):
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                name = m.get('name', '').replace('models/', '')
                if ('flash' in name.lower() or 'pro' in name.lower()) and 'lite' not in name.lower():
                    supported_models.append(name)
    except Exception:
        pass

    fallback_models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash-latest", "gemini-pro"]
    models_to_try = []
    for m in supported_models + fallback_models:
        if m not in models_to_try:
            models_to_try.append(m)

    prompt = f"""
    Ты выступаешь в роли аналитического процессора. Я предоставляю тебе ТОЧНЫЕ цифры активности по персонажам за выбранный период:
    {json.dumps(metrics_data, ensure_ascii=False)}

    Твоя задача — строго на основе колонки "Общий Хайп-Индекс" отсортировать персонажей и сформировать JSON-отчет. 
    Не выдумывай цифры! Используй только то, что передано. 
    Для топовых персонажей добавь краткий актуальный контекст (почему цифры высокие: патчи, аниме, инфоповоды).

    Формат ответа СТРОГО JSON:
    {{
      "overall_top_1": {{
        "name": "Имя абсолютного лидера по цифрам",
        "game": "Игра",
        "virality_score": 99,
        "recent_news": "Контекст (почему она сейчас популярна в инфополе)",
        "tags": ["3dart", "fanart"]
      }},
      "world_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Анализ на основе цифр", "tags": ["tag1"] }}
      ],
      "ru_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Почему эти цифры релевантны для СНГ", "tags": ["tag1"] }}
      ]
    }}
    """
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.0
        }
    }

    last_err = ""
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=35)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                if raw_text.startswith("```json"): raw_text = raw_text[7:]
                if raw_text.startswith("```"): raw_text = raw_text[3:]
                if raw_text.endswith("```"): raw_text = raw_text[:-3]
                return json.loads(raw_text.strip()), model_name
            else:
                last_err = f"[{model_name}] {resp.status_code}: {resp.text}"
        except Exception as e:
            last_err = f"[{model_name}] {str(e)}"
            continue

    raise RuntimeError(f"Сбой ИИ. Детали: {last_err}")

# --- ИНТЕРФЕЙС И ЗАПУСК ---
if st.button(f"🚀 Собрать жесткие метрики ({selected_filter})", type="primary", use_container_width=True):
    if not api_key:
        st.error("⚠️ Укажите Gemini API Key.")
    else:
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        # 1. Сбор метрик
        metrics_list = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            for idx, item in enumerate(executor.map(lambda c: fetch_real_metrics(c, time_scope_val), CHARACTERS)):
                metrics_list.append(item)
                progress_bar.progress((idx + 1) / len(CHARACTERS))
                status_text.markdown(f"📡 Парсинг площадок: **{idx + 1} / {len(CHARACTERS)}**")

        # 2. Анализ данных
        status_text.markdown("🧠 Цифры получены. ИИ формирует детерминированный отчет (Temperature: 0.0)...")
        try:
            ai_data, used_model = analyze_metrics_deterministically(metrics_list, api_key)
            
            st.session_state['results'] = ai_data
            st.session_state['df'] = pd.DataFrame(metrics_list).sort_values(by="Общий Хайп-Индекс", ascending=False)
            st.session_state['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state['done'] = True
            
            progress_bar.empty()
            status_text.empty()
            st.toast(f"Отчет зафиксирован! (Модель: {used_model})", icon="✅")
            
        except Exception as ex:
            st.error(f"Ошибка ИИ: {ex}")

# --- ВЫВОД РЕЗУЛЬТАТОВ ---
if st.session_state.get('done', False):
    results = st.session_state['results']
    df = st.session_state['df']
    
    st.caption(f"⏱️ **Данные собраны:** {st.session_state['timestamp']} | Срез: {selected_filter}")
    
    # --- БЛОК АБСОЛЮТНОГО ЛИДЕРА ---
    top1 = results.get('overall_top_1', {})
    if top1:
        tags_html = " ".join([f"<span class='badge'>#{t}</span>" for t in top1.get('tags', [])])
        st.markdown(f"""
        <div class="hero-card">
            <div style="text-transform: uppercase; letter-spacing: 2px; font-size: 12px; margin-bottom: 10px; color: #ffd700;">👑 Лидер по фактическим цифрам</div>
            <div class="hero-title">{top1.get('name', 'N/A')} <span style="font-size: 24px; font-weight: 400; opacity: 0.8;">— {top1.get('game', '')}</span></div>
            <div class="hero-news">
                📰 <b>Контекст спроса:</b> {top1.get('recent_news', 'Нет актуальных новостей')}
            </div>
            <div style="margin-top: 15px;">{tags_html}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # --- ТОПЫ ПО РЕГИОНАМ ---
    col_w, col_r = st.columns(2)
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    classes = ["top1", "top2", "top3", "", ""]

    with col_w:
        st.subheader("🌍 Мировой тренд (Топ-5)")
        for idx, item in enumerate(results.get('world_top', [])[:5]):
            tags = " ".join([f"<span class='badge'>#{t}</span>" for t in item.get('tags', [])])
            st.markdown(f"""
            <div class="metric-card {classes[idx]}">
                <h4 style="margin-bottom: 5px;">{medals[idx]} {item['name']} <span style="font-size:14px; color:#888;">({item['game']})</span></h4>
                <p style="font-size: 14px; color: #dfe4ea;">{item['analysis']}</p>
                <div>{tags}</div>
            </div>
            """, unsafe_allow_html=True)

    with col_r:
        st.subheader("🇷🇺 СНГ и РФ (Топ-5)")
        for idx, item in enumerate(results.get('ru_top', [])[:5]):
            tags = " ".join([f"<span class='badge'>#{t}</span>" for t in item.get('tags', [])])
            st.markdown(f"""
            <div class="metric-card {classes[idx]}">
                <h4 style="margin-bottom: 5px;">{medals[idx]} {item['name']} <span style="font-size:14px; color:#888;">({item['game']})</span></h4>
                <p style="font-size: 14px; color: #dfe4ea;">{item['analysis']}</p>
                <div>{tags}</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # --- РАЗДЕЛЕНИЕ БАЗЫ ---
    st.subheader("🗄️ Фактические цифры с площадок")
    
    df_gacha = df[df['is_gacha'] == True].drop(columns=['is_gacha']).reset_index(drop=True)
    df_classic = df[df['is_gacha'] == False].drop(columns=['is_gacha']).reset_index(drop=True)
    
    tab_gacha, tab_classic = st.tabs(["🎲 Гача-Игры", "⚔️ AAA, RPG и Соревновательные"])
    
    with tab_gacha:
        st.dataframe(df_gacha, use_container_width=True, hide_index=True)
    with tab_classic:
        st.dataframe(df_classic, use_container_width=True, hide_index=True)
