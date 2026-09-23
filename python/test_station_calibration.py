from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATASET_FILE = (
    ROOT
    / "data"
    / "processed"
    / "final_ml_dataset_v3.csv"
)

VALIDATION_FILE = (
    ROOT
    / "data"
    / "exports"
    / "v3_best_validation_predictions.csv"
)

MODEL_DIR = (
    ROOT
    / "models"
    / "production"
)

OUTPUT_FILE = (
    ROOT
    / "data"
    / "exports"
    / "station_calibration_experiments.csv"
)

BEST_FILE = (
    ROOT
    / "data"
    / "exports"
    / "station_calibrated_validation.csv"
)


# ============================================================
# FEATURE LIST
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


TARGETS = [
    "PM25",
    "PM10",
    "NO2",
    "O3_8H",
]


# ============================================================
# CPCB AQI BREAKPOINTS
# ============================================================

BREAKPOINTS = {

    "PM25": [
        (0, 30, 0, 50),
        (30, 60, 51, 100),
        (60, 90, 101, 200),
        (90, 120, 201, 300),
        (120, 250, 301, 400),
        (250, 1000, 401, 500),
    ],

    "PM10": [
        (0, 50, 0, 50),
        (50, 100, 51, 100),
        (100, 250, 101, 200),
        (250, 350, 201, 300),
        (350, 430, 301, 400),
        (430, 2000, 401, 500),
    ],

    "NO2": [
        (0, 40, 0, 50),
        (40, 80, 51, 100),
        (80, 180, 101, 200),
        (180, 280, 201, 300),
        (280, 400, 301, 400),
        (400, 2000, 401, 500),
    ],

    "O3_8H": [
        (0, 50, 0, 50),
        (50, 100, 51, 100),
        (100, 168, 101, 200),
        (168, 208, 201, 300),
        (208, 748, 301, 400),
        (748, 2000, 401, 500),
    ],
}


# ============================================================
# AQI FUNCTIONS
# ============================================================

def subindex(value, pollutant):

    if pd.isna(value):
        return np.nan

    value = max(0.0, float(value))

    for c_low, c_high, i_low, i_high in BREAKPOINTS[pollutant]:

        if value <= c_high:

            return (
                i_low
                +
                ((i_high - i_low)
                 * (value - c_low)
                 / (c_high - c_low))
            )

    return 500.0


def calculate_aqi(pm25, pm10, no2, o3):

    values = [
        subindex(pm25, "PM25"),
        subindex(pm10, "PM10"),
        subindex(no2, "NO2"),
        subindex(o3, "O3_8H"),
    ]

    values = [
        x for x in values
        if not pd.isna(x)
    ]

    if not values:
        return np.nan

    return max(values)


def category(aqi):

    if pd.isna(aqi):
        return "Unknown"

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
# CHECK FILES
# ============================================================

if not DATASET_FILE.exists():
    raise FileNotFoundError(DATASET_FILE)

if not VALIDATION_FILE.exists():
    raise FileNotFoundError(VALIDATION_FILE)


# ============================================================
# LOAD DATA
# ============================================================

print()
print("=" * 72)
print("AEROVISION STATION-AWARE CALIBRATION TEST")
print("=" * 72)

df = pd.read_csv(DATASET_FILE)

df["date"] = pd.to_datetime(
    df["date_text"]
)

validation = pd.read_csv(
    VALIDATION_FILE
)


# ============================================================
# TRAINING DATA ONLY
#
# Absolutely no June 24-30 CPCB values are used for calibration.
# ============================================================

train = df[
    df["date"] <= pd.Timestamp("2026-06-23")
].copy()


print(
    f"Calibration learning rows : {len(train)}"
)

print(
    "Calibration period        : "
    "2026-06-01 → 2026-06-23"
)

print(
    f"Validation rows            : {len(validation)}"
)

print(
    "Validation period         : "
    "2026-06-24 → 2026-06-30"
)


# ============================================================
# LOAD V3 MODELS
# ============================================================

MODEL_FILES = {

    "PM25":
        MODEL_DIR
        / "aerovision_PM25.joblib",

    "PM10":
        MODEL_DIR
        / "aerovision_PM10.joblib",

    "NO2":
        MODEL_DIR
        / "aerovision_NO2.joblib",

    "O3_8H":
        MODEL_DIR
        / "aerovision_O3_8H.joblib",
}


models = {}

for target, path in MODEL_FILES.items():

    if not path.exists():

        raise FileNotFoundError(
            f"Missing model: {path}"
        )

    models[target] = joblib.load(path)


# ============================================================
# GENERATE TRAINING PREDICTIONS
#
# These predictions are ONLY used to calculate historical
# station residual behaviour.
# ============================================================

for target in TARGETS:

    model = models[target]

    train[
        f"BASE_PRED_{target}"
    ] = np.maximum(

        model.predict(
            train[FEATURES]
        ),

        0
    )


# ============================================================
# CALCULATE REAL HISTORICAL STATION RESIDUALS
#
# residual = CPCB - XGBoost
#
# Positive residual:
# model historically underpredicts station
#
# Negative residual:
# model historically overpredicts station
# ============================================================

