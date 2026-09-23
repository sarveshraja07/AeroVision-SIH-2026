import os
import numpy as np
import pandas as pd

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    confusion_matrix
)

BASE = r"E:\AeroVision-Real"

INPUT = os.path.join(
    BASE,
    "data",
    "processed",
    "cpcb_vs_aerovision_aqi.csv"
)

OUTPUT_DIR = os.path.join(
    BASE,
    "data",
    "processed",
    "validation"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 75)
print("AEROVISION - AQI VALIDATION DIAGNOSTICS")
print("=" * 75)

df = pd.read_csv(INPUT)

df["date_text"] = pd.to_datetime(
    df["date_text"],
    errors="coerce"
)

# ============================================================
# VALID ROWS
# ============================================================

valid = df.dropna(
    subset=[
        "CPCB_AQI",
        "AEROVISION_AQI"
    ]
).copy()

print("\nValidation rows:", len(valid))

print(
    "Stations:",
    valid["station"].nunique()
)

print(
    "Dates:",
    valid["date_text"].nunique()
)


# ============================================================
# OVERALL AQI METRICS
# ============================================================

actual = valid["CPCB_AQI"]
pred = valid["AEROVISION_AQI"]

mae = mean_absolute_error(
    actual,
    pred
)

rmse = np.sqrt(
    mean_squared_error(
        actual,
        pred
    )
)

r2 = r2_score(
    actual,
    pred
)

correlation = actual.corr(pred)

bias = (
    pred - actual
).mean()

median_error = (
    pred - actual
).median()

median_abs_error = (
    pred - actual
).abs().median()


print("\n" + "=" * 75)
print("OVERALL AQI PERFORMANCE")
print("=" * 75)

print(
    f"MAE                  : {mae:.2f}"
)

print(
    f"RMSE                 : {rmse:.2f}"
)

print(
    f"R²                   : {r2:.3f}"
)

print(
    f"Correlation          : {correlation:.3f}"
)

print(
    f"Mean bias            : {bias:+.2f}"
)

print(
    f"Median error         : {median_error:+.2f}"
)

print(
    f"Median absolute error: {median_abs_error:.2f}"
)


# ============================================================
# CATEGORY AGREEMENT
# ============================================================

valid["CATEGORY_CORRECT"] = (
    valid["CPCB_CATEGORY"]
    ==
    valid["AEROVISION_CATEGORY"]
)

agreement = (
    valid["CATEGORY_CORRECT"].mean()
    * 100
)

print(
    f"\nExact category agreement: "
    f"{agreement:.2f}%"
)


# ============================================================
# CATEGORY CONFUSION MATRIX
# ============================================================

CATEGORY_ORDER = [
    "Good",
    "Satisfactory",
    "Moderate",
    "Poor",
    "Very Poor",
    "Severe"
]

matrix = confusion_matrix(
    valid["CPCB_CATEGORY"],
    valid["AEROVISION_CATEGORY"],
    labels=CATEGORY_ORDER
)

matrix_df = pd.DataFrame(
    matrix,
    index=[
        f"Actual_{x}"
        for x in CATEGORY_ORDER
    ],
    columns=[
        f"Predicted_{x}"
        for x in CATEGORY_ORDER
    ]
)

matrix_path = os.path.join(
    OUTPUT_DIR,
    "aqi_category_confusion_matrix.csv"
)

matrix_df.to_csv(
    matrix_path
)

print("\n" + "=" * 75)
print("AQI CATEGORY CONFUSION MATRIX")
print("=" * 75)

print(
    matrix_df.to_string()
)


# ============================================================
# ERROR COLUMNS
# ============================================================

valid["SIGNED_ERROR"] = (
    valid["AEROVISION_AQI"]
    -
    valid["CPCB_AQI"]
)

valid["ABS_ERROR"] = (
    valid["SIGNED_ERROR"].abs()
)


# ============================================================
# STATION PERFORMANCE
# ============================================================

station_rows = []

