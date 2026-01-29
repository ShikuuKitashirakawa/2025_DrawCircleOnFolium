import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.features import DivIcon
import math
from geopy.geocoders import Nominatim
from streamlit_gsheets import GSheetsConnection
import datetime
import pandas as pd

# --- ページ設定 ---
st.set_page_config(layout="wide", page_title="同心円エリア描画ツール（試作版）")

st.title("📍 同心円エリア描画ツール（試作版）")

st.markdown("""
### 💡 このツールの活用シーン
* **商圏分析**: 店舗を中心に、徒歩・自転車それぞれの集客範囲を可視化。
* **物件探し・立地評価**: 検討中の物件から駅やスーパーまでの距離感を直感的に把握。
* **防災・避難計画**: 自宅から避難所までの距離や、災害時の影響範囲の目安を確認。
* **健康・ウォーキング**: 指定した範囲の移動による消費カロリーや歩数の目安を把握。
""")

# --- 関数群 ---
def calculate_zoom_level(radius_km):
    if radius_km <= 0: return 13
    zoom = 14.2 - math.log2(radius_km)
    return max(1, min(18, round(zoom)))

@st.cache_data(ttl=3600)
def search_location(query):
    try:
        # user_agentをよりユニークなものに変更
        geolocator = Nominatim(user_agent="shikuu_circle_app_final_test_001")
        location = geolocator.geocode(query, language='ja', timeout=10)
        if location:
            # location.addressが長すぎる場合があるので、少し整理される
            return location.latitude, location.longitude, location.address
        return None, None, "地点が見つかりませんでした"
    except Exception as e:
        # ログに詳細を出す（デバッグ用）
        print(f"DEBUG: Geocode Error: {e}")
        return None, None, f"検索エラー: {e}"

@st.cache_data(ttl=3600)
def get_simple_address(lat, lon):
    try:
        # ここもuser_agentを統一
        geolocator = Nominatim(user_agent="shikuu_circle_app_final_test_001")
        location = geolocator.reverse(f"{lat}, {lon}", language='ja', timeout=10)
        if location:
            return location.address
        return "住所不明"
    except Exception as e:
        # 何が原因でエラーになっているか画面に少し出す
        return f"住所取得エラー ({e})"

def save_log_to_sheets(user_name, address, lat, lon, r1, r2, r3):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        existing_data = conn.read(ttl=0)
        
        new_row = pd.DataFrame([{
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_name": user_name,
            "address": address,
            "lat": lat,
            "lon": lon,
            "r1": r1,
            "r2": r2,
            "r3": r3
        }])
        
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        conn.update(data=updated_df)
        return True
    except Exception as e:
        # ここが重要！エラーの正体を画面に出します
        st.error(f"⚠️ 詳細エラー内容: {e}")
        return False

# --- セッション状態の初期化 ---
if 'clicked_lat' not in st.session_state:
    st.session_state.clicked_lat = 35.6812
if 'clicked_lon' not in st.session_state:
    st.session_state.clicked_lon = 139.7671
if 'last_search' not in st.session_state:
    st.session_state.last_search = ""
if 'r1_val' not in st.session_state: st.session_state.r1_val = 1.0
if 'r2_val' not in st.session_state: st.session_state.r2_val = 2.5
if 'r3_val' not in st.session_state: st.session_state.r3_val = 5.0

