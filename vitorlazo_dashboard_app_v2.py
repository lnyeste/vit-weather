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

# Szándékosan egyszerű háttér.
# A korábbi verzióban a weboldal URL-je nem volt közvetlen
# képfájl, ezért háttérképként nem működött megbízhatóan.

st.markdown(
    """
    <style>
    .stApp {
        background:
            linear-gradient(
                rgba(255,255,255,0.93),
                rgba(255,255,255,0.93)
            );
    }

    .weather-card {
        padding: 15px;
        border-radius: 12px;
        background-color: rgba(255,255,255,0.92);
        border: 1px solid #e5e7eb;
        margin-bottom: 10px;
    }

    .good {
        color: #15803d;
        font-weight: bold;
    }

    .warning {
        color: #b45309;
        font-weight: bold;
    }

    .danger {
        color: #b91c1c;
        font-weight: bold;
    }
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
    "A Kvasz András Repülőklub negyedórás "
    "repülésmeteorológiai dashboardja (10:00–20:00)."
)


# ============================================================
# 4. REPÜLŐTEREK
# ============================================================

AIRFIELDS = {
    "Békéscsaba (LHBC)": {
        "lat": 46.68,
        "lon": 21.16,
        "elevation": 89
    },
    "Szeged (LHUD)": {
        "lat": 46.25,
        "lon": 20.09,
        "elevation": 82
    },
    "Debrecen (LHDC)": {
        "lat": 47.49,
        "lon": 21.62,
        "elevation": 121
    },
    "Miskolc (LHMC)": {
        "lat": 48.07,
        "lon": 20.79,
        "elevation": 123
    },
    "Nyíregyháza (LHNY)": {
        "lat": 47.95,
        "lon": 21.69,
        "elevation": 103
    }
}


# ============================================================
# 5. VITORLÁZÓREPÜLŐK
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


today_dt = datetime.date.today()
tomorrow_dt = today_dt + datetime.timedelta(days=1)
after_tomorrow_dt = today_dt + datetime.timedelta(days=2)


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
    get_day_label(today_dt, "Ma"): 0,
    get_day_label(tomorrow_dt, "Holnap"): 1,
    get_day_label(after_tomorrow_dt, "Holnapután"): 2
}


# ============================================================
# 7. OLDALSÁV
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

day_offset = day_options[selected_day_label]

target_date = (
    today_dt +
    datetime.timedelta(days=day_offset)
)

glider_glide_ratio = GLIDER_TYPES[selected_glider]


# ============================================================
# 8. SEGÉDFÜGGVÉNYEK
# ============================================================

def safe_float(value, default=np.nan):
    """
    Biztonságos float konverzió.
    """
    try:
        if value is None:
            return default

        return float(value)

    except Exception:
        return default


def interpolate_value(
    values,
    index_float
):
    """
    Lineáris interpoláció.
    """

    if values is None or len(values) == 0:
        return np.nan

    index_float = max(
        0,
        min(
            index_float,
            len(values) - 1
        )
    )

    i0 = int(math.floor(index_float))
    i1 = int(math.ceil(index_float))

    if i0 == i1:
        return safe_float(values[i0])

    v0 = safe_float(values[i0])
    v1 = safe_float(values[i1])

    if np.isnan(v0) or np.isnan(v1):
        return np.nan

    fraction = index_float - i0

    return (
        v0 * (1 - fraction)
        + v1 * fraction
    )


def dewpoint_from_rh(
    temperature,
    relative_humidity
):
    """
    Magnus-formula.
    """

    if (
        np.isnan(temperature)
        or np.isnan(relative_humidity)
    ):
        return np.nan

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
        / (b + temperature)
        + math.log(rh / 100.0)
    )

    return (
        b * alpha
        / (a - alpha)
    )


def calculate_lapse_rate(
    lower_temp,
    upper_temp,
    lower_height,
    upper_height
):
    """
    Vertikális hőmérsékleti gradiens °C/km-ben.

    Pozitív érték:
        lefelé melegebb -> normális lapse rate

    9.8 °C/km körül:
        száraz adiabatikus gradiens

    6 °C/km körül:
        standard atmoszféra nagyságrend
    """

    if any(
        np.isnan(x)
        for x in [
            lower_temp,
            upper_temp,
            lower_height,
            upper_height
        ]
    ):
        return np.nan

    dz = (
        upper_height
        - lower_height
    )

    if dz <= 50:
        return np.nan

    return (
        (lower_temp - upper_temp)
        / (dz / 1000.0)
    )


def calculate_lcl(
    surface_temperature,
    surface_dewpoint
):
    """
    Egyszerű LCL-becslés.

    LCL ≈ 125 * (T - Td)

    AGL-ben értendő.

    Ez nem a végleges cloudbase, hanem
    a termikből kialakuló cumulus kondenzációs
    szintjének fizikai kiindulópontja.
    """

    if (
        np.isnan(surface_temperature)
        or np.isnan(surface_dewpoint)
    ):
        return np.nan

    spread = (
        surface_temperature
        - surface_dewpoint
    )

    spread = max(
        0,
        spread
    )

    return 125.0 * spread


def circular_mean_degrees(values):
    """
    Szélirány vektoros átlagolása.
    """

    values = [
        x for x in values
        if not np.isnan(x)
    ]

    if not values:
        return 0

    radians = np.radians(values)

    sin_mean = np.mean(
        np.sin(radians)
    )

    cos_mean = np.mean(
        np.cos(radians)
    )

    angle = np.degrees(
        math.atan2(
            sin_mean,
            cos_mean
        )
    )

    return int(
        round(angle % 360)
    )


# ============================================================
# 9. FÜGGŐLEGES PROFIL FELDOLGOZÁSA
# ============================================================

PRESSURE_LEVELS = [
    1000,
    975,
    950,
    925,
    900,
    850,
    800,
    750,
    700
]


def build_vertical_profile(
    response,
    hour_index
):
    """
    Az Open-Meteo nyomásszintű adataiból
    elkészíti az adott órához tartozó
    függőleges profilt.

    T:
        hőmérséklet

    Td:
        harmatpont

    H:
        geopotenciális magasság

    RH:
        relatív nedvesség

    Cloud:
        nyomásszinti felhőzet
    """

    hourly = response.get(
        "hourly",
        {}
    )

    profile = []

    for pressure in PRESSURE_LEVELS:

        temp_key = (
            f"temperature_{pressure}hPa"
        )

        dew_key = (
            f"dew_point_{pressure}hPa"
        )

        rh_key = (
            f"relative_humidity_{pressure}hPa"
        )

        height_key = (
            f"geopotential_height_{pressure}hPa"
        )

        cloud_key = (
            f"cloud_cover_{pressure}hPa"
        )

        temp_values = hourly.get(
            temp_key,
            []
        )

        dew_values = hourly.get(
            dew_key,
            []
        )

        rh_values = hourly.get(
            rh_key,
            []
        )

        height_values = hourly.get(
            height_key,
            []
        )

        cloud_values = hourly.get(
            cloud_key,
            []
        )

        temp = interpolate_value(
            temp_values,
            hour_index
        )

        dew = interpolate_value(
            dew_values,
            hour_index
        )

        rh = interpolate_value(
            rh_values,
            hour_index
        )

        height = interpolate_value(
            height_values,
            hour_index
        )

        cloud = interpolate_value(
            cloud_values,
            hour_index
        )

        # Ha nincs nyomásszinti Td,
        # RH alapján kiszámítjuk.
        if np.isnan(dew):
            dew = dewpoint_from_rh(
                temp,
                rh
            )

        profile.append({
            "pressure": pressure,
            "height": height,
            "temperature": temp,
            "dewpoint": dew,
            "rh": rh,
            "cloud": cloud
        })

    # Magasság szerint rendezzük
    profile = sorted(
        profile,
        key=lambda x: (
            x["height"]
            if not np.isnan(x["height"])
            else 99999
        )
    )

    # Rétegenkénti gradiens
    for i in range(
        len(profile)
    ):
        profile[i]["lapse_rate"] = np.nan

        if i > 0:

            lower = profile[i - 1]
            upper = profile[i]

            profile[i]["lapse_rate"] = (
                calculate_lapse_rate(
                    lower["temperature"],
                    upper["temperature"],
                    lower["height"],
                    upper["height"]
                )
            )

    return profile


# ============================================================
# 10. TERMÉSZETES FELHŐALAP-KORREKCIÓ
# ============================================================

def estimate_cloud_base(
    surface_temp,
    surface_dewpoint,
    profile,
    surface_cloud,
    pbl_height,
    field_elevation
):
    """
    Békéscsabai vitorlázórepülési kalibrációjú
    felhőalap-becslés.

    Kiindulás:
        LCL = 125 * (T - Td)

    Ezután ellenőrizzük a függőleges Td-profilt.

    Fontos:
    nem engedjük a modellt korlátlanul elszállni,
    de a jó és extrém jó alföldi napoknál
    megengedjük a 2500–3200 m AGL értékeket.
    """

    if (
        np.isnan(surface_temp)
        or np.isnan(surface_dewpoint)
    ):
        return np.nan

    # --------------------------------------------------------
    # 1. Alap LCL
    # --------------------------------------------------------

    lcl_agl = calculate_lcl(
        surface_temp,
        surface_dewpoint
    )

    if np.isnan(lcl_agl):
        return np.nan

    # --------------------------------------------------------
    # 2. Profil alapú ellenőrzés
    # --------------------------------------------------------

    profile_cloud_levels = []

    for p in profile:

        h = p["height"]
        t = p["temperature"]
        td = p["dewpoint"]

        if (
            np.isnan(h)
            or np.isnan(t)
            or np.isnan(td)
        ):
            continue

        spread = t - td

        # Olyan szintet keresünk,
        # ahol a telítettséghez közelítünk.
        if spread <= 3.0:
            profile_cloud_levels.append(
                h - field_elevation
            )

    profile_estimate = np.nan

    if profile_cloud_levels:

        positive_levels = [
            h for h in profile_cloud_levels
            if h >= 200
        ]

        if positive_levels:
            profile_estimate = min(
                positive_levels
            )

    # --------------------------------------------------------
    # 3. Profil csak ellenőrző tényező
    # --------------------------------------------------------

    if not np.isnan(profile_estimate):

        # Ha a profil és az LCL nagyon közel van:
        if abs(
            profile_estimate - lcl_agl
        ) < 500:

            lcl_agl = (
                0.65 * lcl_agl
                + 0.35 * profile_estimate
            )

        # Ha nagy az eltérés,
        # a klasszikus LCL marad elsődleges.
        else:

            lcl_agl = (
                0.80 * lcl_agl
                + 0.20 * profile_estimate
            )

    # --------------------------------------------------------
    # 4. Nagyon erős konvektív nap
    # --------------------------------------------------------

    # A PBL önmagában nem cloudbase,
    # de ha a PBL jóval magasabb az LCL-nél,
    # az erős termikus fejlődés jele.
    if not np.isnan(pbl_height):

        if (
            pbl_height > 2200
            and lcl_agl > 2400
        ):
            lcl_agl *= 1.02

        elif (
            pbl_height < 1200
            and lcl_agl > 2200
        ):
            lcl_agl *= 0.95

    # --------------------------------------------------------
    # 5. Felhőzet hatása
    # --------------------------------------------------------

    if not np.isnan(surface_cloud):

        # Zárt felhőzetnél a tényleges
        # használható termikus felhőalap
        # általában nem olyan magas.
        if surface_cloud > 80:
            lcl_agl *= 0.90

        elif surface_cloud > 65:
            lcl_agl *= 0.95

    # --------------------------------------------------------
    # 6. Vitorlázórepülési tapasztalati korlátok
    # --------------------------------------------------------

    # Minimum használható cumulus base.
    lcl_agl = max(
        500,
        lcl_agl
    )

    # Békéscsaba / Alföld:
    # extrém jó napon sem engedjük
    # a kijelzést irreálisan magasra.
    lcl_agl = min(
        3200,
        lcl_agl
    )

    return int(
        round(
            lcl_agl / 50
        ) * 50
    )


# ============================================================
# 11. TERMERŐSSÉG MODELL
# ============================================================

def estimate_thermal_strength(
    surface_temp,
    surface_dewpoint,
    profile,
    solar_radiation,
    cloud_cover,
    pbl_height,
    cape,
    wind_speed,
    hour
):
    """
    Empirikus vitorlázórepülési termikmodell.

    Nem azt állítja, hogy a meteorológiai modell
    közvetlenül megmondja a pilóta által érzékelt
    maximális emelést.

    A cél egy használható, kalibrált becslés.

    Békéscsabai nyári referencia:

        gyenge:      0.8–1.5 m/s
        mérsékelt:   1.5–2.5 m/s
        jó:          2.5–3.0 m/s
        erős:        3.0–4.0 m/s
        extrém:      >4.0 m/s
    """

    if (
        np.isnan(surface_temp)
        or np.isnan(surface_dewpoint)
    ):
        return 0.0

    # --------------------------------------------------------
    # 1. Alsó légköri lapse rate
    # --------------------------------------------------------

    lapse_values = []

    for p in profile:

        lr = p.get(
            "lapse_rate",
            np.nan
        )

        h = p.get(
            "height",
            np.nan
        )

        if (
            np.isnan(lr)
            or np.isnan(h)
        ):
            continue

        # Felszíntől kb. 1500 m-ig
        if h <= 1600:
            lapse_values.append(
                lr
            )

    if lapse_values:

        # A szélső értékek helyett
        # mediánt használunk.
        lapse_rate = float(
            np.nanmedian(
                lapse_values
            )
        )

    else:
        lapse_rate = 6.5

    # --------------------------------------------------------
    # 2. Instabilitási faktor
    # --------------------------------------------------------

    # 6.0 °C/km alatt gyenge.
    # 7.0 körül már jó.
    # 8+ erős.
    #
    # Nem használjuk közvetlenül a 9.8-at,
    # mert az túl agresszív eredményt adna.

    lapse_factor = (
        lapse_rate - 5.5
    ) / 3.5

    lapse_factor = max(
        0,
        min(
            1.25,
            lapse_factor
        )
    )

    # --------------------------------------------------------
    # 3. Napsugárzás
    # --------------------------------------------------------

    if np.isnan(
        solar_radiation
    ):
        radiation_factor = 0.65
    else:

        radiation_factor = (
            solar_radiation
            - 200
        ) / 650

        radiation_factor = max(
            0,
            min(
                1.15,
                radiation_factor
            )
        )

    # --------------------------------------------------------
    # 4. Harmatpont / szárazság
    # --------------------------------------------------------

    spread = (
        surface_temp
        - surface_dewpoint
    )

    # 6–14 °C körül nagyon gyakori
    # a használható termikus nap.
    #
    # Nagyon száraz levegőnél nem akarjuk
    # automatikusan 4–5 m/s-ra növelni.

    moisture_factor = 1.0

    if spread < 4:
        moisture_factor = 0.75

    elif spread < 7:
        moisture_factor = 0.90

    elif spread <= 15:
        moisture_factor = 1.05

    elif spread <= 20:
        moisture_factor = 1.02

    else:
        moisture_factor = 0.92

    # --------------------------------------------------------
    # 5. PBL
    # --------------------------------------------------------

    if np.isnan(
        pbl_height
    ):
        pbl_factor = 0.9

    else:

        pbl_factor = (
            pbl_height - 900
        ) / 1500

        pbl_factor = max(
            0.65,
            min(
                1.15,
                pbl_factor
            )
        )

    # --------------------------------------------------------
    # 6. CAPE
    # --------------------------------------------------------

    if np.isnan(cape):
        cape_factor = 0.90

    elif cape < 100:
        cape_factor = 0.80

    elif cape < 300:
        cape_factor = 0.90

    elif cape < 700:
        cape_factor = 1.00

    elif cape < 1200:
        cape_factor = 1.08

    elif cape < 1800:
        cape_factor = 1.15

    else:
        cape_factor = 1.20

    # --------------------------------------------------------
    # 7. Felhőzet
    # --------------------------------------------------------

    if np.isnan(
        cloud_cover
    ):
        cloud_factor = 1.0

    elif cloud_cover < 20:
        cloud_factor = 1.00

    elif cloud_cover < 45:
        cloud_factor = 1.08

    elif cloud_cover < 70:
        cloud_factor = 1.00

    elif cloud_cover < 85:
        cloud_factor = 0.82

    else:
        cloud_factor = 0.60

    # --------------------------------------------------------
    # 8. Szél
    # --------------------------------------------------------

    if np.isnan(
        wind_speed
    ):
        wind_factor = 1.0

    elif wind_speed < 8:
        wind_factor = 0.92

    elif wind_speed < 18:
        wind_factor = 1.00

    elif wind_speed < 25:
        wind_factor = 0.94

    elif wind_speed < 32:
        wind_factor = 0.84

    else:
        wind_factor = 0.70

    # --------------------------------------------------------
    # 9. Napszak
    # --------------------------------------------------------

    # A legerősebb termikus időszak
    # kb. 12:30–16:30.

    if hour < 10.5:
        time_factor = 0.35

    elif hour < 11.5:
        time_factor = 0.60

    elif hour < 12.5:
        time_factor = 0.80

    elif hour < 14.0:
        time_factor = 1.00

    elif hour < 16.0:
        time_factor = 1.08

    elif hour < 17.0:
        time_factor = 0.95

    elif hour < 18.0:
        time_factor = 0.78

    elif hour < 19.0:
        time_factor = 0.55

    else:
        time_factor = 0.30

    # --------------------------------------------------------
    # 10. ALAP EMELÉSI MODELL
    # --------------------------------------------------------

    #
    # A 2.8-as konstans szándékosan
    # Békéscsaba nyári tapasztalathoz van kalibrálva.
    #

    base_thermal = (
        2.8
        * lapse_factor
        * radiation_factor
        * moisture_factor
        * pbl_factor
        * cape_factor
        * cloud_factor
        * wind_factor
        * time_factor
    )

    # --------------------------------------------------------
    # 11. Felszíni hőmérséklet korrekció
    # --------------------------------------------------------

    if surface_temp < 20:
        temp_factor = 0.65

    elif surface_temp < 24:
        temp_factor = 0.80

    elif surface_temp < 27:
        temp_factor = 0.92

    elif surface_temp < 31:
        temp_factor = 1.00

    elif surface_temp < 34:
        temp_factor = 1.07

    else:
        temp_factor = 1.10

    base_thermal *= temp_factor

    # --------------------------------------------------------
    # 12. Nagyon stabil réteg esetén erős visszavágás
    # --------------------------------------------------------

    if lapse_rate < 4.5:
        base_thermal *= 0.45

    elif lapse_rate < 5.5:
        base_thermal *= 0.70

    elif lapse_rate < 6.0:
        base_thermal *= 0.85

    # --------------------------------------------------------
    # 13. Extrém instabilitás
    # --------------------------------------------------------

    if lapse_rate > 8.5:
        base_thermal *= 1.08

    if (
        not np.isnan(cape)
        and cape > 1800
        and lapse_rate > 7.5
    ):
        base_thermal *= 1.08

    # --------------------------------------------------------
    # 14. Fizikai / repülési korlát
    # --------------------------------------------------------

    # 0.4 m/s alatt a program nem tekinti
    # használható termiknek.

    if base_thermal < 0.4:
        return 0.0

    # 5 m/s fölé nem engedjük a normál
    # előrejelzési modellt.
    #
    # 4 m/s felett már "extrém" kategória.

    base_thermal = min(
        base_thermal,
        5.0
    )

    return round(
        base_thermal,
        1
    )


# ============================================================
# 12. TERMÁLIS MINŐSÍTÉS
# ============================================================

def thermal_category(value):

    if value <= 0:
        return "Nincs / gyenge"

    if value < 1.0:
        return "Gyenge"

    if value < 2.0:
        return "Mérsékelt"

    if value < 3.0:
        return "Jó"

    if value < 4.0:
        return "Erős"

    if value < 5.0:
        return "Nagyon erős"

    return "Extrém"


# ============================================================
# 13. FŐ ÉLŐ IDŐJÁRÁS MOTOR
# ============================================================

@st.cache_data(ttl=900)
def download_weather(
    lat,
    lon
):
    """
    Open-Meteo API lekérés.

    15 perces dashboardhoz órás előrejelzést kérünk,
    majd a megjelenítéshez interpoláljuk.
    """

    url = (
        "https://api.open-meteo.com/v1/forecast"
    )

    pressure_variables = []

    for pressure in PRESSURE_LEVELS:

        pressure_variables.extend([
            f"temperature_{pressure}hPa",
            f"dew_point_{pressure}hPa",
            f"relative_humidity_{pressure}hPa",
            f"cloud_cover_{pressure}hPa",
            f"geopotential_height_{pressure}hPa"
        ])

    hourly_variables = [
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "cloud_cover",
        "wind_speed_10m",
        "wind_direction_10m",
        "shortwave_radiation",
        "direct_radiation",
        "diffuse_radiation",
        "boundary_layer_height",
        "cape"
    ]

    hourly_variables.extend(
        pressure_variables
    )

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(
            hourly_variables
        ),
        "forecast_days": 3,
        "timezone": "Europe/Budapest",
        "wind_speed_unit": "kmh",
        "temperature_unit": "celsius"
    }

    headers = {
        "User-Agent":
            "Kvasz-Andras-Repuloklub-Weather-Dashboard/2.0"
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()

    result = response.json()

    if "hourly" not in result:
        raise RuntimeError(
            "Az Open-Meteo válasz nem tartalmaz hourly adatokat."
        )

    return result


def get_pure_live_weather(
    field,
    day_idx
):
    """
    Teljes vitorlázórepülési időjárásmotor.

    10:00–20:00 között 15 perces adatokat állít elő.

    A meteorológiai alap órás Open-Meteo adat,
    amelyből:
        - T
        - Td
        - felhőzet
        - szél
        - sugárzás
        - PBL
        - CAPE
        - függőleges T/Td profil
        - lapse rate

    alapján számoljuk:
        - termik
        - cloudbase
        - felhőzet
        - szélnyírási kockázat
    """

    target = (
        today_dt
        + datetime.timedelta(
            days=day_idx
        )
    )

    start_time = datetime.datetime.combine(
        target,
        datetime.time(10, 0)
    )

    lat = AIRFIELDS[field]["lat"]
    lon = AIRFIELDS[field]["lon"]
    field_elevation = AIRFIELDS[field]["elevation"]

    try:

        res = download_weather(
            lat,
            lon
        )

    except Exception as e:

        st.error(
            "❌ Nem sikerült csatlakozni az "
            f"Open-Meteo időjárási API-hoz.\n\n"
            f"Hiba: {str(e)}"
        )

        st.stop()

    hourly = res["hourly"]

    times = hourly.get(
        "time",
        []
    )

    if not times:
        st.error(
            "❌ Az időjárási API nem küldött idősort."
        )
        st.stop()

    # --------------------------------------------------------
    # API időindexek
    # --------------------------------------------------------

    time_to_index = {
        t: i
        for i, t in enumerate(times)
    }

    data_rows = []

    all_wind_speeds = []
    all_wind_dirs = []

    # Profilok a részletes megjelenítéshez
    debug_profiles = []

    # --------------------------------------------------------
    # 41 negyedórás pont
    # --------------------------------------------------------

    for i in range(41):

        current_time = (
            start_time
            + datetime.timedelta(
                minutes=15 * i
            )
        )

        time_str = current_time.strftime(
            "%H:%M"
        )

        # A target nap 00:00-jához viszonyított óra
        hour_index = (
            current_time.hour
            + current_time.minute / 60.0
        )

        # ----------------------------------------------------
        # Felszíni adatok
        # ----------------------------------------------------

        current_temp = interpolate_value(
            hourly.get(
                "temperature_2m",
                []
            ),
            hour_index
        )

        current_rh = interpolate_value(
            hourly.get(
                "relative_humidity_2m",
                []
            ),
            hour_index
        )

        current_dew = interpolate_value(
            hourly.get(
                "dew_point_2m",
                []
            ),
            hour_index
        )

        if np.isnan(current_dew):
            current_dew = dewpoint_from_rh(
                current_temp,
                current_rh
            )

        current_cloud = interpolate_value(
            hourly.get(
                "cloud_cover",
                []
            ),
            hour_index
        )

        current_wind_speed = interpolate_value(
            hourly.get(
                "wind_speed_10m",
                []
            ),
            hour_index
        )

        current_wind_dir = interpolate_value(
            hourly.get(
                "wind_direction_10m",
                []
            ),
            hour_index
        )

        current_radiation = interpolate_value(
            hourly.get(
                "shortwave_radiation",
                []
            ),
            hour_index
        )

        current_direct_radiation = interpolate_value(
            hourly.get(
                "direct_radiation",
                []
            ),
            hour_index
        )

        current_diffuse_radiation = interpolate_value(
            hourly.get(
                "diffuse_radiation",
                []
            ),
            hour_index
        )

        current_pbl = interpolate_value(
            hourly.get(
                "boundary_layer_height",
                []
            ),
            hour_index
        )

        current_cape = interpolate_value(
            hourly.get(
                "cape",
                []
            ),
            hour_index
        )

        # ----------------------------------------------------
        # Függőleges profil
        # ----------------------------------------------------

        profile = build_vertical_profile(
            res,
            hour_index
        )

        # ----------------------------------------------------
        # Lapse rate
        # ----------------------------------------------------

        lower_lapse_rates = []

        for p in profile:

            h = p.get(
                "height",
                np.nan
            )

            lr = p.get(
                "lapse_rate",
                np.nan
            )

            if (
                not np.isnan(h)
                and not np.isnan(lr)
                and h <= (
                    field_elevation
                    + 1600
                )
            ):
                lower_lapse_rates.append(
                    lr
                )

        if lower_lapse_rates:
            mean_lapse_rate = round(
                float(
                    np.nanmedian(
                        lower_lapse_rates
                    )
                ),
                1
            )
        else:
            mean_lapse_rate = np.nan

        # ----------------------------------------------------
        # Felhőalap
        # ----------------------------------------------------

        cloud_base = estimate_cloud_base(
            current_temp,
            current_dew,
            profile,
            current_cloud,
            current_pbl,
            field_elevation
        )

        # ----------------------------------------------------
        # Termik
        # ----------------------------------------------------

        thermal_strength = (
            estimate_thermal_strength(
                current_temp,
                current_dew,
                profile,
                current_radiation,
                current_cloud,
                current_pbl,
                current_cape,
                current_wind_speed,
                current_time.hour
                + current_time.minute / 60.0
            )
        )

        # ----------------------------------------------------
        # Felhőzet
        # ----------------------------------------------------

        if np.isnan(current_cloud):
            cu_cover = "N/A"

        elif current_cloud < 15:
            cu_cover = "0/8 SKC"

        elif current_cloud < 40:
            cu_cover = "1-2/8 FEW"

        elif current_cloud < 75:
            cu_cover = "3-4/8 SCT"

        else:
            cu_cover = "5-6/8 BKN"

        # ----------------------------------------------------
        # Szélnyírás / erős szél
        # ----------------------------------------------------

        wind_shear = "Alacsony"

        if (
            not np.isnan(current_wind_speed)
            and current_wind_speed > 25
        ):
            wind_shear = (
                "Erős (magas alapszél)"
            )

        elif (
            not np.isnan(current_wind_speed)
            and current_wind_speed > 18
        ):
            wind_shear = (
                "Közepes"
            )

        # ----------------------------------------------------
        # Túlfejlődés
        # ----------------------------------------------------

        overdevelopment = "Alacsony"

        if (
            not np.isnan(current_cloud)
            and current_cloud >= 75
        ):
            overdevelopment = "Közepes"

        if (
            not np.isnan(current_cloud)
            and current_cloud >= 90
            and not np.isnan(current_cape)
            and current_cape > 1000
        ):
            overdevelopment = "Magas"

        # ----------------------------------------------------
        # Termik kategória
        # ----------------------------------------------------

        thermal_class = thermal_category(
            thermal_strength
        )

        # ----------------------------------------------------
        # Adatbázis sor
        # ----------------------------------------------------

        data_rows.append({
            "Időpont": time_str,

            "Hőmérséklet (°C)": (
                round(
                    current_temp,
                    1
                )
                if not np.isnan(current_temp)
                else "-"
            ),

            "Harmatpont (°C)": (
                round(
                    current_dew,
                    1
                )
                if not np.isnan(current_dew)
                else "-"
            ),

            "Termik (m/s)": (
                thermal_strength
                if thermal_strength > 0
                else "-"
            ),

            "Termik minősítés": (
                thermal_class
            ),

            "Felhőalap (m AGL)": (
                cloud_base
                if not np.isnan(cloud_base)
                else "-"
            ),

            "Felhőzet": cu_cover,

            "Szél": (
                f"{int(round(current_wind_dir))}° / "
                f"{int(round(current_wind_speed))} km/h"
                if (
                    not np.isnan(current_wind_dir)
                    and not np.isnan(current_wind_speed)
                )
                else "-"
            ),

            "Lapse rate (°C/km)": (
                mean_lapse_rate
                if not np.isnan(mean_lapse_rate)
                else "-"
            ),

            "PBL (m)": (
                int(round(current_pbl))
                if not np.isnan(current_pbl)
                else "-"
            ),

            "CAPE (J/kg)": (
                int(round(current_cape))
                if not np.isnan(current_cape)
                else "-"
            ),

            "Szélnyírás": wind_shear,

            "Túlfejlődés": overdevelopment
        })

        # ----------------------------------------------------
        # Átlagos szélhez
        # ----------------------------------------------------

        if not np.isnan(
            current_wind_speed
        ):
            all_wind_speeds.append(
                current_wind_speed
            )

        if not np.isnan(
            current_wind_dir
        ):
            all_wind_dirs.append(
                current_wind_dir
            )

        # ----------------------------------------------------
        # Profil debug
        # ----------------------------------------------------

        if (
            current_time.minute == 0
            and 10 <= current_time.hour <= 20
        ):

            debug_profiles.append({
                "Időpont": time_str,
                "Profil": profile
            })

    # --------------------------------------------------------
    # Átlagos szél
    # --------------------------------------------------------

    if all_wind_dirs:
        base_wind_dir = (
            circular_mean_degrees(
                all_wind_dirs
            )
        )
    else:
        base_wind_dir = 0

    if all_wind_speeds:
        base_wind_speed = int(
            round(
                np.mean(
                    all_wind_speeds
                )
            )
        )
    else:
        base_wind_speed = 0

    df = pd.DataFrame(
        data_rows
    )

    return (
        df,
        base_wind_dir,
        base_wind_speed,
        debug_profiles
    )


# ============================================================
# 14. ADATLEKÉRÉS
# ============================================================

(
    df,
    w_dir,
    w_spd,
    debug_profiles
) = get_pure_live_weather(
    selected_field,
    day_offset
)


# ============================================================
# 15. NUMERIKUSAN KEZELHETŐ OSZLOPOK
# ============================================================

thermal_numeric = pd.to_numeric(
    df["Termik (m/s)"],
    errors="coerce"
)

cloudbase_numeric = pd.to_numeric(
    df["Felhőalap (m AGL)"],
    errors="coerce"
)


# ============================================================
# 16. KPI
# ============================================================

col1, col2, col3, col4 = st.columns(4)


max_thermal = (
    thermal_numeric.max()
    if not thermal_numeric.dropna().empty
    else 0
)

max_cloudbase = (
    cloudbase_numeric.max()
    if not cloudbase_numeric.dropna().empty
    else 0
)


col1.metric(
    "Max Termik",
    f"{max_thermal:.1f} m/s"
)

col2.metric(
    "Max Felhőalap",
    f"{int(max_cloudbase)} m AGL"
)

col3.metric(
    "Napi Alapszél",
    f"{w_dir}° / {w_spd} km/h"
)

col4.metric(
    f"{selected_glider} Teljesítmény",
    f"Siklószám: 1:{glider_glide_ratio}"
)


# ============================================================
# 17. FŐ TÁBLÁZAT
# ============================================================

st.subheader(
    f"Valós negyedórás előrejelzés: "
    f"{selected_field} "
    f"({target_date.strftime('%Y.%m.%d.')})"
)

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 18. TERMÉK ÉS FELHŐALAP GRAFIKON
# ============================================================

st.subheader(
    "Termik és felhőalap napközbeni lefutása"
)

fig = go.Figure()


fig.add_trace(
    go.Scatter(
        x=df["Időpont"],
        y=thermal_numeric,
        name="Termik (m/s)",
        yaxis="y1",
        line=dict(
            width=3
        ),
        mode="lines+markers"
    )
)


fig.add_trace(
    go.Scatter(
        x=df["Időpont"],
        y=cloudbase_numeric,
        name="Felhőalap (m AGL)",
        yaxis="y2",
        line=dict(
            width=3,
            dash="dot"
        ),
        mode="lines+markers"
    )
)


fig.update_layout(
    height=500,

    xaxis=dict(
        title="Helyi idő"
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

    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="center",
        x=0.5
    ),

    hovermode="x unified"
)


st.plotly_chart(
    fig,
    use_container_width=True
)


# ============================================================
# 19. FÜGGŐLEGES PROFIL
# ============================================================

st.subheader(
    "🌡️ Függőleges hőmérsékleti és harmatpont-profil"
)

st.caption(
    "A profil mutatja, hogy a modell az egyes "
    "nyomásszinteken milyen hőmérsékletet, "
    "harmatpontot és gradienst jelez."
)


if debug_profiles:

    profile_times = [
        x["Időpont"]
        for x in debug_profiles
    ]

    selected_profile_time = st.selectbox(
        "Profil időpontja:",
        profile_times,
        index=min(
            5,
            len(profile_times) - 1
        )
    )

    selected_profile = next(
        x["Profil"]
        for x in debug_profiles
        if x["Időpont"]
        == selected_profile_time
    )

    profile_rows = []

    for p in selected_profile:

        profile_rows.append({

            "Nyomás (hPa)": p["pressure"],

            "Magasság (m MSL)": (
                int(round(p["height"]))
                if not np.isnan(
                    p["height"]
                )
                else "-"
            ),

            "Magasság (m AGL)": (
                int(
                    round(
                        p["height"]
                        - AIRFIELDS[
                            selected_field
                        ]["elevation"]
                    )
                )
                if not np.isnan(
                    p["height"]
                )
                else "-"
            ),

            "Hőmérséklet (°C)": (
                round(
                    p["temperature"],
                    1
                )
                if not np.isnan(
                    p["temperature"]
                )
                else "-"
            ),

            "Harmatpont (°C)": (
                round(
                    p["dewpoint"],
                    1
                )
                if not np.isnan(
                    p["dewpoint"]
                )
                else "-"
            ),

            "T-Td (°C)": (
                round(
                    p["temperature"]
                    - p["dewpoint"],
                    1
                )
                if (
                    not np.isnan(
                        p["temperature"]
                    )
                    and not np.isnan(
                        p["dewpoint"]
                    )
                )
                else "-"
            ),

            "RH (%)": (
                round(
                    p["rh"]
                )
                if not np.isnan(
                    p["rh"]
                )
                else "-"
            ),

            "Lapse rate (°C/km)": (
                round(
                    p["lapse_rate"],
                    1
                )
                if not np.isnan(
                    p["lapse_rate"]
                )
                else "-"
            ),

            "Felhőzet (%)": (
                round(
                    p["cloud"]
                )
                if not np.isnan(
                    p["cloud"]
                )
                else "-"
            )
        })

    profile_df = pd.DataFrame(
        profile_rows
    )

    st.dataframe(
        profile_df,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# 20. PROFIL GRAFIKON
# ============================================================

if debug_profiles:

    profile = selected_profile

    heights = []
    temperatures = []
    dewpoints = []

    for p in profile:

        if (
            not np.isnan(
                p["height"]
            )
            and not np.isnan(
                p["temperature"]
            )
        ):

            heights.append(
                p["height"]
                - AIRFIELDS[
                    selected_field
                ]["elevation"]
            )

            temperatures.append(
                p["temperature"]
            )

            dewpoints.append(
                p["dewpoint"]
            )

    fig_profile = go.Figure()

    fig_profile.add_trace(
        go.Scatter(
            x=temperatures,
            y=heights,
            name="Hőmérséklet",
            mode="lines+markers",
            line=dict(
                width=3
            )
        )
    )

    fig_profile.add_trace(
        go.Scatter(
            x=dewpoints,
            y=heights,
            name="Harmatpont",
            mode="lines+markers",
            line=dict(
                width=3,
                dash="dot"
            )
        )
    )

    fig_profile.update_layout(
        height=550,
        xaxis_title="°C",
        yaxis_title="Magasság AGL (m)",
        hovermode="x unified"
    )

    st.plotly_chart(
        fig_profile,
        use_container_width=True
    )


# ============================================================
# 21. NAPI ÖSSZEFOGLALÓ
# ============================================================

st.subheader(
    "🛫 Vitorlázórepülési értékelés"
)


valid_thermal = (
    thermal_numeric
    .dropna()
)

valid_cloudbase = (
    cloudbase_numeric
    .dropna()
)


if not valid_thermal.empty:

    daily_mean_thermal = (
        valid_thermal[
            valid_thermal > 0
        ].mean()
    )

    daily_max_thermal = (
        valid_thermal.max()
    )

else:

    daily_mean_thermal = 0
    daily_max_thermal = 0


if not valid_cloudbase.empty:

    mean_cloudbase = (
        valid_cloudbase.mean()
    )

else:

    mean_cloudbase = 0


# ------------------------------------------------------------
# Termikus minősítés
# ------------------------------------------------------------

if daily_max_thermal < 1.0:

    thermal_summary = (
        "Gyenge termikus nap"
    )

elif daily_max_thermal < 2.0:

    thermal_summary = (
        "Mérsékelt termikus nap"
    )

elif daily_max_thermal < 3.0:

    thermal_summary = (
        "Jó termikus nap"
    )

elif daily_max_thermal < 4.0:

    thermal_summary = (
        "Erős termikus nap"
    )

else:

    thermal_summary = (
        "⚠️ Nagyon erős / extrém termikus nap"
    )


# ------------------------------------------------------------
# Felhőalap minősítés
# ------------------------------------------------------------

if mean_cloudbase < 1000:

    cloudbase_summary = (
        "Alacsony felhőalap"
    )

elif mean_cloudbase < 1800:

    cloudbase_summary = (
        "Mérsékelt felhőalap"
    )

elif mean_cloudbase < 2300:

    cloudbase_summary = (
        "Jó felhőalap"
    )

elif mean_cloudbase < 2700:

    cloudbase_summary = (
        "Nagyon jó felhőalap"
    )

elif mean_cloudbase <= 3200:

    cloudbase_summary = (
        "Extrém magas felhőalap"
    )

else:

    cloudbase_summary = (
        "Szokatlanul magas"
    )


summary_col1, summary_col2 = st.columns(2)


with summary_col1:

    st.markdown(
        f"""
        ### Termikus helyzet

        **{thermal_summary}**

        Becsült napi átlagos használható emelés:
        **{daily_mean_thermal:.1f} m/s**

        Becsült maximális emelés:
        **{daily_max_thermal:.1f} m/s**
        """
    )


with summary_col2:

    st.markdown(
        f"""
        ### Felhőalap

        **{cloudbase_summary}**

        Becsült átlagos felhőalap:
        **{int(mean_cloudbase)} m AGL**

        Repülőtér:
        **{selected_field}**
        """
    )


# ============================================================
# 22. FONTOS METEOROLÓGIAI FIGYELMEZTETÉS
# ============================================================

st.warning(
    "⚠️ A termik- és felhőalapértékek "
    "meteorológiai modellből származó becslések. "
    "Nem helyettesítik a tényleges helyszíni "
    "megfigyelést, METAR/TAF-ot, radar- és "
    "szondataadatokat, illetve a repülésvezető "
    "meteorológiai döntését."
)


# ============================================================
# 23. MODELL INFORMÁCIÓ
# ============================================================

with st.expander(
    "ℹ️ Hogyan számolja a program a termiket és a felhőalapot?"
):

    st.markdown(
        """
        **Felhőalap**

        A modell elsődleges kiindulópontja a felszíni
        hőmérséklet és harmatpont különbsége:

        `LCL ≈ 125 × (T - Td)`

        Ezt ezután ellenőrzi a függőleges
        hőmérséklet- és harmatpontprofil alapján.

        **Termik**

        A termikerősség becslése több tényezőt használ:

        - alsó 0–1600 m átlagos hőmérsékleti gradiens,
        - felszíni hőmérséklet,
        - harmatpont,
        - napsugárzás,
        - PBL,
        - CAPE,
        - felhőzet,
        - szél,
        - napszak.

        A modell Békéscsaba nyári termikus napjaira
        van kalibrálva.

        **Irányadó kategóriák:**

        - 0–1 m/s → gyenge
        - 1–2 m/s → mérsékelt
        - 2–3 m/s → jó
        - 3–4 m/s → erős
        - 4 m/s felett → nagyon erős / extrém

        **Felhőalap:**

        - 1000 m alatt → alacsony
        - 1000–1800 m → mérsékelt
        - 1800–2300 m → jó
        - 2300–2700 m → nagyon jó
        - 2700–3200 m → extrém magas
        """
    )
