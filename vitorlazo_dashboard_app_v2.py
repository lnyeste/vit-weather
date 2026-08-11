import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go
import requests
import math


# ============================================================
# 1. OLDAL KONFIGURÁCIÓ
# ============================================================

st.set_page_config(
    page_title="Kvasz András Repülőklub - Időjárás",
    page_icon="🛫",
    layout="wide"
)


# ============================================================
# 2. HÁTTÉRKÉP BEÁLLÍTÁSA
# ============================================================

hangar_bg_url = "https://behir.hu"

st.markdown(
    f"""
    <style>
    .stApp {{
        background:
            linear-gradient(
                rgba(255, 255, 255, 0.88),
                rgba(255, 255, 255, 0.88)
            ),
            url("{hangar_bg_url}");

        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}

    .weather-warning {{
        padding: 12px;
        border-radius: 10px;
        margin: 8px 0;
        background-color: rgba(255, 243, 205, 0.95);
        border-left: 5px solid #f59e0b;
    }}

    .weather-good {{
        padding: 12px;
        border-radius: 10px;
        margin: 8px 0;
        background-color: rgba(220, 252, 231, 0.95);
        border-left: 5px solid #16a34a;
    }}

    .weather-danger {{
        padding: 12px;
        border-radius: 10px;
        margin: 8px 0;
        background-color: rgba(254, 226, 226, 0.95);
        border-left: 5px solid #dc2626;
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 3. KVASZ ANDRÁS EGYESÜLET CÍMERE
# ============================================================

st.sidebar.markdown(
    f"""
    <div style="
        text-align: center;
        background-color: rgba(255, 255, 255, 0.95);
        padding: 15px;
        border-radius: 15px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    ">

        <img
            src="https://soaringhungary.com"
            style="
                width: 100%;
                max-width: 160px;
                margin-bottom: 10px;
                border-radius: 10px;
            "
        >

        <h3 style="
            margin: 5px 0 0 0;
            color: #1E3A8A;
            font-size: 15px;
            font-weight: bold;
        ">
            „KVASZ ANDRÁS”
        </h3>

        <p style="
            margin: 2px 0;
            color: #4B5563;
            font-size: 11px;
            font-weight: bold;
        ">
            Békés Megyei Repülő és Ejtőernyős Egyesület
        </p>

        <div style="
            font-size: 11px;
            color: #9CA3AF;
            margin-top: 5px;
        ">
            LHBC • Békéscsaba
        </div>

    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 4. FŐCÍM
# ============================================================

st.title(
    "🛫 Kelet-Magyarország 3 Napos "
    "Vitorlázórepülő Időjárás-Előrejelzője"
)

st.write(
    "A Kvasz András Repülőklub hivatalos "
    "negyedórás repülésmeteorológiai dashboardja "
    "(10:00 - 20:00)."
)


# ============================================================
# 5. REPÜLŐTEREK
# ============================================================

AIRFIELDS = {

    "Békéscsaba (LHBC)": {
        "lat": 46.68,
        "lon": 21.16,
        "elevation": 91
    },

    "Szeged (LHUD)": {
        "lat": 46.25,
        "lon": 20.09,
        "elevation": 80
    },

    "Debrecen (LHDC)": {
        "lat": 47.49,
        "lon": 21.62,
        "elevation": 113
    },

    "Miskolc (LHMC)": {
        "lat": 48.07,
        "lon": 20.79,
        "elevation": 122
    },

    "Nyíregyháza (LHNY)": {
        "lat": 47.95,
        "lon": 21.69,
        "elevation": 103
    }
}


# ============================================================
# 6. REPÜLŐGÉP TÍPUSOK
# ============================================================

GLIDER_TYPES = {

    "KA-7": 26,

    "SF25C Falke": 22,

    "Astir": 38,

    "Cirrus": 38,

    "Cirrus VTC": 39,

    "Standard Jantar 2": 40,

    "Jantar 2B": 48
}


# ============================================================
# 7. MAGYAR NAPOK
# ============================================================

HUNGARIAN_DAYS = {

    "Monday": "Hétfő",
    "Tuesday": "Kedd",
    "Wednesday": "Szerda",
    "Thursday": "Csütörtök",
    "Friday": "Péntek",
    "Saturday": "Szombat",
    "Sunday": "Vasárnap"
}


# ============================================================
# 8. DÁTUMOK
# ============================================================

today_dt = datetime.date.today()

tomorrow_dt = (
    today_dt +
    datetime.timedelta(days=1)
)

after_tomorrow_dt = (
    today_dt +
    datetime.timedelta(days=2)
)


def get_day_label(dt, prefix):

    day_name_eng = dt.strftime("%A")

    day_name_hu = HUNGARIAN_DAYS.get(
        day_name_eng,
        day_name_eng
    )

    return (
        f"{prefix} "
        f"({day_name_hu} - {dt.strftime('%m.%d.')})"
    )


day_options = {

    get_day_label(
        today_dt,
        "Ma"
    ): 0,

    get_day_label(
        tomorrow_dt,
        "Holnap"
    ): 1,

    get_day_label(
        after_tomorrow_dt,
        "Holnapután"
    ): 2
}


# ============================================================
# 9. OLDALSÁV VEZÉRLŐK
# ============================================================

st.sidebar.header("Beállítások")

selected_field = st.sidebar.selectbox(
    "Válassz repülőteret:",
    list(AIRFIELDS.keys()),
    index=0
)

selected_glider = st.sidebar.selectbox(
    "Repülőgép típusa:",
    list(GLIDER_TYPES.keys())
)

selected_day_label = st.sidebar.radio(
    "Válassz napot:",
    list(day_options.keys())
)


day_offset = day_options[
    selected_day_label
]

target_date = (
    today_dt +
    datetime.timedelta(days=day_offset)
)

glider_glide_ratio = GLIDER_TYPES[
    selected_glider
]


# ============================================================
# 10. METEOROLÓGIAI MOTOR
# ============================================================

def get_pure_live_weather(field, day_idx):

    """
    Vitorlázórepüléshez optimalizált meteorológiai feldolgozás.

    Forrás:
        Open-Meteo Weather Forecast API

    A függvény:
        - 10:00–20:00 közötti időszakot vizsgál
        - órás előrejelzésből 15 perces értékeket készít
        - harmatpontot közvetlenül az API-ból használ
        - LCL/Espy közelítéssel becsüli a felhőalapot
        - több tényezőből becsüli a termikus aktivitást
        - kezeli az időzónát
        - körkörösen átlagolja a szélirányt

    FONTOS:
        A termikerősség modellbecslés, nem mért érték.
    """

    # --------------------------------------------------------
    # IDŐ
    # --------------------------------------------------------

    start_time = datetime.datetime.combine(
        target_date,
        datetime.time(10, 0)
    )

    data_rows = []

    lat = AIRFIELDS[field]["lat"]
    lon = AIRFIELDS[field]["lon"]

    # --------------------------------------------------------
    # OPEN-METEO
    # --------------------------------------------------------

    url = (
        "https://api.open-meteo.com/v1/forecast"
    )

    params = {

        "latitude": lat,

        "longitude": lon,

        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "dew_point_2m,"
            "wind_speed_10m,"
            "wind_direction_10m,"
            "cloud_cover,"
            "cloud_cover_low,"
            "cloud_cover_mid,"
            "cloud_cover_high,"
            "precipitation_probability,"
            "precipitation,"
            "shortwave_radiation,"
            "cape"
        ),

        "wind_speed_unit": "kmh",

        "timezone": "Europe/Budapest",

        "forecast_days": 3
    }

    headers = {

        "User-Agent":
            "Kvasz-Andras-Repuloklub-Weather-Dashboard/2.0"
    }

    # --------------------------------------------------------
    # API LEKÉRÉS
    # --------------------------------------------------------

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=15
        )

        if response.status_code != 200:

            st.error(
                "❌ Hálózati hiba: az Open-Meteo "
                "szerver nem válaszolt megfelelően. "
                f"HTTP: {response.status_code}"
            )

            st.stop()

        res = response.json()

        if "hourly" not in res:

            st.error(
                "❌ Az időjárási szerver nem adott "
                "hourly adatokat."
            )

            st.stop()

        hourly = res["hourly"]

        required_fields = [

            "temperature_2m",

            "relative_humidity_2m",

            "dew_point_2m",

            "wind_speed_10m",

            "wind_direction_10m",

            "cloud_cover"
        ]

        missing_fields = [

            field_name

            for field_name in required_fields

            if field_name not in hourly
        ]

        if missing_fields:

            st.error(
                "❌ Hiányzó meteorológiai adatok: "
                +
                ", ".join(missing_fields)
            )

            st.stop()

        # ----------------------------------------------------
        # ÓRÁS ADATOK
        # ----------------------------------------------------

        start_idx = (
            day_idx * 24 + 10
        )

        end_idx = (
            start_idx + 11
        )

        hourly_temps = (
            hourly["temperature_2m"]
            [start_idx:end_idx]
        )

        hourly_rh = (
            hourly["relative_humidity_2m"]
            [start_idx:end_idx]
        )

        hourly_dew = (
            hourly["dew_point_2m"]
            [start_idx:end_idx]
        )

        hourly_wind_speeds = (
            hourly["wind_speed_10m"]
            [start_idx:end_idx]
        )

        hourly_wind_dirs = (
            hourly["wind_direction_10m"]
            [start_idx:end_idx]
        )

        hourly_clouds = (
            hourly["cloud_cover"]
            [start_idx:end_idx]
        )

        hourly_cloud_low = (
            hourly.get(
                "cloud_cover_low",
                [0] * len(hourly_temps)
            )[start_idx:end_idx]
        )

        hourly_precip_prob = (
            hourly.get(
                "precipitation_probability",
                [0] * len(hourly_temps)
            )[start_idx:end_idx]
        )

        hourly_precip = (
            hourly.get(
                "precipitation",
                [0] * len(hourly_temps)
            )[start_idx:end_idx]
        )

        hourly_radiation = (
            hourly.get(
                "shortwave_radiation",
                [0] * len(hourly_temps)
            )[start_idx:end_idx]
        )

        hourly_cape = (
            hourly.get(
                "cape",
                [0] * len(hourly_temps)
            )[start_idx:end_idx]
        )

        if len(hourly_temps) < 11:

            st.error(
                "❌ Nem érkezett elegendő órás "
                "előrejelzési adat."
            )

            st.stop()

        # ----------------------------------------------------
        # NAPI ÁTLAGSZÉL
        # ----------------------------------------------------

        valid_winds = [

            x for x in hourly_wind_speeds

            if x is not None
        ]

        if valid_winds:

            base_wind_speed = int(
                round(
                    np.mean(valid_winds)
                )
            )

        else:

            base_wind_speed = 0

        # ----------------------------------------------------
        # KÖRKÖRÖS SZÉLIRÁNY ÁTLAG
        # ----------------------------------------------------

        valid_dirs = [

            x for x in hourly_wind_dirs

            if x is not None
        ]

        if valid_dirs:

            dir_radians = [

                math.radians(x)

                for x in valid_dirs
            ]

            mean_sin = np.mean(
                [
                    math.sin(x)
                    for x in dir_radians
                ]
            )

            mean_cos = np.mean(
                [
                    math.cos(x)
                    for x in dir_radians
                ]
            )

            base_wind_dir = int(
                round(
                    math.degrees(
                        math.atan2(
                            mean_sin,
                            mean_cos
                        )
                    )
                )
                % 360
            )

        else:

            base_wind_dir = 0

        st.sidebar.success(
            "📡 Valós meteorológiai adatok betöltve!"
        )

    except requests.exceptions.RequestException as e:

        st.error(
            "❌ Internetkapcsolati hiba az "
            "időjárási szolgáltatás elérésekor:\n\n"
            f"{str(e)}"
        )

        st.stop()

    except Exception as e:

        st.error(
            "❌ Meteorológiai adatfeldolgozási hiba:\n\n"
            f"{str(e)}"
        )

        st.stop()

    # ========================================================
    # SEGÉDFÜGGVÉNY
    # ========================================================

    def interpolate(values, position):

        if not values:

            return 0

        floor_idx = int(
            math.floor(position)
        )

        ceil_idx = int(
            math.ceil(position)
        )

        floor_idx = max(
            0,
            min(
                floor_idx,
                len(values) - 1
            )
        )

        ceil_idx = max(
            0,
            min(
                ceil_idx,
                len(values) - 1
            )
        )

        if floor_idx == ceil_idx:

            value = values[floor_idx]

            if value is None:

                return 0

            return value

        v1 = values[floor_idx]

        v2 = values[ceil_idx]

        if v1 is None:
            v1 = v2

        if v2 is None:
            v2 = v1

        weight = (
            position -
            floor_idx
        )

        return (
            v1 * (1 - weight)
            +
            v2 * weight
        )

    # ========================================================
    # HARMATPONT BIZTONSÁGI SZÁMÍTÁS
    # ========================================================

    def calculate_dew_point(
        temperature,
        relative_humidity
    ):

        rh = max(
            1.0,
            min(
                100.0,
                relative_humidity
            )
        )

        a = 17.27

        b = 237.7

        alpha = (

            (a * temperature)
            /
            (b + temperature)

            +
            math.log(
                rh / 100.0
            )
        )

        return (
            b * alpha
            /
            (a - alpha)
        )

    # ========================================================
    # 15 PERCES ADATOK
    # ========================================================

    for i in range(41):

        current_time = (

            start_time

            +
            datetime.timedelta(
                minutes=15 * i
            )
        )

        time_str = (
            current_time.strftime("%H:%M")
        )

        hour_position = (

            current_time.hour

            +
            current_time.minute / 60.0

            -
            10.0
        )

        # ----------------------------------------------------
        # INTERPOLÁCIÓ
        # ----------------------------------------------------

        current_temp = interpolate(
            hourly_temps,
            hour_position
        )

        current_rh = interpolate(
            hourly_rh,
            hour_position
        )

        current_dew = interpolate(
            hourly_dew,
            hour_position
        )

        current_wind_spd = interpolate(
            hourly_wind_speeds,
            hour_position
        )

        current_wind_dir = interpolate(
            hourly_wind_dirs,
            hour_position
        )

        current_cloud = interpolate(
            hourly_clouds,
            hour_position
        )

        current_cloud_low = interpolate(
            hourly_cloud_low,
            hour_position
        )

        current_precip_prob = interpolate(
            hourly_precip_prob,
            hour_position
        )

        current_precip = interpolate(
            hourly_precip,
            hour_position
        )

        current_radiation = interpolate(
            hourly_radiation,
            hour_position
        )

        current_cape = interpolate(
            hourly_cape,
            hour_position
        )

        # ----------------------------------------------------
        # HARMATPONT
        # ----------------------------------------------------

        if (
            current_dew is None
            or current_dew > current_temp
        ):

            current_dew = calculate_dew_point(
                current_temp,
                current_rh
            )

        current_dew = min(
            current_dew,
            current_temp
        )

        # ----------------------------------------------------
        # T - TD
        # ----------------------------------------------------

        spread = max(
            0.0,
            current_temp - current_dew
        )

        # ====================================================
        # FELHŐALAP
        # ====================================================

        # Klasszikus LCL/Espy közelítés:
        #
        # LCL ≈ 125 × (T - Td)
        #
        # Ez AGL érték.

        lcl_base = (
            spread * 125.0
        )

        # ----------------------------------------------------
        # FELHŐKÉPZŐDÉSI VALÓSZÍNŰSÉG
        # ----------------------------------------------------

        if current_rh < 35:

            cloud_probability_factor = 0.20

        elif current_rh < 45:

            cloud_probability_factor = 0.40

        elif current_rh < 55:

            cloud_probability_factor = 0.65

        elif current_rh < 70:

            cloud_probability_factor = 0.85

        else:

            cloud_probability_factor = 1.00

        # Alacsony felhőzet fontosabb jelzés,
        # mint az összes felhőzet.

        if current_cloud_low >= 50:

            cloud_probability_factor *= 1.15

        elif current_cloud_low >= 25:

            cloud_probability_factor *= 1.05

        elif current_cloud < 15:

            cloud_probability_factor *= 0.65

        cloud_probability_factor = max(
            0.0,
            min(
                1.0,
                cloud_probability_factor
            )
        )

        # ----------------------------------------------------
        # FELHŐALAP MEGADÁSA
        # ----------------------------------------------------

        if spread < 1.0:

            cumulus_base = 0

        elif spread <= 20:

            cumulus_base = int(
                round(lcl_base)
            )

        else:

            cumulus_base = int(
                round(
                    lcl_base * 0.90
                )
            )

        # ----------------------------------------------------
        # HA NINCS ÉRDEMI FELHŐKÉPZŐDÉS
        # ----------------------------------------------------

        if (
            current_cloud < 15
            and current_rh < 55
        ):

            display_cloud_base = "-"

        else:

            display_cloud_base = (
                cumulus_base
            )

        # ----------------------------------------------------
        # FELHŐALAP MINŐSÍTÉS
        # ----------------------------------------------------

        if spread < 1:

            cloud_base_quality = (
                "Köd / talajközeli"
            )

        elif spread < 3:

            cloud_base_quality = (
                "Nagyon alacsony"
            )

        elif spread < 6:

            cloud_base_quality = (
                "Alacsony"
            )

        elif spread < 10:

            cloud_base_quality = (
                "Közepes"
            )

        elif spread < 15:

            cloud_base_quality = (
                "Magas"
            )

        else:

            cloud_base_quality = (
                "Nagyon magas / száraz"
            )

        # ====================================================
        # TERMIKUS AKTIVITÁS
        # ====================================================

        # ----------------------------------------------------
        # NAPSZAK
        # ----------------------------------------------------

        thermal_time_factor = math.exp(
            -(
                (hour_position - 4.5)
                /
                3.0
            ) ** 2
        )

        thermal_time_factor = max(
            0.0,
            min(
                1.0,
                thermal_time_factor
            )
        )

        # ----------------------------------------------------
        # NAPSUGÁRZÁS
        # ----------------------------------------------------

        if current_radiation >= 650:

            radiation_factor = 1.00

        elif current_radiation >= 450:

            radiation_factor = 0.90

        elif current_radiation >= 300:

            radiation_factor = 0.75

        elif current_radiation >= 150:

            radiation_factor = 0.50

        else:

            radiation_factor = 0.20

        # ----------------------------------------------------
        # FELHŐZET
        # ----------------------------------------------------

        if current_cloud < 15:

            solar_factor = 1.00

        elif current_cloud < 35:

            solar_factor = 0.92

        elif current_cloud < 55:

            solar_factor = 0.78

        elif current_cloud < 70:

            solar_factor = 0.60

        elif current_cloud < 85:

            solar_factor = 0.35

        else:

            solar_factor = 0.15

        # ----------------------------------------------------
        # PÁRATARTALOM
        # ----------------------------------------------------

        if current_rh < 35:

            moisture_factor = 0.85

        elif current_rh < 50:

            moisture_factor = 1.00

        elif current_rh < 65:

            moisture_factor = 0.95

        elif current_rh < 80:

            moisture_factor = 0.78

        else:

            moisture_factor = 0.55

        # ----------------------------------------------------
        # HŐMÉRSÉKLET
        # ----------------------------------------------------

        if current_temp < 15:

            temperature_factor = 0.45

        elif current_temp < 20:

            temperature_factor = 0.65

        elif current_temp < 25:

            temperature_factor = 0.82

        elif current_temp < 30:

            temperature_factor = 1.00

        elif current_temp < 35:

            temperature_factor = 0.92

        else:

            temperature_factor = 0.82

        # ----------------------------------------------------
        # CU VISSZACSATOLÁS
        # ----------------------------------------------------

        if (
            15 <= current_cloud <= 60
        ):

            cu_feedback = 1.08

        elif current_cloud < 15:

            cu_feedback = 1.00

        elif current_cloud <= 75:

            cu_feedback = 0.90

        else:

            cu_feedback = 0.65

        # ----------------------------------------------------
        # SZÉL
        # ----------------------------------------------------

        if current_wind_spd < 5:

            wind_factor = 0.90

        elif current_wind_spd < 15:

            wind_factor = 1.00

        elif current_wind_spd < 22:

            wind_factor = 0.90

        elif current_wind_spd < 30:

            wind_factor = 0.70

        else:

            wind_factor = 0.45

        # ----------------------------------------------------
        # CAPE HATÁSA
        # ----------------------------------------------------

        if current_cape >= 1000:

            cape_factor = 1.15

        elif current_cape >= 500:

            cape_factor = 1.08

        elif current_cape >= 200:

            cape_factor = 1.03

        elif current_cape >= 50:

            cape_factor = 1.00

        else:

            cape_factor = 0.90

        # ----------------------------------------------------
        # KONVEKTÍV INDEX
        # ----------------------------------------------------

        convective_index = (

            thermal_time_factor

            *
            radiation_factor

            *
            solar_factor

            *
            moisture_factor

            *
            temperature_factor

            *
            cu_feedback

            *
            wind_factor

            *
            cape_factor
        )

        # ----------------------------------------------------
        # TERMERŐSSÉG
        # ----------------------------------------------------

        if convective_index < 0.20:

            thermal_climb = 0.0

        elif convective_index < 0.35:

            thermal_climb = (
                0.6
                +
                (
                    convective_index - 0.20
                )
                * 2.0
            )

        elif convective_index < 0.55:

            thermal_climb = (
                0.9
                +
                (
                    convective_index - 0.35
                )
                * 4.0
            )

        elif convective_index < 0.75:

            thermal_climb = (
                1.7
                +
                (
                    convective_index - 0.55
                )
                * 5.0
            )

        else:

            thermal_climb = (
                2.7
                +
                (
                    convective_index - 0.75
                )
                * 5.0
            )

        thermal_climb = min(
            thermal_climb,
            5.0
        )

        thermal_climb = round(
            max(
                0.0,
                thermal_climb
            ),
            1
        )

        # ====================================================
        # SZÉLNYÍRÁS / ERŐS SZÉL
        # ====================================================

        if current_wind_spd > 30:

            wind_shear = "Erős"

        elif current_wind_spd > 22:

            wind_shear = "Közepes"

        elif current_wind_spd > 15:

            wind_shear = "Mérsékelt"

        else:

            wind_shear = "Alacsony"

        # ====================================================
        # FELHŐZET
        # ====================================================

        if current_cloud < 15:

            cu_cover = "0/8 SKC"

        elif current_cloud < 40:

            cu_cover = "1-2/8 FEW"

        elif current_cloud < 75:

            cu_cover = "3-4/8 SCT"

        elif current_cloud < 90:

            cu_cover = "5-6/8 BKN"

        else:

            cu_cover = "7-8/8 OVC"

        # ====================================================
        # TÚLFEJLŐDÉS
        # ====================================================

        if (
            current_cloud >= 75
            and current_precip_prob >= 40
        ):

            overdev = "Magas"

        elif (
            current_cloud >= 60
            and current_precip_prob >= 25
        ):

            overdev = "Közepes"

        else:

            overdev = "Alacsony"

        # ====================================================
        # REPÜLÉSMETEOROLÓGIAI ADATSOR
        # ====================================================

        data_rows.append({

            "Időpont":
                time_str,

            "Hőmérséklet (°C)":
                round(
                    current_temp,
                    1
                ),

            "Harmatpont (°C)":
                round(
                    current_dew,
                    1
                ),

            "T-D különbség (°C)":
                round(
                    spread,
                    1
                ),

            "Termik (m/s)":
                thermal_climb
                if thermal_climb > 0
                else "-",

            "Alap (m AGL)":
                display_cloud_base,

            "Felhőalap":
                cloud_base_quality,

            "Felhőzet":
                cu_cover,

            "Szél":
                (
                    f"{int(round(current_wind_dir))}° / "
                    f"{int(round(current_wind_spd))} km/h"
                ),

            "Szélnyírás":
                wind_shear,

            "Túlfejlődés":
                overdev
        })

    # ========================================================
    # DATAFRAME
    # ========================================================

    df = pd.DataFrame(
        data_rows
    )

    return (
        df,
        base_wind_dir,
        base_wind_speed
    )


