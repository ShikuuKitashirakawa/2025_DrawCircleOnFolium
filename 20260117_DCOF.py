import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.features import DivIcon
import math
from geopy.geocoders import Nominatim

# --- ページ設定 ---
st.set_page_config(layout="wide", page_title="同心円エリア描画ツール（試作版）")

# タイトルと使用用途例
st.title("📍 同心円エリア描画ツール（試作版）")

st.markdown("""
### 💡 このツールの活用シーン
* **商圏分析**: 店舗を中心に、徒歩・自転車・自動車それぞれの集客範囲を可視化。
* **ランニング・散歩コースの検討**: 自宅からの距離を把握し、無理のないトレーニングメニューを計画。
* **物件探し・立地評価**: 検討中の物件から駅やスーパーまでの距離感を直感的に把握。
* **防災・避難計画**: 自宅から避難所までの距離や、災害時の影響範囲の目安を確認。
* **サービス提供エリアの確認**: 配送・デリバリーや出張修理などの対応範囲のシミュレーション。
""")

st.info("地図上をクリック、またはサイドバーからキーワード検索をすると、その地点を中心に描画します。")

# --- ズームレベル計算関数 ---
def calculate_zoom_level(radius_km):
    if radius_km <= 0: return 13
    zoom = 14.2 - math.log2(radius_km)
    return max(1, min(18, round(zoom)))

# --- 住所・名称からの検索関数 (ジオコーディング) ---
@st.cache_data(ttl=3600)
def search_location(query):
    try:
        geolocator = Nominatim(user_agent="area_analyzer_final_2026")
        location = geolocator.geocode(query, language='ja')
        if location:
            return location.latitude, location.longitude, location.address
        return None, None, "地点が見つかりませんでした"
    except:
        return None, None, "検索エラーが発生しました"

# --- 座標からの住所取得関数 (逆ジオコーディング) ---
@st.cache_data(ttl=3600)
def get_simple_address(lat, lon):
    try:
        geolocator = Nominatim(user_agent="area_analyzer_final_2026")
        location = geolocator.reverse(f"{lat}, {lon}", language='ja')
        return location.address if location else "住所が見つかりませんでした"
    except:
        return "住所取得エラー"

# --- セッション状態の初期化 ---
if 'clicked_lat' not in st.session_state:
    st.session_state.clicked_lat = 35.6812
if 'clicked_lon' not in st.session_state:
    st.session_state.clicked_lon = 139.7671

# --- サイドバー設定 ---
with st.sidebar:
    st.header("⚙️ エリア設定")
    
    # 🔍 キーワード検索（Enter対応版）
    st.subheader("🔍 キーワード検索")
    
    # 前回の検索語を保持するセッションを初期化
    if 'last_search' not in st.session_state:
        st.session_state.last_search = ""

    # text_input自体がEnterキーでrerunをトリガーします
    search_query = st.text_input("施設名・地名・住所を入力", placeholder="例：東京駅、京都市四条河原町", key="search_input")

    # 検索を実行する条件：Enterが押されて内容が前回と異なる、またはボタンが押された場合
    search_triggered = st.button("検索")
    
    # Enterキーまたはボタンによるトリガー検知
    if (search_query and search_query != st.session_state.last_search) or search_triggered:
        with st.spinner("地点を検索中..."):
            res_lat, res_lon, res_address = search_location(search_query)
            if res_lat:
                st.session_state.clicked_lat = res_lat
                st.session_state.clicked_lon = res_lon
                st.session_state.last_search = search_query # 検索語を保存
                st.success(f"発見: {res_address[:30]}...")
                st.rerun()
            else:
                st.error("地点が見つかりませんでした。")
    
    st.markdown("---")
    
    # 緯度経度の直接入力（セッション状態を反映）
    lat = st.number_input("中心緯度", value=st.session_state.clicked_lat, format="%.6f")
    lon = st.number_input("中心経度", value=st.session_state.clicked_lon, format="%.6f")
    
    # 手動入力があった場合にセッションを更新
    if lat != st.session_state.clicked_lat or lon != st.session_state.clicked_lon:
        st.session_state.clicked_lat = lat
        st.session_state.clicked_lon = lon

    st.markdown("---")
    
    sets = []
    configs = [
        {"id": 1, "def_r": 1.0, "def_c": "#FF4B4B", "label": "🔴 円1 (近圏: 太実線)"},
        {"id": 2, "def_r": 2.5, "def_c": "#1E90FF", "label": "🔵 円2 (中圏: 細実線)"},
        {"id": 3, "def_r": 5.0, "def_c": "#2E8B57", "label": "🟢 円3 (広域: 細点線)"}
    ]
    
    for conf in configs:
        st.subheader(conf["label"])
        col_r, col_c = st.columns([2, 1])
        r = col_r.number_input(f"半径 (km)", min_value=0.0, value=conf["def_r"], step=0.5, key=f"r{conf['id']}")
        c = col_c.color_picker("色", conf["def_c"], key=f"c{conf['id']}")
        sets.append((r, c))
    
    st.markdown("---")
    map_style = st.radio("地図スタイル", ["標準地図", "淡色地図", "シームレス空中写真"])

    st.markdown("---")
    with st.expander("ℹ️ 免責事項・ライセンス"):
        st.caption("""
        **免責事項**
        - 本アプリの計算結果（面積・住所等）の正確性は保証されません。
        - 本アプリの利用により生じた損害について、作者は一切の責任を負いません。
        - 地図データは国土地理院タイル、住所検索はOpenStreetMap(Nominatim)を利用しています。
        
        **ライセンス**
        MIT License
        © 2026 Shikuu Kitashirakawa
        """)

