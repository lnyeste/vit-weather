```python
import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go
import requests
import math


# ============================================================
# KVASZ ANDRÁS REPÜLŐKLUB
# VITORLÁZÓREPÜLÉS - METEOROLÓGIAI DASHBOARD
# ============================================================


# ============================================================
# 1. OLDAL KONFIGURÁCIÓ
# ============================================================

st.set_page_config(
    page_title="Kvasz András Repülőklub - Időjárás",
    page_icon="🛫",
    layout="wide"
)


# ============================================================
# 2. HÁTTÉR
# ============================================================

st.markdown(
    """
    <style>

    .stApp {
        background: linear-gradient(
            rgba(255,255,255,0.90),
            rgba(255,255,255,0.90)
        );
        background-attachment: fixed;
    }

    .metric-card {
        background-color: rgba(255,255,255,0.90);
        border-radius: 12px;
        padding: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 3. CÍM
# ============================================================

st.title(
    "🛫 Kelet-Magyarország 3 Napos "
    "Vitorlázórepülő Időjárás-Előrejelzője"
)

st.write(
    "Negyedórás repülésmeteorológiai előrejelzés "
    "10:00–20:00 között."
)


# ============================================================
# 4. REPÜLŐTEREK
#
# A koordináták mellett hozzávetőleges repülőtér-magasságot
# is megadunk. Az Open-Meteo válaszából származó elevation
# lesz az elsődleges, ez csak tartalék.
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
# 5. REPÜLŐGÉPEK
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
# 6. NAPOK
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

tomorrow_dt = (
    today_dt +
    datetime.timedelta(days=1)
)

after_tomorrow_dt = (
    today_dt +
    datetime.timedelta(days=2)
)


def get_day_label(dt, prefix):

    day_name = dt.strftime("%A")

    day_name_hu = HUNGARIAN_DAYS.get(
        day_name,
        day_name
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
# 7. OLDALSÁV
# ============================================================

st.sidebar.header("⚙️ Beállítások")


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
# 8. SEGÉDFÜGGVÉNYEK
# ============================================================

def safe_float(value, default=np.nan):

    try:

        if value is None:
            return default

        return float(value)

    except (TypeError, ValueError):

        return default


def clamp(value, minimum, maximum):

    return max(
        minimum,
        min(
            maximum,
            value
        )
    )


def saturation_vapor_pressure(temp_c):

    """
    Magnus-formula.
    """

    return (
        6.112 *
        math.exp(
            (17.67 * temp_c)
            /
            (temp_c + 243.5)
        )
    )


def dewpoint_from_rh(temp_c, rh):

    """
    Harmatpont Magnus-formulával.
    """

    rh = clamp(
        rh,
        1.0,
        100.0
    )

    gamma = (
        math.log(rh / 100.0)
        +
        (
            17.67 *
            temp_c
            /
            (243.5 + temp_c)
        )
    )

    return (
        243.5 * gamma
        /
        (17.67 - gamma)
    )


def lcl_height_agl(temp_c, dewpoint_c):

    """
    Becsült LCL magasság AGL-ben.

    A klasszikus közelítés:
        LCL ≈ 125 m × (T - Td)

    Ez csak becslés.
    """

    spread = max(
        0.0,
        temp_c - dewpoint_c
    )

    return (
        125.0 *
        spread
    )


def circular_mean_degrees(values):

    """
    Körkörös szélirány-átlag.
    """

    values = [
        value
        for value in values
        if not pd.isna(value)
    ]

    if not values:
        return 0

    radians = np.radians(
        values
    )

    sin_mean = np.mean(
        np.sin(radians)
    )

    cos_mean = np.mean(
        np.cos(radians)
    )

    result = np.degrees(
        np.arctan2(
            sin_mean,
            cos_mean
        )
    )

    return int(
        round(result) % 360
    )


# ============================================================
# 9. VITORLÁZÓREPÜLÉSI MODELL
# ============================================================

def calculate_gliding_parameters(

    temp,
    dewpoint,
    cloud_cover,
    cloud_low,
    solar_radiation,
    direct_radiation,
    pbl_height,
    cape,
    wind_speed,
    temp_1000,
    temp_950,
    temp_900,
    temp_850,
    height_1000,
    height_950,
    height_900,
    height_850,
    elevation

):

    # --------------------------------------------------------
    # 1. LCL
    # --------------------------------------------------------

    lcl_agl = lcl_height_agl(
        temp,
        dewpoint
    )


    lcl_msl = (
        elevation +
        lcl_agl
    )


    # --------------------------------------------------------
    # 2. HŐMÉRSÉKLETI GRADIENS
    #
    # Környezeti lapse rate.
    #
    # A troposzférában a 6–7 °C/km körüli gradiens kedvez
    # a konvekciónak. A kisebb gradiens stabilabb.
    # --------------------------------------------------------

    lapse_rates = []


    levels = [

        (
            temp_1000,
            height_1000,
            temp_950,
            height_950
        ),

        (
            temp_950,
            height_950,
            temp_900,
            height_900
        ),

        (
            temp_900,
            height_900,
            temp_850,
            height_850
        )

    ]


    for (
        t_low,
        h_low,
        t_high,
        h_high
    ) in levels:

        if any(
            pd.isna(value)
            for value in [
                t_low,
                h_low,
                t_high,
                h_high
            ]
        ):
            continue


        dh = (
            h_high -
            h_low
        )


        if dh > 100:

            lapse = (
                t_low -
                t_high
            ) / dh * 1000

            lapse_rates.append(
                lapse
            )


    if lapse_rates:

        mean_lapse = float(
            np.mean(
                lapse_rates
            )
        )

    else:

        mean_lapse = 6.0


    # --------------------------------------------------------
    # 3. STABILITÁS / INVERZIÓ
    # --------------------------------------------------------

    stability_factor = 1.0


    if mean_lapse < 3.0:

        stability_factor = 0.25

    elif mean_lapse < 4.0:

        stability_factor = 0.50

    elif mean_lapse < 5.0:

        stability_factor = 0.72

    elif mean_lapse < 6.0:

        stability_factor = 0.88

    elif mean_lapse < 7.0:

        stability_factor = 1.00

    elif mean_lapse < 8.0:

        stability_factor = 1.08

    else:

        stability_factor = 1.12


    # --------------------------------------------------------
    # 4. NAPSUGÁRZÁS
    # --------------------------------------------------------

    solar_factor = clamp(
        solar_radiation / 700.0,
        0.0,
        1.25
    )


    direct_factor = clamp(
        direct_radiation / 600.0,
        0.0,
        1.20
    )


    # --------------------------------------------------------
    # 5. FELHŐZETI KORREKCIÓ
    # --------------------------------------------------------

    cloud_factor = 1.0


    if cloud_cover < 20:

        cloud_factor = 1.00

    elif cloud_cover < 40:

        cloud_factor = 0.94

    elif cloud_cover < 60:

        cloud_factor = 0.82

    elif cloud_cover < 75:

        cloud_factor = 0.65

    elif cloud_cover < 90:

        cloud_factor = 0.45

    else:

        cloud_factor = 0.20


    # --------------------------------------------------------
    # 6. PBL / HATÁRRÉTEG
    # --------------------------------------------------------

    if pd.isna(pbl_height):

        pbl_factor = 0.8

    else:

        pbl_factor = clamp(
            pbl_height / 1500.0,
            0.35,
            1.35
        )


    # --------------------------------------------------------
    # 7. CAPE
    #
    # CAPE nem egyenlő a termik erősségével.
    # Ezért csak részleges súlyt kap.
    # --------------------------------------------------------

    if pd.isna(cape):

        cape_factor = 0.75

    else:

        cape_factor = (
            0.70
            +
            0.30 *
            clamp(
                cape / 1000.0,
                0.0,
                1.0
            )
        )


    # --------------------------------------------------------
    # 8. SZÉL KORREKCIÓ
    #
    # Erős szél keverheti a határréteget, de a termik
    # szerveződését és kihasználhatóságát ronthatja.
    # --------------------------------------------------------

    if wind_speed < 10:

        wind_factor = 1.00

    elif wind_speed < 18:

        wind_factor = 0.96

    elif wind_speed < 25:

        wind_factor = 0.88

    elif wind_speed < 32:

        wind_factor = 0.76

    elif wind_speed < 40:

        wind_factor = 0.62

    else:

        wind_factor = 0.45


    # --------------------------------------------------------
    # 9. NAPPALI KONVEKCIÓ
    # --------------------------------------------------------

    # A termikus aktivitás napszakfüggő.
    # 14:00 körül a legerősebb, majd fokozatosan gyengül.

    current_hour = datetime.datetime.now().hour

    # Ezt később az aktuális adatpont órája felülírja.
    daylight_factor = 1.0


    # --------------------------------------------------------
    # 10. ALAP KONVEKTÍV POTENCIÁL
    # --------------------------------------------------------

    # A modell szándékosan több tényezőből áll.
    # Nem egyetlen képletből próbáljuk megjósolni
    # a termiksebességet.

    thermal_score = (

        0.28 *
        solar_factor

        +

        0.14 *
        direct_factor

        +

        0.18 *
        stability_factor

        +

        0.12 *
        pbl_factor

        +

        0.10 *
        cape_factor

        +

        0.10 *
        cloud_factor

        +

        0.08 *
        wind_factor

    )


    # --------------------------------------------------------
    # 11. HŐMÉRSÉKLET / HARMATPONT
    #
    # Túl nagy spread száraz, gyenge Cu-környezetet jelenthet.
    # Mérsékelt spread gyakran kedvez a Cu-képződésnek.
    # --------------------------------------------------------

    spread = (
        temp -
        dewpoint
    )


    if spread < 2:

        moisture_factor = 0.80

    elif spread < 5:

        moisture_factor = 1.05

    elif spread < 8:

        moisture_factor = 1.00

    elif spread < 12:

        moisture_factor = 0.88

    else:

        moisture_factor = 0.70


    thermal_score *= (
        moisture_factor
    )


    # --------------------------------------------------------
    # 12. TERMÉSZETES SKÁLÁZÁS
    #
    # A modellből egy becsült átlagos termiksebességet készítünk.
    # Ez NEM garantált emelés.
    # --------------------------------------------------------

    thermal_strength = (
        thermal_score *
        3.8
    )


    # CAPE erősen konvektív helyzetben
    # kismértékben növelheti az értéket.

    if not pd.isna(cape):

        if cape > 1500:

            thermal_strength *= 1.15

        elif cape > 800:

            thermal_strength *= 1.08


    # --------------------------------------------------------
    # 13. ERŐS STABILITÁS / INVERZIÓ
    # --------------------------------------------------------

    if mean_lapse < 3:

        thermal_strength *= 0.55


    # --------------------------------------------------------
    # 14. VÉGSŐ LIMIT
    # --------------------------------------------------------

    thermal_strength = clamp(
        thermal_strength,
        0.0,
        5.0
    )


    thermal_strength = round(
        thermal_strength,
        1
    )


    # --------------------------------------------------------
    # 15. FELHŐALAP
    # --------------------------------------------------------

    # LCL a fő becslés.

    cloud_base_agl = lcl_agl

    cloud_base_msl = lcl_msl


    # Ha a PBL nagyon alacsony, a termikus Cu-képződés
    # korlátozott lehet.

    if not pd.isna(pbl_height):

        if pbl_height < cloud_base_agl:

            convective_cloud_base_agl = (
                pbl_height * 0.90
            )

        else:

            convective_cloud_base_agl = (
                cloud_base_agl
            )

    else:

        convective_cloud_base_agl = (
            cloud_base_agl
        )


    convective_cloud_base_agl = max(
        150,
        convective_cloud_base_agl
    )


    convective_cloud_base_msl = (
        elevation +
        convective_cloud_base_agl
    )


    # --------------------------------------------------------
    # 16. TÚLFEJLŐDÉSI KOCKÁZAT
    # --------------------------------------------------------

    overdevelopment_score = 0.0


    if cloud_cover > 70:

        overdevelopment_score += 0.35


    if cloud_cover > 85:

        overdevelopment_score += 0.25


    if not pd.isna(cape):

        if cape > 500:

            overdevelopment_score += 0.15

        if cape > 1000:

            overdevelopment_score += 0.20


    if spread < 4:

        overdevelopment_score += 0.15


    overdevelopment_score = clamp(
        overdevelopment_score,
        0,
        1
    )


    if overdevelopment_score < 0.25:

        overdevelopment = "Alacsony"

    elif overdevelopment_score < 0.55:

        overdevelopment = "Közepes"

    elif overdevelopment_score < 0.75:

        overdevelopment = "Magas"

    else:

        overdevelopment = "Nagyon magas"


    # --------------------------------------------------------
    # 17. REPÜLHETŐSÉGI KATEGÓRIA
    # --------------------------------------------------------

    if thermal_strength < 0.6:

        flyability = "Gyenge / termikszegény"

    elif thermal_strength < 1.2:

        flyability = "Gyenge"

    elif thermal_strength < 2.0:

        flyability = "Mérsékelt"

    elif thermal_strength < 3.0:

        flyability = "Jó"

    elif thermal_strength < 4.0:

        flyability = "Nagyon jó"

    else:

        flyability = "Erős"


    return {

        "thermal_strength":
            thermal_strength,

        "cloud_base_agl":
            int(round(
                convective_cloud_base_agl
            )),

        "cloud_base_msl":
            int(round(
                convective_cloud_base_msl
            )),

        "lcl_agl":
            int(round(
                lcl_agl
            )),

        "pbl_height":
            int(round(pbl_height))
            if not pd.isna(pbl_height)
            else np.nan,

        "cape":
            cape,

        "lapse_rate":
            round(
                mean_lapse,
                1
            ),

        "overdevelopment":
            overdevelopment,

        "flyability":
            flyability
    }


# ============================================================
# 10. FŐ IDŐJÁRÁSI LEKÉRDEZÉS
# ============================================================

def get_pure_live_weather(
    field,
    day_idx
):

    data_rows = []


    target_date_local = (
        today_dt +
        datetime.timedelta(days=day_idx)
    )


    start_time = datetime.datetime.combine(
        target_date_local,
        datetime.time(10, 0)
    )


    end_time = datetime.datetime.combine(
        target_date_local,
        datetime.time(20, 0)
    )


    lat = AIRFIELDS[field]["lat"]
    lon = AIRFIELDS[field]["lon"]

    fallback_elevation = AIRFIELDS[
        field
    ]["elevation"]


    # --------------------------------------------------------
    # OPEN-METEO
    # --------------------------------------------------------

    url = (
        "https://api.open-meteo.com/v1/forecast"
    )


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

        "shortwave_radiation",
        "direct_radiation",

        "boundary_layer_height",
        "cape",

        "temperature_1000hPa",
        "temperature_950hPa",
        "temperature_900hPa",
        "temperature_850hPa",

        "geopotential_height_1000hPa",
        "geopotential_height_950hPa",
        "geopotential_height_900hPa",
        "geopotential_height_850hPa"

    ]


    params = {

        "latitude":
            lat,

        "longitude":
            lon,

        "hourly":
            ",".join(
                hourly_variables
            ),

        "wind_speed_unit":
            "kmh",

        "timezone":
            "Europe/Budapest",

        "forecast_days":
            3,

        # ECMWF IFS:
        # globális, jó választás Közép-Európára.
        "models":
            "ecmwf_ifs025"

    }


    headers = {

        "User-Agent":
            "Kvasz-Andras-Gliding-Weather-Dashboard/2.0"

    }


    # --------------------------------------------------------
    # API KÉRÉS
    # --------------------------------------------------------

    try:

        response = requests.get(

            url,

            params=params,

            headers=headers,

            timeout=20

        )


        if response.status_code != 200:

            st.error(
                "❌ Open-Meteo API hiba: "
                f"HTTP {response.status_code}"
            )

            try:

                st.code(
                    response.text[:1000]
                )

            except Exception:

                pass

            st.stop()


        res = response.json()


    except requests.exceptions.Timeout:

        st.error(
            "❌ Az időjárási szerver nem válaszolt "
            "20 másodpercen belül."
        )

        st.stop()


    except requests.exceptions.ConnectionError:

        st.error(
            "❌ Nem sikerült kapcsolódni "
            "az Open-Meteo szerverhez."
        )

        st.stop()


    except requests.exceptions.RequestException as e:

        st.error(
            f"❌ Hálózati hiba: {e}"
        )

        st.stop()


    except ValueError:

        st.error(
            "❌ Az API nem érvényes JSON adatot küldött."
        )

        st.stop()


    # --------------------------------------------------------
    # API ELLENŐRZÉS
    # --------------------------------------------------------

    if "hourly" not in res:

        st.error(
            "❌ Hiányzik az API-válasz 'hourly' része."
        )

        st.stop()


    hourly = res[
        "hourly"
    ]


    # --------------------------------------------------------
    # TÉNYLEGES ELEVATION
    # --------------------------------------------------------

    elevation = safe_float(
        res.get(
            "elevation",
            fallback_elevation
        ),
        fallback_elevation
    )


    # --------------------------------------------------------
    # IDŐPONTOK
    # --------------------------------------------------------

    try:

        api_times = [

            datetime.datetime.fromisoformat(
                value
            )

            for value in hourly[
                "time"
            ]

        ]

    except Exception as e:

        st.error(
            f"❌ Az időpontok feldolgozása sikertelen: {e}"
        )

        st.stop()


    # --------------------------------------------------------
    # ADATOK DICTIONARY
    # --------------------------------------------------------

    weather_data = {}


    for i, dt_value in enumerate(
        api_times
    ):

        row = {}


        for variable in hourly_variables:

            try:

                row[variable] = safe_float(
                    hourly[
                        variable
                    ][i]
                )

            except (
                KeyError,
                IndexError,
                TypeError
            ):

                row[variable] = np.nan


        weather_data[
            dt_value
        ] = row


    # --------------------------------------------------------
    # INTERPOLÁCIÓ
    # --------------------------------------------------------

    def interpolate(
        current_dt,
        variable
    ):

        if current_dt in weather_data:

            return weather_data[
                current_dt
            ][variable]


        previous_hour = (
            current_dt.replace(
                minute=0,
                second=0,
                microsecond=0
            )
        )


        next_hour = (
            previous_hour +
            datetime.timedelta(
                hours=1
            )
        )


        if previous_hour not in weather_data:

            return np.nan


        if next_hour not in weather_data:

            return weather_data[
                previous_hour
            ][variable]


        v1 = weather_data[
            previous_hour
        ][variable]


        v2 = weather_data[
            next_hour
        ][variable]


        if pd.isna(v1):

            return v2


        if pd.isna(v2):

            return v1


        weight = (
            (
                current_dt -
                previous_hour
            ).total_seconds()
            /
            3600.0
        )


        return (
            v1 * (1 - weight)
            +
            v2 * weight
        )


    # --------------------------------------------------------
    # SZÉLIRÁNY INTERPOLÁCIÓ
    # --------------------------------------------------------

    def interpolate_direction(
        current_dt
    ):

        if current_dt in weather_data:

            return weather_data[
                current_dt
            ]["wind_direction_10m"]


        previous_hour = (
            current_dt.replace(
                minute=0,
                second=0,
                microsecond=0
            )
        )


        next_hour = (
            previous_hour +
            datetime.timedelta(
                hours=1
            )
        )


        if (
            previous_hour not in weather_data
            or
            next_hour not in weather_data
        ):

            return np.nan


        d1 = weather_data[
            previous_hour
        ]["wind_direction_10m"]


        d2 = weather_data[
            next_hour
        ]["wind_direction_10m"]


        if pd.isna(d1):

            return d2


        if pd.isna(d2):

            return d1


        weight = (
            (
                current_dt -
                previous_hour
            ).total_seconds()
            /
            3600.0
        )


        difference = (
            (d2 - d1 + 180)
            % 360
        ) - 180


        return (
            d1 +
            difference * weight
        ) % 360


    # --------------------------------------------------------
    # 41 NEGYEDÓRÁS PONT
    # --------------------------------------------------------

    for i in range(41):

        current_time = (
            start_time +
            datetime.timedelta(
                minutes=15 * i
            )
        )


        time_str = (
            current_time.strftime(
                "%H:%M"
            )
        )


        # ----------------------------------------------------
        # METEOROLÓGIAI ADATOK
        # ----------------------------------------------------

        temp = interpolate(
            current_time,
            "temperature_2m"
        )


        rh = interpolate(
            current_time,
            "relative_humidity_2m"
        )


        dewpoint = interpolate(
            current_time,
            "dew_point_2m"
        )


        if pd.isna(dewpoint) and not pd.isna(temp):

            dewpoint = dewpoint_from_rh(
                temp,
                rh
            )


        cloud_cover = interpolate(
            current_time,
            "cloud_cover"
        )


        cloud_low = interpolate(
            current_time,
            "cloud_cover_low"
        )


        cloud_mid = interpolate(
            current_time,
            "cloud_cover_mid"
        )


        cloud_high = interpolate(
            current_time,
            "cloud_cover_high"
        )


        wind_speed = interpolate(
            current_time,
            "wind_speed_10m"
        )


        wind_gust = interpolate(
            current_time,
            "wind_gusts_10m"
        )


        wind_direction = interpolate_direction(
            current_time
        )


        solar = interpolate(
            current_time,
            "shortwave_radiation"
        )


        direct_solar = interpolate(
            current_time,
            "direct_radiation"
        )


        pbl = interpolate(
            current_time,
            "boundary_layer_height"
        )


        cape = interpolate(
            current_time,
            "cape"
        )


        # ----------------------------------------------------
        # NYOMÁSSZINTI ADATOK
        # ----------------------------------------------------

        temp_1000 = interpolate(
            current_time,
            "temperature_1000hPa"
        )


        temp_950 = interpolate(
            current_time,
            "temperature_950hPa"
        )


        temp_900 = interpolate(
            current_time,
            "temperature_900hPa"
        )


        temp_850 = interpolate(
            current_time,
            "temperature_850hPa"
        )


        height_1000 = interpolate(
            current_time,
            "geopotential_height_1000hPa"
        )


        height_950 = interpolate(
            current_time,
            "geopotential_height_950hPa"
        )


        height_900 = interpolate(
            current_time,
            "geopotential_height_900hPa"
        )


        height_850 = interpolate(
            current_time,
            "geopotential_height_850hPa"
        )


        # ----------------------------------------------------
        # VITORLÁZÓREPÜLÉSI SZÁMÍTÁS
        # ----------------------------------------------------

        parameters = calculate_gliding_parameters(

            temp=temp,

            dewpoint=dewpoint,

            cloud_cover=cloud_cover,

            cloud_low=cloud_low,

            solar_radiation=solar,

            direct_radiation=direct_solar,

            pbl_height=pbl,

            cape=cape,

            wind_speed=wind_speed,

            temp_1000=temp_1000,

            temp_950=temp_950,

            temp_900=temp_900,

            temp_850=temp_850,

            height_1000=height_1000,

            height_950=height_950,

            height_900=height_900,

            height_850=height_850,

            elevation=elevation

        )


        # ----------------------------------------------------
        # FELHŐZET
        # ----------------------------------------------------

        if cloud_cover < 15:

            cloud_text = "SKC"

        elif cloud_cover < 40:

            cloud_text = "FEW"

        elif cloud_cover < 75:

            cloud_text = "SCT"

        else:

            cloud_text = "BKN/OVC"


        # ----------------------------------------------------
        # SZÉLNYÍRÁS / ERŐS SZÉL
        # ----------------------------------------------------

        if wind_speed < 18:

            wind_shear = "Alacsony"

        elif wind_speed < 25:

            wind_shear = "Mérsékelt"

        elif wind_speed < 32:

            wind_shear = "Erős"

        else:

            wind_shear = "Nagyon erős"


        # ----------------------------------------------------
        # REPÜLÉSI MINŐSÍTÉS
        # ----------------------------------------------------

        flyability = parameters[
            "flyability"
        ]


        # ----------------------------------------------------
        # DATA ROW
        # ----------------------------------------------------

        data_rows.append({

            "Időpont":
                time_str,

            "Hőmérséklet (°C)":
                round(
                    temp,
                    1
                ),

            "Harmatpont (°C)":
                round(
                    dewpoint,
                    1
                ),

            "Termik (m/s)":
                parameters[
                    "thermal_strength"
                ],

            "Felhőalap AGL (m)":
                parameters[
                    "cloud_base_agl"
                ],

            "Felhőalap QNH (m)":
                parameters[
                    "cloud_base_msl"
                ],

            "LCL AGL (m)":
                parameters[
                    "lcl_agl"
                ],

            "PBL (m)":
                parameters[
                    "pbl_height"
                ],

            "CAPE (J/kg)":
                round(
                    cape,
                    0
                )
                if not pd.isna(cape)
                else 0,

            "Lapse rate (°C/km)":
                parameters[
                    "lapse_rate"
                ],

            "Felhőzet":
                cloud_text,

            "Felhőzet (%)":
                round(
                    cloud_cover,
                    0
                ),

            "Szél":
                (
                    f"{int(round(wind_direction))}° / "
                    f"{int(round(wind_speed))} km/h"
                ),

            "Szél (km/h)":
                round(
                    wind_speed,
                    1
                ),

            "Lökés (km/h)":
                round(
                    wind_gust,
                    1
                ),

            "Napsugárzás (W/m²)":
                round(
                    solar,
                    0
                ),

            "Szélnyírás":
                wind_shear,

            "Túlfejlődés":
                parameters[
                    "overdevelopment"
                ],

            "Repülhetőség":
                flyability

        })


    # --------------------------------------------------------
    # DATAFRAME
    # --------------------------------------------------------

    df_result = pd.DataFrame(
        data_rows
    )


    numeric_columns = [

        "Hőmérséklet (°C)",
        "Harmatpont (°C)",
        "Termik (m/s)",
        "Felhőalap AGL (m)",
        "Felhőalap QNH (m)",
        "LCL AGL (m)",
        "PBL (m)",
        "CAPE (J/kg)",
        "Lapse rate (°C/km)",
        "Felhőzet (%)",
        "Szél (km/h)",
        "Lökés (km/h)",
        "Napsugárzás (W/m²)"

    ]


    for column in numeric_columns:

        df_result[
            column
        ] = pd.to_numeric(

            df_result[
                column
            ],

            errors="coerce"

        )


    # --------------------------------------------------------
    # NAPI ÁTLAGOS SZÉL
    # --------------------------------------------------------

    base_wind_speed = int(
        round(
            df_result[
                "Szél (km/h)"
            ].mean()
        )
    )


    wind_directions = []


    for value in df_result[
        "Szél"
    ]:

        try:

            direction = int(
                str(value)
                .split("°")[0]
            )

            wind_directions.append(
                direction
            )

        except Exception:

            pass


    base_wind_dir = circular_mean_degrees(
        wind_directions
    )


    st.sidebar.success(
        "📡 Valós modelladatok betöltve!"
    )


    return (
        df_result,
        base_wind_dir,
        base_wind_speed
    )


# ============================================================
# 11. ADATOK BETÖLTÉSE
# ============================================================

df, w_dir, w_spd = get_pure_live_weather(
    selected_field,
    day_offset
)


# ============================================================
# 12. KPI-K
# ============================================================

max_thermal = df[
    "Termik (m/s)"
].max()


max_cloud_base = df[
    "Felhőalap QNH (m)"
].max()


max_pbl = df[
    "PBL (m)"
].max()


max_cape = df[
    "CAPE (J/kg)"
].max()


mean_solar = df[
    "Napsugárzás (W/m²)"
].mean()


col1, col2, col3, col4 = st.columns(4)


col1.metric(
    "Max. becsült termik",
    f"{max_thermal:.1f} m/s"
)


col2.metric(
    "Max. becsült felhőalap",
    f"{int(max_cloud_base)} m QNH"
)


col3.metric(
    "Alapszél",
    f"{w_dir}° / {w_spd} km/h"
)


col4.metric(
    f"{selected_glider} siklószám",
    f"1:{glider_glide_ratio}"
)


# ============================================================
# 13. TERMÁLIS ÁLLAPOT
# ============================================================

st.subheader(
    "🌡️ Termikus állapot"
)


average_thermal = df[
    "Termik (m/s)"
].mean()


best_row = df.loc[
    df["Termik (m/s)"].idxmax()
]


best_time = best_row[
    "Időpont"
]


best_thermal = best_row[
    "Termik (m/s)"
]


best_base = best_row[
    "Felhőalap QNH (m)"
]


if average_thermal < 0.6:

    thermal_summary = (
        "Gyenge termikus nap"
    )

elif average_thermal < 1.2:

    thermal_summary = (
        "Gyenge–mérsékelt termikus nap"
    )

elif average_thermal < 2.0:

    thermal_summary = (
        "Mérsékelt termikus nap"
    )

elif average_thermal < 3.0:

    thermal_summary = (
        "Jó termikus nap"
    )

elif average_thermal < 4.0:

    thermal_summary = (
        "Nagyon jó termikus nap"
    )

else:

    thermal_summary = (
        "Erősen konvektív nap"
    )


st.success(
    f"**{thermal_summary}** — "
    f"a modell szerint a legerősebb termikus időszak "
    f"kb. **{best_time}**, "
    f"becsült emeléssel **{best_thermal:.1f} m/s**."
)


# ============================================================
# 14. ADATTÁBLÁZAT
# ============================================================

st.subheader(
    "📊 Negyedórás vitorlázórepülési előrejelzés"
)


display_columns = [

    "Időpont",

    "Hőmérséklet (°C)",

    "Harmatpont (°C)",

    "Termik (m/s)",

    "Felhőalap AGL (m)",

    "Felhőalap QNH (m)",

    "PBL (m)",

    "CAPE (J/kg)",

    "Lapse rate (°C/km)",

    "Felhőzet",

    "Szél",

    "Lökés (km/h)",

    "Napsugárzás (W/m²)",

    "Túlfejlődés",

    "Repülhetőség"

]


st.dataframe(

    df[
        display_columns
    ],

    use_container_width=True,

    hide_index=True

)


# ============================================================
# 15. TERMIK + FELHŐALAP GRAFIKON
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
            "Termik (m/s)"
        ],

        name="Becsült termik",

        mode="lines+markers",

        line=dict(
            width=3
        ),

        yaxis="y1"

    )

)


fig.add_trace(

    go.Scatter(

        x=df[
            "Időpont"
        ],

        y=df[
            "Felhőalap QNH (m)"
        ],

        name="Felhőalap QNH",

        mode="lines",

        line=dict(
            width=3,
            dash="dash"
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
        title="Felhőalap (m QNH)",
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
# 16. PBL + CAPE
# ============================================================

st.subheader(
    "🌤️ Határréteg és konvektív energia"
)


fig2 = go.Figure()


fig2.add_trace(

    go.Scatter(

        x=df[
            "Időpont"
        ],

        y=df[
            "PBL (m)"
        ],

        name="PBL",

        mode="lines",

        line=dict(
            width=3
        ),

        yaxis="y1"

    )

)


fig2.add_trace(

    go.Scatter(

        x=df[
            "Időpont"
        ],

        y=df[
            "CAPE (J/kg)"
        ],

        name="CAPE",

        mode="lines",

        line=dict(
            width=2,
            dash="dot"
        ),

        yaxis="y2"

    )

)


fig2.update_layout(

    height=450,

    xaxis=dict(
        title="Időpont"
    ),

    yaxis=dict(
        title="PBL (m)"
    ),

    yaxis2=dict(
        title="CAPE (J/kg)",
        overlaying="y",
        side="right"
    ),

    hovermode="x unified"

)


st.plotly_chart(
    fig2,
    use_container_width=True
)


# ============================================================
# 17. SZÉL
# ============================================================

st.subheader(
    "💨 Szélsebesség"
)


wind_fig = go.Figure()


wind_fig.add_trace(

    go.Scatter(

        x=df[
            "Időpont"
        ],

        y=df[
            "Szél (km/h)"
        ],

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

        y=df[
            "Lökés (km/h)"
        ],

        name="Széllökés",

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
        title="Időpont"
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
# 18. NAPSUGÁRZÁS
# ============================================================

st.subheader(
    "☀️ Napsugárzás"
)


solar_fig = go.Figure()


solar_fig.add_trace(

    go.Scatter(

        x=df[
            "Időpont"
        ],

        y=df[
            "Napsugárzás (W/m²)"
        ],

        name="Globális napsugárzás",

        mode="lines",

        line=dict(
            width=3
        )

    )

)


solar_fig.update_layout(

    height=350,

    xaxis=dict(
        title="Időpont"
    ),

    yaxis=dict(
        title="W/m²",
        rangemode="tozero"
    ),

    hovermode="x unified"

)


st.plotly_chart(
    solar_fig,
    use_container_width=True
)


# ============================================================
# 19. REPÜLÉSI ÖSSZEFOGLALÓ
# ============================================================

st.subheader(
    "🛫 Vitorlázórepülési összefoglaló"
)


thermal_rows = df[
    df[
        "Termik (m/s)"
    ] >= 1.0
]


if len(thermal_rows) > 0:

    thermal_start = thermal_rows.iloc[
        0
    ]["Időpont"]

    thermal_end = thermal_rows.iloc[
        -1
    ]["Időpont"]

    thermal_period = (
        f"{thermal_start} – "
        f"{thermal_end}"
    )

else:

    thermal_period = (
        "1 m/s feletti termikus időszak "
        "nem valószínű"
    )


mean_wind = df[
    "Szél (km/h)"
].mean()


max_wind = df[
    "Lökés (km/h)"
].max()


mean_pbl = df[
    "PBL (m)"
].mean()


mean_cape = df[
    "CAPE (J/kg)"
].mean()


summary_text = f"""
**Repülőtér:** {selected_field}

**Nap:** {target_date.strftime('%Y.%m.%d.')}

**Becsült termikus időszak:** {thermal_period}

**Legjobb termikus időpont:** {best_time}

**Max. becsült emelés:** {best_thermal:.1f} m/s

**Becsült felhőalap:** {int(best_base)} m QNH

**Átlagos PBL:** {int(mean_pbl)} m

**Átlagos CAPE:** {int(mean_cape)} J/kg

**Átlagos szél:** {mean_wind:.1f} km/h

**Max. széllökés:** {int(max_wind)} km/h
"""


st.info(
    summary_text
)


# ============================================================
# 20. FONTOS FIGYELMEZTETÉS
# ============================================================

st.warning(
    "⚠️ Ez egy modellalapú vitorlázórepülési becslés. "
    "A termiksebesség és a felhőalap nem mérési adat, "
    "és nem helyettesíti a hivatalos repülésmeteorológiai "
    "információkat, METAR/TAF adatokat, szondázást, "
    "radart, műholdképet vagy a helyi repülőtér "
    "aktuális megfigyelését."
)


# ============================================================
# 21. FORRÁS
# ============================================================

st.markdown("---")

st.caption(
    "Időjárási modelladatok: Open-Meteo / ECMWF IFS. "
    "A termikus paraméterek saját, vitorlázórepülésre "
    "hangolt modellbecslések."
)
```
