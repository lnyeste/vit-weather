import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go
import requests
import math

# 1. OLDAL KONFIGURÁCIÓ
st.set_page_config(page_title="Kvasz András Repülőklub - Időjárás", page_icon="🛫", layout="wide")

# 2. HÁTTÉRKÉP BEÁLLÍTÁSA (A békéscsabai nagyhangár)
hangar_bg_url = "https://behir.hu"

st.markdown(
    f"""
    <style>
    .stApp {{
        background: linear-gradient(rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.88)), url("{hangar_bg_url}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# 3. KVASZ ANDRÁS EGYESÜLET CÍMERE AZ OLDALSÁVBAN
st.sidebar.markdown(
    f"""
    <div style="text-align: center; background-color: rgba(255, 255, 255, 0.95); padding: 15px; border-radius: 15px; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); margin-bottom: 20px;">
        <img src="https://soaringhungary.com" style="width: 100%; max-width: 160px; margin-bottom: 10px; border-radius: 10px;">
        <h3 style="margin: 5px 0 0 0; color: #1E3A8A; font-size: 15px; font-weight: bold;">„KVASZ ANDRÁS”</h3>
        <p style="margin: 2px 0; color: #4B5563; font-size: 11px; font-weight: bold;">Békés Megyei Repülő és Ejtőernyős Egyesület</p>
        <div style="font-size: 11px; color: #9CA3AF; margin-top: 5px;">LHBC • Békéscsaba</div>
    </div>
    """,
    unsafe_allow_html=True
)

# 4. FŐCÍMSOR
st.title("🛫 Kelet-Magyarország 3 Napos Vitorlázórepülő Időjárás-Előrejelzője")
st.write("A Kvasz András Repülőklub hivatalos negyedórás repülésmeteorológiai dashboardja (10:00 - 20:00).")

# Repülőterek koordinátái
AIRFIELDS = {
    "Békéscsaba (LHBC)": {"lat": 46.68, "lon": 21.16},
    "Szeged (LHUD)": {"lat": 46.25, "lon": 20.09},
    "Debrecen (LHDC)": {"lat": 47.49, "lon": 21.62},
    "Miskolc (LHMC)": {"lat": 48.07, "lon": 20.79},
    "Nyíregyháza (LHNY)": {"lat": 47.95, "lon": 21.69}
}

# Repülőgép típusok
GLIDER_TYPES = {
    "KA-7": 26,
    "SF25C Falke": 22,
    "Astir": 38,
    "Cirrus": 38,
    "Cirrus VTC": 39,
    "Standard Jantar 2": 40,
    "Jantar 2B": 48
}

HUNGARIAN_DAYS = {
    "Monday": "Hétfő", "Tuesday": "Kedd", "Wednesday": "Szerda",
    "Thursday": "Csütörtök", "Friday": "Péntek", "Saturday": "Szombat", "Sunday": "Vasárnap"
}

today_dt = datetime.date.today()
tomorrow_dt = today_dt + datetime.timedelta(days=1)
after_tomorrow_dt = today_dt + datetime.timedelta(days=2)

def get_day_label(dt, prefix):
    day_name_eng = dt.strftime("%A")
    day_name_hu = HUNGARIAN_DAYS.get(day_name_eng, day_name_eng)
    return f"{prefix} ({day_name_hu} - {dt.strftime('%m.%d.')})"

day_options = {
    get_day_label(today_dt, "Ma"): 0,
    get_day_label(tomorrow_dt, "Holnap"): 1,
    get_day_label(after_tomorrow_dt, "Holnapután"): 2
}

# Oldalsáv vezérlők
st.sidebar.header("Beállítások")
selected_field = st.sidebar.selectbox("Válassz repülőteret:", list(AIRFIELDS.keys()), index=0)
selected_glider = st.sidebar.selectbox("Repülőgép típusa:", list(GLIDER_TYPES.keys()))
selected_day_label = st.sidebar.radio("Válassz napot:", list(day_options.keys()))

day_offset = day_options[selected_day_label]
target_date = today_dt + datetime.timedelta(days=day_offset)
glider_glide_ratio = GLIDER_TYPES[selected_glider]

# 5. GOLYÓÁLLÓ MET.NO ELŐREJELZŐ MOTOR (Tökéletesített URL-struktúrával)
def get_pure_live_weather(field, day_idx):
    start_time = datetime.datetime.combine(target_date, datetime.time(10, 0))
    data_rows = []
    
    lat = AIRFIELDS[field]["lat"]
    lon = AIRFIELDS[field]["lon"]
    
    headers = {
        'User-Agent': 'KvaszAndrasGlidingClubLHBC contact-nyestel@lhbc.hu'
    }
    
    # FIX ALAPCÍM, perjelek és elgépelések nélkül!
    url = "https://met.no"
    params = {
        "lat": lat,
        "lon": lon
    }
    
    try:
        # A requests.get automatikusan és hibátlanul fűzi össze a címet a paraméterekkel
        response = requests.get(url, params=params, headers=headers, timeout=8)
        if response.status_code != 200:
            st.error(f"❌ Hiba: Az európai időjárási szerver nem válaszolt (HTTP Kód: {response.status_code}).")
            st.stop()
            
        res = response.json()
        if "properties" not in res or "timeseries" not in res["properties"]:
            st.error("❌ Hiba: Üres vagy formázatlan adatcsomag érkezett.")
            st.stop()
            
        timeseries = res["properties"]["timeseries"]
        
        hourly_temps = []
        hourly_wind_speeds = []
        hourly_wind_dirs = []
        hourly_clouds = []
        hourly_rh = []
        
        for ts in timeseries:
            # Időzóna korrekció (+2 óra a magyar időhöz)
            time_dt = datetime.datetime.strptime(ts["time"], "%Y-%m-%dT%H:%M:%SZ") + datetime.timedelta(hours=2)
            if time_dt.date() == target_date and 10 <= time_dt.hour <= 20:
                instant = ts["data"]["instant"]["details"]
                hourly_temps.append(instant["air_temperature"])
                hourly_wind_speeds.append(instant["wind_speed"] * 3.6) # m/s -> km/h
                hourly_wind_dirs.append(instant["wind_from_direction"])
                hourly_clouds.append(instant.get("cloud_area_fraction", 40))
                hourly_rh.append(instant["relative_humidity"])
                
        if len(hourly_temps) < 11:
            st.error("❌ Hiba: A választott nap adatai még nem érhetők el a műholdas hálózaton.")
            st.stop()
            
        base_wind_dir = int(np.mean(hourly_wind_dirs))
        base_wind_speed = int(np.mean(hourly_wind_speeds))
        
        st.sidebar.success("📡 Élő MET.no adatok sikeresen frissítve!")
        
    except Exception as e:
        st.error(f"❌ Kapcsolódási hiba: Nem sikerült az élő szinkronizáció. Ok: {str(e)}")
        st.stop()

    # 41 darab negyedórás lépés (10:00 - 20:00) lineáris interpolációval
    for i in range(41):
        current_time = start_time + datetime.timedelta(minutes=15 * i)
        time_str = current_time.strftime("%H:%M")
        
        hour_val = current_time.hour + current_time.minute / 60.0
        
        idx_float = hour_val - 10.0
        idx_floor = min(int(math.floor(idx_float)), len(hourly_temps) - 1)
        idx_ceil = min(int(math.ceil(idx_float)), len(hourly_temps) - 1)
        weight = idx_float - idx_floor
        
        current_temp = round(hourly_temps[idx_floor] * (1 - weight) + hourly_temps[idx_ceil] * weight, 1)
        current_cloud = round(hourly_clouds[idx_floor] * (1 - weight) + hourly_clouds[idx_ceil] * weight)
        current_wind_spd = round(hourly_wind_speeds[idx_floor] * (1 - weight) + hourly_wind_speeds[idx_ceil] * weight)
        current_wind_dir = round(hourly_wind_dirs[idx_floor] * (1 - weight) + hourly_wind_dirs[idx_ceil] * weight)
        current_rh = hourly_rh[idx_floor] * (1 - weight) + hourly_rh[idx_ceil] * weight
        
        # Harmatpont számítás (Magnus-Formula közelítés)
        alpha = ((17.27 * current_temp) / (237.7 + current_temp)) + math.log(max(1, current_rh) / 100.0)
        current_dew = (237.7 * alpha) / (17.27 - alpha)
        
        # VALÓS FELHŐALAP: Hennig-képlet alapján: (Hőmérséklet - Harmatpont) * 125
        calc_base = int((current_temp - current_dew) * 125)
        cumulus_base = max(500, calc_base) if current_cloud > 15 else 0
        
        # VALÓS TERMIK ERŐSSÉG
        thermal_factor = max(0, 1 - ((hour_val - 14.0) / 4.5) ** 2)
        if thermal_factor > 0.05 and current_cloud < 80:
            base_climb = (current_temp - current_dew) * 0.25 * (1 - current_cloud / 120)
            thermal_climb = round(max(0.5, min(base_climb * thermal_factor, 5.0)), 1)
        else:
            thermal_climb = 0
        
        # Szélnyírás figyelmeztetés
        wind_shear = "Alacsony"
        if hour_val > 18.0 and current_wind_spd > 18:
            wind_shear = "Közepes (Esti stabilizáció)"
        elif current_wind_spd > 25:
            wind_shear = "Erős (Magas alapszél)"
            
        if current_cloud < 15: cu_cover = "0/8 SKC"
        elif current_cloud < 40: cu_cover = "1-2/8 FEW"
        elif current_cloud < 75: cu_cover = "3-4/8 SCT"
        else: cu_cover = "5-6/8 BKN"
            
        overdev = "Alacsony" if current_cloud < 70 else "Közepes"
        
        data_rows.append({
            "Időpont": time_str,
            "Hőmérséklet (°C)": current_temp,
            "Termik (m/s)": thermal_climb if thermal_climb > 0 else "-",
            "Alap (m QNH)": cumulus_base if cumulus_base > 0 else "-",
            "Felhőzet": cu_cover,
            "Szél": f"{int(current_wind_dir)}° / {int(current_wind_spd)} km/h",
            "Szélnyírás": wind_shear,
            "Túlfejlődés": overdev
        })
        
    return pd.DataFrame(data_rows), base_wind_dir, base_wind_speed

df, w_dir, w_spd = get_pure_live_weather(selected_field, day_offset)

# 6. KPI KIJELZŐK
col1, col2, col3, col4 = st.columns(4)
col1.metric("Max Termik", f"{df['Termik (m/s)'].replace('-', 0).max()} m/s")
col2.metric("Max Felhőalap", f"{df['Alap (m QNH)'].replace('-', 0).max()} m QNH")
col3.metric("Napi Alapszél (Átlag)", f"{w_dir}° / {w_spd} km/h")
col4.metric(f"{selected_glider} Teljesítmény", f"Siklószám: 1:{glider_glide_ratio}")

# 7. ADATTÁBLÁZAT
st.subheader(f"Valós negyedórás előrejelzés: {selected_field} ({target_date.strftime('%Y.%m.%d.')})")
st.dataframe(df, use_container_width=True)

# 8. GRAFIKON
st.subheader("Termik és Felhőalap napközbeni lefutása")
fig = go.Figure()
fig.add_trace(go.Scatter(x=df["Időpont"], y=df["Termik (m/s)"].replace('-', 0), name="Termik erősség (m/s)", yaxis="y1", line=dict(color='orange', width=3)))