for station, group in valid.groupby("station"):

    if len(group) < 2:
        continue

    y = group["CPCB_AQI"]
    p = group["AEROVISION_AQI"]

    station_mae = mean_absolute_error(
        y,
        p
    )

    station_rmse = np.sqrt(
        mean_squared_error(
            y,
            p
        )
    )

    station_bias = (
        p - y
    ).mean()

    station_corr = (
        y.corr(p)
        if len(group) >= 3
        else np.nan
    )

    station_agreement = (
        group["CATEGORY_CORRECT"]
        .mean()
        * 100
    )

    station_rows.append({
        "station": station,
        "city": group["city"].iloc[0],
        "state": group["state"].iloc[0],
        "rows": len(group),
        "mean_cpcb_aqi": y.mean(),
        "mean_aerovision_aqi": p.mean(),
        "MAE": station_mae,
        "RMSE": station_rmse,
        "bias": station_bias,
        "correlation": station_corr,
        "category_agreement_pct":
            station_agreement
    })


station_df = pd.DataFrame(
    station_rows
).sort_values(
    "MAE"
)

station_path = os.path.join(
    OUTPUT_DIR,
    "station_validation.csv"
)

station_df.to_csv(
    station_path,
    index=False
)


print("\n" + "=" * 75)
print("BEST 5 STATIONS BY AQI MAE")
print("=" * 75)

print(
    station_df[
        [
            "station",
            "MAE",
            "bias",
            "category_agreement_pct"
        ]
    ]
    .head(5)
    .round(2)
    .to_string(index=False)
)


print("\n" + "=" * 75)
print("WORST 5 STATIONS BY AQI MAE")
print("=" * 75)

print(
    station_df[
        [
            "station",
            "MAE",
            "bias",
            "category_agreement_pct"
        ]
    ]
    .tail(5)
    .sort_values(
        "MAE",
        ascending=False
    )
    .round(2)
    .to_string(index=False)
)


# ============================================================
# DAILY PERFORMANCE
# ============================================================

daily_rows = []

for date, group in valid.groupby("date_text"):

    y = group["CPCB_AQI"]
    p = group["AEROVISION_AQI"]

    daily_rows.append({

        "date":
            date.strftime("%Y-%m-%d"),

        "rows":
            len(group),

        "CPCB_mean_AQI":
            y.mean(),

        "AeroVision_mean_AQI":
            p.mean(),

        "MAE":
            mean_absolute_error(
                y,
                p
            ),

        "bias":
            (p - y).mean(),

        "category_agreement_pct":
            group[
                "CATEGORY_CORRECT"
            ].mean() * 100
    })


daily_df = pd.DataFrame(
    daily_rows
)

daily_path = os.path.join(
    OUTPUT_DIR,
    "daily_validation.csv"
)

daily_df.to_csv(
    daily_path,
    index=False
)


print("\n" + "=" * 75)
print("DAILY VALIDATION")
print("=" * 75)

print(
    daily_df
    .round(2)
    .to_string(index=False)
)


# ============================================================
# WORST INDIVIDUAL PREDICTIONS
# ============================================================

worst = (
    valid.sort_values(
        "ABS_ERROR",
        ascending=False
    )
    .head(15)
)

worst_path = os.path.join(
    OUTPUT_DIR,
    "worst_predictions.csv"
)

worst.to_csv(
    worst_path,
    index=False
)


print("\n" + "=" * 75)
print("TOP 10 LARGEST AQI ERRORS")
print("=" * 75)

print(
    worst[
        [
            "date_text",
            "station",
            "CPCB_AQI",
            "AEROVISION_AQI",
            "SIGNED_ERROR",
            "ABS_ERROR",
            "CPCB_CATEGORY",
            "AEROVISION_CATEGORY"
        ]
    ]
    .head(10)
    .round(2)
    .to_string(index=False)
)


# ============================================================
# DOMINANT POLLUTANT
# ============================================================

CPCB_SUBS = {
    "PM25": "CPCB_PM25_SUBINDEX",
    "PM10": "CPCB_PM10_SUBINDEX",
    "NO2": "CPCB_NO2_SUBINDEX",
    "O3": "CPCB_O3_SUBINDEX"
}

