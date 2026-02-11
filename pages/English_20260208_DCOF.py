import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.features import DivIcon
import math
from geopy.geocoders import Nominatim
from streamlit_gsheets import GSheetsConnection
import datetime
import pandas as pd

# --- Page Config ---
st.set_page_config(layout="wide", page_title="Area Tool (EN)")
st.title("📍 Concentric Circle Area Tool (English: trial product)")

# --- Info / License / Disclaimer (English version) ---
st.markdown("---")
with st.expander("ℹ️ Info / License / Disclaimer"):
    st.markdown("""
    ### **【Disclaimer】**
    - The results provided by this application (travel time, calories burned, address data, etc.) are theoretical estimates based on straight-line distances and are not guaranteed to be accurate or safe for navigation.
    - The developer is not responsible for any accidents, damages, or troubles resulting from the use of this application. Please follow local traffic rules and actual road conditions.
    - **Map Labels**: Note that map labels may switch to the local language depending on the zoom level due to map tile specifications.

    ### **【Data Sources / Credits】**
    - **Map Data**: [OpenStreetMap](https://www.openstreetmap.org/copyright) (c) OpenStreetMap contributors
    - **Map Tiles (Standard)**: [CartoDB Voyager Tiles](https://carto.com/basemaps/)
    - **Map Tiles (Satellite)**: [ESRI World Imagery](https://www.esri.com/)
    - **Geocoding Service**: [Nominatim](https://nominatim.org/) (Data by OpenStreetMap)

    ### **【Calculation Basis】**
    - Travel estimates are based on: Walk (80m/min), Run (167m/min), Bike (250m/min).
    - Calories are rough estimates based on an average adult weight of 60kg.

    ### **【License】**
    - **MIT License**
    - © 2026 Shikuu Kitashirakawa (ShikuuKitashirakawa)
    """)

# --- Units & Constants ---
KM_TO_MILE = 0.621371

# --- Translation Dictionary ---
T = {
    "user_set": "👤 User Settings", "nickname": "Nickname", "resume_btn": "Resume from Last Session",
    "area_set": "⚙️ Area Settings", "search_label": "Search Location", "search_btn": "Search",
    "history_label": "📜 Restore from History", "history_select": "Select past location", "restore_btn": "Restore this location",
    "coord_move": "📍 Move by Coordinates", "lat": "Latitude", "lon": "Longitude", "move_btn": "Move to Coords",
    "unit_select": "Unit Setting", "radius": "Radius", "map_style": "Map Style",
    "info_title": "🏠 Location Info", "addr_btn": "🗺️ Show Address",
    "travel_estimate": "🚶 Travel Estimates", "calories": "Estimated Calories",
    "license_info": "ℹ️ Info / License / Disclaimer",
    "map_note": "💡 Note: Map labels are designed to display in English. Some detailed labels may vary by zoom level."
}

# --- Functions ---
def calculate_zoom_level(radius_km):
    if radius_km <= 0: return 13
    zoom = 14.2 - math.log2(radius_km)
    return max(1, min(18, round(zoom)))

@st.cache_data(ttl=3600)
def search_location(query):
    geolocator = Nominatim(user_agent="shikuu_analyzer_2026_en_carto_v9")
    try:
        location = geolocator.geocode(query, language='en', timeout=10)
        if location: return location.latitude, location.longitude, location.address
    except: pass
    return None, None, "Not Found"

def get_simple_address(lat, lon):
    geolocator = Nominatim(user_agent="shikuu_analyzer_2026_en_carto_v9")
    try:
        location = geolocator.reverse(f"{lat}, {lon}", language='en', timeout=10)
        if location: return location.address
    except: pass
    return "Address Not Found"

def save_log_to_sheets(user_name, address, lat, lon, r1, r2, r3):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        existing_data = conn.read(ttl=0)
        new_row = pd.DataFrame([{"date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                 "user_name": user_name, "address": address, "lat": lat, "lon": lon,
                                 "r1": r1, "r2": r2, "r3": r3}])
        updated_df = pd.concat([existing_data, new_row], ignore_index=True)
        conn.update(data=updated_df)
    except: pass

# --- Session State ---
if 'clicked_lat' not in st.session_state: st.session_state.clicked_lat = 35.6812
if 'clicked_lon' not in st.session_state: st.session_state.clicked_lon = 139.7671
if 'r1_val' not in st.session_state: st.session_state.r1_val = 1.0
if 'r2_val' not in st.session_state: st.session_state.r2_val = 2.5
if 'r3_val' not in st.session_state: st.session_state.r3_val = 5.0

