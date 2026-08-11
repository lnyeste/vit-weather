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

# 5. STRAPABÍRÓ, IDŐZÓNA-BIZTOS ÉLŐ ADATFELDOLGOZÓ MOTOR


def get_pure_live_weather(field, day_idx):
    """
    Open-Meteo alapú időjárás-lekérdezés.
    10:00–20:00 között 15 perces pontokat készít
    az órás előrejelzés lineáris interpolációjával.

    day_idx:
        0 = ma
        1 = holnap
        2 = holnapután
    """

    data_rows = []

    lat = AIRFIELDS[field]["lat"]
    lon = AIRFIELDS[field]["lon"]

    # A megfelelő dátum
    target_date_local = today_dt + datetime.timedelta(days=day_idx)

    # A 15 perces megjelenítés kezdete
    start_time = datetime.datetime.combine(
        target_date_local,
        datetime.time(10, 0)
    )

    # ------------------------------------------------------------------
    # OPEN-METEO API
    # ------------------------------------------------------------------

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": (
            "temperature_2m,"
            "wind_speed_10m,"
            "wind_direction_10m,"
            "cloud_cover,"
            "relative_humidity_2m"
        ),
        "wind_speed_unit": "kmh",
        "timezone": "Europe/Budapest",
        "forecast_days": 3
    }

    headers = {
        "User-Agent": "Kvasz-Andras-Repuloklub-Weather-Dashboard/1.0"
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=15
        )

        # HTTP hiba
        response.raise_for_status()

        res = response.json()

    except requests.exceptions.Timeout:
        st.error(
            "❌ Időtúllépés: az időjárási szerver nem válaszolt 15 másodpercen belül."
        )
        st.stop()

    except requests.exceptions.ConnectionError:
        st.error(
            "❌ Kapcsolódási hiba: nem sikerült elérni az Open-Meteo szervert."
        )
        st.stop()

    except requests.exceptions.HTTPError as e:
        st.error(
            f"❌ Open-Meteo HTTP hiba: {e}"
        )
        st.stop()

    except requests.exceptions.RequestException as e:
        st.error(
            f"❌ Hálózati hiba az időjárási adatok lekérésekor: {e}"
        )
        st.stop()

    except ValueError:
        st.error(
            "❌ Hibás válasz érkezett az időjárási szervertől."
        )
        st.stop()

    except Exception as e:
        st.error(
            f"❌ Ismeretlen kapcsolódási hiba: {e}"
        )
        st.stop()

    # ------------------------------------------------------------------
    # API-VÁLASZ ELLENŐRZÉSE
    # ------------------------------------------------------------------

    if "hourly" not in res:
        st.error(
            "❌ Az Open-Meteo válaszában nincs 'hourly' adat."
        )
        st.stop()

    hourly = res["hourly"]

    required_fields = [
        "time",
        "temperature_2m",
        "wind_speed_10m",
        "wind_direction_10m",
        "cloud_cover",
        "relative_humidity_2m"
    ]

    missing_fields = [
        field_name
        for field_name in required_fields
        if field_name not in hourly
    ]

    if missing_fields:
        st.error(
            "❌ Hiányzó időjárási adatok: "
            + ", ".join(missing_fields)
        )
        st.stop()

    # ------------------------------------------------------------------
    # ÓRÁS ADATOK DICTIONARY-BE RENDEZÉSE
    #
    # Nem index alapján dolgozunk, hanem az API által visszaadott
    # dátum/idő alapján. Ez sokkal biztonságosabb.
    # ------------------------------------------------------------------

    try:
        api_times = [
            datetime.datetime.fromisoformat(t)
            for t in hourly["time"]
        ]
    except Exception as e:
        st.error(
            f"❌ Az Open-Meteo időbélyegeinek feldolgozása sikertelen: {e}"
        )
        st.stop()

    weather_data = {}

    for i, dt_value in enumerate(api_times):

        # Csak olyan pontot használunk, amelyhez minden szükséges
        # meteorológiai adat rendelkezésre áll.
        try:
            temp = hourly["temperature_2m"][i]
            wind_speed = hourly["wind_speed_10m"][i]
            wind_dir = hourly["wind_direction_10m"][i]
            cloud = hourly["cloud_cover"][i]
            rh = hourly["relative_humidity_2m"][i]

            if any(
                value is None
                for value in [temp, wind_speed, wind_dir, cloud, rh]
            ):
                continue

            weather_data[dt_value] = {
                "temp": float(temp),
                "wind_speed": float(wind_speed),
                "wind_dir": float(wind_dir),
                "cloud": float(cloud),
                "rh": float(rh)
            }

        except (IndexError, TypeError, ValueError):
            continue

    # ------------------------------------------------------------------
    # ELLENŐRIZZÜK, HOGY A KÍVÁNT NAP ADATAI MEGVANNAK-E
    # ------------------------------------------------------------------

    required_start = datetime.datetime.combine(
        target_date_local,
        datetime.time(10, 0)
    )

    required_end = datetime.datetime.combine(
        target_date_local,
        datetime.time(20, 0)
    )

    # Az interpolációhoz 10:00 és 20:00 között minden órás pontnak
    # rendelkezésre kell állnia.
    required_hours = []

    current_hour = required_start

    while current_hour <= required_end:
        required_hours.append(current_hour)
        current_hour += datetime.timedelta(hours=1)

    missing_hours = [
        dt_value.strftime("%Y-%m-%d %H:%M")
        for dt_value in required_hours
        if dt_value not in weather_data
    ]

    if missing_hours:
        st.error(
            "❌ Nem áll rendelkezésre elegendő órás előrejelzési adat "
            f"{target_date_local.strftime('%Y.%m.%d.')} napra."
        )
        st.stop()

    # ------------------------------------------------------------------
    # NAPI ALAPSZÉL
    # ------------------------------------------------------------------

    daily_period_data = [
        weather_data[dt_value]
        for dt_value in required_hours
    ]

    # Szélirányt egyszerű számtani átlaggal közelítjük.
    # Ez normál dashboardhoz megfelelő, bár körkörös átlag lenne
    # meteorológiailag pontosabb.
    base_wind_dir = int(
        round(
            np.mean(
                [item["wind_dir"] for item in daily_period_data]
            )
        )
    )

    base_wind_speed = int(
        round(
            np.mean(
                [item["wind_speed"] for item in daily_period_data]
            )
        )
    )

    # ------------------------------------------------------------------
    # SEGÉDFÜGGVÉNY LINEÁRIS INTERPOLÁCIÓHOZ
    # ------------------------------------------------------------------

    def interpolate_value(current_dt, key):
        """
        Két szomszédos órás Open-Meteo értékből lineárisan
        interpolálja a negyedórás értéket.
        """

        # Pontos órára esünk
        if current_dt in weather_data:
            return weather_data[current_dt][key]

        # Az előző óra
        previous_hour = current_dt.replace(
            minute=0,
            second=0,
            microsecond=0
        )

        # A következő óra
        next_hour = previous_hour + datetime.timedelta(hours=1)

        if previous_hour not in weather_data:
            previous_hour = required_start

        if next_hour not in weather_data:
            next_hour = required_end

        previous_value = weather_data[previous_hour][key]
        next_value = weather_data[next_hour][key]

        total_seconds = (
            next_hour - previous_hour
        ).total_seconds()

        if total_seconds <= 0:
            return previous_value

        elapsed_seconds = (
            current_dt - previous_hour
        ).total_seconds()

        weight = elapsed_seconds / total_seconds

        return (
            previous_value * (1 - weight)
            + next_value * weight
        )

    # ------------------------------------------------------------------
    # 41 DARAB NEGYEDÓRÁS ADAT
    #
    # 10:00, 10:15, ..., 19:45, 20:00
    # ------------------------------------------------------------------

    for i in range(41):

        current_time = start_time + datetime.timedelta(
            minutes=15 * i
        )

        time_str = current_time.strftime("%H:%M")

        # --------------------------------------------------------------
        # INTERPOLÁLT METEOROLÓGIAI ÉRTÉKEK
        # --------------------------------------------------------------

        current_temp = round(
            interpolate_value(
                current_time,
                "temp"
            ),
            1
        )

        current_cloud = round(
            interpolate_value(
                current_time,
                "cloud"
            )
        )

        current_wind_spd = round(
            interpolate_value(
                current_time,
                "wind_speed"
            )
        )

        current_wind_dir = round(
            interpolate_value(
                current_time,
                "wind_dir"
            )
        )

        current_rh = interpolate_value(
            current_time,
            "rh"
        )

        # --------------------------------------------------------------
        # HARMATPONT
        # Magnus-képlet közelítés
        # --------------------------------------------------------------

        safe_rh = max(
            1.0,
            min(100.0, current_rh)
        )

        alpha = (
            (17.27 * current_temp)
            / (237.7 + current_temp)
        ) + math.log(
            safe_rh / 100.0
        )

        current_dew = (
            237.7 * alpha
        ) / (
            17.27 - alpha
        )

        # --------------------------------------------------------------
        # FELHŐALAP
        # --------------------------------------------------------------

        calc_base = int(
            (current_temp - current_dew) * 125
        )

        if current_cloud > 15:
            cumulus_base = max(
                500,
                calc_base
            )
        else:
            cumulus_base = 0

        # --------------------------------------------------------------
        # TERMIK ERŐSSÉG
        # --------------------------------------------------------------

        hour_val = (
            current_time.hour
            + current_time.minute / 60.0
        )

        thermal_factor = max(
            0,
            1 - ((hour_val - 14.0) / 4.5) ** 2
        )

        if (
            thermal_factor > 0.05
            and current_cloud < 80
        ):
            base_climb = (
                (current_temp - current_dew)
                * 0.25
                * (1 - current_cloud / 120)
            )

            thermal_climb = round(
                max(
                    0.5,
                    min(
                        base_climb * thermal_factor,
                        5.0
                    )
                ),
                1
            )
        else:
            thermal_climb = 0

        # --------------------------------------------------------------
        # SZÉLNYÍRÁS
        # --------------------------------------------------------------

        wind_shear = "Alacsony"

        if (
            hour_val > 18.0
            and current_wind_spd > 18
        ):
            wind_shear = "Közepes (Esti stabilizáció)"

        elif current_wind_spd > 25:
            wind_shear = "Erős (Magas alapszél)"

        # --------------------------------------------------------------
        # FELHŐZET
        # --------------------------------------------------------------

        if current_cloud < 15:
            cu_cover = "0/8 SKC"

        elif current_cloud < 40:
            cu_cover = "1-2/8 FEW"

        elif current_cloud < 75:
            cu_cover = "3-4/8 SCT"

        else:
            cu_cover = "5-6/8 BKN"

        # --------------------------------------------------------------
        # TÚLFEJLŐDÉS
        # --------------------------------------------------------------

        overdev = (
            "Alacsony"
            if current_cloud < 70
            else "Közepes"
        )

        # --------------------------------------------------------------
        # ADATSOR
        # --------------------------------------------------------------

        data_rows.append({
            "Időpont": time_str,
            "Hőmérséklet (°C)": current_temp,
            "Termik (m/s)": (
                thermal_climb
                if thermal_climb > 0
                else "-"
            ),
            "Alap (m QNH)": (
                cumulus_base
                if cumulus_base > 0
                else "-"
            ),
            "Felhőzet": cu_cover,
            "Szél": (
                f"{int(current_wind_dir)}° / "
                f"{int(current_wind_spd)} km/h"
            ),
            "Szélnyírás": wind_shear,
            "Túlfejlődés": overdev
        })

    # ------------------------------------------------------------------
    # SIKERES ADATBETÖLTÉS
    # ------------------------------------------------------------------

    st.sidebar.success(
        "📡 Valós adatok sikeresen betöltve!"
    )

    return (
        pd.DataFrame(data_rows),
        base_wind_dir,
        base_wind_speed
    )
```



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
