import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from xgboost import XGBRegressor


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DATASET = ROOT / "data" / "processed" / "final_ml_dataset_v3.csv"

CURRENT_COMPARISON_CANDIDATES = [
    ROOT / "data" / "exports" / "cpcb_vs_aerovision_aqi_corrected.csv",
    ROOT / "data" / "processed" / "cpcb_vs_aerovision_aqi.csv",
]

EXPERIMENT_DIR = ROOT / "models" / "experimental_v3"
REPORT_DIR = ROOT / "data" / "exports"

EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CPCB AQI FUNCTIONS
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


def pollutant_subindex(value, pollutant):

    if pd.isna(value):
        return np.nan

    value = max(0.0, float(value))

    for bp_low, bp_high, i_low, i_high in BREAKPOINTS[pollutant]:

        if value <= bp_high:

            return i_low + (
                (i_high - i_low)
                * (value - bp_low)
                / (bp_high - bp_low)
            )

    return 500.0


def calculate_aqi(pm25, pm10, no2, o3):

    values = [
        pollutant_subindex(pm25, "PM25"),
        pollutant_subindex(pm10, "PM10"),
        pollutant_subindex(no2, "NO2"),
        pollutant_subindex(o3, "O3_8H"),
    ]

    values = [
        x for x in values
        if not pd.isna(x)
    ]

    if not values:
        return np.nan

    return max(values)


def aqi_category(aqi):

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
# FEATURE ENGINEERING
# ============================================================

def add_features(df):

    df = df.copy()

    df["date"] = pd.to_datetime(df["date_text"])

    df["DAY_OF_YEAR"] = df["date"].dt.dayofyear.astype(float)

    df["DOY_SIN"] = np.sin(
        2 * np.pi * df["DAY_OF_YEAR"] / 365.25
    )

    df["DOY_COS"] = np.cos(
        2 * np.pi * df["DAY_OF_YEAR"] / 365.25
    )

    safe_wind = df["WIND_SPEED"].clip(lower=0.2)

    df["AOD_X_RH"] = (
        df["AOD"]
        * df["ERA5_RH"]
    )

    df["AOD_X_INVWIND"] = (
        df["AOD"]
        / safe_wind
    )

    df["SATNO2_X_INVWIND"] = (
        df["SAT_NO2"]
        / safe_wind
    )

    df["HCHO_X_TEMP"] = (
        df["HCHO"]
        * df["ERA5_TEMP"]
    )

    df["FIRE_X_INVWIND"] = (
        df["FIRE_COUNT_25KM"]
        / safe_wind
    )

    df["TEMP_X_RH"] = (
        df["ERA5_TEMP"]
        * df["ERA5_RH"]
    )

    return df


# ============================================================
# LOAD DATA
# ============================================================

print()
print("=" * 70)
print("AEROVISION V3 REAL-DATA MODEL EXPERIMENT")
print("=" * 70)

if not DATASET.exists():
    raise FileNotFoundError(
        f"Dataset not found:\n{DATASET}"
    )

df = pd.read_csv(DATASET)

df = add_features(df)


comparison_file = None

for path in CURRENT_COMPARISON_CANDIDATES:

    if path.exists():
        comparison_file = path
        break


if comparison_file is None:
    raise FileNotFoundError(
        "Could not find CPCB vs AeroVision comparison CSV."
    )


current = pd.read_csv(comparison_file)


# ============================================================
# TEMPORAL SPLIT
#
# IMPORTANT:
# 1-23 June = training
# 24-30 June = completely unseen validation
# ============================================================

TRAIN_END = pd.Timestamp("2026-06-23")
VALIDATION_START = pd.Timestamp("2026-06-24")

train = df[
    df["date"] <= TRAIN_END
].copy()

validation = df[
    df["date"] >= VALIDATION_START
].copy()


print(f"Training rows   : {len(train)}")
print(f"Validation rows : {len(validation)}")

print(
    f"Training period : "
    f"{train['date'].min().date()} → "
    f"{train['date'].max().date()}"
)

print(
    f"Validation      : "
    f"{validation['date'].min().date()} → "
    f"{validation['date'].max().date()}"
)


# ============================================================
# FEATURE SETS
# ============================================================

