import os
import json
import math

import joblib
import numpy as np
import pandas as pd


# ============================================================
# AEROVISION INDIA
# PREPARE REAL JUNE 2026 DASHBOARD DATA
#
# INPUT:
#   data/processed/final_ml_dataset_v3.csv
#
# OUTPUT:
#   data/exports/dashboard_june_2026.json
#
# NO SIMULATION
# NO MANUAL VALUE INSERTION
# ============================================================


BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

ROOT = os.path.dirname(
    BASE_DIR
)

DATASET_PATH = os.path.join(
    ROOT,
    "data",
    "processed",
    "final_ml_dataset_v3.csv"
)

MODEL_DIR = os.path.join(
    ROOT,
    "models",
    "production"
)

OUTPUT_PATH = os.path.join(
    ROOT,
    "data",
    "exports",
    "dashboard_june_2026.json"
)


MODEL_PATHS = {

    "PM25": os.path.join(
        MODEL_DIR,
        "aerovision_PM25.joblib"
    ),

    "PM10": os.path.join(
        MODEL_DIR,
        "aerovision_PM10.joblib"
    ),

    "NO2": os.path.join(
        MODEL_DIR,
        "aerovision_NO2.joblib"
    ),

    "O3_8H": os.path.join(
        MODEL_DIR,
        "aerovision_O3_8H.joblib"
    )

}


# ============================================================
# FEATURES USED BY V3
# ============================================================

FEATURES = [

    "AOD",

    "ERA5_DEWPOINT",

    "ERA5_RH",

    "ERA5_TEMP",

    "HCHO",

    "SAT_NO2",

    "WIND_SPEED",

    "WIND_U",

    "WIND_V",

    "FIRE_COUNT_25KM",

    "FIRE_CONF_MAX_25KM",

    "FIRE_T21_MAX_25KM",

    "latitude",

    "longitude"

]


# ============================================================
# AQI BREAKPOINTS
# ============================================================

PM25_BREAKPOINTS = [

    (0, 30, 0, 50),

    (30, 60, 50, 100),

    (60, 90, 100, 200),

    (90, 120, 200, 300),

    (120, 250, 300, 400),

    (250, 500, 400, 500)

]


PM10_BREAKPOINTS = [

    (0, 50, 0, 50),

    (50, 100, 50, 100),

    (100, 250, 100, 200),

    (250, 350, 200, 300),

    (350, 430, 300, 400),

    (430, 600, 400, 500)

]


NO2_BREAKPOINTS = [

    (0, 40, 0, 50),

    (40, 80, 50, 100),

    (80, 180, 100, 200),

    (180, 280, 200, 300),

    (280, 400, 300, 400),

    (400, 800, 400, 500)

]


O3_BREAKPOINTS = [

    (0, 50, 0, 50),

    (50, 100, 50, 100),

    (100, 168, 100, 200),

    (168, 208, 200, 300),

    (208, 748, 300, 400),

    (748, 1000, 400, 500)

]


# ============================================================
# HELPERS
# ============================================================

def number_or_none(value):

    if value is None:

        return None

    try:

        value = float(value)

        if not math.isfinite(value):

            return None

        return value

    except Exception:

        return None


def clean_json_number(
    value,
    digits=6
):

    value = number_or_none(
        value
    )

    if value is None:

        return None

    return round(
        value,
        digits
    )


def pollutant_subindex(
    concentration,
    breakpoints
):

    concentration = number_or_none(
        concentration
    )

    if concentration is None:

        return None

    concentration = max(
        0,
        concentration
    )


    for (
        c_low,
        c_high,
        i_low,
        i_high
    ) in breakpoints:

        if c_low <= concentration <= c_high:

            return (

                (
                    i_high -
                    i_low
                )

                /

                (
                    c_high -
                    c_low
                )

                *

                (
                    concentration -
                    c_low
                )

                +

                i_low

            )


    return 500.0


