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
# 2. HÁTTÉRKÉP
# ============================================================

hangar_bg_url = "https://behir.hu"

st.markdown(
    f"""
    <style>

    .stApp {{
        background:
        linear-gradient(
            rgba(255,255,255,0.88),
            rgba(255,255,255,0.88)
        ),
        url("{hangar_bg_url}");

        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}

    .weather-good {{
        padding: 12px;
        border-radius: 10px;
        margin: 8px 0;
        background-color: rgba(220,252,231,0.95);
        border-left: 5px solid #16a34a;
    }}

    .weather-warning {{
        padding: 12px;
        border-radius: 10px;
        margin: 8px 0;
        background-color: rgba(255,243,205,0.95);
        border-left: 5px solid #f59e0b;
    }}

    .weather-danger {{
        padding: 12px;
        border-radius: 10px;
        margin: 8px 0;
        background-color: rgba(254,226,226,0.95);
        border-left: 5px solid #dc2626;
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 3. FŐCÍM
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
# 4. REPÜLŐTEREK
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
# 5. REPÜLŐGÉP TÍPUSOK
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
# 6. MAGYAR NAPOK
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
# 7. DÁTUMOK
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
# 8. OLDALSÁV
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
# 9. SEGÉDFÜGGVÉNYEK
# ============================================================

def safe_float(value, default=0.0):

    try:

        if value is None:
            return default

        value = float(value)

        if not math.isfinite(value):
            return default

        return value

    except Exception:

        return default


def interpolate(values, position):

    if not values:
        return 0.0

    valid = [
        safe_float(x)
        for x in values
    ]

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
            len(valid) - 1
        )
    )

    ceil_idx = max(
        0,
        min(
            ceil_idx,
            len(valid) - 1
        )
    )

    if floor_idx == ceil_idx:
        return valid[floor_idx]

    weight = (
        position -
        floor_idx
    )

    return (
        valid[floor_idx] * (1 - weight)
        +
        valid[ceil_idx] * weight
    )


def dew_point_from_rh(
    temperature,
    relative_humidity
):

    temperature = safe_float(
        temperature
    )

    rh = max(
        1.0,
        min(
            100.0,
            safe_float(
                relative_humidity,
                50
            )
        )
    )

    a = 17.27
    b = 237.7

    alpha = (
        (a * temperature)
        /
        (b + temperature)
        +
        math.log(rh / 100.0)
    )

    return (
        b * alpha
        /
        (a - alpha)
    )


def pressure_level_altitude(
    geopotential_height,
    airport_elevation
):

    """
    A nyomási szint magassága MSL.
    Átalakítás AGL-re.
    """

    return max(
        0.0,
        safe_float(
            geopotential_height
        )
        -
        airport_elevation
    )


def calculate_lcl(
    temperature,
    dew_point
):

    """
    Klasszikus felszíni LCL-becslés.

    Ez csak kiindulási érték.
    A végleges felhőalapot a vertikális
    felhőprofil korrigálja.
    """

    spread = max(
        0.0,
        temperature - dew_point
    )

    return (
        125.0 * spread
    )


def circular_mean_directions(
    directions
):

    directions = [

        safe_float(x)
        for x in directions
        if x is not None
    ]

    if not directions:
        return 0

    radians = [
        math.radians(x)
        for x in directions
    ]

    sin_mean = np.mean(
        np.sin(radians)
    )

    cos_mean = np.mean(
        np.cos(radians)
    )

    return int(
        round(
            math.degrees(
                math.atan2(
                    sin_mean,
                    cos_mean
                )
            )
        )
        % 360
    )


# ============================================================
# 10. METEOROLÓGIAI MOTOR
# ============================================================

def get_pure_live_weather(
    field,
    day_idx
):

    """
    Vitorlázórepülési meteorológiai modell.

    A modell nem pusztán felszíni T/Td értékből
    próbálja meghatározni a felhőalapot és
    termikerősséget.

    Felhasználja:

        - felszíni T
        - felszíni Td
        - RH
        - napsugárzás
        - CAPE
        - PBL magasság
        - nyomási szintű T
        - nyomási szintű Td
        - nyomási szintű RH
        - nyomási szintű felhőzet
        - geopotenciális magasság
        - szél
        - alacsony felhőzet
        - csapadék

    FONTOS:
    Ez meteorológiai MODELLBECSLÉS,
    nem mérés.
    """

    start_time = datetime.datetime.combine(
        target_date,
        datetime.time(10, 0)
    )

    lat = AIRFIELDS[field]["lat"]
    lon = AIRFIELDS[field]["lon"]

    airport_elevation = (
        AIRFIELDS[field]["elevation"]
    )

    data_rows = []


    # ========================================================
    # OPEN-METEO API
    # ========================================================

    url = (
        "https://api.open-meteo.com/v1/forecast"
    )


    # --------------------------------------------------------
    # NYOMÁSI SZINTEK
    # --------------------------------------------------------

    pressure_levels = [
        "1000hPa",
        "975hPa",
        "950hPa",
        "925hPa",
        "900hPa",
        "850hPa",
        "800hPa",
        "750hPa",
        "700hPa"
    ]


    pressure_variables = []

    for level in pressure_levels:

        pressure_variables.extend([

            f"temperature_{level}",

            f"dew_point_{level}",

            f"relative_humidity_{level}",

            f"cloud_cover_{level}",

            f"geopotential_height_{level}"
        ])


    hourly_variables = [

        "temperature_2m",

        "relative_humidity_2m",

        "dew_point_2m",

        "wind_speed_10m",

        "wind_direction_10m",

        "wind_gusts_10m",

        "cloud_cover",

        "cloud_cover_low",

        "cloud_cover_mid",

        "cloud_cover_high",

        "precipitation_probability",

        "precipitation",

        "shortwave_radiation",

        "cape",

        "boundary_layer_height",

        "surface_pressure"

    ]


    params = {

        "latitude": lat,

        "longitude": lon,

        "hourly":
            ",".join(
                hourly_variables
                +
                pressure_variables
            ),

        "wind_speed_unit": "kmh",

        "timezone":
            "Europe/Budapest",

        "forecast_days": 3
    }


    headers = {

        "User-Agent":
            "Kvasz-Andras-Repuloklub-Weather/3.0"
    }


    # ========================================================
    # API LEKÉRÉS
    # ========================================================

    try:

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=20
        )

        if response.status_code != 200:

            st.error(
                "❌ Az időjárási API hibát adott.\n\n"
                f"HTTP kód: {response.status_code}"
            )

            st.stop()

        res = response.json()

        if "hourly" not in res:

            st.error(
                "❌ Az API-válaszban nincs "
                "hourly adat."
            )

            st.stop()

        hourly = res["hourly"]

    except requests.exceptions.RequestException as e:

        st.error(
            "❌ Nem sikerült csatlakozni "
            "az időjárási szerverhez.\n\n"
            f"{str(e)}"
        )

        st.stop()

    except Exception as e:

        st.error(
            "❌ Hiba az időjárási adatok "
            "feldolgozásakor.\n\n"
            f"{str(e)}"
        )

        st.stop()


    # ========================================================
    # SEGÉDFÜGGVÉNY AZ ÓRÁS ADATOKHOZ
    # ========================================================

    def get_series(
        name
    ):

        if name not in hourly:

            return [0] * 72

        return hourly[name]


    # ========================================================
    # FELSZÍNI ADATOK
    # ========================================================

    surface_temp = get_series(
        "temperature_2m"
    )

    surface_rh = get_series(
        "relative_humidity_2m"
    )

    surface_dew = get_series(
        "dew_point_2m"
    )

    surface_wind = get_series(
        "wind_speed_10m"
    )

    surface_wind_dir = get_series(
        "wind_direction_10m"
    )

    surface_gust = get_series(
        "wind_gusts_10m"
    )

    cloud_total = get_series(
        "cloud_cover"
    )

    cloud_low = get_series(
        "cloud_cover_low"
    )

    precipitation_probability = get_series(
        "precipitation_probability"
    )

    precipitation = get_series(
        "precipitation"
    )

    radiation = get_series(
        "shortwave_radiation"
    )

    cape = get_series(
        "cape"
    )

    pbl_height = get_series(
        "boundary_layer_height"
    )

    surface_pressure = get_series(
        "surface_pressure"
    )


    # ========================================================
    # NAPI SZÉL
    # ========================================================

    start_idx = (
        day_idx * 24 + 10
    )

    end_idx = (
        start_idx + 11
    )

    day_winds = (
        surface_wind[
            start_idx:end_idx
        ]
    )

    day_dirs = (
        surface_wind_dir[
            start_idx:end_idx
        ]
    )

    valid_winds = [
        safe_float(x)
        for x in day_winds
    ]

    base_wind_speed = int(
        round(
            np.mean(valid_winds)
        )
    )

    base_wind_dir = (
        circular_mean_directions(
            day_dirs
        )
    )


    st.sidebar.success(
        "📡 Vertikális meteorológiai adatok betöltve"
    )


    # ========================================================
    # NYOMÁSI SZINTŰ ADATOK
    # ========================================================

    pressure_profile = {}

    for level in pressure_levels:

        temp_name = (
            f"temperature_{level}"
        )

        dew_name = (
            f"dew_point_{level}"
        )

        rh_name = (
            f"relative_humidity_{level}"
        )

        cloud_name = (
            f"cloud_cover_{level}"
        )

        height_name = (
            f"geopotential_height_{level}"
        )

        pressure_profile[level] = {

            "temperature":
                get_series(temp_name),

            "dew_point":
                get_series(dew_name),

            "rh":
                get_series(rh_name),

            "cloud":
                get_series(cloud_name),

            "height":
                get_series(height_name)
        }


    # ========================================================
    # FELHŐALAP MODELLEZÉS
    # ========================================================

    def estimate_cloud_base(
        surface_t,
        surface_td,
        surface_rh_value,
        surface_cloud_low,
        pbl,
        profile_index
    ):

        """
        Többlépcsős felhőalap-becslés.

        1. LCL
        2. nyomási szintű low-level RH
        3. nyomási szintű cloud cover
        4. PBL ellenőrzés

        Nem engedi, hogy a felszíni
        T-Td képlet önmagában irreálisan
        magas értéket adjon.
        """

        lcl = calculate_lcl(
            surface_t,
            surface_td
        )

        # ----------------------------------------------------
        # PBL KORLÁT
        # ----------------------------------------------------

        pbl_agl = max(
            100.0,
            safe_float(pbl)
        )

        # A PBL nem maga a felhőalap.
        # Csak fizikailag ésszerű felső korlátként
        # használjuk, ha a modell szerint nincs
        # szabad konvektív keveredés.
        #
        # Cumulus esetén a cloud base tipikusan
        # a mixed layer tetejéhez kötődik.

        # ----------------------------------------------------
        # PROFIL FELDOLGOZÁSA
        # ----------------------------------------------------

        profile_points = []

        for level in pressure_levels:

            profile = pressure_profile[level]

            height = safe_float(
                interpolate(
                    profile["height"],
                    profile_index
                )
            )

            temp = safe_float(
                interpolate(
                    profile["temperature"],
                    profile_index
                )
            )

            dew = safe_float(
                interpolate(
                    profile["dew_point"],
                    profile_index
                )
            )

            rh = safe_float(
                interpolate(
                    profile["rh"],
                    profile_index
                )
            )

            cloud = safe_float(
                interpolate(
                    profile["cloud"],
                    profile_index
                )
            )

            agl = (
                height
                -
                airport_elevation
            )

            if agl >= 0:

                profile_points.append({

                    "agl": agl,

                    "temp": temp,

                    "dew": dew,

                    "rh": rh,

                    "cloud": cloud
                })


        profile_points.sort(
            key=lambda x: x["agl"]
        )


        # ----------------------------------------------------
        # ELSŐ ÉRDEMI FELHŐRÉTEG
        # ----------------------------------------------------

        model_cloud_base = None

        for point in profile_points:

            agl = point["agl"]

            rh = point["rh"]

            cloud = point["cloud"]

            # 400 m alatt ne tekintsük automatikusan
            # a modell által jelzett nedves réteget
            # használható CU cloudbase-nak.

            if agl < 300:
                continue

            if (
                cloud >= 30
                and rh >= 75
            ):

                model_cloud_base = agl

                break


        # ----------------------------------------------------
        # LCL KORREKCIÓ
        # ----------------------------------------------------

        # Nagyon száraz levegőn a modell gyakran
        # túl magas LCL-t adhat.
        #
        # A felszíni RH alapján mérsékeljük
        # a tisztán elméleti LCL súlyát.

        if surface_rh_value >= 75:

            lcl_weight = 0.35

        elif surface_rh_value >= 65:

            lcl_weight = 0.50

        elif surface_rh_value >= 55:

            lcl_weight = 0.65

        else:

            lcl_weight = 0.80


        # ----------------------------------------------------
        # KORAI CUMULUS ELLENŐRZÉS
        # ----------------------------------------------------

        if surface_cloud_low >= 20:

            cloud_presence_factor = 1.0

        elif surface_cloud_low >= 10:

            cloud_presence_factor = 0.85

        else:

            cloud_presence_factor = 0.60


        # ----------------------------------------------------
        # KANDIDÁTUS
        # ----------------------------------------------------

        if model_cloud_base is not None:

            estimated = (

                lcl * lcl_weight

                +
                model_cloud_base
                * (1 - lcl_weight)
            )

        else:

            estimated = lcl


        # ----------------------------------------------------
        # PBL KORREKCIÓ
        # ----------------------------------------------------

        # Ha az LCL messze a PBL fölött van,
        # a konvektív CU cloudbase kevésbé valószínű.

        if estimated > pbl_agl * 1.20:

            estimated *= 0.88


        # ----------------------------------------------------
        # ALSÓ ÉS FELSŐ ÉSSZERŰ KORLÁT
        # ----------------------------------------------------

        estimated = max(
            250.0,
            estimated
        )

        estimated = min(
            estimated,
            4500.0
        )


        # ----------------------------------------------------
        # HA NINCS FELHŐKÉPZŐDÉS
        # ----------------------------------------------------

        if (
            surface_cloud_low < 10
            and surface_rh_value < 55
            and surface_t - surface_td > 8
        ):

            return 0


        return int(
            round(
                estimated /
                50
            )
            *
            50
        )


    # ========================================================
    # TERMIKERŐSSÉG MODELL
    # ========================================================

    def estimate_thermal_strength(
        surface_t,
        surface_td,
        wind,
        cloud,
        radiation_value,
        cape_value,
        pbl,
        profile_index
    ):

        """
        Termikerősség-becslés.

        A cél nem egy fizikailag egzakt w* számítása,
        hanem egy vitorlázórepülésben értelmezhető
        becslés.

        Fő tényezők:

            - lapse rate
            - PBL depth
            - napsugárzás
            - cloud cover
            - CAPE
            - szél
            - nedvesség
            - napszak
        """

        # ----------------------------------------------------
        # NAPSZAK
        # ----------------------------------------------------

        hour_value = (
            10.0
            +
            profile_index
        )

        solar_time_factor = (

            math.sin(
                math.pi
                *
                (
                    hour_value - 8
                )
                /
                10
            )

        )

        solar_time_factor = max(
            0.0,
            solar_time_factor
        )


        # ----------------------------------------------------
        # RADIÁCIÓ
        # ----------------------------------------------------

        radiation_value = safe_float(
            radiation_value
        )

        if radiation_value < 100:

            radiation_factor = 0.20

        elif radiation_value < 250:

            radiation_factor = 0.45

        elif radiation_value < 400:

            radiation_factor = 0.65

        elif radiation_value < 600:

            radiation_factor = 0.85

        else:

            radiation_factor = 1.00


        # ----------------------------------------------------
        # LÉGKÖRI HŐMÉRSÉKLETI PROFIL
        # ----------------------------------------------------

        environmental_lapse_rates = []

        surface_temperature_k = (
            surface_t
            +
            273.15
        )

        # 925 és 900 hPa elsősorban
        # az alsó 1 km állapotát jelzi.

        for level in [
            "975hPa",
            "950hPa",
            "925hPa",
            "900hPa"
        ]:

            profile = pressure_profile[level]

            upper_temp = safe_float(
                interpolate(
                    profile["temperature"],
                    profile_index
                )
            )

            upper_height = safe_float(
                interpolate(
                    profile["height"],
                    profile_index
                )
            )

            upper_agl = (
                upper_height
                -
                airport_elevation
            )

            if upper_agl > 200:

                lapse = (
                    surface_t
                    -
                    upper_temp
                ) / (
                    upper_agl / 1000
                )

                environmental_lapse_rates.append(
                    lapse
                )


        if environmental_lapse_rates:

            low_level_lapse = np.mean(
                environmental_lapse_rates
            )

        else:

            low_level_lapse = 6.0


        # ----------------------------------------------------
        # LAPSE RATE FAKTOR
        # ----------------------------------------------------

        if low_level_lapse < 3.5:

            lapse_factor = 0.35

        elif low_level_lapse < 5.0:

            lapse_factor = 0.60

        elif low_level_lapse < 6.0:

            lapse_factor = 0.80

        elif low_level_lapse < 7.0:

            lapse_factor = 1.00

        elif low_level_lapse < 8.5:

            lapse_factor = 1.08

        else:

            lapse_factor = 0.90


        # ----------------------------------------------------
        # PBL
        # ----------------------------------------------------

        pbl_value = max(
            100.0,
            safe_float(pbl)
        )

        if pbl_value < 500:

            pbl_factor = 0.45

        elif pbl_value < 800:

            pbl_factor = 0.65

        elif pbl_value < 1200:

            pbl_factor = 0.82

        elif pbl_value < 1800:

            pbl_factor = 1.00

        elif pbl_value < 2500:

            pbl_factor = 1.08

        else:

            pbl_factor = 1.00


        # ----------------------------------------------------
        # CAPE
        # ----------------------------------------------------

        cape_value = safe_float(
            cape_value
        )

        if cape_value < 50:

            cape_factor = 0.85

        elif cape_value < 150:

            cape_factor = 0.95

        elif cape_value < 300:

            cape_factor = 1.00

        elif cape_value < 800:

            cape_factor = 1.08

        elif cape_value < 1500:

            cape_factor = 1.15

        else:

            cape_factor = 1.20


        # ----------------------------------------------------
        # FELHŐZET
        # ----------------------------------------------------

        cloud = safe_float(
            cloud
        )

        if cloud < 15:

            cloud_factor = 1.00

        elif cloud < 35:

            cloud_factor = 1.05

        elif cloud < 55:

            cloud_factor = 1.00

        elif cloud < 70:

            cloud_factor = 0.85

        elif cloud < 85:

            cloud_factor = 0.65

        else:

            cloud_factor = 0.40


        # ----------------------------------------------------
        # SZÉL
        # ----------------------------------------------------

        wind = safe_float(
            wind
        )

        if wind < 5:

            wind_factor = 0.82

        elif wind < 12:

            wind_factor = 1.00

        elif wind < 18:

            wind_factor = 0.95

        elif wind < 25:

            wind_factor = 0.80

        elif wind < 32:

            wind_factor = 0.60

        else:

            wind_factor = 0.40


        # ----------------------------------------------------
        # NEDVESSÉG
        # ----------------------------------------------------

        spread = max(
            0.0,
            surface_t - surface_td
        )

        if spread < 2:

            moisture_factor = 0.70

        elif spread < 4:

            moisture_factor = 0.88

        elif spread < 8:

            moisture_factor = 1.00

        elif spread < 12:

            moisture_factor = 0.94

        else:

            moisture_factor = 0.82


        # ----------------------------------------------------
        # KONVEKTÍV INDEX
        # ----------------------------------------------------

        convective_index = (

            solar_time_factor

            *
            radiation_factor

            *
            lapse_factor

            *
            pbl_factor

            *
            cape_factor

            *
            cloud_factor

            *
            wind_factor

            *
            moisture_factor
        )


        # ----------------------------------------------------
        # ALAP TERMERŐSSÉG
        # ----------------------------------------------------

        # A célzott tartomány:
        #
        # gyenge       0.5–1.0
        # közepes      1.0–2.0
        # jó           2.0–3.0
        # erős         3.0–4.0
        # nagyon erős  >4.0
        #
        # A 5 m/s-os plafon megmarad.

        if convective_index < 0.25:

            thermal = 0.0

        elif convective_index < 0.40:

            thermal = (
                0.5
                +
                (
                    convective_index
                    -
                    0.25
                )
                * 3.0
            )

        elif convective_index < 0.60:

            thermal = (
                0.95
                +
                (
                    convective_index
                    -
                    0.40
                )
                * 5.0
            )

        elif convective_index < 0.80:

            thermal = (
                1.95
                +
                (
                    convective_index
                    -
                    0.60
                )
                * 5.5
            )

        else:

            thermal = (
                3.05
                +
                (
                    convective_index
                    -
                    0.80
                )
                * 4.0
            )


        # ----------------------------------------------------
        # REÁLIS FELSŐ KORLÁT
        # ----------------------------------------------------

        thermal = min(
            5.0,
            max(
                0.0,
                thermal
            )
        )


        return round(
            thermal,
            1
        ), round(
            low_level_lapse,
            1
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
            current_time.strftime(
                "%H:%M"
            )
        )

        hour_position = (

            current_time.hour
            +
            current_time.minute / 60
            -
            10.0
        )


        # ----------------------------------------------------
        # FELSZÍNI ADATOK
        # ----------------------------------------------------

        current_temp = interpolate(
            surface_temp,
            day_idx * 24
            +
            10
            +
            hour_position
        )

        current_rh = interpolate(
            surface_rh,
            day_idx * 24
            +
            10
            +
            hour_position
        )

        current_dew = interpolate(
            surface_dew,
            day_idx * 24
            +
            10
            +
            hour_position
        )

        current_wind = interpolate(
            surface_wind,
            day_idx * 24
            +
            10
            +
            hour_position
        )

        current_wind_dir = interpolate(
            surface_wind_dir,
            day_idx * 24
            +
            10
            +
            hour_position
        )

        current_gust = interpolate(
            surface_gust,
            day_idx * 24
            +
            10
            +
            hour_position
        )

        current_cloud = interpolate(
            cloud_total,
            day_idx * 24
            +
            10
            +
            hour_position
        )

        current_cloud_low = interpolate(
            cloud_low,
            day_idx * 24
            +
            10
            +
            hour_position
        )

        current_precip_prob = interpolate(
            precipitation_probability,
            day_idx * 24
            +
            10
            +
            hour_position
        )

        current_precip = interpolate(
            precipitation,
            day_idx * 24
            +
            10
            +
            hour_position
        )

        current_radiation = interpolate(
            radiation,
            day_idx * 24
            +
            10
            +
            hour_position
        )

        current_cape = interpolate(
            cape,
            day_idx * 24
            +
            10
            +
            hour_position
        )

        current_pbl = interpolate(
            pbl_height,
            day_idx * 24
            +
            10
            +
            hour_position
        )


        # ----------------------------------------------------
        # HARMATPONT
        # ----------------------------------------------------

        if (
            current_dew is None
            or
            current_dew > current_temp
        ):

            current_dew = dew_point_from_rh(
                current_temp,
                current_rh
            )


        # ----------------------------------------------------
        # FELHŐALAP
        # ----------------------------------------------------

        cloud_base = estimate_cloud_base(

            current_temp,

            current_dew,

            current_rh,

            current_cloud_low,

            current_pbl,

            day_idx * 24
            +
            10
            +
            hour_position
        )


        # ----------------------------------------------------
        # TERMIK
        # ----------------------------------------------------

        thermal_climb, lapse_rate = (
            estimate_thermal_strength(

                current_temp,

                current_dew,

                current_wind,

                current_cloud,

                current_radiation,

                current_cape,

                current_pbl,

                day_idx * 24
                +
                10
                +
                hour_position
            )
        )


        # ----------------------------------------------------
        # FELHŐZET
        # ----------------------------------------------------

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


        # ----------------------------------------------------
        # SZÉLNYÍRÁS
        # ----------------------------------------------------

        if current_wind > 32:

            wind_shear = "Erős"

        elif current_wind > 25:

            wind_shear = "Közepes"

        elif current_wind > 18:

            wind_shear = "Mérsékelt"

        else:

            wind_shear = "Alacsony"


        # ----------------------------------------------------
        # TÚLFEJLŐDÉS
        # ----------------------------------------------------

        if (
            current_cloud >= 80
            and
            current_precip_prob >= 50
        ):

            overdev = "Magas"

        elif (
            current_cloud >= 65
            and
            current_precip_prob >= 30
        ):

            overdev = "Közepes"

        else:

            overdev = "Alacsony"


        # ----------------------------------------------------
        # FELHŐALAP MEGJELENÍTÉS
        # ----------------------------------------------------

        if cloud_base <= 0:

            cloud_base_display = "-"

        else:

            cloud_base_display = cloud_base


        # ----------------------------------------------------
        # ADATSOR
        # ----------------------------------------------------

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

            "T-Td (°C)":
                round(
                    current_temp
                    -
                    current_dew,
                    1
                ),

            "Termik (m/s)":
                thermal_climb
                if thermal_climb > 0
                else "-",

            "Alap (m AGL)":
                cloud_base_display,

            "Felhőzet":
                cu_cover,

            "Szél":
                (
                    f"{int(round(current_wind_dir))}° / "
                    f"{int(round(current_wind))} km/h"
                ),

            "Lökés":
                f"{int(round(current_gust))} km/h",

            "PBL (m AGL)":
                int(round(current_pbl)),

            "Lapse rate":
                f"{lapse_rate:.1f} °C/km",

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
# 12. NUMERIKUS ADATOK
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


positive_thermal = (
    thermal_values[
        thermal_values > 0
    ]
)


if len(positive_thermal) > 0:

    avg_thermal = (
        positive_thermal.mean()
    )

else:

    avg_thermal = 0


# ============================================================
# 13. KPI
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
# 14. ÁLTALÁNOS ÉRTÉKELÉS
# ============================================================

if max_thermal >= 3.0:

    st.markdown(
        """
        <div class="weather-good">
        <b>🟢 Jó–erős termikus nap</b><br>
        A modell szerint több órán át
        használható, illetve jó termikus aktivitás
        várható.
        </div>
        """,
        unsafe_allow_html=True
    )

elif max_thermal >= 2.0:

    st.markdown(
        """
        <div class="weather-good">
        <b>🟢 Jó termikus aktivitás</b><br>
        Közepes, helyenként jó emelések
        várhatók.
        </div>
        """,
        unsafe_allow_html=True
    )

elif max_thermal >= 1.2:

    st.markdown(
        """
        <div class="weather-warning">
        <b>🟡 Mérsékelt termikus aktivitás</b><br>
        Használható, de várhatóan nem folyamatos
        termikus környezet.
        </div>
        """,
        unsafe_allow_html=True
    )

else:

    st.markdown(
        """
        <div class="weather-warning">
        <b>🟠 Gyenge termikus aktivitás</b><br>
        A modell alapján inkább gyenge,
        időszakos emelések várhatók.
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
    "Termik és felhőalap napközbeni lefutása"
)

