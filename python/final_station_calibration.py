# ============================================================
# AEROVISION INDIA
# FINAL STATION-AWARE CALIBRATION
#
# REAL DATA ONLY
#
# Calibration learning:
#   01 June 2026 -> 23 June 2026
#
# Evaluation / dashboard:
#   24 June 2026 -> 30 June 2026
#
# IMPORTANT:
# - Does NOT use validation CPCB values for calibration.
# - Does NOT change arbitrary-map predictions.
# - Does NOT fabricate pollutant measurements.
# - Missing CPCB values remain missing.
# ============================================================

from pathlib import Path
import json
import shutil
import warnings

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


# ============================================================
# PROJECT PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATASET = (
    ROOT
    / "data"
    / "processed"
    / "final_ml_dataset_v3.csv"
)
# ============================================================
# CORRECTED CPCB AQI REFERENCE
# ============================================================

CPCB_REFERENCE_FILE = (
    ROOT
    / "data"
    / "exports"
    / "cpcb_vs_aerovision_aqi_corrected.csv"
)
PRODUCTION_DIR = (
    ROOT
    / "models"
    / "production"
)

EXPORT_DIR = (
    ROOT
    / "data"
    / "exports"
)

EXPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# OUTPUTS
# ============================================================

CALIBRATION_FILE = (
    EXPORT_DIR
    / "station_calibration_final.csv"
)

COMPARISON_CSV = (
    EXPORT_DIR
    / "cpcb_vs_aerovision_station_calibrated.csv"
)

GEOJSON_FILE = (
    EXPORT_DIR
    / "cpcb_comparison.geojson"
)

BACKUP_GEOJSON = (
    EXPORT_DIR
    / "cpcb_comparison_before_station_calibration.geojson"
)

SUMMARY_FILE = (
    EXPORT_DIR
    / "station_calibration_final_summary.json"
)


# ============================================================
# MODEL FILES
# ============================================================

MODEL_FILES = {

    "PM25":
        PRODUCTION_DIR
        / "aerovision_PM25.joblib",

    "PM10":
        PRODUCTION_DIR
        / "aerovision_PM10.joblib",

    "NO2":
        PRODUCTION_DIR
        / "aerovision_NO2.joblib",

    "O3_8H":
        PRODUCTION_DIR
        / "aerovision_O3_8H.joblib",
}


# ============================================================
# EXACT V3 FEATURES
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

    "longitude",
]


# ============================================================
# CALIBRATION SETTINGS
# ============================================================

TRAIN_END = pd.Timestamp(
    "2026-06-23"
)

VALID_START = pd.Timestamp(
    "2026-06-24"
)


# 0 = no correction
# 1 = complete historical residual correction
#
# Earlier testing showed 1.0 gave best typical
# station performance.
#
# We add shrinkage based on sample count below.

CALIBRATION_STRENGTH = 1.0


# More history = more confidence in station correction.
#
# Station has ~23 training days.
#
# n/(n+4) gives around:
# 23/(23+4) = 0.85
#
# This prevents aggressive correction.

SHRINKAGE_K = 4.0


# Never allow one strange training residual to create
# an unlimited correction.
#
# Caps below are intentionally conservative and are based
# on realistic pollutant concentration units.

MAX_CORRECTION = {

    "PM25": 45.0,

    "PM10": 70.0,

    "NO2": 25.0,

    "O3_8H": 30.0,
}


# ============================================================
# LOAD DATA
# ============================================================

print()
print("=" * 70)
print("AEROVISION FINAL STATION CALIBRATION")
print("=" * 70)

print()
print("Loading:")
print(DATASET)


df = pd.read_csv(
    DATASET
)
# ============================================================
# MERGE OFFICIAL CPCB AQI REFERENCE
# ============================================================

print()
print("Loading corrected CPCB AQI reference:")
print(CPCB_REFERENCE_FILE)


if not CPCB_REFERENCE_FILE.exists():

    raise FileNotFoundError(
        f"Corrected CPCB reference not found: "
        f"{CPCB_REFERENCE_FILE}"
    )


reference = pd.read_csv(
    CPCB_REFERENCE_FILE
)


print(
    "Reference rows:",
    len(reference)
)


# ------------------------------------------------------------
# Make sure station_day_id exists
# ------------------------------------------------------------