def aqi_category(
    value
):

    if value is None:

        return "N/A"

    if value <= 50:

        return "Good"

    if value <= 100:

        return "Satisfactory"

    if value <= 200:

        return "Moderate"

    if value <= 300:

        return "Poor"

    if value <= 400:

        return "Very Poor"

    return "Severe"


def calculate_aqi(
    pm25,
    pm10,
    no2,
    o3
):

    values = {

        "PM2.5":
            pollutant_subindex(
                pm25,
                PM25_BREAKPOINTS
            ),

        "PM10":
            pollutant_subindex(
                pm10,
                PM10_BREAKPOINTS
            ),

        "NO2":
            pollutant_subindex(
                no2,
                NO2_BREAKPOINTS
            ),

        "O3":
            pollutant_subindex(
                o3,
                O3_BREAKPOINTS
            )

    }


    valid = {

        key: value

        for key, value in values.items()

        if value is not None

    }


    if not valid:

        return (
            None,
            "N/A",
            "N/A"
        )


    dominant = max(
        valid,
        key=valid.get
    )


    aqi = valid[
        dominant
    ]


    return (

        round(
            aqi,
            1
        ),

        aqi_category(
            aqi
        ),

        dominant

    )


# ============================================================
# LOAD DATASET
# ============================================================

print()
print("=" * 65)
print("AEROVISION JUNE DASHBOARD PREPARATION")
print("=" * 65)

print()
print(
    "Reading:",
    DATASET_PATH
)


df = pd.read_csv(
    DATASET_PATH
)


print(
    "Rows:",
    len(df)
)


# ============================================================
# NORMALIZE DATE
# ============================================================

if "sample_date" in df.columns:

    df["date"] = pd.to_datetime(
        df["sample_date"]
    )

elif "date_text" in df.columns:

    df["date"] = pd.to_datetime(
        df["date_text"]
    )

else:

    raise RuntimeError(
        "No sample_date/date_text column found."
    )


# June 2026 only

df = df[
    (
        df["date"] >=
        "2026-06-01"
    )
    &
    (
        df["date"] <=
        "2026-06-30"
    )
].copy()


df["date_text"] = (
    df["date"]
    .dt.strftime(
        "%Y-%m-%d"
    )
)


print(
    "June rows:",
    len(df)
)


# ============================================================
# LOAD MODELS
# ============================================================

models = {}


for target, path in MODEL_PATHS.items():

    print(
        "Loading:",
        target
    )

    if not os.path.exists(path):

        raise FileNotFoundError(
            path
        )

    models[target] = joblib.load(
        path
    )


# ============================================================
# MODEL INPUT
# ============================================================

for feature in FEATURES:

    if feature not in df.columns:

        raise RuntimeError(
            f"Missing required feature: {feature}"
        )


X = df[
    FEATURES
].copy()


# Keep true missing values as NaN.
# XGBoost can handle missing feature values.

for column in FEATURES:

    X[column] = pd.to_numeric(
        X[column],
        errors="coerce"
    )


# ============================================================
# PREDICT ALL REAL STATION-DAYS
# ============================================================

print()
print(
    "Running AeroVision V3 predictions..."
)


df[
    "PRED_PM25"
] = np.maximum(

    0,

    models[
        "PM25"
    ].predict(
        X
    )

)


df[
    "PRED_PM10"
] = np.maximum(

    0,

    models[
        "PM10"
    ].predict(
        X
    )

)


df[
    "PRED_NO2"
] = np.maximum(

    0,

    models[
        "NO2"
    ].predict(
        X
    )

)


df[
    "PRED_O3_8H"
] = np.maximum(

    0,

    models[
        "O3_8H"
    ].predict(
        X
    )

)


# ============================================================
# CALCULATE CPCB + AEROVISION AQI
# ============================================================

records = []


