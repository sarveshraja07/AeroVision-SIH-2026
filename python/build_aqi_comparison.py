import os
import joblib
import numpy as np
import pandas as pd

BASE = r"E:\AeroVision-Real"

INPUT = os.path.join(
    BASE,
    "data",
    "processed",
    "final_ml_dataset_v3.csv"
)

OUTPUT = os.path.join(
    BASE,
    "data",
    "processed",
    "cpcb_vs_aerovision_aqi.csv"
)

MODEL_DIR = os.path.join(
    BASE,
    "models"
)

# Held-out validation models
PM25_MODEL = os.path.join(MODEL_DIR, "xgboost_v2_PM25.joblib")
PM10_MODEL = os.path.join(MODEL_DIR, "xgboost_v2_PM10.joblib")
NO2_MODEL  = os.path.join(MODEL_DIR, "xgboost_v2_NO2.joblib")
O3_MODEL   = os.path.join(MODEL_DIR, "xgboost_v3_O3_8H.joblib")

FEATURES = [
    "latitude",
    "longitude",
    "AOD",
    "HCHO",
    "SAT_NO2",
    "ERA5_TEMP",
    "ERA5_DEWPOINT",
    "ERA5_RH",
    "WIND_U",
    "WIND_V",
    "WIND_SPEED",
    "FIRE_COUNT_25KM",
    "FIRE_CONF_MAX_25KM",
    "FIRE_T21_MAX_25KM"
]

TEST_START = pd.Timestamp("2026-06-24")
TEST_END   = pd.Timestamp("2026-07-01")


# ============================================================
# CPCB AQI BREAKPOINTS
# ============================================================

AQI_RANGES = [
    (0, 50),
    (51, 100),
    (101, 200),
    (201, 300),
    (301, 400),
    (401, 500)
]

BREAKPOINTS = {

    "PM25": [
        (0, 30),
        (31, 60),
        (61, 90),
        (91, 120),
        (121, 250),
        (251, 500)
    ],

    "PM10": [
        (0, 50),
        (51, 100),
        (101, 250),
        (251, 350),
        (351, 430),
        (431, 600)
    ],

    "NO2": [
        (0, 40),
        (41, 80),
        (81, 180),
        (181, 280),
        (281, 400),
        (401, 800)
    ],

    "O3": [
        (0, 50),
        (51, 100),
        (101, 168),
        (169, 208),
        (209, 748),
        (749, 1000)
    ]
}


def pollutant_subindex(value, pollutant):

    if pd.isna(value):
        return np.nan

    value = max(float(value), 0.0)

    ranges = BREAKPOINTS[pollutant]

    # Severe extension capped at 500
    if value > ranges[-1][1]:
        return 500.0

    for (bp_low, bp_high), (aqi_low, aqi_high) in zip(
        ranges,
        AQI_RANGES
    ):

        if bp_low <= value <= bp_high:

            if bp_high == bp_low:
                return float(aqi_high)

            result = (
                (aqi_high - aqi_low)
                / (bp_high - bp_low)
                * (value - bp_low)
                + aqi_low
            )

            return float(result)

    return np.nan


def final_aqi(pm25, pm10, no2, o3):

    values = [
        pollutant_subindex(pm25, "PM25"),
        pollutant_subindex(pm10, "PM10"),
        pollutant_subindex(no2, "NO2"),
        pollutant_subindex(o3, "O3")
    ]

    valid = [
        x for x in values
        if not pd.isna(x)
    ]

    if not valid:
        return np.nan

    return min(max(valid), 500.0)


def category(aqi):

    if pd.isna(aqi):
        return "Unavailable"

    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Satisfactory"
    elif aqi <= 200:
        return "Moderate"
    elif aqi <= 300:
        return "Poor"
    elif aqi <= 400:
        return "Very Poor"
    else:
        return "Severe"


print("=" * 70)
print("AEROVISION CPCB VS MODEL AQI COMPARISON")
print("=" * 70)

df = pd.read_csv(INPUT)

df["date_text"] = pd.to_datetime(
    df["date_text"],
    errors="coerce"
)

test = df[
    (df["date_text"] >= TEST_START)
    &
    (df["date_text"] < TEST_END)
].copy()

print("Validation rows:", len(test))
print(
    "Period:",
    test["date_text"].min(),
    "to",
    test["date_text"].max()
)


# ============================================================
# LOAD VALIDATION MODELS
# ============================================================

models = {
    "PM25": joblib.load(PM25_MODEL),
    "PM10": joblib.load(PM10_MODEL),
    "NO2": joblib.load(NO2_MODEL),
    "O3": joblib.load(O3_MODEL)
}