# ============================================================
# 11. ADATOK LEKÉRÉSE
# ============================================================

df, w_dir, w_spd = (
    get_pure_live_weather(
        selected_field,
        day_offset
    )
)


# ============================================================
# 12. NUMERIKUS KPI-ÉRTÉKEK
# ============================================================

thermal_values = pd.to_numeric(
    df["Termik (m/s)"],
    errors="coerce"
).fillna(0)

cloud_base_values = pd.to_numeric(
    df["Alap (m AGL)"],
    errors="coerce"
).fillna(0)

max_thermal = (
    thermal_values.max()
)

max_cloud_base = (
    cloud_base_values.max()
)


# ============================================================
# 13. KPI KIJELZŐK
# ============================================================

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Max Termik",
    f"{max_thermal:.1f} m/s"
)

col2.metric(
    "Max Felhőalap",
    f"{int(max_cloud_base)} m AGL"
)

col3.metric(
    "Napi Alapszél (Átlag)",
    f"{w_dir}° / {w_spd} km/h"
)

col4.metric(
    f"{selected_glider} Teljesítmény",
    f"Siklószám: 1:{glider_glide_ratio}"
)


# ============================================================
# 14. METEOROLÓGIAI ÁLLAPOT
# ============================================================

if max_thermal >= 2.5:

    st.markdown(
        """
        <div class="weather-good">
        <b>🟢 Jó termikus aktivitás várható.</b><br>
        A modell alapján a nap folyamán több
        használható termikus időszak várható.
        </div>
        """,
        unsafe_allow_html=True
    )

