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
st.set_page_config(layout="wide", page_title="同心円エリア描画ツール（安定版）")

st.title("📍 同心円エリア描画ツール（安定版）")

# --- 関数群 ---
def calculate_zoom_level(radius_km):
    if radius_km <= 0: return 13
    zoom = 14.2 - math.log2(radius_km)
    return max(1, min(18, round(zoom)))

@st.cache_data(ttl=3600)
def search_location(query):
    try:
        # User-Agentをさらにユニークに変更
        geolocator = Nominatim(user_agent="shikuu_analyzer_2026_stable_fixed")
        location = geolocator.geocode(query, language='ja', timeout=10)
        if location:
            return location.latitude, location.longitude, location.address
        return None, None, "地点が見つかりませんでした"
    except Exception as e:
        return None, None, f"検索エラー: {e}"

def get_simple_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="shikuu_analyzer_2026_stable_fixed")
        location = geolocator.reverse(f"{lat}, {lon}", language='ja', timeout=10)
        if location:
            return location.address
        return "住所が見つかりませんでした"
    except Exception as e:
        return f"⚠️ サーバー混雑中（時間をおいて再度お試しください）"

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
        st.error(f"⚠️ スプレッドシート保存エラー: {e}")
        return False

# --- セッション状態の初期化 ---
if 'clicked_lat' not in st.session_state: st.session_state.clicked_lat = 35.6812
if 'clicked_lon' not in st.session_state: st.session_state.clicked_lon = 139.7671
if 'last_search' not in st.session_state: st.session_state.last_search = ""
if 'r1_val' not in st.session_state: st.session_state.r1_val = 1.0
if 'r2_val' not in st.session_state: st.session_state.r2_val = 2.5
if 'r3_val' not in st.session_state: st.session_state.r3_val = 5.0

# --- サイドバー設定 ---
with st.sidebar:
    st.header("👤 ユーザー設定")
    user_name_input = st.text_input("ニックネーム", value="", placeholder="匿名ユーザー")
    display_name = user_name_input if user_name_input else "匿名ユーザー"
    
    if st.button("前回の続きから再開"):
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl=0)
            user_history = df[df['user_name'] == display_name]
            if not user_history.empty:
                last_record = user_history.iloc[-1]
                st.session_state.clicked_lat = float(last_record['lat'])
                st.session_state.clicked_lon = float(last_record['lon'])
                st.session_state.r1_val = float(last_record['r1'])
                st.session_state.r2_val = float(last_record['r2'])
                st.session_state.r3_val = float(last_record['r3'])
                st.success(f"{display_name}さんのデータを復元しました")
                st.rerun()
            else:
                st.warning(f"{display_name}さんの履歴が見つかりません")
        except:
            st.error("履歴の読み込みに失敗しました")
            
    st.markdown("---")
    st.header("⚙️ エリア設定")
    search_query = st.text_input("地名・住所で検索", placeholder="例：青森空港", key="search_input")
    search_button = st.button("検索実行")
    
    # 半径の設定
    sets = []
    configs = [
        {"id": 1, "key": "r1_val", "def_c": "#FF4B4B", "label": "🔴 円1"},
        {"id": 2, "key": "r2_val", "def_c": "#1E90FF", "label": "🔵 円2"},
        {"id": 3, "key": "r3_val", "def_c": "#2E8B57", "label": "🟢 円3"}
    ]
    for conf in configs:
        st.subheader(conf["label"])
        col_r, col_c = st.columns([2, 1])
        r = col_r.number_input("半径(km)", min_value=0.0, value=st.session_state[conf["key"]], step=0.5, key=f"r_in_{conf['id']}")
        c = col_c.color_picker("色", conf["def_c"], key=f"c_{conf['id']}")
        st.session_state[conf["key"]] = r
        sets.append((r, c))

    # 検索実行ロジック
    if (search_query and search_query != st.session_state.last_search) or search_button:
        if search_query:
            with st.spinner("地点を検索中..."):
                res_lat, res_lon, res_address = search_location(search_query)
                if res_lat:
                    st.session_state.clicked_lat, st.session_state.clicked_lon = res_lat, res_lon
                    st.session_state.last_search = search_query
                    # 検索時は住所が判明しているのでそのまま保存
                    save_log_to_sheets(display_name, res_address, res_lat, res_lon, sets[0][0], sets[1][0], sets[2][0])
                    st.toast("✅ 検索地点を保存しました")
                    st.rerun()
                else:
                    st.error("❓ 地点が見つかりませんでした")

    st.markdown("---")
    map_style = st.radio("地図スタイル", ["OpenStreetMap", "地理院 標準地図", "地理院 空中写真"])

