
import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go
import requests
import math


# ============================================================
# KVASZ ANDRÁS REPÜLŐKLUB
# VITORLÁZÓREPÜLÉSI METEOROLÓGIAI DASHBOARD
# ============================================================


# ============================================================
# 1. KONFIGURÁCIÓ
# ============================================================

st.set_page_config(
    page_title="Kvasz András Repülőklub - Vitorlázó időjárás",
    page_icon="🛫",
    layout="wide"
)


st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(
            rgba(255,255,255,0.90),
            rgba(255,255,255,0.90)
        );
    }

    .small-note {
        font-size: 12px;
        color: #666;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 2. CÍM
# ============================================================

st.title(
    "🛫 Kelet-Magyarország 3 napos "
    "vitorlázórepülési időjárás"
)

st.write(
    "ICON-D2 + ECMWF összevetés, "
    "negyedórás termik-, felhőalap- és "
    "távbecsléssel."
)


# ============================================================
# 3. REPÜLŐTEREK
# ============================================================

AIRFIELDS = {

    "Békéscsaba (LHBC)": {
        "lat": 46.68,
        "lon": 21.16,
        "elevation": 88
    },

    "Szeged (LHUD)": {
        "lat": 46.25,
        "lon": 20.09,
        "elevation": 81
    },

    "Debrecen (LHDC)": {
        "lat": 47.49,
        "lon": 21.62,
        "elevation": 121
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
# 4. REPÜLŐGÉPEK
# ============================================================

GLIDER_TYPES = {

    "KA-7": {
        "glide_ratio": 26,
        "comfort_factor": 0.48
    },

    "SF25C Falke": {
        "glide_ratio": 22,
        "comfort_factor": 0.45
    },

    "Astir": {
        "glide_ratio": 38,
        "comfort_factor": 0.55
    },

    "Cirrus": {
        "glide_ratio": 38,
        "comfort_factor": 0.57
    },

    "Cirrus VTC": {
        "glide_ratio": 39,
        "comfort_factor": 0.57
    },

    "Standard Jantar 2": {
        "glide_ratio": 40,
        "comfort_factor": 0.58
    },

    "Jantar 2B": {
        "glide_ratio": 48,
        "comfort_factor": 0.60
    }
}


# ============================================================
# 5. NAPOK
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


def day_label(date_value, prefix):

    name = HUNGARIAN_DAYS.get(
        date_value.strftime("%A"),
        date_value.strftime("%A")
    )

    return (
        f"{prefix} "
        f"({name} - "
        f"{date_value.strftime('%m.%d.')})"
    )


day_options = {

    day_label(
        today_dt,
        "Ma"
    ): 0,

    day_label(
        today_dt + datetime.timedelta(days=1),
        "Holnap"
    ): 1,

    day_label(
        today_dt + datetime.timedelta(days=2),
        "Holnapután"
    ): 2
}


# ============================================================
# 6. OLDALSÁV
# ============================================================

st.sidebar.header("⚙️ Beállítások")


selected_field = st.sidebar.selectbox(
    "Repülőtér:",
    list(AIRFIELDS.keys())
)


selected_glider = st.sidebar.selectbox(
    "Vitorlázórepülő:",
    list(GLIDER_TYPES.keys())
)


selected_day = st.sidebar.radio(
    "Nap:",
    list(day_options.keys())
)


day_offset = day_options[
    selected_day
]


target_date = (
    today_dt +
    datetime.timedelta(days=day_offset)
)


glider_data = GLIDER_TYPES[
    selected_glider
]


glide_ratio = glider_data[
    "glide_ratio"
]


comfort_factor = glider_data[
    "comfort_factor"
]


# ============================================================
# 7. SEGÉDFÜGGVÉNYEK
# ============================================================

def safe_float(value):

    try:

        if value is None:
            return np.nan

        return float(value)

    except Exception:

        return np.nan


def clamp(value, minimum, maximum):

    if pd.isna(value):
        return minimum

    return max(
        minimum,
        min(
            maximum,
            value
        )
    )


def dewpoint_from_rh(
    temperature,
    rh
):

    if pd.isna(temperature):
        return np.nan

    if pd.isna(rh):
        return np.nan

    rh = clamp(
        rh,
        1,
        100
    )

    gamma = (
        math.log(rh / 100)
        +
        (
            17.27 * temperature
            /
            (237.7 + temperature)
        )
    )

    return (
        237.7 * gamma
        /
        (17.27 - gamma)
    )


def lcl_height(
    temperature,
    dewpoint
):

    if (
        pd.isna(temperature)
        or
        pd.isna(dewpoint)
    ):
        return np.nan

    spread = max(
        0,
        temperature - dewpoint
    )

    return (
        125 *
        spread
    )


def circular_mean(
    values
):

    values = [
        x for x in values
        if not pd.isna(x)
    ]

    if not values:
        return 0

    radians = np.radians(
        values
    )

    angle = np.degrees(
        np.arctan2(
            np.mean(
                np.sin(radians)
            ),
            np.mean(
                np.cos(radians)
            )
        )
    )

    return int(
        round(angle) % 360
    )


# ============================================================
# 8. ÁLTALÁNOS API LEKÉRDEZŐ
# ============================================================

def request_weather_api(
    url,
    params
):

    try:

        response = requests.get(
            url,
            params=params,
            timeout=20,
            headers={
                "User-Agent":
                "Kvasz-Andras-Gliding-Dashboard/3.0"
            }
        )

        if response.status_code != 200:

            return None

        return response.json()

    except Exception:

        return None


# ============================================================
# 9. IDŐSOR SEGÉD
# ============================================================

def create_time_dict(
    response,
    variables
):

    if (
        response is None
        or
        "hourly" not in response
    ):

        return {}


    hourly = response[
        "hourly"
    ]


    if "time" not in hourly:

        return {}


    result = {}


    for i, time_string in enumerate(
        hourly["time"]
    ):

        try:

            dt = datetime.datetime.fromisoformat(
                time_string
            )

        except Exception:

            continue


        row = {}


        for variable in variables:

            try:

                row[variable] = safe_float(
                    hourly[
                        variable
                    ][i]
                )

            except Exception:

                row[variable] = np.nan


        result[dt] = row


    return result


# ============================================================
# 10. IDŐBELI INTERPOLÁCIÓ
# ============================================================

def interpolate_value(
    data,
    dt,
    variable
):

    if not data:
        return np.nan


    if dt in data:

        return data[
            dt
        ].get(
            variable,
            np.nan
        )


    previous = dt.replace(
        minute=0,
        second=0,
        microsecond=0
    )


    following = (
        previous +
        datetime.timedelta(hours=1)
    )


    if previous not in data:

        return np.nan


    v1 = data[
        previous
    ].get(
        variable,
        np.nan
    )


    if following not in data:

        return v1


    v2 = data[
        following
    ].get(
        variable,
        np.nan
    )


    if pd.isna(v1):
        return v2

    if pd.isna(v2):
        return v1


    weight = (
        dt - previous
    ).total_seconds() / 3600


    return (
        v1 * (1 - weight)
        +
        v2 * weight
    )


# ============================================================
# 11. SZÉLIRÁNY INTERPOLÁCIÓ
# ============================================================

def interpolate_direction(
    data,
    dt,
    variable
):

    d1 = interpolate_value(
        data,
        dt,
        variable
    )

    if pd.isna(d1):

        return np.nan


    return d1


# ============================================================
# 12. MODELLFELHŐALAP
#
# A nyomásszinteken található felhőzet / RH alapján
# megkeressük az első jelentős nedves/felhős réteget.
#
# Ez NEM helyettesíti a radioszondát.
# ============================================================

def model_cloud_base(
    profile,
    elevation
):

    levels = []

    for pressure in [
        1000,
        975,
        950,
        925,
        900,
        850,
        800
    ]:

        h = profile.get(
            f"height_{pressure}",
            np.nan
        )

        rh = profile.get(
            f"rh_{pressure}",
            np.nan
        )

        cloud = profile.get(
            f"cloud_{pressure}",
            np.nan
        )


        if pd.isna(h):
            continue


        levels.append({

            "height": h,
            "rh": rh,
            "cloud": cloud

        })


    if not levels:

        return np.nan


    levels = sorted(
        levels,
        key=lambda x: x["height"]
    )


    # A repülőtér közvetlen környezetét
    # nem kezeljük felhőalapként.
    minimum_height = (
        elevation + 100
    )


    for level in levels:

        if level["height"] < minimum_height:

            continue


        rh = level["rh"]

        cloud = level["cloud"]


        # Jelentős nedvesség / felhőréteg.
        if (
            (
                not pd.isna(cloud)
                and
                cloud >= 60
            )
            or
            (
                not pd.isna(rh)
                and
                rh >= 90
            )
        ):

            return (
                level["height"]
                -
                elevation
            )


    return np.nan


# ============================================================
# 13. KONSZENZUS FELHŐALAP
#
# Három információ:
#
# 1. LCL
# 2. modell nyomásszinti felhőalap
# 3. alacsonyszintű felhőzet
#
# Konzervatív, vitorlázó célú értéket készítünk.
# ============================================================

def calculate_cloud_base(
    temperature,
    dewpoint,
    cloud_cover_low,
    lcl,
    model_base
):

    candidates = []


    if not pd.isna(lcl):

        candidates.append(
            lcl
        )


    if not pd.isna(model_base):

        candidates.append(
            model_base
        )


    if not candidates:

        return np.nan


    # Ha a modell ténylegesen felhőréteget jelez,
    # annak nagyobb súlyt adunk.
    if not pd.isna(model_base):

        base = (
            0.35 * lcl
            +
            0.65 * model_base
        )

    else:

        base = lcl


    # Erős alacsonyszintű felhőzet esetén
    # nem engedjük irreálisan magasra a becslést.
    if (
        not pd.isna(cloud_cover_low)
        and
        cloud_cover_low >= 70
    ):

        base *= 0.90


    # Nagyon száraz alsó légréteg esetén
    # a Cu-alap bizonytalanabb.
    spread = (
        temperature -
        dewpoint
    )


    if spread > 12:

        base *= 0.94


    # Minimum és maximum reális tartomány.
    base = clamp(
        base,
        300,
        3500
    )


    return int(
        round(base / 50)
        * 50
    )


# ============================================================
# 14. TERMIKMODELL
# ============================================================

def calculate_thermal_strength(
    temperature,
    dewpoint,
    cloud_cover,
    solar,
    pbl,
    cape,
    lapse_rate,
    wind_speed,
    cloud_base
):

    if pd.isna(temperature):
        return 0.0


    # --------------------------------------------------------
    # NAPSUGÁRZÁS
    # --------------------------------------------------------

    solar_factor = clamp(
        solar / 700,
        0,
        1.15
    )


    # --------------------------------------------------------
    # HŐMÉRSÉKLETI GRADIENS
    # --------------------------------------------------------

    if pd.isna(lapse_rate):

        lapse_factor = 0.80

    else:

        lapse_factor = np.interp(
            lapse_rate,
            [
                2.5,
                4.0,
                5.0,
                6.0,
                7.0,
                8.0
            ],
            [
                0.25,
                0.50,
                0.72,
                0.90,
                1.05,
                1.10
            ]
        )


    # --------------------------------------------------------
    # PBL
    # --------------------------------------------------------

    if pd.isna(pbl):

        pbl_factor = 0.80

    else:

        pbl_factor = clamp(
            pbl / 1400,
            0.40,
            1.20
        )


    # --------------------------------------------------------
    # FELHŐZET
    # --------------------------------------------------------

    if cloud_cover < 20:

        cloud_factor = 1.00

    elif cloud_cover < 40:

        cloud_factor = 0.95

    elif cloud_cover < 60:

        cloud_factor = 0.85

    elif cloud_cover < 75:

        cloud_factor = 0.72

    elif cloud_cover < 90:

        cloud_factor = 0.50

    else:

        cloud_factor = 0.25


    # --------------------------------------------------------
    # NEDVESSÉG
    # --------------------------------------------------------

    if pd.isna(dewpoint):

        moisture_factor = 0.85

    else:

        spread = (
            temperature -
            dewpoint
        )

        if spread < 2:

            moisture_factor = 0.70

        elif spread < 4:

            moisture_factor = 0.90

        elif spread < 8:

            moisture_factor = 1.00

        elif spread < 12:

            moisture_factor = 0.95

        else:

            moisture_factor = 0.85


    # --------------------------------------------------------
    # CAPE
    # --------------------------------------------------------

    if pd.isna(cape):

        cape_factor = 0.90

    else:

        cape_factor = np.interp(
            cape,
            [
                0,
                100,
                300,
                600,
                1000,
                1500
            ],
            [
                0.85,
                0.90,
                0.96,
                1.02,
                1.07,
                1.12
            ]
        )


    # --------------------------------------------------------
    # SZÉL
    # --------------------------------------------------------

    if wind_speed < 10:

        wind_factor = 1.00

    elif wind_speed < 18:

        wind_factor = 0.97

    elif wind_speed < 25:

        wind_factor = 0.90

    elif wind_speed < 32:

        wind_factor = 0.78

    elif wind_speed < 40:

        wind_factor = 0.62

    else:

        wind_factor = 0.45


    # --------------------------------------------------------
    # FELHŐALAP / KONVEKTÍV TÉR
    # --------------------------------------------------------

    if pd.isna(cloud_base):

        height_factor = 0.80

    else:

        height_factor = np.interp(
            cloud_base,
            [
                400,
                700,
                1000,
                1500,
                2000,
                2500
            ],
            [
                0.55,
                0.70,
                0.85,
                1.00,
                1.08,
                1.12
            ]
        )


    # --------------------------------------------------------
    # ÖSSZESÍTÉS
    # --------------------------------------------------------

    score = (

        0.24 * solar_factor

        +

        0.22 * lapse_factor

        +

        0.15 * pbl_factor

        +

        0.12 * cloud_factor

        +

        0.10 * moisture_factor

        +

        0.07 * cape_factor

        +

        0.05 * wind_factor

        +

        0.05 * height_factor

    )


    # Alap használható termik.
    #
    # Nem a maximális turbulens feláramot,
    # hanem a várható használható emelést becsüljük.

    thermal = (
        score *
        3.25
    )


    # Stabil réteg erős büntetése.

    if (
        not pd.isna(lapse_rate)
        and
        lapse_rate < 3.5
    ):

        thermal *= 0.72


    thermal = clamp(
        thermal,
        0,
        4.5
    )


    return round(
        thermal,
        1
    )


# ============================================================
# 15. MODELLKONSZENZUS
# ============================================================

def calculate_model_consensus(
    icon_value,
    ecmwf_value
):

    if (
        pd.isna(icon_value)
        and
        pd.isna(ecmwf_value)
    ):

        return (
            np.nan,
            "Nincs adat"
        )


    if pd.isna(icon_value):

        return (
            ecmwf_value,
            "ECMWF"
        )


    if pd.isna(ecmwf_value):

        return (
            icon_value,
            "ICON-D2"
        )


    mean_value = (
        icon_value +
        ecmwf_value
    ) / 2


    difference = abs(
        icon_value -
        ecmwf_value
    )


    if difference < 0.3:

        confidence = "🟢 Magas"

    elif difference < 0.7:

        confidence = "🟡 Közepes"

    else:

        confidence = "🔴 Alacsony"


    return (
        mean_value,
        confidence
    )


# ============================================================
# 16. KOMFORTOS TÁV
# ============================================================

def calculate_recommended_distance(
    cloud_base,
    thermal_strength,
    wind_speed,
    wind_gust,
    glide_ratio,
    comfort_factor,
    forecast_confidence
):

    if pd.isna(cloud_base):

        return 0


    # --------------------------------------------------------
    # HASZNÁLHATÓ MAGASSÁG
    #
    # Nem számítjuk bele az egész felhőalapot.
    #
    # 300 m: minimális biztonsági tartalék
    # 100 m: alacsony szintű forduló/útvonal tartalék
    # --------------------------------------------------------

    usable_height = (
        cloud_base -
        400
    )


    if usable_height < 300:

        return 0


    # --------------------------------------------------------
    # ELMÉLETI SIKLÓTÁV
    # --------------------------------------------------------

    theoretical_distance = (
        usable_height
        /
        1000
        *
        glide_ratio
    )


    # --------------------------------------------------------
    # TERMIK KORREKCIÓ
    # --------------------------------------------------------

    if thermal_strength < 0.7:

        thermal_factor = 0.50

    elif thermal_strength < 1.2:

        thermal_factor = 0.65

    elif thermal_strength < 1.8:

        thermal_factor = 0.78

    elif thermal_strength < 2.5:

        thermal_factor = 0.90

    elif thermal_strength < 3.2:

        thermal_factor = 1.00

    else:

        thermal_factor = 1.05


    # --------------------------------------------------------
    # SZÉL KORREKCIÓ
    # --------------------------------------------------------

    if wind_speed < 15:

        wind_factor = 1.00

    elif wind_speed < 22:

        wind_factor = 0.92

    elif wind_speed < 30:

        wind_factor = 0.82

    elif wind_speed < 38:

        wind_factor = 0.68

    else:

        wind_factor = 0.50


    # Széllökés külön büntetés.

    if wind_gust > 35:

        wind_factor *= 0.85

    elif wind_gust > 30:

        wind_factor *= 0.92


    # --------------------------------------------------------
    # ELŐREJELZÉSI BIZONYTALANSÁG
    # --------------------------------------------------------

    if "Alacsony" in str(
        forecast_confidence
    ):

        confidence_factor = 0.75

    elif "Közepes" in str(
        forecast_confidence
    ):

        confidence_factor = 0.88

    else:

        confidence_factor = 1.00


    # --------------------------------------------------------
    # VÉGSŐ TÁV
    # --------------------------------------------------------

    recommended = (

        theoretical_distance

        *

        comfort_factor

        *

        thermal_factor

        *

        wind_factor

        *

        confidence_factor

    )


    # --------------------------------------------------------
    # KEREKÍTÉS
    # --------------------------------------------------------

    if recommended < 5:

        return 0


    if recommended < 20:

        step = 1

    elif recommended < 50:

        step = 5

    else:

        step = 10


    return int(
        round(
            recommended / step
        )
        * step
    )


# ============================================================
# 17. API ADATOK
# ============================================================

def get_weather_data(
    field,
    day_idx
):

    config = AIRFIELDS[
        field
    ]


    lat = config[
        "lat"
    ]

    lon = config[
        "lon"
    ]

    elevation = config[
        "elevation"
    ]


    # --------------------------------------------------------
    # ICON-D2
    # --------------------------------------------------------

    icon_url = (
        "https://api.open-meteo.com/v1/dwd-icon"
    )


    icon_variables = [

        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",

        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",

        "cloud_cover",
        "cloud_cover_low",

        "shortwave_radiation",
        "direct_radiation",

        "boundary_layer_height",
        "cape",

        "temperature_1000hPa",
        "temperature_975hPa",
        "temperature_950hPa",
        "temperature_925hPa",
        "temperature_900hPa",
        "temperature_850hPa",

        "relative_humidity_1000hPa",
        "relative_humidity_975hPa",
        "relative_humidity_950hPa",
        "relative_humidity_925hPa",
        "relative_humidity_900hPa",
        "relative_humidity_850hPa",

        "cloud_cover_1000hPa",
        "cloud_cover_975hPa",
        "cloud_cover_950hPa",
        "cloud_cover_925hPa",
        "cloud_cover_900hPa",
        "cloud_cover_850hPa",

        "geopotential_height_1000hPa",
        "geopotential_height_975hPa",
        "geopotential_height_950hPa",
        "geopotential_height_925hPa",
        "geopotential_height_900hPa",
        "geopotential_height_850hPa"

    ]


    icon_params = {

        "latitude": lat,
        "longitude": lon,

        "hourly":
            ",".join(
                icon_variables
            ),

        "timezone":
            "Europe/Budapest",

        "wind_speed_unit":
            "kmh",

        "forecast_days":
            3,

        "models":
            "icon_d2"

    }


    icon_response = request_weather_api(
        icon_url,
        icon_params
    )


    icon_data = create_time_dict(
        icon_response,
        icon_variables
    )


    # --------------------------------------------------------
    # ECMWF
    # --------------------------------------------------------

    ecmwf_url = (
        "https://api.open-meteo.com/v1/ecmwf"
    )


    ecmwf_variables = [

        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",

        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",

        "cloud_cover",
        "cloud_cover_low",

        "shortwave_radiation",
        "direct_radiation",

        "boundary_layer_height",
        "cape"

    ]


    ecmwf_params = {

        "latitude": lat,
        "longitude": lon,

        "hourly":
            ",".join(
                ecmwf_variables
            ),

        "timezone":
            "Europe/Budapest",

        "wind_speed_unit":
            "kmh",

        "forecast_days":
            3,

        "models":
            "ecmwf_ifs025"

    }


    ecmwf_response = request_weather_api(
        ecmwf_url,
        ecmwf_params
    )


    ecmwf_data = create_time_dict(
        ecmwf_response,
        ecmwf_variables
    )


    # --------------------------------------------------------
    # ELEVATION
    # --------------------------------------------------------

    if (
        icon_response
        and
        "elevation" in icon_response
    ):

        elevation = safe_float(
            icon_response[
                "elevation"
            ]
        )


    # --------------------------------------------------------
    # 41 NEGYEDÓRÁS PONT
    # --------------------------------------------------------

    start = datetime.datetime.combine(
        target_date,
        datetime.time(10, 0)
    )


    rows = []


    for i in range(41):

        current = (
            start +
            datetime.timedelta(
                minutes=15 * i
            )
        )


        # ----------------------------------------------------
        # ICON
        # ----------------------------------------------------

        temp_icon = interpolate_value(
            icon_data,
            current,
            "temperature_2m"
        )

        dew_icon = interpolate_value(
            icon_data,
            current,
            "dew_point_2m"
        )

        rh_icon = interpolate_value(
            icon_data,
            current,
            "relative_humidity_2m"
        )

        wind_icon = interpolate_value(
            icon_data,
            current,
            "wind_speed_10m"
        )

        gust_icon = interpolate_value(
            icon_data,
            current,
            "wind_gusts_10m"
        )

        direction_icon = interpolate_direction(
            icon_data,
            current,
            "wind_direction_10m"
        )

        cloud_icon = interpolate_value(
            icon_data,
            current,
            "cloud_cover"
        )

        low_cloud_icon = interpolate_value(
            icon_data,
            current,
            "cloud_cover_low"
        )

        solar_icon = interpolate_value(
            icon_data,
            current,
            "shortwave_radiation"
        )

        pbl_icon = interpolate_value(
            icon_data,
            current,
            "boundary_layer_height"
        )

        cape_icon = interpolate_value(
            icon_data,
            current,
            "cape"
        )


        if pd.isna(dew_icon):

            dew_icon = dewpoint_from_rh(
                temp_icon,
                rh_icon
            )


        # ----------------------------------------------------
        # ICON SOUNDING
        # ----------------------------------------------------

        profile = {}


        for pressure in [
            1000,
            975,
            950,
            925,
            900,
            850
        ]:

            profile[
                f"height_{pressure}"
            ] = interpolate_value(
                icon_data,
                current,
                f"geopotential_height_{pressure}hPa"
            )


            profile[
                f"rh_{pressure}"
            ] = interpolate_value(
                icon_data,
                current,
                f"relative_humidity_{pressure}hPa"
            )


            profile[
                f"cloud_{pressure}"
            ] = interpolate_value(
                icon_data,
                current,
                f"cloud_cover_{pressure}hPa"
            )


        # ----------------------------------------------------
        # LCL
        # ----------------------------------------------------

        lcl = lcl_height(
            temp_icon,
            dew_icon
        )


        # ----------------------------------------------------
        # MODELLFELHŐALAP
        # ----------------------------------------------------

        model_base = model_cloud_base(
            profile,
            elevation
        )


        # ----------------------------------------------------
        # JAVASOLT FELHŐALAP
        # ----------------------------------------------------

        cloud_base = calculate_cloud_base(
            temp_icon,
            dew_icon,
            low_cloud_icon,
            lcl,
            model_base
        )


        # ----------------------------------------------------
        # HŐMÉRSÉKLETI GRADIENS
        # ----------------------------------------------------

        lapse_values = []


        pairs = [

            (1000, 975),
            (975, 950),
            (950, 925),
            (925, 900),
            (900, 850)

        ]


        for low, high in pairs:

            t1 = interpolate_value(
                icon_data,
                current,
                f"temperature_{low}hPa"
            )

            t2 = interpolate_value(
                icon_data,
                current,
                f"temperature_{high}hPa"
            )

            h1 = interpolate_value(
                icon_data,
                current,
                f"geopotential_height_{low}hPa"
            )

            h2 = interpolate_value(
                icon_data,
                current,
                f"geopotential_height_{high}hPa"
            )


            if any(
                pd.isna(x)
                for x in [
                    t1,
                    t2,
                    h1,
                    h2
                ]
            ):

                continue


            dh = (
                h2 -
                h1
            )


            if dh > 50:

                lapse = (
                    t1 -
                    t2
                ) / dh * 1000

                lapse_values.append(
                    lapse
                )


        if lapse_values:

            lapse_rate = np.mean(
                lapse_values
            )

        else:

            lapse_rate = np.nan


        # ----------------------------------------------------
        # TERMÉK ICON
        # ----------------------------------------------------

        thermal_icon = calculate_thermal_strength(
            temp_icon,
            dew_icon,
            cloud_icon,
            solar_icon,
            pbl_icon,
            cape_icon,
            lapse_rate,
            wind_icon,
            cloud_base
        )


        # ----------------------------------------------------
        # ECMWF
        # ----------------------------------------------------

        temp_ecmwf = interpolate_value(
            ecmwf_data,
            current,
            "temperature_2m"
        )

        dew_ecmwf = interpolate_value(
            ecmwf_data,
            current,
            "dew_point_2m"
        )

        wind_ecmwf = interpolate_value(
            ecmwf_data,
            current,
            "wind_speed_10m"
        )

        cloud_ecmwf = interpolate_value(
            ecmwf_data,
            current,
            "cloud_cover"
        )

        solar_ecmwf = interpolate_value(
            ecmwf_data,
            current,
            "shortwave_radiation"
        )

        pbl_ecmwf = interpolate_value(
            ecmwf_data,
            current,
            "boundary_layer_height"
        )

        cape_ecmwf = interpolate_value(
            ecmwf_data,
            current,
            "cape"
        )


        if pd.isna(dew_ecmwf):

            rh_ecmwf = interpolate_value(
                ecmwf_data,
                current,
                "relative_humidity_2m"
            )

            dew_ecmwf = dewpoint_from_rh(
                temp_ecmwf,
                rh_ecmwf
            )


        lcl_ecmwf = lcl_height(
            temp_ecmwf,
            dew_ecmwf
        )


        thermal_ecmwf = calculate_thermal_strength(

            temp_ecmwf,

            dew_ecmwf,

            cloud_ecmwf,

            solar_ecmwf,

            pbl_ecmwf,

            cape_ecmwf,

            lapse_rate,

            wind_ecmwf,

            lcl_ecmwf

        )


        # ----------------------------------------------------
        # MODELLEK ÖSSZEHASONLÍTÁSA
        # ----------------------------------------------------

        thermal_consensus, confidence = (
            calculate_model_consensus(
                thermal_icon,
                thermal_ecmwf
            )
        )


        if not pd.isna(
            lcl_ecmwf
        ):

            cloud_base_ecmwf = lcl_ecmwf

        else:

            cloud_base_ecmwf = np.nan


        # ----------------------------------------------------
        # SZÉL
        # ----------------------------------------------------

        wind = wind_icon

        gust = gust_icon

        direction = direction_icon


        if pd.isna(wind):

            wind = wind_ecmwf


        if pd.isna(cloud_icon):

            cloud_icon = cloud_ecmwf


        if pd.isna(solar_icon):

            solar_icon = solar_ecmwf


        # ----------------------------------------------------
        # TÁV
        # ----------------------------------------------------

        recommended_distance = (
            calculate_recommended_distance(

                cloud_base,

                thermal_consensus,

                wind,

                gust,

                glide_ratio,

                comfort_factor,

                confidence

            )
        )


        # ----------------------------------------------------
        # REPÜLHETŐSÉG
        # ----------------------------------------------------

        if thermal_consensus < 0.6:

            flyability = (
                "Gyenge / termikszegény"
            )

        elif thermal_consensus < 1.2:

            flyability = "Gyenge"

        elif thermal_consensus < 2.0:

            flyability = "Mérsékelt"

        elif thermal_consensus < 3.0:

            flyability = "Jó"

        elif thermal_consensus < 4.0:

            flyability = "Nagyon jó"

        else:

            flyability = "Erős"


        # ----------------------------------------------------
        # TÚLFEJLŐDÉS
        # ----------------------------------------------------

        overdevelopment_score = 0


        if cloud_icon > 70:

            overdevelopment_score += 0.35


        if cloud_icon > 85:

            overdevelopment_score += 0.25


        if not pd.isna(cape_icon):

            if cape_icon > 500:

                overdevelopment_score += 0.15

            if cape_icon > 1000:

                overdevelopment_score += 0.20


        if (
            not pd.isna(dew_icon)
            and
            not pd.isna(temp_icon)
            and
            temp_icon - dew_icon < 4
        ):

            overdevelopment_score += 0.15


        if overdevelopment_score < 0.25:

            overdevelopment = "Alacsony"

        elif overdevelopment_score < 0.55:

            overdevelopment = "Közepes"

        elif overdevelopment_score < 0.75:

            overdevelopment = "Magas"

        else:

            overdevelopment = "Nagyon magas"


        # ----------------------------------------------------
        # DATA ROW
        # ----------------------------------------------------

        rows.append({

            "Időpont":
                current.strftime("%H:%M"),

            "Hőmérséklet":
                round(
                    temp_icon,
                    1
                ),

            "Harmatpont":
                round(
                    dew_icon,
                    1
                ),

            "LCL AGL":
                int(
                    round(lcl)
                )
                if not pd.isna(lcl)
                else 0,

            "Modell alap AGL":
                int(
                    round(model_base)
                )
                if not pd.isna(model_base)
                else 0,

            "Javasolt Cu-alap":
                int(
                    round(cloud_base)
                )
                if not pd.isna(cloud_base)
                else 0,

            "Termik ICON":
                round(
                    thermal_icon,
                    1
                ),

            "Termik ECMWF":
                round(
                    thermal_ecmwf,
                    1
                ),

            "Termik konszenzus":
                round(
                    thermal_consensus,
                    1
                ),

            "Bizonytalanság":
                confidence,

            "PBL":
                int(
                    round(pbl_icon)
                )
                if not pd.isna(pbl_icon)
                else 0,

            "CAPE":
                int(
                    round(cape_icon)
                )
                if not pd.isna(cape_icon)
                else 0,

            "Lapse rate":
                round(
                    lapse_rate,
                    1
                )
                if not pd.isna(lapse_rate)
                else 0,

            "Felhőzet":
                int(
                    round(cloud_icon)
                )
                if not pd.isna(cloud_icon)
                else 0,

            "Szél":
                (
                    f"{int(round(direction))}° / "
                    f"{int(round(wind))} km/h"
                )
                if not pd.isna(direction)
                else "-",

            "Lökés":
                int(
                    round(gust)
                )
                if not pd.isna(gust)
                else 0,

            "Túlfejlődés":
                overdevelopment,

            "Repülhetőség":
                flyability,

            f"Javasolt táv ({selected_glider})":
                recommended_distance

        })


    return pd.DataFrame(
        rows
    ), elevation


# ============================================================
# 18. ADATOK BETÖLTÉSE
# ============================================================

with st.spinner(
    "🌦️ ICON-D2 és ECMWF adatok betöltése..."
):

    df, field_elevation = get_weather_data(
        selected_field,
        day_offset
    )


if df.empty:

    st.error(
        "❌ Nem sikerült időjárási adatot betölteni."
    )

    st.stop()


# ============================================================
# 19. KPI
# ============================================================

max_thermal = df[
    "Termik konszenzus"
].max()


max_cloud_base = df[
    "Javasolt Cu-alap"
].max()


max_distance = df[
    f"Javasolt táv ({selected_glider})"
].max()


best_index = df[
    "Termik konszenzus"
].idxmax()


best_row = df.loc[
    best_index
]


best_time = best_row[
    "Időpont"
]


best_thermal = best_row[
    "Termik konszenzus"
]


best_base = best_row[
    "Javasolt Cu-alap"
]


col1, col2, col3, col4 = st.columns(4)


col1.metric(
    "Max. termik",
    f"{best_thermal:.1f} m/s"
)


col2.metric(
    "Javasolt Cu-alap",
    f"{int(best_base)} m"
)


col3.metric(
    f"Kényelmes táv – {selected_glider}",
    f"{int(max_distance)} km"
)


col4.metric(
    "Legjobb időpont",
    best_time
)


# ============================================================
# 20. MODELLBIZONYTALANSÁG
# ============================================================

st.subheader(
    "🎯 Modellkonszenzus"
)


confidence_counts = df[
    "Bizonytalanság"
].value_counts()


high_conf = confidence_counts.get(
    "🟢 Magas",
    0
)

medium_conf = confidence_counts.get(
    "🟡 Közepes",
    0
)

low_conf = confidence_counts.get(
    "🔴 Alacsony",
    0
)


st.info(
    f"🟢 Magas egyezés: {high_conf} időpont  |  "
    f"🟡 Közepes: {medium_conf} időpont  |  "
    f"🔴 Nagy eltérés: {low_conf} időpont"
)


# ============================================================
# 21. REPÜLÉSI ÖSSZEFOGLALÓ
# ============================================================

st.subheader(
    "🛫 Repülési összefoglaló"
)


st.success(
    f"""
**{selected_field} — {target_date.strftime('%Y.%m.%d.')}**

A modellkonszenzus szerint a legerősebb termikus időszak:
**{best_time}**

Becsült használható emelés:
**{best_thermal:.1f} m/s**

Konzervatív, vitorlázó célú felhőalap:
**{int(best_base)} m AGL**

A kiválasztott géppel
(**{selected_glider}, 1:{glide_ratio}**)
a jelenlegi modell alapján javasolt maximális komfortos táv:
**{int(max_distance)} km**
"""
)


# ============================================================
# 22. TÁV TÍPUSONKÉNT
# ============================================================

st.subheader(
    "🗺️ Javasolt komfortos táv géptípusonként"
)


# Legjobb napi időpontból számolunk.

distance_rows = []


for aircraft, aircraft_data in GLIDER_TYPES.items():

    distance = calculate_recommended_distance(

        best_base,

        best_thermal,

        best_row["Szél (km/h)"]
        if "Szél (km/h)" in best_row
        else float(
            str(
                best_row["Szél"]
            ).split("/")[-1]
            .replace("km/h", "")
        ),

        best_row["Lökés"],

        aircraft_data[
            "glide_ratio"
        ],

        aircraft_data[
            "comfort_factor"
        ],

        best_row[
            "Bizonytalanság"
        ]

    )


    distance_rows.append({

        "Repülőgép":
            aircraft,

        "Siklószám":
            f"1:{aircraft_data['glide_ratio']}",

        "Javasolt komfortos táv (km)":
            distance

    })


distance_df = pd.DataFrame(
    distance_rows
)


st.dataframe(
    distance_df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 23. TELJES ADATTÁBLA
# ============================================================

st.subheader(
    "📊 Negyedórás részletes előrejelzés"
)


st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 24. TERMÉK + FELHŐALAP GRAFIKON
# ============================================================

st.subheader(
    "📈 Termik és felhőalap"
)


fig = go.Figure()


fig.add_trace(
    go.Scatter(

        x=df[
            "Időpont"
        ],

        y=df[
            "Termik ICON"
        ],

        name="ICON-D2 termik",

        mode="lines",

        line=dict(
            width=2,
            dash="dot"
        )

    )
)


fig.add_trace(
    go.Scatter(

        x=df[
            "Időpont"
        ],

        y=df[
            "Termik ECMWF"
        ],

        name="ECMWF termik",

        mode="lines",

        line=dict(
            width=2,
            dash="dash"
        )

    )
)


fig.add_trace(
    go.Scatter(

        x=df[
            "Időpont"
        ],

        y=df[
            "Termik konszenzus"
        ],

        name="Konszenzus",

        mode="lines+markers",

        line=dict(
            width=4
        )

    )
)


fig.add_trace(
    go.Scatter(

        x=df[
            "Időpont"
        ],

        y=df[
            "Javasolt Cu-alap"
        ],

        name="Cu-alap",

        mode="lines",

        line=dict(
            width=3
        ),

        yaxis="y2"

    )
)


fig.update_layout(

    height=550,

    xaxis=dict(
        title="Idő"
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

    hovermode="x unified"

)


st.plotly_chart(
    fig,
    use_container_width=True
)


# ============================================================
# 25. TÁV GRAFIKON
# ============================================================

st.subheader(
    f"🗺️ Komfortos táv – {selected_glider}"
)


distance_fig = go.Figure()


distance_fig.add_trace(

    go.Scatter(

        x=df[
            "Időpont"
        ],

        y=df[
            f"Javasolt táv ({selected_glider})"
        ],

        mode="lines+markers",

        name="Javasolt táv",

        line=dict(
            width=4
        )

    )

)


distance_fig.update_layout(

    height=400,

    xaxis=dict(
        title="Idő"
    ),

    yaxis=dict(
        title="Javasolt komfortos táv (km)",
        rangemode="tozero"
    ),

    hovermode="x unified"

)


st.plotly_chart(
    distance_fig,
    use_container_width=True
)


# ============================================================
# 26. SZÉL
# ============================================================

st.subheader(
    "💨 Szél"
)


wind_values = []


gust_values = []


for value in df[
    "Szél"
]:

    try:

        speed = float(
            str(value)
            .split("/")[-1]
            .replace(
                "km/h",
                ""
            )
        )

        wind_values.append(
            speed
        )

    except Exception:

        wind_values.append(
            np.nan
        )


for value in df[
    "Lökés"
]:

    gust_values.append(
        value
    )


wind_fig = go.Figure()


wind_fig.add_trace(

    go.Scatter(

        x=df[
            "Időpont"
        ],

        y=wind_values,

        name="Szél",

        mode="lines+markers",

        line=dict(
            width=3
        )

    )
)


wind_fig.add_trace(

    go.Scatter(

        x=df[
            "Időpont"
        ],

        y=gust_values,

        name="Lökés",

        mode="lines",

        line=dict(
            width=2,
            dash="dash"
        )

    )
)


wind_fig.update_layout(

    height=400,

    xaxis=dict(
        title="Idő"
    ),

    yaxis=dict(
        title="km/h",
        rangemode="tozero"
    ),

    hovermode="x unified"

)


st.plotly_chart(
    wind_fig,
    use_container_width=True
)


# ============================================================
# 27. FONTOS REPÜLÉSBIZTONSÁGI MEGJEGYZÉS
# ============================================================

st.warning(
    """
⚠️ **Fontos:** a termiksebesség, felhőalap és javasolt táv
modellalapú becslés. A „komfortos táv” nem biztonságos
visszatérési távolság és nem repülési engedély.

A tényleges repülés előtt ellenőrizni kell a METAR/TAF,
aktuális szél-, csapadék-, radar- és műholdadatokat,
valamint a helyi repülőtér és a pilóta aktuális
repülésmeteorológiai információit.

Erős szél, szélnyírás, túlfejlődő gomolyfelhő,
front vagy zivataros környezet esetén a modell által
számított távot nem szabad automatikusan elfogadni.
"""
)


# ============================================================
# 28. FORRÁS
# ============================================================

st.caption(
    "Modellek: DWD ICON-D2 + ECMWF IFS. "
    "A vitorlázórepülési indexek saját számított "
    "modellparaméterek."
)