AERO_SUBS = {
    "PM25": "AEROVISION_PM25_SUBINDEX",
    "PM10": "AEROVISION_PM10_SUBINDEX",
    "NO2": "AEROVISION_NO2_SUBINDEX",
    "O3": "AEROVISION_O3_SUBINDEX"
}


def dominant_pollutant(row, mapping):

    available = {}

    for pollutant, column in mapping.items():

        if (
            column in row.index
            and
            pd.notna(row[column])
        ):
            available[pollutant] = row[column]

    if not available:
        return "Unavailable"

    return max(
        available,
        key=available.get
    )


valid["CPCB_DOMINANT"] = valid.apply(
    lambda row:
        dominant_pollutant(
            row,
            CPCB_SUBS
        ),
    axis=1
)

valid["AEROVISION_DOMINANT"] = valid.apply(
    lambda row:
        dominant_pollutant(
            row,
            AERO_SUBS
        ),
    axis=1
)

valid["DOMINANT_MATCH"] = (
    valid["CPCB_DOMINANT"]
    ==
    valid["AEROVISION_DOMINANT"]
)

dominant_agreement = (
    valid["DOMINANT_MATCH"]
    .mean()
    * 100
)


print("\n" + "=" * 75)
print("DOMINANT POLLUTANT ANALYSIS")
print("=" * 75)

print(
    "Dominant pollutant agreement:",
    round(
        dominant_agreement,
        2
    ),
    "%"
)

print("\nCPCB dominant pollutant counts:")

print(
    valid["CPCB_DOMINANT"]
    .value_counts()
    .to_string()
)

print(
    "\nAeroVision dominant pollutant counts:"
)

print(
    valid["AEROVISION_DOMINANT"]
    .value_counts()
    .to_string()
)


# ============================================================
# POLLUTANT CONCENTRATION PERFORMANCE
# ============================================================

pollutants = [
    (
        "PM25",
        "PM25",
        "PRED_PM25"
    ),
    (
        "PM10",
        "PM10",
        "PRED_PM10"
    ),
    (
        "NO2",
        "NO2",
        "PRED_NO2"
    ),
    (
        "O3_8H",
        "O3_8H",
        "PRED_O3_8H"
    )
]


pollutant_rows = []


for name, actual_col, pred_col in pollutants:

    subset = valid.dropna(
        subset=[
            actual_col,
            pred_col
        ]
    )

    if len(subset) == 0:
        continue

    y = subset[actual_col]
    p = subset[pred_col]

    pollutant_rows.append({

        "pollutant":
            name,

        "rows":
            len(subset),

        "MAE":
            mean_absolute_error(
                y,
                p
            ),

        "RMSE":
            np.sqrt(
                mean_squared_error(
                    y,
                    p
                )
            ),

        "R2":
            r2_score(
                y,
                p
            ),

        "correlation":
            y.corr(p),

        "bias":
            (p - y).mean()
    })


pollutant_df = pd.DataFrame(
    pollutant_rows
)

pollutant_path = os.path.join(
    OUTPUT_DIR,
    "pollutant_validation.csv"
)

pollutant_df.to_csv(
    pollutant_path,
    index=False
)


print("\n" + "=" * 75)
print("POLLUTANT VALIDATION")
print("=" * 75)

print(
    pollutant_df
    .round(3)
    .to_string(index=False)
)


# ============================================================
# SAVE FULL ANALYSIS
# ============================================================

full_path = os.path.join(
    OUTPUT_DIR,
    "aqi_validation_detailed.csv"
)

valid.to_csv(
    full_path,
    index=False
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 75)
print("AEROVISION VALIDATION SUMMARY")
print("=" * 75)

print(
    f"AQI R²                     : {r2:.3f}"
)

print(
    f"AQI correlation            : {correlation:.3f}"
)

print(
    f"AQI MAE                    : {mae:.2f}"
)

print(
    f"AQI RMSE                   : {rmse:.2f}"
)

print(
    f"AQI bias                   : {bias:+.2f}"
)

print(
    f"Category agreement         : {agreement:.2f}%"
)

print(
    f"Dominant pollutant agreement: "
    f"{dominant_agreement:.2f}%"
)

print("\nReports saved in:")
print(OUTPUT_DIR)

print("=" * 75)