if "station_day_id" not in df.columns:

    raise KeyError(
        "station_day_id missing from final_ml_dataset_v3.csv"
    )


if "station_day_id" not in reference.columns:

    raise KeyError(
        "station_day_id missing from corrected CPCB reference"
    )


# ------------------------------------------------------------
# Only import CPCB reference metadata.
#
# DO NOT import old AeroVision predictions because we are
# generating fresh predictions from the current V3 models.
# ------------------------------------------------------------

reference_columns = [
    "station_day_id",
    "CPCB_AQI",
    "CPCB_CATEGORY"
]


# Include corrected reference-quality fields when available.

optional_reference_columns = [

    "CPCB_REFERENCE_COUNT",

    "CPCB_REFERENCE_STATUS",

    "USE_FOR_FULL_AQI_VALIDATION"
]


for column in optional_reference_columns:

    if column in reference.columns:

        reference_columns.append(
            column
        )


reference = reference[
    reference_columns
].copy()


# ------------------------------------------------------------
# Avoid accidental duplicate station-day rows
# ------------------------------------------------------------

reference = reference.drop_duplicates(
    subset=["station_day_id"],
    keep="last"
)


# ------------------------------------------------------------
# Remove columns first if they somehow already exist
# ------------------------------------------------------------

columns_to_remove = [

    "CPCB_AQI",

    "CPCB_CATEGORY",

    "CPCB_REFERENCE_COUNT",

    "CPCB_REFERENCE_STATUS",

    "USE_FOR_FULL_AQI_VALIDATION"

]


for column in columns_to_remove:

    if column in df.columns:

        df = df.drop(
            columns=[column]
        )


# ------------------------------------------------------------
# Merge by exact station-day identifier
# ------------------------------------------------------------

df = df.merge(

    reference,

    on="station_day_id",

    how="left",

    validate="one_to_one"

)


print()
print("CPCB reference successfully merged.")


print(
    "Rows with CPCB AQI:",
    df["CPCB_AQI"].notna().sum()
)


if "CPCB_REFERENCE_STATUS" in df.columns:

    print(
        "Full CPCB reference:",
        (
            df[
                "CPCB_REFERENCE_STATUS"
            ] == "FULL"
        ).sum()
    )


    print(
        "Partial CPCB reference:",
        (
            df[
                "CPCB_REFERENCE_STATUS"
            ] == "PARTIAL"
        ).sum()
    )

# ============================================================
# DATE
# ============================================================

df["date"] = pd.to_datetime(
    df["date_text"],
    errors="coerce"
)


df = df[
    df["date"].notna()
].copy()


print()
print(
    "Dataset rows:",
    len(df)
)


print(
    "Stations:",
    df["station"].nunique()
)


print(
    "Period:",
    df["date"].min().date(),
    "->",
    df["date"].max().date()
)


# ============================================================
# TRAIN / VALIDATION SPLIT
# ============================================================

train = df[
    df["date"] <= TRAIN_END
].copy()


valid = df[
    df["date"] >= VALID_START
].copy()


print()
print(
    "Calibration learning rows:",
    len(train)
)


print(
    "Validation rows:",
    len(valid)
)


print(
    "Calibration period:",
    train["date"].min().date(),
    "->",
    train["date"].max().date()
)


print(
    "Validation period:",
    valid["date"].min().date(),
    "->",
    valid["date"].max().date()
)


# ============================================================
# LOAD MODELS
# ============================================================

models = {}


print()
print("Loading production V3 models...")


for target, path in MODEL_FILES.items():

    if not path.exists():

        raise FileNotFoundError(
            f"Missing model: {path}"
        )


    models[target] = joblib.load(
        path
    )


    print(
        "Loaded:",
        target,
        "->",
        path.name
    )


# ============================================================
# PREPARE FEATURES
# ============================================================

for feature in FEATURES:

    if feature not in df.columns:

        raise ValueError(
            f"Feature missing from dataset: {feature}"
        )


def prepare_features(frame):

    X = frame[
        FEATURES
    ].copy()


    for col in FEATURES:

        X[col] = pd.to_numeric(
            X[col],
            errors="coerce"
        )


    return X


# ============================================================
# RAW MODEL PREDICTIONS
# ============================================================

