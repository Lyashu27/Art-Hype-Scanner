import streamlit as st
import pandas as pd
import requests
import json
import time
import plotly.express as px

# --- КОНФИГУРАЦИЯ СТРАНИЦЫ ---
st.set_page_config(page_title="3D Art Hype Scanner", page_icon="🎨", layout="wide")

st.markdown("""
<style>
    .metric-card {background-color: #1a1c23; padding: 20px; border-radius: 12px; border-left: 5px solid #ff4b4b; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);}
    .top1 {border-left-color: #ffd700;} 
    .top2 {border-left-color: #c0c0c0;} 
    .top3 {border-left-color: #cd7f32;}
    .badge {background-color: #2b2d35; padding: 4px 10px; border-radius: 6px; font-size: 13px; margin-right: 6px; color: #a5b1c2; border: 1px solid #3d404b;}
    .stat-row {display: flex; justify-content: space-between; margin-top: 10px; font-size: 14px; color: #d1d8e0;}
</style>
""", unsafe_allow_html=True)

# --- БЕЗОПАСНАЯ ЗАГРУЗКА КЛЮЧА ---
# Скрипт сначала ищет ключ в секретах сервера. Если не находит - показывает поле ввода.
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except (KeyError, FileNotFoundError):
    api_key = st.sidebar.text_input("Gemini API Key (Секрет не настроен):", type="password")

st.title("🎨 Радар 3D-арта: Аналитика хайпа персонажей")
st.markdown("Поиск идеальных героинь для максимизации охватов на арт-площадках.")

with st.sidebar:
    if api_key:
        st.success("✅ API Ключ подключен")
    st.divider()
    st.info("💡 **Как это работает:** Алгоритм собирает соотношение новых артов к количеству лайков. Пузырьковая диаграмма покажет персонажей с огромным спросом и низкой конкуренцией.")

# --- БАЗА ТЕГОВ ---
CHARACTERS = [
    {"name": "Jane Doe", "tag": "jane_doe_(zenless_zone_zero)", "game": "ZZZ"},
    {"name": "Ellen Joe", "tag": "ellen_joe_(zenless_zone_zero)", "game": "ZZZ"},
    {"name": "Miyabi", "tag": "hoshimi_miyabi", "game": "ZZZ"},
    {"name": "Zhu Yuan", "tag": "zhu_yuan_(zenless_zone_zero)", "game": "ZZZ"},
    {"name": "Nicole Demara", "tag": "nicole_demara", "game": "ZZZ"},
    {"name": "Firefly", "tag": "firefly_(honkai_star_rail)", "game": "Honkai Star Rail"},
    {"name": "Acheron", "tag": "acheron_(honkai_star_rail)", "game": "Honkai Star Rail"},
    {"name": "Kafka", "tag": "kafka_(honkai_star_rail)", "game": "Honkai Star Rail"},
    {"name": "Black Swan", "tag": "black_swan_(honkai_star_rail)", "game": "Honkai Star Rail"},
    {"name": "Ruan Mei", "tag": "ruan_mei_(honkai_star_rail)", "game": "Honkai Star Rail"},
    {"name": "Sparkle", "tag": "sparkle_(honkai_star_rail)", "game": "Honkai Star Rail"},
    {"name": "Jingliu", "tag": "jingliu_(honkai_star_rail)", "game": "Honkai Star Rail"},
    {"name": "Furina", "tag": "furina_(genshin_impact)", "game": "Genshin Impact"},
    {"name": "Raiden Shogun", "tag": "raiden_shogun", "game": "Genshin Impact"},
    {"name": "Yelan", "tag": "yelan_(genshin_impact)", "game": "Genshin Impact"},
    {"name": "Navia", "tag": "navia_(genshin_impact)", "game": "Genshin Impact"},
    {"name": "Arlecchino", "tag": "arlecchino_(genshin_impact)", "game": "Genshin Impact"},
    {"name": "Hu Tao", "tag": "hu_tao_(genshin_impact)", "game": "Genshin Impact"},
    {"name": "Tifa Lockhart", "tag": "tifa_lockhart", "game": "Final Fantasy VII"},
    {"name": "Aerith Gainsborough", "tag": "aerith_gainsborough", "game": "Final Fantasy VII"},
    {"name": "2B", "tag": "yorha_no._2_type_b", "game": "NieR:Automata"},
    {"name": "Ada Wong", "tag": "ada_wong", "game": "Resident Evil"},
    {"name": "Eve", "tag": "eve_(stellar_blade)", "game": "Stellar Blade"},
    {"name": "Lara Croft", "tag": "lara_croft", "game": "Tomb Raider"},
    {"name": "Chun-Li", "tag": "chun-li", "game": "Street Fighter"},
    {"name": "Cammy White", "tag": "cammy_white", "game": "Street Fighter"},
    {"name": "Juri Han", "tag": "juri_han", "game": "Street Fighter"},
    {"name": "Ciri", "tag": "cirilla_fiona_elen_riannon", "game": "The Witcher"},
    {"name": "Yennefer", "tag": "yennefer_of_vengerberg", "game": "The Witcher"},
    {"name": "Lucy", "tag": "lucyna_kushinada", "game": "Cyberpunk"},
    {"name": "D.Va", "tag": "d.va_(overwatch)", "game": "Overwatch"},
    {"name": "Ahri", "tag": "ahri_(league_of_legends)", "game": "League of Legends"},
    {"name": "Jinx", "tag": "jinx_(league_of_legends)", "game": "League of Legends"}
]

