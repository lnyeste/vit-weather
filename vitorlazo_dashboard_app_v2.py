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
        background: linear-gradient(
            rgba(255, 255, 255, 0.88),
            rgba(255, 255, 255, 0.88)
        ),
        url("{hangar_bg_url}");

        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 3. KVASZ ANDRÁS EGYESÜLET OLDALSÁV
# ============================================================

st.sidebar.markdown(
    """
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
    "A Kvasz András Repülőklub hivatalos negyedórás "
    "repülésmeteorológiai dashboardja (10:00 - 20:00)."
)


# ============================================================
# REPÜLŐTEREK
# ============================================================

AIRFIELDS = {
    "Békéscsaba (LHBC)": {
        "lat": 46.68,
        "lon": 21.16
    },

    "Szeged (LHUD)": {
        "lat": 46.25,
        "lon": 20.09
    },

    "Debrecen (LHDC)": {
        "lat": 47.49,
        "lon": 21.62
    },

    "Miskolc (LHMC)": {
        "lat": 48.07,
        "lon": 20.79
    },

    "Nyíregyháza (LHNY)": {
        "lat": 47.95,
        "lon": 21.69
    }
}


# ============================================================
# REPÜLŐGÉP TÍPUSOK
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
# MAGYAR NAPOK
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
# DÁTUMOK
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
    get_day_label(today_dt, "Ma"): 0,
    get_day_label(tomorrow_dt, "Holnap"): 1,
    get_day_label(after_tomorrow_dt, "Holnapután"): 2
}


# ============================================================
# OLDALSÁV VEZÉRLŐK
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

day_offset = day_options[selected_day_label]

target_date = (
    today_dt +
    datetime.timedelta(days=day_offset)
)

glider_glide_ratio = GLIDER_TYPES[
    selected_glider
]


# ============================================================
# 5. IDŐJÁRÁSI ADATOK LEKÉRÉSE
# ============================================================

def get_pure_live_weather(field, day_idx):

    """
    Open-Meteo időjárási adatok lekérése.

    10:00 - 20:00 között 15 perces adatpontokat készítünk.
    Az Open-Meteo órás adatait lineárisan interpoláljuk.

    day_idx:
        0 = ma
        1 = holnap
        2 = holnapután
    """

    data_rows = []

    # --------------------------------------------------------
    # DÁTUM
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # REPÜLŐTÉR KOORDINÁTÁI
    # --------------------------------------------------------

    lat = AIRFIELDS[field]["lat"]
    lon = AIRFIELDS[field]["lon"]


    # --------------------------------------------------------
    # OPEN-METEO API
    # --------------------------------------------------------

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
        "User-Agent": (
            "Kvasz-Andras-Repuloklub-Weather-Dashboard/1.0"
        )
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

        response.raise_for_status()

        res = response.json()


    except requests.exceptions.Timeout:

        st.error(
            "❌ Időtúllépés: az Open-Meteo szerver "
            "15 másodpercen belül nem válaszolt."
        )

        st.stop()


    except requests.exceptions.ConnectionError:

        st.error(
            "❌ Kapcsolódási hiba: nem sikerült "
            "elérni az Open-Meteo szervert."
        )

        st.stop()


    except requests.exceptions.HTTPError as e:

        st.error(
            f"❌ Open-Meteo HTTP hiba: {e}"
        )

        st.stop()


    except requests.exceptions.RequestException as e:

        st.error(
            f"❌ Hálózati hiba az időjárási adatok "
            f"lekérésekor: {e}"
        )

        st.stop()


    except ValueError:

        st.error(
            "❌ Az Open-Meteo nem érvényes JSON "
            "adatot küldött vissza."
        )

        st.stop()


    except Exception as e:

        st.error(
            f"❌ Ismeretlen API hiba: {e}"
        )

        st.stop()


    # --------------------------------------------------------
    # API VÁLASZ ELLENŐRZÉSE
    # --------------------------------------------------------

    if "hourly" not in res:

        st.error(
            "❌ Az Open-Meteo válaszából hiányzik "
            "az 'hourly' adatrész."
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
        name
        for name in required_fields
        if name not in hourly
    ]


    if missing_fields:

        st.error(
            "❌ Hiányzó időjárási adatok: "
            + ", ".join(missing_fields)
        )

        st.stop()


    # --------------------------------------------------------
    # ÓRÁS ADATOK FELDOLGOZÁSA
    # --------------------------------------------------------

    weather_data = {}


    try:

        api_times = [
            datetime.datetime.fromisoformat(value)
            for value in hourly["time"]
        ]

    except Exception as e:

        st.error(
            f"❌ Az időbélyegek feldolgozása sikertelen: {e}"
        )

        st.stop()


    for i, dt_value in enumerate(api_times):

        try:

            temp = hourly["temperature_2m"][i]
            wind_speed = hourly["wind_speed_10m"][i]
            wind_dir = hourly["wind_direction_10m"][i]
            cloud = hourly["cloud_cover"][i]
            rh = hourly["relative_humidity_2m"][i]


            if any(
                value is None
                for value in [
                    temp,
                    wind_speed,
                    wind_dir,
                    cloud,
                    rh
                ]
            ):
                continue


            weather_data[dt_value] = {
                "temp": float(temp),
                "wind_speed": float(wind_speed),
                "wind_dir": float(wind_dir),
                "cloud": float(cloud),
                "rh": float(rh)
            }


        except (
            IndexError,
            TypeError,
            ValueError
        ):

            continue


    # --------------------------------------------------------
    # SZÜKSÉGES ÓRÁS PONTOK
    # --------------------------------------------------------

    required_hours = []

    current_hour = start_time


    while current_hour <= end_time:

        required_hours.append(
            current_hour
        )

        current_hour += datetime.timedelta(hours=1)


    missing_hours = [
        value.strftime("%Y-%m-%d %H:%M")
        for value in required_hours
        if value not in weather_data
    ]


    if missing_hours:

        st.error(
            "❌ Nem áll rendelkezésre elegendő "
            "órás előrejelzési adat erre a napra: "
            f"{target_date_local.strftime('%Y.%m.%d.')}"
        )

        st.warning(
            "Hiányzó időpontok: "
            + ", ".join(missing_hours)
        )

        st.stop()


    # ========================================================
    # SEGÉDFÜGGVÉNY - LINEÁRIS INTERPOLÁCIÓ
    # ========================================================

    def interpolate_value(current_dt, key):

        if current_dt in weather_data:

            return weather_data[
                current_dt
            ][key]


        previous_hour = current_dt.replace(
            minute=0,
            second=0,
            microsecond=0
        )

        next_hour = (
            previous_hour +
            datetime.timedelta(hours=1)
        )


        if previous_hour not in weather_data:
            previous_hour = start_time


        if next_hour not in weather_data:
            next_hour = end_time


        previous_value = weather_data[
            previous_hour
        ][key]

        next_value = weather_data[
            next_hour
        ][key]


        total_seconds = (
            next_hour -
            previous_hour
        ).total_seconds()


        if total_seconds <= 0:

            return previous_value


        elapsed_seconds = (
            current_dt -
            previous_hour
        ).total_seconds()


        weight = (
            elapsed_seconds /
            total_seconds
        )


        return (
            previous_value * (1 - weight)
            +
            next_value * weight
        )


    # ========================================================
    # SEGÉDFÜGGVÉNY - SZÉLIRÁNY INTERPOLÁCIÓ
    # ========================================================

    def interpolate_wind_direction(current_dt):

        if current_dt in weather_data:

            return weather_data[
                current_dt
            ]["wind_dir"]


        previous_hour = current_dt.replace(
            minute=0,
            second=0,
            microsecond=0
        )

        next_hour = (
            previous_hour +
            datetime.timedelta(hours=1)
        )


        if next_hour not in weather_data:

            return weather_data[
                previous_hour
            ]["wind_dir"]


        d1 = weather_data[
            previous_hour
        ]["wind_dir"]

        d2 = weather_data[
            next_hour
        ]["wind_dir"]


        total_seconds = (
            next_hour -
            previous_hour
        ).total_seconds()


        elapsed_seconds = (
            current_dt -
            previous_hour
        ).total_seconds()


        weight = (
            elapsed_seconds /
            total_seconds
        )


        # Körkörös interpoláció.
        # Például 350° -> 10° esetén
        # nem 180°-ot kapunk.

        angle_difference = (
            (d2 - d1 + 180) % 360
        ) - 180


        result = (
            d1 +
            angle_difference * weight
        )


        return result % 360


    # ========================================================
    # NAPI ÁTLAGOS ALAPSZÉL
    # ========================================================

    daily_period_data = [
        weather_data[value]
        for value in required_hours
    ]


    base_wind_speed = int(
        round(
            np.mean([
                item["wind_speed"]
                for item in daily_period_data
            ])
        )
    )


    # Körkörös szélirány-átlag
    wind_angles = np.radians([
        item["wind_dir"]
        for item in daily_period_data
    ])


    sin_mean = np.mean(
        np.sin(wind_angles)
    )

    cos_mean = np.mean(
        np.cos(wind_angles)
    )


    base_wind_dir = int(
        round(
            np.degrees(
                np.arctan2(
                    sin_mean,
                    cos_mean
                )
            )
        ) % 360
    )


    # ========================================================
    # 41 DARAB NEGYEDÓRÁS PONT
    # ========================================================

    for i in range(41):

        current_time = (
            start_time +
            datetime.timedelta(
                minutes=15 * i
            )
        )


        time_str = current_time.strftime(
            "%H:%M"
        )


        hour_val = (
            current_time.hour
            +
            current_time.minute / 60.0
        )


        # ----------------------------------------------------
        # INTERPOLÁLT ADATOK
        # ----------------------------------------------------

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
            interpolate_wind_direction(
                current_time
            )
        )


        current_rh = interpolate_value(
            current_time,
            "rh"
        )


        # ----------------------------------------------------
        # HARMATPONT
        # ----------------------------------------------------

        safe_rh = max(
            1.0,
            min(
                100.0,
                current_rh
            )
        )


        alpha = (
            (
                17.27 *
                current_temp
            )
            /
            (
                237.7 +
                current_temp
            )
        ) + math.log(
            safe_rh / 100.0
        )


        current_dew = (
            237.7 *
            alpha
        ) / (
            17.27 -
            alpha
        )


        # ----------------------------------------------------
        # FELHŐALAP
        # ----------------------------------------------------

        calc_base = int(
            (
                current_temp -
                current_dew
            ) * 125
        )


        if current_cloud > 15:

            cumulus_base = max(
                500,
                calc_base
            )

        else:

            cumulus_base = 0


        # ----------------------------------------------------
        # TERMIK
        # ----------------------------------------------------

        thermal_factor = max(
            0,
            1 -
            (
                (hour_val - 14.0) /
                4.5
            ) ** 2
        )


        if (
            thermal_factor > 0.05
            and current_cloud < 80
        ):

            base_climb = (
                (
                    current_temp -
                    current_dew
                )
                *
                0.25
                *
                (
                    1 -
                    current_cloud / 120
                )
            )


            thermal_climb = round(
                max(
                    0.5,
                    min(
                        base_climb *
                        thermal_factor,
                        5.0
                    )
                ),
                1
            )

        else:

            thermal_climb = 0


        # ----------------------------------------------------
        # SZÉLNYÍRÁS
        # ----------------------------------------------------

        wind_shear = "Alacsony"


        if (
            hour_val > 18.0
            and current_wind_spd > 18
        ):

            wind_shear = (
                "Közepes "
                "(Esti stabilizáció)"
            )


        elif current_wind_spd > 25:

            wind_shear = (
                "Erős "
                "(Magas alapszél)"
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

        else:

            cu_cover = "5-6/8 BKN"


        # ----------------------------------------------------
        # TÚLFEJLŐDÉS
        # ----------------------------------------------------

        if current_cloud < 70:

            overdev = "Alacsony"

        else:

            overdev = "Közepes"


        # ----------------------------------------------------
        # ADATSOR
        # ----------------------------------------------------

        data_rows.append({

            "Időpont":
                time_str,

            "Hőmérséklet (°C)":
                current_temp,

            "Termik (m/s)":
                thermal_climb
                if thermal_climb > 0
                else 0.0,

            "Alap (m QNH)":
                cumulus_base
                if cumulus_base > 0
                else 0,

            "Felhőzet":
                cu_cover,

            "Felhőzet (%)":
                current_cloud,

            "Páratartalom (%)":
                round(
                    current_rh,
                    1
                ),

            "Harmatpont (°C)":
                round(
                    current_dew,
                    1
                ),

            "Szél":
                (
                    f"{int(current_wind_dir)}° / "
                    f"{int(current_wind_spd)} km/h"
                ),

            "Szélirány (°)":
                int(current_wind_dir),

            "Szél (km/h)":
                int(current_wind_spd),

            "Szélnyírás":
                wind_shear,

            "Túlfejlődés":
                overdev
        })


    # ========================================================
    # DATAFRAME
    # ========================================================

    df_result = pd.DataFrame(
        data_rows
    )


    # Biztosítjuk, hogy a numerikus oszlopok valóban
    # numerikusak legyenek.

    numeric_columns = [
        "Hőmérséklet (°C)",
        "Termik (m/s)",
        "Alap (m QNH)",
        "Felhőzet (%)",
        "Páratartalom (%)",
        "Harmatpont (°C)",
        "Szélirány (°)",
        "Szél (km/h)"
    ]


    for column in numeric_columns:

        df_result[column] = pd.to_numeric(
            df_result[column],
            errors="coerce"
        )


    st.sidebar.success(
        "📡 Valós adatok sikeresen betöltve!"
    )


    return (
        df_result,
        base_wind_dir,
        base_wind_speed
    )


# ============================================================
# 6. IDŐJÁRÁSI ADATOK BETÖLTÉSE
# ============================================================

df, w_dir, w_spd = get_pure_live_weather(
    selected_field,
    day_offset
)


# ============================================================
# 7. KPI-K
# ============================================================

max_thermal = pd.to_numeric(
    df["Termik (m/s)"],
    errors="coerce"
).max()


max_cloud_base = pd.to_numeric(
    df["Alap (m QNH)"],
    errors="coerce"
).max()


if pd.isna(max_thermal):
    max_thermal = 0


if pd.isna(max_cloud_base):
    max_cloud_base = 0


col1, col2, col3, col4 = st.columns(4)


col1.metric(
    "Max Termik",
    f"{max_thermal:.1f} m/s"
)


col2.metric(
    "Max Felhőalap",
    f"{int(max_cloud_base):,} m QNH".replace(
        ",",
        " "
    )
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
# 8. ADATTÁBLÁZAT
# ============================================================

st.subheader(
    "Valós negyedórás előrejelzés: "
    f"{selected_field} "
    f"({target_date.strftime('%Y.%m.%d.')})"
)


# A belső technikai oszlopokat nem feltétlenül akarjuk
# megmutatni a fő táblázatban.

display_columns = [
    "Időpont",
    "Hőmérséklet (°C)",
    "Termik (m/s)",
    "Alap (m QNH)",
    "Felhőzet",
    "Szél",
    "Szélnyírás",
    "Túlfejlődés"
]


st.dataframe(
    df[display_columns],
    use_container_width=True,
    hide_index=True
)


# ============================================================
# 9. TERMIK GRAFIKON
# ============================================================

st.subheader(
    "Termik és Felhőalap napközbeni lefutása"
)


fig = go.Figure()


fig.add_trace(
    go.Scatter(
        x=df["Időpont"],
        y=df["Termik (m/s)"],
        name="Termik erősség (m/s)",
        yaxis="y1",
        mode="lines+markers",
        line=dict(
            color="orange",
            width=3
        )
    )
)


fig.add_trace(
    go.Scatter(
        x=df["Időpont"],
        y=df["Alap (m QNH)"],
        name="Felhőalap (m QNH)",
        yaxis="y2",
        mode="lines",
        line=dict(
            color="blue",
            width=2
        )
    )
)


fig.update_layout(
    height=500,

    xaxis=dict(
        title="Időpont",
        tickangle=-45
    ),

    yaxis=dict(
        title="Termik (m/s)",
        side="left",
        rangemode="tozero"
    ),

    yaxis2=dict(
        title="Felhőalap (m QNH)",
        side="right",
        overlaying="y",
        rangemode="tozero"
    ),

    hovermode="x unified",

    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="center",
        x=0.5
    ),

    margin=dict(
        l=60,
        r=70,
        t=70,
        b=80
    )
)


st.plotly_chart(
    fig,
    use_container_width=True
)


# ============================================================
# 10. SZÉL GRAFIKON
# ============================================================

st.subheader(
    "Szélsebesség és szélirány"
)


wind_fig = go.Figure()


wind_fig.add_trace(
    go.Scatter(
        x=df["Időpont"],
        y=df["Szél (km/h)"],
        name="Szélsebesség",
        mode="lines+markers",
        line=dict(
            color="green",
            width=3
        )
    )
)


wind_fig.update_layout(
    height=400,

    xaxis=dict(
        title="Időpont",
        tickangle=-45
    ),

    yaxis=dict(
        title="Szélsebesség (km/h)",
        rangemode="tozero"
    ),

    hovermode="x unified",

    margin=dict(
        l=60,
        r=40,
        t=30,
        b=80
    )
)


st.plotly_chart(
    wind_fig,
    use_container_width=True
)


# ============================================================
# 11. ÖSSZEFOGLALÓ
# ============================================================

st.subheader("📋 Repülési összefoglaló")


avg_temp = df[
    "Hőmérséklet (°C)"
].mean()


avg_wind = df[
    "Szél (km/h)"
].mean()


max_wind = df[
    "Szél (km/h)"
].max()


thermal_periods = df[
    df["Termik (m/s)"] > 0
]


if len(thermal_periods) > 0:

    thermal_start = thermal_periods.iloc[0]["Időpont"]
    thermal_end = thermal_periods.iloc[-1]["Időpont"]

    thermal_text = (
        f"{thermal_start} – "
        f"{thermal_end}"
    )

else:

    thermal_text = "Nem várható értékelhető termik"


summary_col1, summary_col2, summary_col3 = st.columns(3)


summary_col1.metric(
    "Átlaghőmérséklet",
    f"{avg_temp:.1f} °C"
)


summary_col2.metric(
    "Átlagos szél",
    f"{avg_wind:.1f} km/h"
)


summary_col3.metric(
    "Max. szélerősség",
    f"{int(max_wind)} km/h"
)


st.info(
    f"🛫 Becsült termikus időszak: "
    f"**{thermal_text}**"
)


# ============================================================
# 12. LÁBLÉC
# ============================================================

st.markdown("---")

st.caption(
    "Adatforrás: Open-Meteo • "
    "Az adatok előrejelzési célúak, és nem helyettesítik "
    "a hivatalos repülésmeteorológiai tájékoztatást."
)