# --- メイン表示エリア ---
current_lat, current_lon = st.session_state.clicked_lat, st.session_state.clicked_lon
zoom_val = calculate_zoom_level(sets[1][0] if sets[1][0] > 0 else 1.0)

col_map, col_info = st.columns([3, 1])

with col_map:
    # 地図タイルの設定
    tiles = "OpenStreetMap"
    attr = "OpenStreetMap contributors"
    if map_style == "地理院 標準地図":
        tiles = "https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png"
        attr = "国土地理院"
    elif map_style == "地理院 空中写真":
        tiles = "https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg"
        attr = "国土地理院"

    m = folium.Map(location=[current_lat, current_lon], zoom_start=zoom_val, tiles=tiles, attr=attr)
    folium.Marker([current_lat, current_lon], icon=folium.Icon(color="red", icon="info-sign")).add_to(m)

    for i, (r, color) in enumerate(sets):
        if r > 0:
            weight = 4 if i == 0 else 2
            dash = "10, 10" if i == 2 else None
            folium.Circle(location=[current_lat, current_lon], radius=r*1000, color=color, weight=weight, dash_array=dash, fill=True, fill_opacity=0.07).add_to(m)
            # ラベル
            folium.Marker(location=[current_lat + (r / 111.0), current_lon], icon=DivIcon(icon_size=(150,36), icon_anchor=(75,18),
                html=f'<div style="font-size: 9pt; color: {color}; font-weight: bold; text-align: center; background: white; border: 1px solid {color}; border-radius: 4px;">{r} km</div>')).add_to(m)

    map_data = st_folium(m, width=None, height=600, key=f"map_{current_lat}_{current_lon}", use_container_width=True)

with col_info:
    st.subheader("🏠 地点情報")
    st.write(f"**緯度:** `{current_lat:.5f}`")
    st.write(f"**経度:** `{current_lon:.5f}`")
    
    # ボタンによる住所取得（エラー対策）
    if st.button("🗺️ 住所を表示する"):
        with st.spinner("住所を取得中..."):
            address = get_simple_address(current_lat, current_lon)
            st.info(f"**現在の住所:**\n{address}")
    else:
        st.caption("※サーバー負荷軽減のため、住所表示は手動にしています。")

    st.markdown("---")
    st.subheader("🚶 到達目安")
    for i, (r, color) in enumerate(sets):
        if r > 0:
            with st.expander(f"円{i+1} ({r} km) の詳細"):
                st.markdown(f"""
                - **徒歩:** 約{int(r*1000/80)}分
                - **自転車:** 約{int(r*1000/250)}分
                - **ラン:** 約{int(r*1000/167)}分
                """)

# 地図クリック処理
if map_data and map_data["last_clicked"]:
    nl, ng = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
    if abs(nl - st.session_state.clicked_lat) > 0.0001:
        st.session_state.clicked_lat, st.session_state.clicked_lon = nl, ng
        # クリック時は住所取得を省き、座標を住所として保存（高速化＆エラー回避）
        save_log_to_sheets(display_name, f"地図クリック地点({nl:.4f}, {ng:.4f})", nl, ng, sets[0][0], sets[1][0], sets[2][0])
        st.rerun()