def add_raw_predictions(frame):

    result = frame.copy()

    X = prepare_features(
        result
    )


    for target, model in models.items():

        pred_col = (
            "RAW_PRED_"
            + target
        )


        predictions = model.predict(
            X
        )


        # Pollution cannot be negative.

        predictions = np.maximum(
            predictions,
            0
        )


        result[pred_col] = (
            predictions
        )


    return result


print()
print(
    "Generating raw predictions..."
)


train = add_raw_predictions(
    train
)


valid = add_raw_predictions(
    valid
)


# ============================================================
# LEARN STATION RESIDUALS
#
# residual =
# observed CPCB - AeroVision prediction
#
# Example:
#
# CPCB PM25 = 100
# model     = 80
#
# residual  = +20
#
# Model historically underpredicts by 20.
# ============================================================

calibration_rows = []


TARGETS = [
    "PM25",
    "PM10",
    "NO2",
    "O3_8H",
]


print()
print(
    "Learning historical station residuals..."
)


for station, station_data in train.groupby(
    "station"
):

    row = {
        "station": station
    }


    for target in TARGETS:

        actual = pd.to_numeric(
            station_data[target],
            errors="coerce"
        )


        predicted = pd.to_numeric(
            station_data[
                "RAW_PRED_" + target
            ],
            errors="coerce"
        )


        mask = (
            actual.notna()
            &
            predicted.notna()
        )


        residuals = (
            actual[mask]
            -
            predicted[mask]
        )


        n = len(
            residuals
        )


        if n == 0:

            median_residual = 0.0
            mean_residual = 0.0
            mad = 0.0

        else:

            median_residual = float(
                residuals.median()
            )


            mean_residual = float(
                residuals.mean()
            )


            mad = float(

                np.median(

                    np.abs(

                        residuals
                        -
                        median_residual

                    )

                )

            )


        # --------------------------------------------
        # ROBUST SHRINKAGE
        # --------------------------------------------

        shrinkage = (

            n
            /
            (
                n
                +
                SHRINKAGE_K
            )

            if n > 0

            else 0.0

        )


        correction = (

            median_residual

            *
            shrinkage

            *
            CALIBRATION_STRENGTH

        )


        # --------------------------------------------
        # SAFETY CAP
        # --------------------------------------------

        cap = MAX_CORRECTION[
            target
        ]


        correction = float(

            np.clip(
                correction,
                -cap,
                cap
            )

        )


        row[
            target
            + "_N"
        ] = n


        row[
            target
            + "_MEDIAN_RESIDUAL"
        ] = median_residual


        row[
            target
            + "_MEAN_RESIDUAL"
        ] = mean_residual


        row[
            target
            + "_MAD"
        ] = mad


        row[
            target
            + "_SHRINKAGE"
        ] = shrinkage


        row[
            target
            + "_CORRECTION"
        ] = correction


    calibration_rows.append(
        row
    )


calibration = pd.DataFrame(
    calibration_rows
)


calibration.to_csv(
    CALIBRATION_FILE,
    index=False
)


print()
print(
    "Calibration file saved:"
)

print(
    CALIBRATION_FILE
)


# ============================================================
# APPLY CALIBRATION
# ============================================================

valid = valid.merge(

    calibration,

    on="station",

    how="left"

)


for target in TARGETS:

    raw_col = (
        "RAW_PRED_"
        + target
    )


    correction_col = (
        target
        + "_CORRECTION"
    )


    output_col = (
        "PRED_"
        + target
    )


    valid[
        correction_col
    ] = pd.to_numeric(

        valid[
            correction_col
        ],

        errors="coerce"

    ).fillna(
        0.0
    )


    valid[
        output_col
    ] = (

        valid[
            raw_col
        ]

        +

        valid[
            correction_col
        ]

    )


    valid[
        output_col
    ] = np.maximum(

        valid[
            output_col
        ],

        0

    )


# ============================================================
# CPCB AQI FUNCTIONS
# ============================================================

