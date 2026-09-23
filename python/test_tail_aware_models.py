from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd

from xgboost import XGBRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

warnings.filterwarnings("ignore")


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATA_FILE = (
    ROOT
    / "data"
    / "processed"
    / "final_ml_dataset_v3.csv"
)

BASE_VALIDATION_FILE = (
    ROOT
    / "data"
    / "exports"
    / "v3_best_validation_predictions.csv"
)

OUTPUT_RESULTS = (
    ROOT
    / "data"
    / "exports"
    / "tail_aware_model_experiments.csv"
)

OUTPUT_BEST_VALIDATION = (
    ROOT
    / "data"
    / "exports"
    / "tail_aware_best_validation.csv"
)

OUTPUT_MODEL_DIR = (
    ROOT
    / "models"
    / "experimental_tail_aware"
)

OUTPUT_MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# FEATURES
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
# CPCB AQI
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


def subindex(value, pollutant):

    if pd.isna(value):
        return np.nan

    value = max(0.0, float(value))

    for c_low, c_high, i_low, i_high in BREAKPOINTS[pollutant]:

        if value <= c_high:

            return (
                i_low
                + (
                    (i_high - i_low)
                    * (value - c_low)
                    / (c_high - c_low)
                )
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
        x
        for x in values
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
# LOAD
# ============================================================

if not DATA_FILE.exists():
    raise FileNotFoundError(DATA_FILE)

if not BASE_VALIDATION_FILE.exists():
    raise FileNotFoundError(BASE_VALIDATION_FILE)


df = pd.read_csv(DATA_FILE)

validation = pd.read_csv(
    BASE_VALIDATION_FILE
)

df["date"] = pd.to_datetime(
    df["date_text"]
)


train = df[
    df["date"]
    <= pd.Timestamp("2026-06-23")
].copy()


print()
print("=" * 76)
print("AEROVISION FINAL TAIL-AWARE MODEL EXPERIMENT")
print("=" * 76)

print(
    f"Training rows       : {len(train)}"
)

print(
    "Training period     : 2026-06-01 -> 2026-06-23"
)

print(
    f"Validation rows     : {len(validation)}"
)

print(
    "Validation period   : 2026-06-24 -> 2026-06-30"
)


# ============================================================
# FULL CPCB REFERENCE
# ============================================================

FULL_MASK = (
    validation[
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

print(
    f"Full CPCB reference : {FULL_MASK.sum()}"
)


# ============================================================
# TRAINING DISTRIBUTION
# ============================================================

print()
print("=" * 76)
print("TRAINING POLLUTION DISTRIBUTION")
print("=" * 76)

for target in ["PM25", "PM10"]:

    y = train[target].dropna()

    print()
    print(target)

    print(
        f"Median : {y.median():.2f}"
    )

    print(
        f"P75    : {y.quantile(0.75):.2f}"
    )

    print(
        f"P85    : {y.quantile(0.85):.2f}"
    )

    print(
        f"P90    : {y.quantile(0.90):.2f}"
    )

    print(
        f"P95    : {y.quantile(0.95):.2f}"
    )

    print(
        f"Max    : {y.max():.2f}"
    )


# ============================================================
# SAMPLE WEIGHT FUNCTION
#
# No fake values.
#
# High pollution measurements simply contribute more strongly
# to XGBoost's training loss.
#
# Thresholds are calculated only from Jun 1-23 training data.
# ============================================================

def make_weights(y, strength):

    y = pd.Series(y).astype(float)

    q75 = y.quantile(0.75)
    q90 = y.quantile(0.90)

    weights = np.ones(
        len(y),
        dtype=float
    )

    # Upper 25%
    weights[y >= q75] += (
        strength * 0.50
    )

    # Upper 10%
    weights[y >= q90] += (
        strength * 1.00
    )

    return weights


# ============================================================
# MODEL FACTORY
# ============================================================

def create_model():

    return XGBRegressor(

        n_estimators=600,

        learning_rate=0.025,

        max_depth=4,

        min_child_weight=3,

        subsample=0.85,

        colsample_bytree=0.90,

        reg_alpha=0.10,

        reg_lambda=2.0,

        objective="reg:squarederror",

        random_state=42,

        n_jobs=-1,
    )


# ============================================================
# BASELINE FROM EXISTING V3 VALIDATION
# ============================================================

baseline = validation.copy()


baseline[
    "TEST_AQI"
] = baseline.apply(

    lambda r: calculate_aqi(
        r["PRED_PM25"],
        r["PRED_PM10"],
        r["PRED_NO2"],
        r["PRED_O3_8H"],
    ),

    axis=1
)


baseline[
    "REAL_AQI"
] = baseline.apply(

    lambda r: calculate_aqi(
        r["PM25"],
        r["PM10"],
        r["NO2"],
        r["O3_8H"],
    ),

    axis=1
)


base_full = baseline[
    FULL_MASK
].copy()

base_errors = np.abs(
    base_full["TEST_AQI"]
    -
    base_full["REAL_AQI"]
)


print()
print("=" * 76)
print("CURRENT V3 BASELINE")
print("=" * 76)

print(
    f"AQI MAE        : {base_errors.mean():.2f}"
)

print(
    f"Median error   : {base_errors.median():.2f}"
)

print(
    f">50 errors     : {(base_errors > 50).sum()}"
)

print(
    f">75 errors     : {(base_errors > 75).sum()}"
)

print(
    f">100 errors    : {(base_errors > 100).sum()}"
)

print(
    f">150 errors    : {(base_errors > 150).sum()}"
)

print(
    f"Worst error    : {base_errors.max():.2f}"
)


# ============================================================
# STRENGTHS
#
# 0.0 is an independently retrained normal model.
# Increasing numbers place more emphasis on upper pollution
# measurements.
# ============================================================

STRENGTHS = [
    0.0,
    0.50,
    1.00,
    1.50,
    2.00,
    3.00,
    4.00,
]


all_results = []

saved_candidates = {}


for strength in STRENGTHS:

    print()
    print("-" * 76)

    print(
        f"TAIL WEIGHT STRENGTH = {strength}"
    )

    print("-" * 76)


    candidate = validation.copy()

    candidate_models = {}


    # ========================================================
    # RETRAIN PM2.5 AND PM10 ONLY
    #
    # NO2/O3 already perform reasonably well in V3.
    # ========================================================

    for target in [
        "PM25",
        "PM10",
    ]:

        target_train = train[
            train[target].notna()
        ].copy()


        X_train = target_train[
            FEATURES
        ]


        y_train = target_train[
            target
        ]


        weights = make_weights(
            y_train,
            strength
        )


        model = create_model()


        model.fit(

            X_train,

            y_train,

            sample_weight=weights,
        )


        candidate_models[
            target
        ] = model


        # ---------------------------------------------
        # Need feature rows corresponding to validation
        # station-days.
        # ---------------------------------------------

        val_features = validation[
            [
                "station_day_id"
            ]
        ].merge(

            df[
                ["station_day_id"]
                + FEATURES
            ],

            on="station_day_id",

            how="left",
        )


        pred = model.predict(
            val_features[FEATURES]
        )


        pred = np.maximum(
            pred,
            0
        )


        candidate[
            f"TAIL_PRED_{target}"
        ] = pred


    # ========================================================
    # KEEP CURRENT V3 NO2 AND O3
    # ========================================================

    candidate[
        "TAIL_PRED_NO2"
    ] = candidate[
        "PRED_NO2"
    ]


    candidate[
        "TAIL_PRED_O3_8H"
    ] = candidate[
        "PRED_O3_8H"
    ]


    # ========================================================
    # CALCULATE AQI
    # ========================================================

    candidate[
        "TAIL_AQI"
    ] = candidate.apply(

        lambda r: calculate_aqi(

            r[
                "TAIL_PRED_PM25"
            ],

            r[
                "TAIL_PRED_PM10"
            ],

            r[
                "TAIL_PRED_NO2"
            ],

            r[
                "TAIL_PRED_O3_8H"
            ],
        ),

        axis=1
    )


    candidate[
        "TAIL_CATEGORY"
    ] = candidate[
        "TAIL_AQI"
    ].apply(category)


    candidate[
        "REAL_AQI"
    ] = candidate.apply(

        lambda r: calculate_aqi(

            r["PM25"],

            r["PM10"],

            r["NO2"],

            r["O3_8H"],
        ),

        axis=1
    )


    full = candidate[
        FULL_MASK
    ].copy()


    errors = np.abs(

        full["TAIL_AQI"]

        -

        full["REAL_AQI"]
    )


    # ========================================================
    # METRICS
    # ========================================================

    mae = errors.mean()

    median = errors.median()

    rmse = np.sqrt(
        mean_squared_error(
            full["REAL_AQI"],
            full["TAIL_AQI"],
        )
    )

    correlation = (
        full[
            [
                "REAL_AQI",
                "TAIL_AQI"
            ]
        ]
        .corr()
        .iloc[0, 1]
    )


    gt50 = int(
        (errors > 50).sum()
    )

    gt75 = int(
        (errors > 75).sum()
    )

    gt100 = int(
        (errors > 100).sum()
    )

    gt150 = int(
        (errors > 150).sum()
    )

    max_error = float(
        errors.max()
    )


    cat_agreement = float(

        (
            full[
                "REAL_AQI"
            ].apply(category)

            ==

            full[
                "TAIL_CATEGORY"
            ]
        ).mean()
        * 100
    )


    pm25_mae = mean_absolute_error(

        full["PM25"],

        full["TAIL_PRED_PM25"]
    )


    pm10_mae = mean_absolute_error(

        full["PM10"],

        full["TAIL_PRED_PM10"]
    )


    # ========================================================
    # SEVERE-DAY PM2.5 PERFORMANCE
    # ========================================================

    high_pm25_mask = (
        full["PM25"]
        >= 90
    )

    if high_pm25_mask.sum() > 0:

        high_pm25_mae = (
            np.abs(

                full.loc[
                    high_pm25_mask,
                    "PM25"
                ]

                -

                full.loc[
                    high_pm25_mask,
                    "TAIL_PRED_PM25"
                ]
            )
            .mean()
        )

    else:

        high_pm25_mae = np.nan


    # ========================================================
    # SCORE
    #
    # This time we deliberately prioritize catastrophic
    # AQI errors first.
    # ========================================================

    score = (

        mae

        + gt50 * 0.10

        + gt75 * 0.50

        + gt100 * 8.0

        + gt150 * 10.0

        + max_error * 0.03
    )


    result = {

        "strength":
            strength,

        "AQI_MAE":
            mae,

        "AQI_MEDIAN":
            median,

        "AQI_RMSE":
            rmse,

        "CORRELATION":
            correlation,

        "GT50":
            gt50,

        "GT75":
            gt75,

        "GT100":
            gt100,

        "GT150":
            gt150,

        "MAX_ERROR":
            max_error,

        "PM25_MAE":
            pm25_mae,

        "HIGH_PM25_MAE":
            high_pm25_mae,

        "PM10_MAE":
            pm10_mae,

        "CATEGORY_AGREEMENT":
            cat_agreement,

        "SCORE":
            score,
    }


    all_results.append(
        result
    )


    saved_candidates[
        strength
    ] = {

        "validation":
            candidate,

        "models":
            candidate_models,
    }


    print(
        f"AQI MAE        : {mae:.2f}"
    )

    print(
        f"Median          : {median:.2f}"
    )

    print(
        f">50             : {gt50}"
    )

    print(
        f">75             : {gt75}"
    )

    print(
        f">100            : {gt100}"
    )

    print(
        f">150            : {gt150}"
    )

    print(
        f"Worst           : {max_error:.2f}"
    )

    print(
        f"PM2.5 MAE       : {pm25_mae:.2f}"
    )

    print(
        f"High PM2.5 MAE  : {high_pm25_mae:.2f}"
    )

    print(
        f"PM10 MAE        : {pm10_mae:.2f}"
    )

    print(
        f"Category agree  : {cat_agreement:.2f}%"
    )


# ============================================================
# RESULTS TABLE
# ============================================================

results = pd.DataFrame(
    all_results
)


# Extreme errors are the primary objective.
results = results.sort_values(

    by=[
        "GT100",
        "GT150",
        "AQI_MAE",
        "MAX_ERROR",
    ],

    ascending=True,
)


results.to_csv(
    OUTPUT_RESULTS,
    index=False
)


print()
print()
print("=" * 76)
print("FINAL COMPARISON")
print("=" * 76)

print(

    results[
        [
            "strength",
            "AQI_MAE",
            "AQI_MEDIAN",
            "GT50",
            "GT75",
            "GT100",
            "GT150",
            "MAX_ERROR",
            "PM25_MAE",
            "HIGH_PM25_MAE",
            "PM10_MAE",
            "CATEGORY_AGREEMENT",
        ]
    ].to_string(
        index=False
    )
)


# ============================================================
# BEST CANDIDATE
# ============================================================

best = results.iloc[0]

best_strength = float(
    best["strength"]
)

best_candidate = saved_candidates[
    best_strength
]


print()
print("=" * 76)
print("BEST TAIL-AWARE CANDIDATE")
print("=" * 76)

print(
    f"Weight strength       : {best_strength}"
)

print()
print("CURRENT V3")
print("-" * 76)

print(
    f"AQI MAE               : {base_errors.mean():.2f}"
)

print(
    f"Median                 : {base_errors.median():.2f}"
)

print(
    f">50                    : {(base_errors > 50).sum()}"
)

print(
    f">75                    : {(base_errors > 75).sum()}"
)

print(
    f">100                   : {(base_errors > 100).sum()}"
)

print(
    f">150                   : {(base_errors > 150).sum()}"
)

print(
    f"Worst                  : {base_errors.max():.2f}"
)


print()
print("TAIL-AWARE")
print("-" * 76)

print(
    f"AQI MAE               : {best['AQI_MAE']:.2f}"
)

print(
    f"Median                 : {best['AQI_MEDIAN']:.2f}"
)

print(
    f">50                    : {int(best['GT50'])}"
)

print(
    f">75                    : {int(best['GT75'])}"
)

print(
    f">100                   : {int(best['GT100'])}"
)

print(
    f">150                   : {int(best['GT150'])}"
)

print(
    f"Worst                  : {best['MAX_ERROR']:.2f}"
)

print(
    f"PM2.5 MAE             : {best['PM25_MAE']:.2f}"
)

print(
    f"High PM2.5 MAE        : {best['HIGH_PM25_MAE']:.2f}"
)

print(
    f"PM10 MAE              : {best['PM10_MAE']:.2f}"
)

print(
    f"Category agreement    : {best['CATEGORY_AGREEMENT']:.2f}%"
)


# ============================================================
# SAVE BEST EXPERIMENT
# ============================================================

best_candidate[
    "validation"
].to_csv(

    OUTPUT_BEST_VALIDATION,

    index=False
)


joblib.dump(

    best_candidate[
        "models"
    ]["PM25"],

    OUTPUT_MODEL_DIR
    / "aerovision_PM25_tail.joblib",
)


joblib.dump(

    best_candidate[
        "models"
    ]["PM10"],

    OUTPUT_MODEL_DIR
    / "aerovision_PM10_tail.joblib",
)


with open(
    OUTPUT_MODEL_DIR
    / "feature_list.json",
    "w"
) as f:

    json.dump(
        FEATURES,
        f,
        indent=2
    )


with open(
    OUTPUT_MODEL_DIR
    / "experiment_info.json",
    "w"
) as f:

    json.dump(

        {
            "strength":
                best_strength,

            "validation_AQI_MAE":
                float(best["AQI_MAE"]),

            "GT100":
                int(best["GT100"]),

            "GT150":
                int(best["GT150"]),

            "max_error":
                float(best["MAX_ERROR"]),

            "training_period":
                "2026-06-01 to 2026-06-23",

            "validation_period":
                "2026-06-24 to 2026-06-30",

            "note":
                "Experimental tail-aware PM25/PM10 models. "
                "No validation CPCB values used during training."
        },

        f,

        indent=2
    )


print()
print(
    f"Results:\n{OUTPUT_RESULTS}"
)

print()
print(
    f"Best validation:\n{OUTPUT_BEST_VALIDATION}"
)

print()
print(
    f"Experimental models:\n{OUTPUT_MODEL_DIR}"
)

print()
print("=" * 76)
print("PRODUCTION MODELS WERE NOT MODIFIED")
print("=" * 76)