for _, row in df.iterrows():

    # --------------------------------------------------------
    # REAL CPCB AQI
    # --------------------------------------------------------

    cpcb_aqi, cpcb_category, cpcb_dominant = calculate_aqi(

        row.get(
            "PM25"
        ),

        row.get(
            "PM10"
        ),

        row.get(
            "NO2"
        ),

        row.get(
            "O3_8H"
        )

    )


    # --------------------------------------------------------
    # AEROVISION AQI
    # --------------------------------------------------------

    aero_aqi, aero_category, aero_dominant = calculate_aqi(

        row.get(
            "PRED_PM25"
        ),

        row.get(
            "PRED_PM10"
        ),

        row.get(
            "PRED_NO2"
        ),

        row.get(
            "PRED_O3_8H"
        )

    )


    # --------------------------------------------------------
    # CPCB REFERENCE COMPLETENESS
    # --------------------------------------------------------

    cpcb_values = [

        number_or_none(
            row.get(
                "PM25"
            )
        ),

        number_or_none(
            row.get(
                "PM10"
            )
        ),

        number_or_none(
            row.get(
                "NO2"
            )
        ),

        number_or_none(
            row.get(
                "O3_8H"
            )
        )

    ]


    valid_count = sum(

        value is not None

        for value in cpcb_values

    )


    reference_status = (

        "FULL"

        if valid_count == 4

        else

        "PARTIAL"

    )


    # --------------------------------------------------------
    # VALIDATION PERIOD LABEL
    # --------------------------------------------------------

    date_value = row[
        "date"
    ]


    validation_status = (

        "HELD_OUT_VALIDATION"

        if date_value >= pd.Timestamp(
            "2026-06-24"
        )

        else

        "TRAINING_PERIOD_ESTIMATE"

    )


    record = {

        "station":
            str(
                row.get(
                    "station",
                    ""
                )
            ),

        "city":
            str(
                row.get(
                    "city",
                    ""
                )
            ),

        "state":
            str(
                row.get(
                    "state",
                    ""
                )
            ),

        "date":
            row[
                "date_text"
            ],

        "day":
            int(
                date_value.day
            ),


        # ----------------------------------------------------
        # LOCATION
        # ----------------------------------------------------

        "latitude":
            clean_json_number(
                row.get(
                    "latitude"
                ),
                6
            ),

        "longitude":
            clean_json_number(
                row.get(
                    "longitude"
                ),
                6
            ),


        # ----------------------------------------------------
        # REAL CPCB
        # ----------------------------------------------------

        "PM25":
            clean_json_number(
                row.get(
                    "PM25"
                ),
                1
            ),

        "PM10":
            clean_json_number(
                row.get(
                    "PM10"
                ),
                1
            ),

        "NO2":
            clean_json_number(
                row.get(
                    "NO2"
                ),
                1
            ),

        "O3_8H":
            clean_json_number(
                row.get(
                    "O3_8H"
                ),
                1
            ),

        "CPCB_AQI":
            clean_json_number(
                cpcb_aqi,
                1
            ),

        "CPCB_CATEGORY":
            cpcb_category,

        "CPCB_DOMINANT":
            cpcb_dominant,

        "CPCB_REFERENCE_STATUS":
            reference_status,

        "CPCB_VALID_POLLUTANTS":
            valid_count,


        # ----------------------------------------------------
        # AEROVISION MODEL OUTPUT
        # ----------------------------------------------------

        "PRED_PM25":
            clean_json_number(
                row.get(
                    "PRED_PM25"
                ),
                1
            ),

        "PRED_PM10":
            clean_json_number(
                row.get(
                    "PRED_PM10"
                ),
                1
            ),

        "PRED_NO2":
            clean_json_number(
                row.get(
                    "PRED_NO2"
                ),
                1
            ),

        "PRED_O3_8H":
            clean_json_number(
                row.get(
                    "PRED_O3_8H"
                ),
                1
            ),

        "AEROVISION_AQI":
            clean_json_number(
                aero_aqi,
                1
            ),

        "AEROVISION_CATEGORY":
            aero_category,

        "AEROVISION_DOMINANT":
            aero_dominant,


        # ----------------------------------------------------
        # REAL SATELLITE
        # ----------------------------------------------------

        "AOD":
            clean_json_number(
                row.get(
                    "AOD"
                ),
                6
            ),

        "HCHO":
            clean_json_number(
                row.get(
                    "HCHO"
                ),
                8
            ),

        "SAT_NO2":
            clean_json_number(
                row.get(
                    "SAT_NO2"
                ),
                8
            ),


        # ----------------------------------------------------
        # REAL ERA5
        # ----------------------------------------------------

        "ERA5_TEMP":
            clean_json_number(
                row.get(
                    "ERA5_TEMP"
                ),
                2
            ),

        "ERA5_DEWPOINT":
            clean_json_number(
                row.get(
                    "ERA5_DEWPOINT"
                ),
                2
            ),

        "ERA5_RH":
            clean_json_number(
                row.get(
                    "ERA5_RH"
                ),
                2
            ),

        "WIND_SPEED":
            clean_json_number(
                row.get(
                    "WIND_SPEED"
                ),
                3
            ),

        "WIND_U":
            clean_json_number(
                row.get(
                    "WIND_U"
                ),
                3
            ),

        "WIND_V":
            clean_json_number(
                row.get(
                    "WIND_V"
                ),
                3
            ),


        # ----------------------------------------------------
        # REAL FIRMS
        # ----------------------------------------------------

        "FIRE_COUNT_25KM":
            clean_json_number(
                row.get(
                    "FIRE_COUNT_25KM"
                ),
                0
            ),

        "FIRE_CONF_MAX_25KM":
            clean_json_number(
                row.get(
                    "FIRE_CONF_MAX_25KM"
                ),
                1
            ),

        "FIRE_T21_MAX_25KM":
            clean_json_number(
                row.get(
                    "FIRE_T21_MAX_25KM"
                ),
                2
            ),


        # ----------------------------------------------------
        # SCIENTIFIC STATUS
        # ----------------------------------------------------

        "model_period":
            validation_status

    }


    # Only calculate a comparison difference when the
    # CPCB reference is complete.

    if (
        reference_status == "FULL"
        and
        cpcb_aqi is not None
        and
        aero_aqi is not None
    ):

        record[
            "AQI_ERROR"
        ] = round(

            abs(
                aero_aqi -
                cpcb_aqi
            ),

            1

        )

    else:

        record[
            "AQI_ERROR"
        ] = None


    records.append(
        record
    )