# --- СБОР ДАННЫХ ---
def fetch_art_stats(char):
    headers = {'User-Agent': 'ArtHypeScanner/2.0 (Analytics for 3D Artists)'}
    try:
        url = "https://danbooru.donmai.us/posts.json"
        params = {"limit": 50, "tags": char['tag']}
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code == 200:
            posts = res.json()
            if isinstance(posts, list) and len(posts) > 0:
                score = sum(int(p.get('score', 0)) + int(p.get('up_score', 0)) for p in posts)
                count = len(posts)
                er = round((score / count), 2) if count > 0 else 0
                return {"Персонаж": char['name'], "Франшиза": char['game'], "Конкуренция (Новых работ)": count, "Суммарный скор": score, "ER (Вовлеченность)": er}
    except:
        pass

    try:
        url = "https://safebooru.org/index.php"
        params = {"page": "dapi", "s": "post", "q": "index", "json": 1, "limit": 50, "tags": char['tag']}
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code == 200:
            posts = res.json()
            if isinstance(posts, list) and len(posts) > 0:
                score = sum(int(p.get('score', 0)) for p in posts)
                count = len(posts)
                er = round((score / count), 2) if count > 0 else 0
                return {"Персонаж": char['name'], "Франшиза": char['game'], "Конкуренция (Новых работ)": count, "Суммарный скор": score, "ER (Вовлеченность)": er}
    except:
        pass

    return {"Персонаж": char['name'], "Франшиза": char['game'], "Конкуренция (Новых работ)": 0, "Суммарный скор": 0, "ER (Вовлеченность)": 0}

# --- ИИ АНАЛИЗ ---
def request_gemini_analysis(metrics, key):
    models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-flash-latest"]
    
    prompt = f"""
    Ты креативный арт-директор. Проанализируй эти точные метрики (ER - вовлеченность, Конкуренция - объем новых работ):
    {json.dumps(metrics, ensure_ascii=False)}

    Отбери ТОП-5 женских персонажей для качественного 3D-арта (расчет на веерную публикацию по 15+ площадкам).
    Выборки:
    1. world_top: Глобальный тренд.
    2. ru_top: Вкусы СНГ (гачи + классика).

    Формат СТРОГО JSON:
    {{
      "world_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Почему это выстрелит", "tags": ["tag1", "tag2"] }}
      ],
      "ru_top": [
        {{ "rank": 1, "name": "Имя", "game": "Игра", "analysis": "Почему это выстрелит", "tags": ["tag1", "tag2"] }}
      ]
    }}
    """
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json"}}

    last_err = ""
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            if resp.status_code == 200:
                raw_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                return json.loads(raw_text), model_name
        except Exception as e:
            last_err = str(e)
            continue
    raise RuntimeError("Сбой API Gemini")