station_bias = {}


for target in TARGETS:

    valid = train[
        train[target].notna()
    ].copy()

    valid[
        "RESIDUAL"
    ] = (

        valid[target]

        -

        valid[
            f"BASE_PRED_{target}"
        ]
    )


    bias = (

        valid
        .groupby("station")
        ["RESIDUAL"]
        .agg(
            [
                "mean",
                "median",
                "count"
            ]
        )
        .reset_index()
    )


    bias.columns = [

        "station",

        f"{target}_BIAS_MEAN",

        f"{target}_BIAS_MEDIAN",

        f"{target}_BIAS_COUNT",
    ]


    station_bias[target] = bias


# ============================================================
# ADD STATION BIASES TO VALIDATION DATA
# ============================================================

work = validation.copy()


for target in TARGETS:

    work = work.merge(

        station_bias[target],

        on="station",

        how="left"
    )


# ============================================================
# CPCB FULL-REFERENCE MASK
# ============================================================

full_reference = (

    work[
        [
            "PM25",
            "PM10",
            "NO2",
            "O3_8H"
        ]
    ]
    .notna()
    .all(axis=1)
)


# ============================================================
# CALCULATE CURRENT V3 BASELINE
# ============================================================

work[
    "BASE_AQI"
] = work.apply(

    lambda r: calculate_aqi(

        r["PRED_PM25"],

        r["PRED_PM10"],

        r["PRED_NO2"],

        r["PRED_O3_8H"],
    ),

    axis=1
)


work[
    "CPCB_AQI_RECALCULATED"
] = work.apply(

    lambda r: calculate_aqi(

        r["PM25"],

        r["PM10"],

        r["NO2"],

        r["O3_8H"],
    ),

    axis=1
)


base = work[
    full_reference
].copy()


base_error = np.abs(

    base["BASE_AQI"]

    -

    base[
        "CPCB_AQI_RECALCULATED"
    ]
)


BASE_MAE = base_error.mean()

BASE_MEDIAN = base_error.median()

BASE_GT50 = (
    base_error > 50
).sum()

BASE_GT75 = (
    base_error > 75
).sum()

BASE_GT100 = (
    base_error > 100
).sum()

BASE_MAX = base_error.max()


print()
print("=" * 72)
print("CURRENT V3 BASELINE")
print("=" * 72)

print(
    f"AQI MAE                 : {BASE_MAE:.2f}"
)

print(
    f"Median absolute error   : {BASE_MEDIAN:.2f}"
)

print(
    f"> 50 AQI errors         : {BASE_GT50}"
)

print(
    f"> 75 AQI errors         : {BASE_GT75}"
)

print(
    f"> 100 AQI errors        : {BASE_GT100}"
)

print(
    f"Maximum AQI error       : {BASE_MAX:.2f}"
)


# ============================================================
# TEST CALIBRATION STRENGTHS
#
# 0.00 = no calibration
# 0.25 = 25% historical station bias
# 0.50 = 50%
# 0.75 = 75%
# 1.00 = full historical station bias
#
# We use MEDIAN station residual because it is more robust to
# extreme pollution episodes than mean residual.
# ============================================================

STRENGTHS = [
    0.00,
    0.25,
    0.50,
    0.75,
    1.00,
]


results = []

prediction_versions = {}