def interpolate_subindex(
    concentration,
    breakpoints
):

    if pd.isna(
        concentration
    ):

        return np.nan


    c = float(
        concentration
    )


    if c < 0:

        c = 0.0


    for (
        bp_low,
        bp_high,
        index_low,
        index_high
    ) in breakpoints:


        if (
            c >= bp_low
            and
            c <= bp_high
        ):


            if (
                bp_high
                ==
                bp_low
            ):

                return float(
                    index_high
                )


            value = (

                (
                    index_high
                    -
                    index_low
                )

                /

                (
                    bp_high
                    -
                    bp_low
                )

                *

                (
                    c
                    -
                    bp_low
                )

                +

                index_low

            )


            return float(
                value
            )


    # Above highest concentration:
    # extend last CPCB band but cap AQI at 500.

    (
        bp_low,
        bp_high,
        index_low,
        index_high

    ) = breakpoints[-1]


    value = (

        (
            index_high
            -
            index_low
        )

        /

        (
            bp_high
            -
            bp_low
        )

        *

        (
            c
            -
            bp_low
        )

        +

        index_low

    )


    return float(

        min(
            500,
            value
        )

    )


# ============================================================
# CPCB BREAKPOINTS
# ============================================================

PM25_BREAKPOINTS = [

    (0, 30, 0, 50),

    (30, 60, 50, 100),

    (60, 90, 100, 200),

    (90, 120, 200, 300),

    (120, 250, 300, 400),

    (250, 500, 400, 500),
]


PM10_BREAKPOINTS = [

    (0, 50, 0, 50),

    (50, 100, 50, 100),

    (100, 250, 100, 200),

    (250, 350, 200, 300),

    (350, 430, 300, 400),

    (430, 600, 400, 500),
]


NO2_BREAKPOINTS = [

    (0, 40, 0, 50),

    (40, 80, 50, 100),

    (80, 180, 100, 200),

    (180, 280, 200, 300),

    (280, 400, 300, 400),

    (400, 800, 400, 500),
]


O3_BREAKPOINTS = [

    (0, 50, 0, 50),

    (50, 100, 50, 100),

    (100, 168, 100, 200),

    (168, 208, 200, 300),

    (208, 748, 300, 400),

    (748, 1000, 400, 500),
]


# ============================================================
# AQI CATEGORY
# ============================================================

def aqi_category(aqi):

    if pd.isna(
        aqi
    ):

        return "N/A"


    if aqi <= 50:

        return "Good"


    if aqi <= 100:

        return "Satisfactory"


    if aqi <= 200:

        return "Moderate"


    if aqi <= 300:

        return "Poor"


    if aqi <= 400:

        return "Very Poor"


    return "Severe"


# ============================================================
# CALCULATE CALIBRATED AQI
# ============================================================

def calculate_aqi(row):

    subindices = {}


    subindices[
        "PM25"
    ] = interpolate_subindex(

        row[
            "PRED_PM25"
        ],

        PM25_BREAKPOINTS

    )


    subindices[
        "PM10"
    ] = interpolate_subindex(

        row[
            "PRED_PM10"
        ],

        PM10_BREAKPOINTS

    )


    subindices[
        "NO2"
    ] = interpolate_subindex(

        row[
            "PRED_NO2"
        ],

        NO2_BREAKPOINTS

    )


    subindices[
        "O3_8H"
    ] = interpolate_subindex(

        row[
            "PRED_O3_8H"
        ],

        O3_BREAKPOINTS

    )


    valid_subindices = {

        pollutant:
            value

        for pollutant, value
        in subindices.items()

        if not pd.isna(
            value
        )

    }


    if not valid_subindices:

        return pd.Series(
            {
                "AEROVISION_AQI":
                    np.nan,

                "AEROVISION_CATEGORY":
                    "N/A",

                "AEROVISION_DOMINANT":
                    "N/A"
            }
        )


    dominant = max(

        valid_subindices,

        key=
            valid_subindices.get

    )


    aqi = max(

        valid_subindices.values()

    )


    return pd.Series(

        {

            "AEROVISION_AQI":
                aqi,

            "AEROVISION_CATEGORY":
                aqi_category(
                    aqi
                ),

            "AEROVISION_DOMINANT":
                dominant

        }

    )


aqi_results = valid.apply(

    calculate_aqi,

    axis=1

)


valid[
    [
        "AEROVISION_AQI",
        "AEROVISION_CATEGORY",
        "AEROVISION_DOMINANT"
    ]
] = aqi_results


# ============================================================
# CPCB REFERENCE STATUS
# ============================================================
# Prefer the status already produced by the corrected CPCB
# validation pipeline. Only calculate it here as a fallback.
# ============================================================