# --- サイドバー設定 ---
with st.sidebar:
    st.header("👤 ユーザー設定")
    
    # ニックネーム入力（プレースホルダー対応）
    user_name_input = st.text_input(
        "ニックネーム", 
        value="", 
        placeholder="匿名ユーザー"
    )
    
    # 入力があればそれを使用、空なら「匿名ユーザー」として扱う（NameError防止）
    display_name = user_name_input if user_name_input else "匿名ユーザー"
    
    st.caption("⚠️ プライバシー保護のため本名以外の入力を推奨します。")
    st.caption("💡 入力後に下のボタンで前回の設定を復元できます。")
    
    if st.button("前回の続きから再開"):
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl=0)
            # 現在のニックネームに一致する履歴を抽出
            user_history = df[df['user_name'] == display_name]
            if not user_history.empty:
                last_record = user_history.iloc[-1]
                st.session_state.clicked_lat = float(last_record['lat'])
                st.session_state.clicked_lon = float(last_record['lon'])
                st.session_state.r1_val = float(last_record['r1'])
                st.session_state.r2_val = float(last_record['r2'])
                st.session_state.r3_val = float(last_record['r3'])
                st.success(f"{display_name}さんの最新データを復元しました")
                st.rerun()
            else:
                st.warning(f"{display_name}さんの履歴が見つかりません")
        except:
            st.error("履歴の読み込みに失敗しました")
            
    st.markdown("---")

    st.header("⚙️ エリア設定")
    
    st.subheader("🔍 キーワード検索")
    search_query = st.text_input("地名・住所を入力", placeholder="例：Paris, Tokyo", key="search_input")
    search_button = st.button("検索")
    
    # 📜 履歴復元セクション（全ユーザー用）
    st.markdown("---")
    st.subheader("📜 履歴から復元")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_history = conn.read(ttl="5m")
        if not df_history.empty:
            history_options = df_history.iloc[::-1]['address'].unique()[:10]
            selected_h = st.selectbox("過去の地点を選択", ["選択してください"] + list(history_options))
            if selected_h != "選択してください":
                target = df_history[df_history['address'] == selected_h].iloc[-1]
                if st.button("この地点と半径を復元"):
                    st.session_state.clicked_lat = float(target['lat'])
                    st.session_state.clicked_lon = float(target['lon'])
                    st.session_state.r1_val = float(target['r1'])
                    st.session_state.r2_val = float(target['r2'])
                    st.session_state.r3_val = float(target['r3'])
                    st.rerun()
    except:
        st.caption("履歴の読み込みに失敗しました")

    st.markdown("---")

    # 半径の設定
    sets = []
    configs = [
        {"id": 1, "key": "r1_val", "def_c": "#FF4B4B", "label": "🔴 円1 (太実線)"},
        {"id": 2, "key": "r2_val", "def_c": "#1E90FF", "label": "🔵 円2 (細実線)"},
        {"id": 3, "key": "r3_val", "def_c": "#2E8B57", "label": "🟢 円3 (細点線)"}
    ]
    
    for conf in configs:
        st.subheader(conf["label"])
        col_r, col_c = st.columns([2, 1])
        r = col_r.number_input(f"半径 (km)", min_value=0.0, value=st.session_state[conf["key"]], step=0.5, key=f"r_input_{conf['id']}")
        c = col_c.color_picker("色", conf["def_c"], key=f"c{conf['id']}")
        st.session_state[conf["key"]] = r
        sets.append((r, c))

# --- 160行目付近：半径の設定（sets.append...）のすぐ下 ---
    
    # ↓↓↓ ここから「デバッグ強化版」に書き換えます ↓↓↓
    if (search_query and search_query != st.session_state.last_search) or search_button:
        if search_query:
            st.write("🔍 検索処理を開始しました...") # 画面に進行状況を出します
            with st.spinner("地点を検索中..."):
                res_lat, res_lon, res_address = search_location(search_query)
                if res_lat:
                    st.write(f"✅ 地点発見: {res_address}")
                    st.session_state.clicked_lat = res_lat
                    st.session_state.clicked_lon = res_lon
                    st.session_state.last_search = search_query
                    
                    st.write("📝 スプレッドシート保存を試みます...")
                    # ここで、以前作成した save_log_to_sheets 関数を呼び出します
                    success = save_log_to_sheets(display_name, res_address, res_lat, res_lon, sets[0][0], sets[1][0], sets[2][0])
                    
                    if success:
                        st.write("🎉 保存に成功しました！画面を更新します。")
                        st.rerun()
                    else:
                        # ここでエラーメッセージが画面に赤く表示されるはずです
                        st.error("❌ 保存に失敗しました。")
                else:
                    st.error("❓ 地点が見つかりませんでした")
    # ↑↑↑ ここまでを書き換え ↑↑↑

    # --- この後に map_style = st.radio(...) が続きます ---
    st.markdown("---")
    map_style = st.radio("地図スタイル", ["OpenStreetMap (世界対応)", "地理院 標準地図 (日本)", "地理院 空中写真 (日本)"])

    st.markdown("---")
    with st.expander("ℹ️ 免責事項・ライセンス"):
        st.caption("""
        **免責事項**
        - 本アプリの計算結果（移動時間、カロリー等）の正確性は保証されません。
        - 本アプリの利用により生じた損害について、作者は一切の責任を負いません。
        
        **使用データ・ライセンス**
        - **地図データ**: 
            - [OpenStreetMap](https://www.openstreetmap.org/copyright) (c) OpenStreetMap contributors
            - [国土地理院タイル](https://maps.gsi.go.jp/development/ichiran.html)
        - **住所検索**: [Nominatim](https://nominatim.org/)
        
        **ライセンス**
        MIT License  
        © 2026 Shikuu Kitashirakawa
        """)

