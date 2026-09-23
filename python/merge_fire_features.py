import os
import pandas as pd
import numpy as np

BASE = r"E:\AeroVision-Real"

ML_FILE = os.path.join(
    BASE,
    "data",
    "processed",
    "ml_dataset_real.csv"
)

FIRE_FILE = os.path.join(
    BASE,
    "data",
    "raw",
    "gee_exports",
    "AeroVision_Fire_Station_Features_June2026.csv"
)

OUTPUT = os.path.join(
    BASE,
    "data",
    "processed",
    "final_ml_dataset.csv"
)

print("=" * 65)
print("AEROVISION - MERGING FIRE FEATURES")
print("=" * 65)

ml = pd.read_csv(ML_FILE)
fire = pd.read_csv(FIRE_FILE)

print("ML rows   :", len(ml))
print("Fire rows :", len(fire))

# ============================================================
# CHECK ID COLUMN
# ============================================================

if "station_day_id" not in ml.columns:
    raise ValueError("station_day_id missing from ML file")

if "station_day_id" not in fire.columns:
    raise ValueError("station_day_id missing from fire file")


# ============================================================
# KEEP ONLY FIRE FEATURES WE NEED
# ============================================================

required_fire = [
    "station_day_id",
    "FIRE_COUNT_25KM",
    "FIRE_CONF_MAX_25KM",
    "FIRE_T21_MAX_25KM"
]

missing = [
    c for c in required_fire
    if c not in fire.columns
]

if missing:
    raise ValueError(
        f"Missing fire columns: {missing}"
    )

fire = fire[required_fire].copy()


# ============================================================
# REMOVE DUPLICATES IF ANY
# ============================================================

fire = fire.drop_duplicates(
    subset=["station_day_id"]
)


# ============================================================
# MERGE
# ============================================================

df = ml.merge(
    fire,
    on="station_day_id",
    how="left",
    validate="one_to_one"
)


# ============================================================
# FIRE FEATURE CLEANING
#
# If there is no nearby detection,
# zero is scientifically meaningful.
# ============================================================

fire_cols = [
    "FIRE_COUNT_25KM",
    "FIRE_CONF_MAX_25KM",
    "FIRE_T21_MAX_25KM"
]

for col in fire_cols:

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

    df[col] = df[col].fillna(0)


# ============================================================
# SANITY CHECKS
# ============================================================

print("\nFIRE FEATURE SUMMARY")

print(
    df[fire_cols]
    .describe()
    .round(2)
    .to_string()
)

print(
    "\nRows with nearby fire:",
    (df["FIRE_COUNT_25KM"] > 0).sum()
)

print(
    "Rows without nearby fire:",
    (df["FIRE_COUNT_25KM"] == 0).sum()
)


# ============================================================
# SAVE
# ============================================================

df.to_csv(
    OUTPUT,
    index=False
)

print("\n" + "=" * 65)
print("FINAL REAL ML DATASET READY")
print("=" * 65)

print("Rows:", len(df))
print("Columns:", len(df.columns))

print("\nSaved:")
print(OUTPUT)

print("=" * 65)