import os
import pandas as pd
import numpy as np

BASE = r"E:\AeroVision-Real"

INPUT = os.path.join(
    BASE,
    "data",
    "raw",
    "gee_exports",
    "AeroVision_REAL_ML_Dataset_June2026.csv"
)

OUTPUT = os.path.join(
    BASE,
    "data",
    "processed",
    "ml_dataset_real.csv"
)

REPORT = os.path.join(
    BASE,
    "data",
    "processed",
    "ml_dataset_quality.csv"
)

print("=" * 65)
print("AEROVISION REAL ML DATA PREPARATION")
print("=" * 65)

df = pd.read_csv(INPUT)

print("Raw rows:", len(df))

print("\nColumns:")
print(df.columns.tolist())


# ============================================================
# REPLACE GEE MISSING SENTINEL
# ============================================================

df = df.replace(-9999, np.nan)


# ============================================================
# FEATURES
# ============================================================

feature_columns = [
    "AOD",
    "HCHO",
    "SAT_NO2",
    "ERA5_TEMP",
    "ERA5_DEWPOINT",
    "ERA5_RH",
    "WIND_U",
    "WIND_V",
    "WIND_SPEED"
]

# Fire features currently excluded because direct point sampling
# returned no usable values. We will rebuild them as nearby-fire
# features in the next GEE step.

target_columns = [
    "PM25",
    "PM10",
    "NO2",
    "O3"
]


# ============================================================
# NUMERIC CONVERSION
# ============================================================

for col in feature_columns + target_columns:

    if col in df.columns:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )


# ============================================================
# QUALITY REPORT
# ============================================================

quality = []

for col in feature_columns + target_columns:

    if col in df.columns:

        valid = df[col].notna().sum()

        quality.append({
            "column": col,
            "valid_rows": valid,
            "missing_rows": len(df) - valid,
            "coverage_pct": round(
                valid / len(df) * 100,
                2
            )
        })


quality_df = pd.DataFrame(
    quality
)

quality_df.to_csv(
    REPORT,
    index=False
)

print("\nDATA COVERAGE:")
print(
    quality_df.to_string(
        index=False
    )
)


# ============================================================
# REQUIRED IDENTITY FIELDS
# ============================================================

required_identity = [
    "station_day_id",
    "station",
    "date_text"
]

for col in required_identity:

    if col not in df.columns:

        raise ValueError(
            f"Required identity column missing: {col}"
        )


df = df.dropna(
    subset=required_identity
)


# ============================================================
# KEEP ROWS WITH AT LEAST ONE TARGET
# ============================================================

available_targets = [
    c
    for c in target_columns
    if c in df.columns
]

df = df[
    df[available_targets]
    .notna()
    .any(axis=1)
].copy()


# ============================================================
# SORT
# ============================================================

df = df.sort_values(
    [
        "date_text",
        "station"
    ]
)


# ============================================================
# SAVE
# ============================================================

df.to_csv(
    OUTPUT,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 65)
print("REAL ML DATASET READY")
print("=" * 65)

print(
    "Rows retained:",
    len(df)
)

print(
    "Stations:",
    df["station"].nunique()
)

print(
    "Dates:",
    df["date_text"].nunique()
)

for target in available_targets:

    print(
        f"{target} valid targets:",
        df[target].notna().sum()
    )

print("\nSaved:")
print(OUTPUT)

print("\nQuality report:")
print(REPORT)

print("=" * 65)