elif max_thermal >= 1.5:

    st.markdown(
        """
        <div class="weather-warning">
        <b>🟡 Mérsékelt termikus aktivitás.</b><br>
        Várhatóan használható termikek,
        de a körülmények nem lesznek végig erősek.
        </div>
        """,
        unsafe_allow_html=True
    )

else:

    st.markdown(
        """
        <div class="weather-warning">
        <b>🟠 Gyenge termikus aktivitás.</b><br>
        A modell alapján inkább gyenge vagy
        időszakos termikek várhatók.
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# 15. ADATTÁBLÁZAT
# ============================================================

st.subheader(
    "Valós negyedórás előrejelzés: "
    f"{selected_field} "
    f"({target_date.strftime('%Y.%m.%d.')})"
)

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 16. GRAFIKON
# ============================================================

st.subheader(
    "Termik és Felhőalap napközbeni lefutása"
)

fig = go.Figure()


# ------------------------------------------------------------
# TERMIK
# ------------------------------------------------------------

fig.add_trace(
    go.Scatter(
        x=df["Időpont"],

        y=thermal_values,

        name="Termik erősség (m/s)",

        yaxis="y1",

        mode="lines+markers",

        line=dict(
            color="orange",
            width=3
        )
    )
)


# ------------------------------------------------------------
# FELHŐALAP
# ------------------------------------------------------------

fig.add_trace(
    go.Scatter(
        x=df["Időpont"],

        y=cloud_base_values,

        name="Felhőalap (m AGL)",

        yaxis="y2",

        mode="lines+markers",

        line=dict(
            color="royalblue",
            width=3
        )
    )
)


# ------------------------------------------------------------
# GRAFIKON BEÁLLÍTÁS
# ------------------------------------------------------------

fig.update_layout(

    xaxis=dict(
        title="Időpont"
    ),

    yaxis=dict(
        title="Termik (m/s)",
        side="left",
        rangemode="tozero"
    ),

    yaxis2=dict(
        title="Felhőalap (m AGL)",
        side="right",
        overlaying="y",
        rangemode="tozero"
    ),

    hovermode="x unified",

    height=500,

    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="center",
        x=0.5
    )
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ============================================================
# 17. REPÜLÉSI METEOROLÓGIAI ÖSSZEFOGLALÓ
# ============================================================

st.subheader(
    "🛫 Vitorlázórepülési összefoglaló"
)


# ------------------------------------------------------------
# ÁTLAGOS TERMERŐSSÉG
# ------------------------------------------------------------

positive_thermal_values = (
    thermal_values[
        thermal_values > 0
    ]
)

if len(positive_thermal_values) > 0:

    avg_thermal = (
        positive_thermal_values.mean()
    )

else:

    avg_thermal = 0


# ------------------------------------------------------------
# HASZNÁLHATÓ TERMIKUS IDŐSZAK
# ------------------------------------------------------------

usable_thermal_count = int(
    (
        thermal_values >= 1.0
    ).sum()
)


usable_hours = (
    usable_thermal_count
    /
    4.0
)


# ------------------------------------------------------------
# SZÖVEGES ÉRTÉKELÉS
# ------------------------------------------------------------

if max_thermal >= 3.0:

    thermal_text = (
        "Erős termikus nap. "
        "A modell alapján több órán keresztül "
        "jó emelkedések lehetnek."
    )

elif max_thermal >= 2.0:

    thermal_text = (
        "Jó termikus nap. "
        "Közepes vagy jó emelések várhatók."
    )

elif max_thermal >= 1.2:

    thermal_text = (
        "Mérsékelt termikus aktivitás. "
        "Rövidebb termikus időszakok várhatók."
    )

else:

    thermal_text = (
        "Gyenge termikus nap. "
        "A termikek várhatóan gyengék vagy "
        "szórványosak lesznek."
    )


st.write(
    thermal_text
)

st.write(
    f"**Becsült maximális termik:** "
    f"{max_thermal:.1f} m/s"
)

st.write(
    f"**Becsült átlagos használható termik:** "
    f"{avg_thermal:.1f} m/s"
)

st.write(
    f"**1,0 m/s feletti termikus időszak:** "
    f"kb. {usable_hours:.1f} óra"
)

st.write(
    f"**Legmagasabb becsült felhőalap:** "
    f"{int(max_cloud_base)} m AGL"
)

st.write(
    f"**Átlagos szél:** "
    f"{w_dir}° / {w_spd} km/h"
)


# ============================================================
# 18. FIGYELMEZTETÉSEK
# ============================================================

strong_wind = (
    df["Szél"]
    .str.extract(
        r"/\s*(\d+)"
    )[0]
    .astype(float)
    .max()
)

if strong_wind > 30:

    st.markdown(
        """
        <div class="weather-danger">
        <b>🔴 Erős szél figyelmeztetés</b><br>
        A maximális előrejelzett szél meghaladja
        a 30 km/h értéket. A tényleges repülhetőség
        külön helyszíni értékelést igényel.
        </div>
        """,
        unsafe_allow_html=True
    )

elif strong_wind > 22:

    st.markdown(
        """
        <div class="weather-warning">
        <b>🟡 Mérsékelt/erős szél</b><br>
        A szél várhatóan jelentősen befolyásolja
        a termikek szerkezetét és a föld feletti
        haladási sebességet.
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# 19. FELHŐALAP FIGYELMEZTETÉS
# ============================================================

low_cloud_count = int(
    (
        cloud_base_values > 0
    )
    &
    (
        cloud_base_values < 800
    )
).sum()


if low_cloud_count >= 8:

    st.markdown(
        """
        <div class="weather-warning">
        <b>🟡 Alacsony felhőalap</b><br>
        A vizsgált időszak jelentős részében
        800 m AGL alatti becsült felhőalap fordul elő.
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# 20. MAGYARÁZAT
# ============================================================

with st.expander(
    "ℹ️ A számítások magyarázata"
):

    st.markdown(
        """
        ### Felhőalap

        A program a felhőalap első közelítésére az
        **LCL/Espy módszert** használja:

        **LCL ≈ 125 × (T − Td)**

        ahol:

        - T = felszíni hőmérséklet
        - Td = harmatpont
        - az eredmény méterben értendő a talajhoz képest.

        A program ezért a felhőalapot **AGL-ben** jeleníti meg.

        Ez lényegesen értelmesebb, mint egy mesterséges
        minimumérték alkalmazása.

        ---

        ### Termik

        A termikerősség nem közvetlen mérés.

        A modell több tényezőt kombinál:

        - napszak
        - napsugárzás
        - felhőzet
        - páratartalom
        - hőmérséklet
        - szél
        - CAPE
        - konvektív felhőzet

        Ezért az értéket **modellbecslésként** kell kezelni.

        ---

        ### Fontos

        A tényleges vitorlázórepülési termik erősségét
        jelentősen befolyásolja a légköri profil,
        a talajfelszín, a nedvesség, az inversion,
        a szélprofil és a helyi konvergencia.

        Ez a dashboard ezért döntéstámogató előrejelzés,
        nem hivatalos repülésmeteorológiai szolgálat.
        """
    )


# ============================================================
# 21. ADATFORRÁS
# ============================================================

st.caption(
    "Meteorológiai adatforrás: Open-Meteo "
    "Weather Forecast API. "
    "Az adatok modell-előrejelzések; a termik- és "
    "felhőalap-értékek számított becslések."
)