BASE_FEATURES = [

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


ENGINEERED_FEATURES = BASE_FEATURES + [

    "DOY_SIN",
    "DOY_COS",

    "AOD_X_RH",
    "AOD_X_INVWIND",

    "SATNO2_X_INVWIND",

    "HCHO_X_TEMP",

    "FIRE_X_INVWIND",

    "TEMP_X_RH",
]


FEATURE_SETS = {

    "BASE":
        BASE_FEATURES,

    "ENGINEERED":
        ENGINEERED_FEATURES,
}


# ============================================================
# XGBOOST CONFIGURATIONS
# ============================================================

CONFIGS = {

    "XGB_A": {

        "n_estimators": 400,

        "max_depth": 3,

        "learning_rate": 0.03,

        "subsample": 0.80,

        "colsample_bytree": 0.80,

        "min_child_weight": 3,

        "reg_alpha": 0.10,

        "reg_lambda": 2.0,
    },


    "XGB_B": {

        "n_estimators": 600,

        "max_depth": 2,

        "learning_rate": 0.025,

        "subsample": 0.85,

        "colsample_bytree": 0.90,

        "min_child_weight": 2,

        "reg_alpha": 0.05,

        "reg_lambda": 3.0,
    },


    "XGB_C": {

        "n_estimators": 350,

        "max_depth": 4,

        "learning_rate": 0.035,

        "subsample": 0.80,

        "colsample_bytree": 0.80,

        "min_child_weight": 5,

        "reg_alpha": 0.20,

        "reg_lambda": 4.0,
    },
}


TARGETS = [

    "PM25",

    "PM10",

    "NO2",

    "O3_8H",
]


# ============================================================
# CURRENT MODEL PERFORMANCE
# ============================================================

current = current[
    current["station_day_id"].isin(
        validation["station_day_id"]
    )
].copy()


# Full CPCB reference only
full_current = current[
    current[
        [
            "PM25",
            "PM10",
            "NO2",
            "O3_8H"
        ]
    ].notna().all(axis=1)
].copy()


CURRENT_AQI_MAE = mean_absolute_error(

    full_current["CPCB_AQI"],

    full_current["AEROVISION_AQI"],
)


CURRENT_AQI_MEDIAN = np.median(

    np.abs(

        full_current["CPCB_AQI"]

        -

        full_current["AEROVISION_AQI"]
    )
)


CURRENT_OVER_100 = (

    np.abs(

        full_current["CPCB_AQI"]

        -

        full_current["AEROVISION_AQI"]

    ) > 100

).sum()


print()
print("CURRENT MODEL")
print("-" * 70)

print(
    f"AQI MAE             : "
    f"{CURRENT_AQI_MAE:.2f}"
)

print(
    f"Median AQI error    : "
    f"{CURRENT_AQI_MEDIAN:.2f}"
)

print(
    f"AQI errors > 100    : "
    f"{CURRENT_OVER_100}"
)


# ============================================================
# TRAIN EXPERIMENTS
# ============================================================

all_results = []

saved_models = {}


for feature_name, features in FEATURE_SETS.items():

    for config_name, params in CONFIGS.items():

        experiment_name = (
            f"{feature_name}_{config_name}"
        )

        print()
        print("=" * 70)
        print(
            f"EXPERIMENT: {experiment_name}"
        )
        print("=" * 70)

        predictions = validation[
            [
                "station_day_id",
                "date_text",
                "station",
                "city",
                "state",
                "latitude",
                "longitude",

                "PM25",
                "PM10",
                "NO2",
                "O3_8H",
            ]
        ].copy()


        experiment_models = {}

        pollutant_metrics = {}


        for target in TARGETS:

            target_train = train[
                train[target].notna()
            ].copy()

            target_validation = validation[
                validation[target].notna()
            ].copy()


            model = XGBRegressor(

                objective="reg:squarederror",

                random_state=42,

                n_jobs=4,

                **params
            )


            model.fit(

                target_train[features],

                target_train[target]
            )


            validation_prediction = model.predict(

                validation[features]
            )


            validation_prediction = np.maximum(

                validation_prediction,

                0
            )


            predictions[
                f"PRED_{target}"
            ] = validation_prediction


            # pollutant validation metric

            mask = validation[
                target
            ].notna()


            true_values = validation.loc[
                mask,
                target
            ]


            predicted_values = validation_prediction[
                mask.values
            ]


            mae = mean_absolute_error(

                true_values,

                predicted_values
            )


            rmse = np.sqrt(

                mean_squared_error(

                    true_values,

                    predicted_values
                )
            )


            r2 = r2_score(

                true_values,

                predicted_values
            )


            pollutant_metrics[target] = {

                "MAE": mae,

                "RMSE": rmse,

                "R2": r2,
            }


            experiment_models[
                target
            ] = model


            print(
                f"{target:8s} "
                f"MAE={mae:7.2f} "
                f"RMSE={rmse:7.2f} "
                f"R2={r2:7.3f}"
            )


        # ====================================================
        # CALCULATE AEROVISION AQI
        # ====================================================

        predictions[
            "AEROVISION_AQI"
        ] = predictions.apply(

            lambda row: calculate_aqi(

                row["PRED_PM25"],

                row["PRED_PM10"],

                row["PRED_NO2"],

                row["PRED_O3_8H"],
            ),

            axis=1
        )


        predictions[
            "AEROVISION_CATEGORY"
        ] = predictions[
            "AEROVISION_AQI"
        ].apply(aqi_category)


        # ====================================================
        # REAL CPCB AQI FROM ALL FOUR OBSERVED POLLUTANTS
        # ====================================================

        predictions[
            "CPCB_AQI"
        ] = predictions.apply(

            lambda row: calculate_aqi(

                row["PM25"],

                row["PM10"],

                row["NO2"],

                row["O3_8H"],
            ),

            axis=1
        )


        predictions[
            "CPCB_CATEGORY"
        ] = predictions[
            "CPCB_AQI"
        ].apply(aqi_category)


        full_mask = predictions[
            [
                "PM25",
                "PM10",
                "NO2",
                "O3_8H"
            ]
        ].notna().all(axis=1)


        full = predictions[
            full_mask
        ].copy()


        full[
            "AQI_ERROR"
        ] = (

            full["AEROVISION_AQI"]

            -

            full["CPCB_AQI"]
        )


        full[
            "AQI_ABS_ERROR"
        ] = np.abs(

            full["AQI_ERROR"]
        )


        aqi_mae = full[
            "AQI_ABS_ERROR"
        ].mean()


        median_error = full[
            "AQI_ABS_ERROR"
        ].median()


        aqi_rmse = np.sqrt(

            np.mean(

                full[
                    "AQI_ERROR"
                ] ** 2
            )
        )


        correlation = full[
            [
                "CPCB_AQI",

                "AEROVISION_AQI"
            ]
        ].corr().iloc[0, 1]


        category_agreement = (

            full["CPCB_CATEGORY"]

            ==

            full["AEROVISION_CATEGORY"]

        ).mean() * 100


        over_25 = (

            full[
                "AQI_ABS_ERROR"
            ] > 25

        ).sum()


        over_50 = (

            full[
                "AQI_ABS_ERROR"
            ] > 50

        ).sum()


        over_75 = (

            full[
                "AQI_ABS_ERROR"
            ] > 75

        ).sum()


        over_100 = (

            full[
                "AQI_ABS_ERROR"
            ] > 100

        ).sum()


        max_error = full[
            "AQI_ABS_ERROR"
        ].max()


        print()
        print("AQI RESULTS")
        print("-" * 70)

        print(
            f"AQI MAE             : "
            f"{aqi_mae:.2f}"
        )

        print(
            f"Median error        : "
            f"{median_error:.2f}"
        )

        print(
            f"AQI RMSE            : "
            f"{aqi_rmse:.2f}"
        )

        print(
            f"Correlation         : "
            f"{correlation:.3f}"
        )

        print(
            f"Category agreement  : "
            f"{category_agreement:.2f}%"
        )

        print(
            f">25 AQI              : "
            f"{over_25}"
        )

        print(
            f">50 AQI              : "
            f"{over_50}"
        )

        print(
            f">75 AQI              : "
            f"{over_75}"
        )

        print(
            f">100 AQI             : "
            f"{over_100}"
        )

        print(
            f"Maximum error        : "
            f"{max_error:.2f}"
        )


        # ====================================================
        # SCORE EXPERIMENT
        #
        # Primary goal:
        # AQI MAE
        #
        # Additional penalty for extreme >100 errors
        # ====================================================

        score = (

            aqi_mae

            +

            (over_100 * 2.0)
        )


        all_results.append({

            "experiment":
                experiment_name,

            "feature_set":
                feature_name,

            "config":
                config_name,

            "AQI_MAE":
                aqi_mae,

            "AQI_MEDIAN_ERROR":
                median_error,

            "AQI_RMSE":
                aqi_rmse,

            "AQI_CORRELATION":
                correlation,

            "CATEGORY_AGREEMENT":
                category_agreement,

            "ERROR_GT_25":
                int(over_25),

            "ERROR_GT_50":
                int(over_50),

            "ERROR_GT_75":
                int(over_75),

            "ERROR_GT_100":
                int(over_100),

            "MAX_ERROR":
                max_error,

            "SCORE":
                score,

            "PM25_MAE":
                pollutant_metrics[
                    "PM25"
                ]["MAE"],

            "PM10_MAE":
                pollutant_metrics[
                    "PM10"
                ]["MAE"],

            "NO2_MAE":
                pollutant_metrics[
                    "NO2"
                ]["MAE"],

            "O3_MAE":
                pollutant_metrics[
                    "O3_8H"
                ]["MAE"],
        })


        saved_models[
            experiment_name
        ] = {

            "models":
                experiment_models,

            "features":
                features,

            "predictions":
                predictions,
        }


# ============================================================
# RANK EXPERIMENTS
# ============================================================

results_df = pd.DataFrame(
    all_results
)

results_df = results_df.sort_values(

    [
        "SCORE",
        "AQI_MAE",
        "ERROR_GT_100"
    ]
)


RESULT_FILE = (

    REPORT_DIR
    /
    "v3_model_experiments.csv"
)

results_df.to_csv(

    RESULT_FILE,

    index=False
)


print()
print()
print("=" * 70)
print("EXPERIMENT RANKING")
print("=" * 70)

print(

    results_df[
        [
            "experiment",
            "AQI_MAE",
            "AQI_MEDIAN_ERROR",
            "ERROR_GT_50",
            "ERROR_GT_100",
            "CATEGORY_AGREEMENT"
        ]
    ].to_string(index=False)
)


# ============================================================
# SELECT BEST
# ============================================================

best = results_df.iloc[0]

best_name = best[
    "experiment"
]


print()
print("=" * 70)
print("BEST EXPERIMENT")
print("=" * 70)

print(
    f"Experiment          : "
    f"{best_name}"
)

print(
    f"Current AQI MAE     : "
    f"{CURRENT_AQI_MAE:.2f}"
)

print(
    f"V3 AQI MAE          : "
    f"{best['AQI_MAE']:.2f}"
)

print(
    f"Current >100 errors : "
    f"{CURRENT_OVER_100}"
)

print(
    f"V3 >100 errors      : "
    f"{int(best['ERROR_GT_100'])}"
)


# ============================================================
# REPLACEMENT RULE
#
# We DO NOT overwrite production models.
#
# Save winner only when:
#
# 1. AQI MAE improves
# 2. >100 errors do not increase
# ============================================================

improved_mae = (

    best[
        "AQI_MAE"
    ]

    <

    CURRENT_AQI_MAE
)


not_more_extreme_errors = (

    best[
        "ERROR_GT_100"
    ]

    <=

    CURRENT_OVER_100
)


if (
    improved_mae
    and
    not_more_extreme_errors
):

    print()
    print(
        "✅ V3 genuinely improves held-out validation."
    )

    print(
        "Saving experimental winner..."
    )


    winner = saved_models[
        best_name
    ]


    for target, model in winner[
        "models"
    ].items():

        filename = (
            EXPERIMENT_DIR
            /
            f"aerovision_{target}_V3.joblib"
        )

        joblib.dump(
            model,
            filename
        )


    feature_file = (
        EXPERIMENT_DIR
        /
        "feature_list.json"
    )


    with open(
        feature_file,
        "w"
    ) as f:

        json.dump(

            winner[
                "features"
            ],

            f,

            indent=2
        )


    winner_predictions = (
        REPORT_DIR
        /
        "v3_best_validation_predictions.csv"
    )


    winner[
        "predictions"
    ].to_csv(

        winner_predictions,

        index=False
    )


    print()
    print(
        f"V3 models saved to:\n"
        f"{EXPERIMENT_DIR}"
    )


else:

    print()
    print(
        "⚠️ V3 DID NOT genuinely beat "
        "the current production model."
    )

    print()

    print(
        "Production models have NOT been changed."
    )

    print()

    print(
        "Keep the existing models and move "
        "to UI/presentation work."
    )


print()
print(
    f"Experiment report:\n"
    f"{RESULT_FILE}"
)

print()
print("=" * 70)