# --- 自動ズームと地図 ---
focus_r = sets[1][0] if sets[1][0] > 0 else (sets[0][0] if sets[0][0] > 0 else 1.0)
zoom_val = calculate_zoom_level(focus_r)

col_map, col_info = st.columns([3, 1])

with col_map:
    map_tiles = {
        "標準地図": "https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png",
        "淡色地図": "https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png",
        "シームレス空中写真": "https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg"
    }
    
    m = folium.Map(location=[lat, lon], zoom_start=zoom_val, tiles=map_tiles[map_style], attr="国土地理院")
    folium.Marker([lat, lon], icon=folium.Icon(color="black", icon="info-sign")).add_to(m)

    for i, (r, color) in enumerate(sets):
        if r > 0:
            weight = 5 if i == 0 else 2
            dash = "10, 10" if i == 2 else None
            folium.Circle(location=[lat, lon], radius=r*1000, color=color, weight=weight, dash_array=dash, fill=True, fill_opacity=0.05).add_to(m)
            
            # 半径ラベル（北側に表示）
            label_lat = lat + (r / 111.0) 
            folium.Marker(location=[label_lat, lon], icon=DivIcon(icon_size=(150, 36), icon_anchor=(75, 18),
                html=f'<div style="font-size: 9pt; color: {color}; font-weight: bold; text-align: center; background-color: rgba(255,255,255,0.8); border: 1px solid {color}; border-radius: 4px; padding: 1px 4px;">{r} km</div>')).add_to(m)

    # 地図描画（keyを緯度・経度・ズームに紐付けることで、検索時に確実にリセットされるようにします）
    map_data = st_folium(m, width=None, height=600, key=f"map_{st.session_state.clicked_lat}_{st.session_state.clicked_lon}_{zoom_val}", use_container_width=True)

with col_info:
    st.subheader("🏠 地点情報")
    address = get_simple_address(lat, lon)
    st.info(f"**住所:**\n{address}")
    st.caption(f"座標: {lat:.6f}, {lon:.6f}")
    
    st.markdown("---")
    st.subheader("📏 エリア面積")
    for i, (r, color) in enumerate(sets):
        if r > 0:
            area = math.pi * (r**2)
            st.markdown(f'<div style="border-left: 5px solid {color}; padding-left: 10px; margin-bottom: 15px;"><span style="font-size: 0.8em; color: gray;">円{i+1} 半径</span><br><b>{r} km</b> / <span style="color:{color};"><b>{area:.2f} km²</b></span></div>', unsafe_allow_html=True)

# 地図クリック処理
if map_data and map_data["last_clicked"]:
    nl, ng = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
    # 前回の座標と一定以上の差があれば更新
    if abs(nl - st.session_state.clicked_lat) > 0.000001:
        st.session_state.clicked_lat, st.session_state.clicked_lon = nl, ng

        st.rerun()