# ============================================================
# SORT
# ============================================================

records.sort(

    key=lambda item: (

        item[
            "station"
        ],

        item[
            "date"
        ]

    )

)


# ============================================================
# STATION LIST
# ============================================================

stations = sorted(

    list({

        item[
            "station"
        ]

        for item in records

        if item[
            "station"
        ]

    })

)


# ============================================================
# DATE LIST
# ============================================================

dates = [

    f"2026-06-{day:02d}"

    for day in range(
        1,
        31
    )

]


# ============================================================
# OUTPUT
# ============================================================

output = {

    "dataset":
        "AeroVision June 2026 real station-day dashboard",

    "data_policy":
        "Real CPCB, satellite, ERA5 and FIRMS inputs only",

    "date_start":
        "2026-06-01",

    "date_end":
        "2026-06-30",

    "dates":
        dates,

    "stations":
        stations,

    "record_count":
        len(
            records
        ),

    "records":
        records

}


os.makedirs(

    os.path.dirname(
        OUTPUT_PATH
    ),

    exist_ok=True

)


with open(
    OUTPUT_PATH,
    "w",
    encoding="utf-8"
) as file:

    json.dump(

        output,

        file,

        indent=2,

        allow_nan=False

    )


print()
print(
    "Saved:"
)

print(
    OUTPUT_PATH
)

print()
print(
    "Stations:",
    len(
        stations
    )
)

print(
    "Records:",
    len(
        records
    )
)

print(
    "Dates:",
    dates[
        0
    ],
    "to",
    dates[
        -1
    ]
)

print()
print(
    "DONE"
)