# --- 地図表示 ---
current_lat, current_lon = st.session_state.clicked_lat, st.session_state.clicked_lon
focus_r = sets[1][0] if sets[1][0] > 0 else 1.0
zoom_val = calculate_zoom_level(focus_r)

col_map, col_info = st.columns([3, 1])

with col_map:
    if map_style == "OpenStreetMap (世界対応)":
        m = folium.Map(location=[current_lat, current_lon], zoom_start=zoom_val)
    else:
        tiles_dict = {
            "地理院 標準地図 (日本)": "https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png",
            "地理院 空中写真 (日本)": "https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg"
        }
        m = folium.Map(location=[current_lat, current_lon], zoom_start=zoom_val, tiles=tiles_dict[map_style], attr="国土地理院")

    folium.Marker([current_lat, current_lon], icon=folium.Icon(color="black", icon="info-sign")).add_to(m)

    for i, (r, color) in enumerate(sets):
        if r > 0:
            weight = 5 if i == 0 else 2
            dash = "10, 10" if i == 2 else None
            folium.Circle(location=[current_lat, current_lon], radius=r*1000, color=color, weight=weight, dash_array=dash, fill=True, fill_opacity=0.05).add_to(m)
            label_lat = current_lat + (r / 111.0) 
            folium.Marker(location=[label_lat, current_lon], icon=DivIcon(icon_size=(150, 36), icon_anchor=(75, 18),
                html=f'<div style="font-size: 9pt; color: {color}; font-weight: bold; text-align: center; background-color: rgba(255,255,255,0.8); border: 1px solid {color}; border-radius: 4px; padding: 1px 4px;">{r} km</div>')).add_to(m)

    map_data = st_folium(m, width=None, height=600, key=f"map_{current_lat}_{current_lon}_{zoom_val}", use_container_width=True)

with col_info:
    st.subheader("🏠 地点情報")
    address = get_simple_address(current_lat, current_lon)
    st.info(f"**住所:**\n{address}")
    
    # 💾 保存に関するガイドを追加
    with st.expander("💾 データの保存について", expanded=False):
        st.caption("""
        現在の設定（場所・半径・ニックネーム）は、以下のタイミングで自動的に保存されます：
        1. **検索ボタン**を押して地点を移動したとき
        2. **Enterキー**で検索を実行したとき
        3. **地図上をクリック**して中心点を変えたとき
        
        ※ニックネームを変更しただけでは保存されません。変更後に一度検索またはクリックを行ってください。
        """)    
    
    st.markdown("---")
    st.subheader("🚶 到達目安・活動量")
    st.warning("⚠️ 以下の数値は、地図上の**直線距離**に基づいた理論値です。実際の道路状況により時間はさらに増加します。")

    for i, (r, color) in enumerate(sets):
        if r > 0:
            walk_time = r * 1000 / 80
            bike_time = r * 1000 / 250
            run_time = r * 1000 / 167

            steps = r * 1250
            calories_walk = r * 60
            calories_run = r * 75

            with st.expander(f"円{i+1} ({r} km) の詳細", expanded=True if i==0 else False):
                st.markdown(f"""
                <div style="border-left: 5px solid {color}; padding-left: 10px;">
                <p><b>🏃 徒歩:</b> 約{int(walk_time)}分</p>
                <p><b>👟 ランニング:</b> 約{int(run_time)}分 <span style="font-size: 0.8em; color: gray;">(6分/kmペース)</span></p>
                <p><b>🚲 自転車:</b> 約{int(bike_time)}分</p>
                <hr style="margin: 10px 0;">
                <p><b>🔥 消費目安:</b></p>
                <ul>
                    <li>ウォーキング: 約{int(calories_walk)}kcal</li>
                    <li>ランニング: 約{int(calories_run)}kcal</li>
                </ul>
                </div>
                """, unsafe_allow_html=True)

    st.info("🏃 活動量の算出基準")
    st.caption("""
    - **徒歩**: 分速80m / 消費 60kcal (1km移動時)
    - **ランニング**: 分速167m / 消費 75kcal (1km移動時)
    - **自転車**: 分速250m
    ※消費カロリーは体重60kgの標準的な数値を基準に算出しています。
    """)

# 地図クリック処理
if map_data and map_data["last_clicked"]:
    nl, ng = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
    if abs(nl - st.session_state.clicked_lat) > 0.0001:
        st.session_state.clicked_lat, st.session_state.clicked_lon = nl, ng
        # 地図クリック時にも現在のニックネームで保存
        save_log_to_sheets(display_name, "地図クリック選択地点", nl, ng, sets[0][0], sets[1][0], sets[2][0])

        st.rerun()