# --- Sidebar ---
with st.sidebar:
    st.header(T["user_set"])
    user_name_input = st.text_input(T["nickname"], value="", placeholder="Anonymous")
    display_name = user_name_input if user_name_input else "Anonymous"
    
    if st.button(T["resume_btn"]):
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(ttl=0)
            user_history = df[df['user_name'] == display_name]
            if not user_history.empty:
                last_record = user_history.iloc[-1]
                st.session_state.clicked_lat, st.session_state.clicked_lon = float(last_record['lat']), float(last_record['lon'])
                st.session_state.r1_val, st.session_state.r2_val, st.session_state.r3_val = float(last_record['r1']), float(last_record['r2']), float(last_record['r3'])
                st.rerun()
        except: pass

    st.markdown("---")
    st.header(T["area_set"])
    unit = st.radio(T["unit_select"], ["km", "mile"], horizontal=True)
    is_mile = (unit == "mile")

    search_query = st.text_input(T["search_label"], placeholder="e.g. Tokyo Tower")
    if st.button(T["search_btn"]):
        if search_query:
            res_lat, res_lon, res_address = search_location(search_query)
            if res_lat:
                st.session_state.clicked_lat, st.session_state.clicked_lon = res_lat, res_lon
                save_log_to_sheets(display_name, res_address, res_lat, res_lon, st.session_state.r1_val, st.session_state.r2_val, st.session_state.r3_val)
                st.rerun()

    st.markdown("---")
    configs = [("r1_val", "#FF4B4B", "🔴 Circle 1"), ("r2_val", "#1E90FF", "🔵 Circle 2"), ("r3_val", "#2E8B57", "🟢 Circle 3")]
    sets = []
    for key, color, label in configs:
        st.subheader(label)
        col_r, col_c = st.columns([2, 1])
        val_to_show = st.session_state[key] * KM_TO_MILE if is_mile else st.session_state[key]
        r_in = col_r.number_input(f"Radius ({unit})", min_value=0.0, value=val_to_show, step=0.5, key=f"in_{key}")
        c = col_c.color_picker("Color", color, key=f"c_{key}")
        st.session_state[key] = r_in / KM_TO_MILE if is_mile else r_in
        sets.append((st.session_state[key], c))

    map_style = st.radio(T["map_style"], ["Standard (English Labels)", "Satellite (ESRI Imagery)"])

# --- Main Area ---
current_lat, current_lon = st.session_state.clicked_lat, st.session_state.clicked_lon
zoom_val = calculate_zoom_level(sets[1][0] if sets[1][0] > 0 else 1.0)
col_map, col_info = st.columns([3, 1])

with col_map:
    # 🌟 CartoDBの英語固定手法: ベース（地名なし）+ 英語ラベルレイヤー
    m = folium.Map(location=[current_lat, current_lon], zoom_start=zoom_val, tiles=None)

    if map_style == "Standard (English Labels)":
        # ベース（地名なし）
        folium.TileLayer(
            tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png",
            attr="© CartoDB", name="CartoDB Voyager (Base)", control=False
        ).add_to(m)
        # 英語ラベルだけを上に重ねる
        folium.TileLayer(
            tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png",
            attr="© CartoDB contributors", name="English Labels", control=False
        ).add_to(m)
    else:
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", 
            attr="© ESRI World Imagery", name="Satellite"
        ).add_to(m)

    folium.Marker([current_lat, current_lon], icon=folium.Icon(color="red", icon="info-sign")).add_to(m)
    for i, (r_km, color) in enumerate(sets):
        if r_km > 0:
            folium.Circle(location=[current_lat, current_lon], radius=r_km*1000, color=color, weight=2, fill=True, fill_opacity=0.07).add_to(m)
            disp_r = r_km * KM_TO_MILE if is_mile else r_km
            folium.Marker(location=[current_lat + (r_km / 111.0), current_lon], 
                          icon=DivIcon(icon_size=(150,36), icon_anchor=(75,18),
                          html=f'<div style="font-size: 9pt; color: {color}; font-weight: bold; text-align: center; background: white; border: 1px solid {color}; border-radius: 4px; padding: 2px;">{disp_r:.2f} {unit}</div>')).add_to(m)

    map_data = st_folium(m, width=None, height=600, key=f"v_carto_strict_{unit}_{map_style}", use_container_width=True)
    st.caption(T["map_note"])

with col_info:
    st.subheader(T["info_title"])
    if st.button(T["addr_btn"]):
        st.info(get_simple_address(current_lat, current_lon))
    st.markdown("---")
    st.subheader(T["travel_estimate"])
    for i, (r_km, color) in enumerate(sets):
        if r_km > 0:
            disp_r = r_km * KM_TO_MILE if is_mile else r_km
            with st.expander(f"Circle {i+1} ({disp_r:.2f} {unit})", expanded=True if i==0 else False):
                walk, run, bike = int(r_km*1000/80), int(r_km*1000/167), int(r_km*1000/250)
                st.markdown(f"""
                <div style="border-left: 5px solid {color}; padding-left: 10px;">
                <b>🚶 Walk:</b> {walk} min<br>
                <b>👟 Run:</b> {run} min<br>
                <b>🚲 Bike:</b> {bike} min<br>
                <hr style="margin: 5px 0;">
                <b>🔥 {T['calories']}:</b><br>
                {int(r_km*60)} - {int(r_km*75)} kcal
                </div>
                """, unsafe_allow_html=True)
    
    st.info("🏃 Basis for calculation")
    st.caption("Walk: 80m/min, Run: 167m/min, Bike: 250m/min\n(Based on 60kg body weight)")

# Click logic
if map_data and map_data["last_clicked"]:
    nl, ng = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
    if abs(nl - st.session_state.clicked_lat) > 0.0001:
        st.session_state.clicked_lat, st.session_state.clicked_lon = nl, ng
        save_log_to_sheets(display_name, f"Click({nl:.4f}, {ng:.4f})", nl, ng, st.session_state.r1_val, st.session_state.r2_val, st.session_state.r3_val)

        st.rerun()