# ============================================================
# PREDICT
# ============================================================

X = test[FEATURES]

test["PRED_PM25"] = models["PM25"].predict(X)
test["PRED_PM10"] = models["PM10"].predict(X)
test["PRED_NO2"] = models["NO2"].predict(X)
test["PRED_O3_8H"] = models["O3"].predict(X)


# No negative pollutant concentrations
for col in [
    "PRED_PM25",
    "PRED_PM10",
    "PRED_NO2",
    "PRED_O3_8H"
]:
    test[col] = test[col].clip(lower=0)


# ============================================================
# CPCB / REFERENCE AQI
# ============================================================

test["CPCB_AQI"] = test.apply(
    lambda r: final_aqi(
        r["PM25"],
        r["PM10"],
        r["NO2"],
        r["O3_8H"]
    ),
    axis=1
)


# ============================================================
# AEROVISION AQI
# ============================================================

test["AEROVISION_AQI"] = test.apply(
    lambda r: final_aqi(
        r["PRED_PM25"],
        r["PRED_PM10"],
        r["PRED_NO2"],
        r["PRED_O3_8H"]
    ),
    axis=1
)


test["CPCB_CATEGORY"] = test["CPCB_AQI"].apply(category)
test["AEROVISION_CATEGORY"] = test["AEROVISION_AQI"].apply(category)

test["AQI_DIFFERENCE"] = (
    test["AEROVISION_AQI"]
    -
    test["CPCB_AQI"]
)

test["AQI_ABS_ERROR"] = (
    test["AQI_DIFFERENCE"]
    .abs()
)


# ============================================================
# SUB-INDICES
# ============================================================

for prefix, cols in {

    "CPCB": {
        "PM25": "PM25",
        "PM10": "PM10",
        "NO2": "NO2",
        "O3": "O3_8H"
    },

    "AEROVISION": {
        "PM25": "PRED_PM25",
        "PM10": "PRED_PM10",
        "NO2": "PRED_NO2",
        "O3": "PRED_O3_8H"
    }

}.items():

    for pollutant, source_col in cols.items():

        test[
            f"{prefix}_{pollutant}_SUBINDEX"
        ] = test[source_col].apply(
            lambda x:
                pollutant_subindex(
                    x,
                    pollutant
                )
        )


# ============================================================
# SAVE CLEAN OUTPUT
# ============================================================

output_columns = [
    "station_day_id",
    "date_text",
    "station",
    "city",
    "state",
    "latitude",
    "longitude",

    "PM25",
    "PRED_PM25",

    "PM10",
    "PRED_PM10",

    "NO2",
    "PRED_NO2",

    "O3_8H",
    "PRED_O3_8H",

    "CPCB_PM25_SUBINDEX",
    "AEROVISION_PM25_SUBINDEX",

    "CPCB_PM10_SUBINDEX",
    "AEROVISION_PM10_SUBINDEX",

    "CPCB_NO2_SUBINDEX",
    "AEROVISION_NO2_SUBINDEX",

    "CPCB_O3_SUBINDEX",
    "AEROVISION_O3_SUBINDEX",

    "CPCB_AQI",
    "AEROVISION_AQI",

    "CPCB_CATEGORY",
    "AEROVISION_CATEGORY",

    "AQI_DIFFERENCE",
    "AQI_ABS_ERROR"
]

output_columns = [
    c for c in output_columns
    if c in test.columns
]

test[output_columns].to_csv(
    OUTPUT,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

valid = test.dropna(
    subset=[
        "CPCB_AQI",
        "AEROVISION_AQI"
    ]
)

print("\n" + "=" * 70)
print("AQI COMPARISON READY")
print("=" * 70)

print("Rows:", len(test))
print("Valid AQI comparisons:", len(valid))

if len(valid) > 0:

    print(
        "Mean absolute AQI error:",
        round(
            valid["AQI_ABS_ERROR"].mean(),
            2
        )
    )

    print(
        "Median absolute AQI error:",
        round(
            valid["AQI_ABS_ERROR"].median(),
            2
        )
    )

    print(
        "CPCB mean AQI:",
        round(
            valid["CPCB_AQI"].mean(),
            2
        )
    )

    print(
        "AeroVision mean AQI:",
        round(
            valid["AEROVISION_AQI"].mean(),
            2
        )
    )

    exact_category = (
        valid["CPCB_CATEGORY"]
        ==
        valid["AEROVISION_CATEGORY"]
    ).mean() * 100

    print(
        "AQI category agreement:",
        round(exact_category, 2),
        "%"
    )

print("\nSaved:")
print(OUTPUT)

print("=" * 70)