fig = go.Figure()


fig.add_trace(
    go.Scatter(
        x=df["Időpont"],

        y=thermal_values,

        name="Termik (m/s)",

        mode="lines+markers",

        line=dict(
            color="orange",
            width=3
        ),

        yaxis="y1"
    )
)


fig.add_trace(
    go.Scatter(
        x=df["Időpont"],

        y=cloud_base_values,

        name="Felhőalap (m AGL)",

        mode="lines+markers",

        line=dict(
            color="royalblue",
            width=3
        ),

        yaxis="y2"
    )
)


fig.update_layout(

    height=500,

    xaxis=dict(
        title="Időpont"
    ),

    yaxis=dict(
        title="Termik (m/s)",
        rangemode="tozero"
    ),

    yaxis2=dict(
        title="Felhőalap (m AGL)",
        overlaying="y",
        side="right",
        rangemode="tozero"
    ),

    hovermode="x unified",

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
# 17. VITORLÁZÓREPÜLÉSI ÖSSZEFOGLALÓ
# ============================================================

st.subheader(
    "🛫 Vitorlázórepülési összefoglaló"
)


usable_thermal_count = int(
    (
        thermal_values >= 1.0
    ).sum()
)


usable_thermal_hours = (
    usable_thermal_count
    /
    4.0
)


st.write(
    f"**Becsült maximális termik:** "
    f"{max_thermal:.1f} m/s"
)


st.write(
    f"**Becsült használható termik átlag:** "
    f"{avg_thermal:.1f} m/s"
)


st.write(
    f"**1,0 m/s feletti időszak:** "
    f"kb. {usable_thermal_hours:.1f} óra"
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
# 18. SZÉL FIGYELMEZTETÉS
# ============================================================

wind_numbers = (
    df["Szél"]
    .str.extract(
        r"/\s*(\d+)"
    )[0]
    .astype(float)
)


max_wind = (
    wind_numbers.max()
)


if max_wind > 32:

    st.markdown(
        """
        <div class="weather-danger">
        <b>🔴 Erős szél</b><br>
        A modell szerint 32 km/h feletti
        szél is előfordulhat.
        </div>
        """,
        unsafe_allow_html=True
    )

elif max_wind > 25:

    st.markdown(
        """
        <div class="weather-warning">
        <b>🟡 Erősebb szél</b><br>
        A szél várhatóan jelentősen
        befolyásolja a termikek szerkezetét.
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# 19. ALACSONY FELHŐALAP
# ============================================================

low_cloud_bases = (
    cloud_base_values[
        (
            cloud_base_values > 0
        )
        &
        (
            cloud_base_values < 800
        )
    ]
)


if len(low_cloud_bases) >= 8:

    st.markdown(
        """
        <div class="weather-warning">
        <b>🟡 Alacsony felhőalap</b><br>
        A vizsgált időszak jelentős részében
        800 m AGL alatti felhőalap becsülhető.
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# 20. MODELL MAGYARÁZAT
# ============================================================

with st.expander(
    "ℹ️ Hogyan számolja a program a felhőalapot és a termiket?"
):

    st.markdown(
        """
        ### ☁️ Felhőalap

        A program már nem kizárólag a felszíni
        hőmérséklet és harmatpont különbségéből
        indul ki.

        A számítás három információt kombinál:

        1. felszíni LCL-becslés,
        2. alacsony légköri relatív nedvesség,
        3. nyomási szintű modell-felhőzet.

        Ezt kiegészíti a határréteg (PBL) magassága.

        A nyomási szintek magasságát a program
        geopotenciális magasságból alakítja
        át repülőtér feletti magasságra.

        ---

        ### 🌡️ Termik

        A termikerősség becslése figyelembe veszi:

        - a hőmérsékleti gradienst,
        - a napsugárzást,
        - a határréteg magasságát,
        - a felhőzetet,
        - a CAPE-t,
        - a szelet,
        - a felszíni nedvességet,
        - valamint a napszakot.

        A modell célja nem az, hogy egyetlen
        „varázsképlettel” megmondja a termiket,
        hanem hogy több meteorológiai jelből
        egy vitorlázórepülés szempontjából
        használható becslést készítsen.

        ---

        ### ⚠️ Fontos

        A termik erőssége és a tényleges felhőalap
        helyi körülmények miatt jelentősen eltérhet
        a numerikus modell értékétől.

        Különösen fontos:

        - felszín típusa,
        - talajnedvesség,
        - szélprofil,
        - konvergencia,
        - inverzió,
        - helyi hőszigetek,
        - tényleges felhőképződés.

        Ezért a program repülésmeteorológiai
        döntéstámogató eszköz, nem hivatalos
        repülésmeteorológiai szolgáltatás.
        """
    )


# ============================================================
# 21. ADATFORRÁS
# ============================================================

st.caption(
    "Meteorológiai adatforrás: Open-Meteo Weather Forecast API. "
    "A nyomási szintű és PBL-adatokból számított értékek "
    "modellbecslések."
)