for strength in STRENGTHS:

    test = work.copy()


    for target in TARGETS:

        bias_column = (
            f"{target}_BIAS_MEDIAN"
        )

        count_column = (
            f"{target}_BIAS_COUNT"
        )


        # Require some real historical observations.
        # If unavailable, apply zero correction.

        usable_bias = np.where(

            test[count_column].fillna(0)
            >= 5,

            test[bias_column].fillna(0),

            0
        )


        test[
            f"CAL_PRED_{target}"
        ] = np.maximum(

            test[
                f"PRED_{target}"
            ]

            +

            strength
            * usable_bias,

            0
        )


    # --------------------------------------------------------
    # CALIBRATED AQI
    # --------------------------------------------------------

    test[
        "CALIBRATED_AQI"
    ] = test.apply(

        lambda r: calculate_aqi(

            r["CAL_PRED_PM25"],

            r["CAL_PRED_PM10"],

            r["CAL_PRED_NO2"],

            r["CAL_PRED_O3_8H"],
        ),

        axis=1
    )


    test[
        "CALIBRATED_CATEGORY"
    ] = test[
        "CALIBRATED_AQI"
    ].apply(category)


    full = test[
        full_reference
    ].copy()


    full[
        "AQI_ERROR"
    ] = (

        full["CALIBRATED_AQI"]

        -

        full[
            "CPCB_AQI_RECALCULATED"
        ]
    )


    full[
        "ABS_ERROR"
    ] = np.abs(
        full["AQI_ERROR"]
    )


    mae = full[
        "ABS_ERROR"
    ].mean()


    median = full[
        "ABS_ERROR"
    ].median()


    rmse = np.sqrt(

        mean_squared_error(

            full[
                "CPCB_AQI_RECALCULATED"
            ],

            full[
                "CALIBRATED_AQI"
            ]
        )
    )


    gt50 = (
        full["ABS_ERROR"] > 50
    ).sum()


    gt75 = (
        full["ABS_ERROR"] > 75
    ).sum()


    gt100 = (
        full["ABS_ERROR"] > 100
    ).sum()


    max_error = full[
        "ABS_ERROR"
    ].max()


    category_agreement = (

        full[
            "CPCB_AQI_RECALCULATED"
        ].apply(category)

        ==

        full[
            "CALIBRATED_CATEGORY"
        ]

    ).mean() * 100


    # --------------------------------------------------------
    # POLLUTANT MAE
    # --------------------------------------------------------

    pollutant_mae = {}


    for target in TARGETS:

        mask = full[
            target
        ].notna()

        pollutant_mae[
            target
        ] = mean_absolute_error(

            full.loc[
                mask,
                target
            ],

            full.loc[
                mask,
                f"CAL_PRED_{target}"
            ]
        )


    # Score strongly penalizes catastrophic misses.

    score = (

        mae

        +

        gt100 * 3

        +

        gt75 * 0.5
    )


    results.append({

        "strength":
            strength,

        "AQI_MAE":
            mae,

        "AQI_MEDIAN":
            median,

        "AQI_RMSE":
            rmse,

        "GT50":
            int(gt50),

        "GT75":
            int(gt75),

        "GT100":
            int(gt100),

        "MAX_ERROR":
            max_error,

        "CATEGORY_AGREEMENT":
            category_agreement,

        "PM25_MAE":
            pollutant_mae["PM25"],

        "PM10_MAE":
            pollutant_mae["PM10"],

        "NO2_MAE":
            pollutant_mae["NO2"],

        "O3_MAE":
            pollutant_mae["O3_8H"],

        "SCORE":
            score,
    })


    prediction_versions[
        strength
    ] = test


# ============================================================
# RESULTS
# ============================================================

results_df = pd.DataFrame(
    results
)

results_df = results_df.sort_values(

    [
        "SCORE",
        "AQI_MAE",
        "GT100"
    ]
)


results_df.to_csv(
    OUTPUT_FILE,
    index=False
)


print()
print("=" * 72)
print("STATION CALIBRATION RESULTS")
print("=" * 72)

print(

    results_df[
        [
            "strength",
            "AQI_MAE",
            "AQI_MEDIAN",
            "GT50",
            "GT75",
            "GT100",
            "MAX_ERROR",
            "PM25_MAE",
            "PM10_MAE",
            "CATEGORY_AGREEMENT",
        ]
    ].to_string(
        index=False
    )
)


# ============================================================
# BEST CALIBRATION
# ============================================================

best = results_df.iloc[0]

best_strength = float(
    best["strength"]
)


print()
print("=" * 72)
print("BEST RESULT")
print("=" * 72)

print(
    f"Calibration strength      : {best_strength:.2f}"
)

print()
print("CURRENT V3")
print("-" * 72)

print(
    f"AQI MAE                   : {BASE_MAE:.2f}"
)

print(
    f"Median error              : {BASE_MEDIAN:.2f}"
)

print(
    f">50 errors                : {BASE_GT50}"
)

print(
    f">75 errors                : {BASE_GT75}"
)

print(
    f">100 errors               : {BASE_GT100}"
)

print(
    f"Worst error               : {BASE_MAX:.2f}"
)


print()
print("CALIBRATED")
print("-" * 72)

print(
    f"AQI MAE                   : {best['AQI_MAE']:.2f}"
)

print(
    f"Median error              : {best['AQI_MEDIAN']:.2f}"
)

print(
    f">50 errors                : {int(best['GT50'])}"
)

print(
    f">75 errors                : {int(best['GT75'])}"
)

print(
    f">100 errors               : {int(best['GT100'])}"
)

print(
    f"Worst error               : {best['MAX_ERROR']:.2f}"
)

print(
    f"PM2.5 MAE                 : {best['PM25_MAE']:.2f}"
)

print(
    f"PM10 MAE                  : {best['PM10_MAE']:.2f}"
)

print(
    f"Category agreement        : "
    f"{best['CATEGORY_AGREEMENT']:.2f}%"
)


# ============================================================
# SAVE BEST ONLY IF IT IS NOT THE ZERO-CORRECTION BASELINE
# ============================================================

if best_strength > 0:

    best_predictions = prediction_versions[
        best_strength
    ]

    best_predictions.to_csv(

        BEST_FILE,

        index=False
    )

    print()
    print(
        "✅ Historical station calibration improved "
        "the scoring objective."
    )

    print(
        f"Best validation file:\n{BEST_FILE}"
    )

else:

    print()
    print(
        "⚠️ Station calibration did NOT improve "
        "held-out validation."
    )

    print(
        "Keep pure V3 predictions."
    )


print()
print(
    f"All experiments:\n{OUTPUT_FILE}"
)

print()
print("=" * 72)
print(
    "NOTE: Production models and backend were NOT modified."
)
print("=" * 72)