if "CPCB_REFERENCE_COUNT" not in valid.columns:

    pollutant_reference_columns = [
        "PM25",
        "PM10",
        "NO2",
        "O3_8H"
    ]


    valid[
        "CPCB_REFERENCE_COUNT"
    ] = valid[
        pollutant_reference_columns
    ].notna().sum(
        axis=1
    )


if "CPCB_REFERENCE_STATUS" not in valid.columns:

    valid[
        "CPCB_REFERENCE_STATUS"
    ] = np.where(

        valid[
            "CPCB_REFERENCE_COUNT"
        ] == 4,

        "FULL",

        "PARTIAL"

    )


if "USE_FOR_FULL_AQI_VALIDATION" not in valid.columns:

    valid[
        "USE_FOR_FULL_AQI_VALIDATION"
    ] = (

        valid[
            "CPCB_REFERENCE_COUNT"
        ] == 4

    )


# Convert possible CSV strings to real booleans.

if (
    valid[
        "USE_FOR_FULL_AQI_VALIDATION"
    ].dtype == object
):

    valid[
        "USE_FOR_FULL_AQI_VALIDATION"
    ] = (

        valid[
            "USE_FOR_FULL_AQI_VALIDATION"
        ]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(
            [
                "true",
                "1",
                "yes"
            ]
        )

    )


# ============================================================
# AQI DIFFERENCE
# ============================================================

valid[
    "AQI_DIFFERENCE"
] = (

    valid[
        "AEROVISION_AQI"
    ]

    -

    valid[
        "CPCB_AQI"
    ]

)


valid[
    "AQI_ABS_ERROR"
] = valid[
    "AQI_DIFFERENCE"
].abs()


valid[
    "ABS_ERROR"
] = valid[
    "AQI_ABS_ERROR"
]


# ============================================================
# MARK CALIBRATION MODE
# ============================================================

valid[
    "PREDICTION_MODE"
] = (
    "V3 + historical station bias calibration"
)


valid[
    "CALIBRATION_TRAIN_END"
] = (
    "2026-06-23"
)


# ============================================================
# SAVE CSV
# ============================================================

valid.to_csv(

    COMPARISON_CSV,

    index=False

)


print()
print(
    "Calibrated comparison saved:"
)

print(
    COMPARISON_CSV
)


# ============================================================
# BACK UP OLD GEOJSON
# ============================================================

if GEOJSON_FILE.exists():

    shutil.copy2(

        GEOJSON_FILE,

        BACKUP_GEOJSON

    )


    print()
    print(
        "Existing GeoJSON backed up:"
    )

    print(
        BACKUP_GEOJSON
    )


# ============================================================
# CREATE GEOJSON
# ============================================================

features = []


def json_safe(value):

    if value is None:

        return None


    if isinstance(
        value,
        (
            np.integer,
            np.int64,
            np.int32
        )
    ):

        return int(
            value
        )


    if isinstance(
        value,
        (
            np.floating,
            np.float64,
            np.float32
        )
    ):

        if np.isnan(
            value
        ):

            return None

        return float(
            value
        )


    if isinstance(
        value,
        pd.Timestamp
    ):

        return value.strftime(
            "%Y-%m-%d"
        )


    if pd.isna(
        value
    ):

        return None


    return value


for _, row in valid.iterrows():

    latitude = json_safe(
        row.get(
            "latitude"
        )
    )


    longitude = json_safe(
        row.get(
            "longitude"
        )
    )


    if (
        latitude is None
        or
        longitude is None
    ):

        continue


    properties = {}


    for column in valid.columns:

        if column == "date":

            continue


        properties[
            column
        ] = json_safe(
            row[
                column
            ]
        )


    feature = {

        "type":
            "Feature",

        "geometry":
        {

            "type":
                "Point",

            "coordinates":
            [
                longitude,
                latitude
            ]

        },

        "properties":
            properties

    }


    features.append(
        feature
    )


geojson = {

    "type":
        "FeatureCollection",

    "features":
        features

}