# --- ИНТЕРФЕЙС И ЗАПУСК ---
if st.button("🚀 Запустить нейросканирование рынка", type="primary", use_container_width=True):
    if not api_key:
        st.error("⚠️ API Ключ не настроен.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        raw_metrics = []
        
        for idx, char in enumerate(CHARACTERS):
            status_text.markdown(f"📡 Сканирование баз данных: **{char['name']}** ({char['game']})...")
            raw_metrics.append(fetch_art_stats(char))
            progress_bar.progress((idx + 1) / len(CHARACTERS))
            time.sleep(0.3)
            
        status_text.markdown("🧠 Массив данных собран. Передаем в ИИ для анализа...")
        
        try:
            ai_response, model_used = request_gemini_analysis(raw_metrics, api_key)
            st.session_state['ai_results'] = ai_response
            st.session_state['metrics_df'] = pd.DataFrame(raw_metrics).sort_values(by="ER (Вовлеченность)", ascending=False)
            st.session_state['scan_done'] = True
            status_text.empty()
            progress_bar.empty()
            st.toast(f"Анализ завершен! (Модель: {model_used})", icon="✅")
        except Exception as ex:
            st.error(f"Ошибка: {ex}")

# --- ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ И ГРАФИКОВ ---
if st.session_state.get('scan_done', False):
    df = st.session_state['metrics_df']
    top_data = st.session_state['ai_results']
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    classes = ["top1", "top2", "top3", "top4", "top5"]

    st.divider()
    
    # --- ВИЗУАЛИЗАЦИЯ ДАННЫХ (ГРАФИКИ) ---
    st.subheader("📊 Аналитика рынка")
    col1, col2 = st.columns(2)
    
    with col1:
        # Столбчатая диаграмма топ-10 по ER
        fig_bar = px.bar(
            df.head(10), x='ER (Вовлеченность)', y='Персонаж', orientation='h', 
            color='ER (Вовлеченность)', color_continuous_scale='Reds',
            title="Топ-10 по горячему спросу (ER)", template="plotly_dark"
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        # Пузырьковая матрица Риск/Награда
        fig_scatter = px.scatter(
            df, x="Конкуренция (Новых работ)", y="ER (Вовлеченность)", 
            color="Франшиза", size="Суммарный скор", hover_name="Персонаж",
            title="Матрица: Конкуренция vs Вовлеченность (Чем выше и левее, тем лучше)", 
            template="plotly_dark", size_max=40
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    # --- ВЫВОД КАРТОЧЕК ---
    tab_world, tab_ru, tab_all = st.tabs(["🌍 ТОП-5 Мировой тренд", "🇷🇺 ТОП-5 СНГ и РФ", "💯 Полная таблица"])

    def render_cards(category):
        for idx, item in enumerate(top_data.get(category, [])[:5]):
            tags = "".join([f"<span class='badge'>#{t}</span>" for t in item.get('tags', [])])
            st.markdown(f"""
            <div class="metric-card {classes[idx]}">
                <h3 style="margin-bottom: 5px;">{medals[idx]} {item['name']} <span style="font-size:16px; color:#a5b1c2; font-weight:normal;">— {item['game']}</span></h3>
                <p style="color: #dfe4ea; margin-bottom: 12px; font-size: 15px;">{item['analysis']}</p>
                <div>{tags}</div>
            </div>
            """, unsafe_allow_html=True)

    with tab_world:
        render_cards('world_top')
    with tab_ru:
        render_cards('ru_top')
    with tab_all:
        st.dataframe(df, use_container_width=True, hide_index=True)