with open(
    GEOJSON_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(

        geojson,

        file,

        ensure_ascii=False,

        indent=2

    )


print()
print(
    "Dashboard GeoJSON updated:"
)

print(
    GEOJSON_FILE
)


print(
    "GeoJSON features:",
    len(features)
)


# ============================================================
# VALIDATION METRICS
# FULL CPCB REFERENCES ONLY
# ============================================================

evaluation = valid[

    valid[
        "USE_FOR_FULL_AQI_VALIDATION"
    ]

    &

    valid[
        "CPCB_AQI"
    ].notna()

    &

    valid[
        "AEROVISION_AQI"
    ].notna()

].copy()


errors = evaluation[
    "AQI_ABS_ERROR"
]


mae = float(
    errors.mean()
)


median_error = float(
    errors.median()
)


rmse = float(

    np.sqrt(

        np.mean(

            np.square(

                evaluation[
                    "AEROVISION_AQI"
                ]

                -

                evaluation[
                    "CPCB_AQI"
                ]

            )

        )

    )

)


gt25 = int(
    (
        errors > 25
    ).sum()
)


gt50 = int(
    (
        errors > 50
    ).sum()
)


gt75 = int(
    (
        errors > 75
    ).sum()
)


gt100 = int(
    (
        errors > 100
    ).sum()
)


max_error = float(
    errors.max()
)


category_agreement = float(

    (

        evaluation[
            "CPCB_CATEGORY"
        ]

        ==

        evaluation[
            "AEROVISION_CATEGORY"
        ]

    ).mean()

    *

    100

)


# ============================================================
# PRINT METRICS
# ============================================================

print()
print("=" * 70)
print("FINAL CALIBRATED VALIDATION")
print("=" * 70)


print(
    "Full CPCB reference rows :",
    len(evaluation)
)


print(
    "AQI MAE                  :",
    round(
        mae,
        2
    )
)


print(
    "Median absolute error    :",
    round(
        median_error,
        2
    )
)


print(
    "AQI RMSE                 :",
    round(
        rmse,
        2
    )
)


print(
    "> 25 AQI errors          :",
    gt25
)


print(
    "> 50 AQI errors          :",
    gt50
)


print(
    "> 75 AQI errors          :",
    gt75
)


print(
    "> 100 AQI errors         :",
    gt100
)


print(
    "Maximum error            :",
    round(
        max_error,
        2
    )
)


print(
    "Category agreement       :",
    round(
        category_agreement,
        2
    ),
    "%"
)


# ============================================================
# WORST CASES
# ============================================================

print()
print("=" * 70)
print("TOP 10 REMAINING AQI ERRORS")
print("=" * 70)


columns_to_show = [

    "station",

    "date_text",

    "CPCB_AQI",

    "AEROVISION_AQI",

    "AQI_ABS_ERROR",

    "PM25",

    "PRED_PM25",

    "PM10",

    "PRED_PM10",

]


worst = evaluation.sort_values(

    "AQI_ABS_ERROR",

    ascending=False

).head(
    10
)


print(

    worst[
        columns_to_show
    ].to_string(
        index=False
    )

)


# ============================================================
# SAVE SUMMARY
# ============================================================

summary = {

    "mode":
        "V3 + historical station bias calibration",

    "calibration_period":
        "2026-06-01 to 2026-06-23",

    "validation_period":
        "2026-06-24 to 2026-06-30",

    "full_reference_rows":
        int(
            len(
                evaluation
            )
        ),

    "aqi_mae":
        mae,

    "median_absolute_error":
        median_error,

    "aqi_rmse":
        rmse,

    "errors_gt_25":
        gt25,

    "errors_gt_50":
        gt50,

    "errors_gt_75":
        gt75,

    "errors_gt_100":
        gt100,

    "maximum_error":
        max_error,

    "category_agreement_percent":
        category_agreement,

    "scientific_note":
        (
            "Station calibration uses only historical "
            "June 1-23 station residuals. "
            "No June 24-30 CPCB measurement is used "
            "to calculate its corresponding prediction."
        )

}


with open(

    SUMMARY_FILE,

    "w",

    encoding="utf-8"

) as file:

    json.dump(

        summary,

        file,

        indent=2

    )


print()
print(
    "Summary saved:"
)

print(
    SUMMARY_FILE
)


print()
print("=" * 70)
print("DONE")
print("=" * 70)

print()
print(
    "Restart Flask and hard-refresh the browser."
)

print(
    "CPCB station markers now use the calibrated "
    "station comparison GeoJSON."
)

print(
    "Random map clicks continue using the pure V3 "
    "Earth Engine prediction endpoint."
)

print()