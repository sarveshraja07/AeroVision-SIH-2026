import os
import pandas as pd

BASE = r"E:\AeroVision-Real"

ML_FILE = os.path.join(
    BASE,
    "data",
    "processed",
    "final_ml_dataset.csv"
)

COORD_FILE = os.path.join(
    BASE,
    "data",
    "processed",
    "station_coordinates.csv"
)

OUTPUT = os.path.join(
    BASE,
    "data",
    "processed",
    "final_ml_dataset_v2.csv"
)

ml = pd.read_csv(ML_FILE)
coords = pd.read_csv(COORD_FILE)

ml["station"] = (
    ml["station"]
    .astype(str)
    .str.strip()
    .str.lower()
)

coords["station"] = (
    coords["station"]
    .astype(str)
    .str.strip()
    .str.lower()
)

# Remove old coordinates if somehow present
for col in ["latitude", "longitude"]:
    if col in ml.columns:
        ml = ml.drop(columns=[col])

ml = ml.merge(
    coords[
        [
            "station",
            "latitude",
            "longitude"
        ]
    ],
    on="station",
    how="left",
    validate="many_to_one"
)

print("=" * 60)
print("ADDING SPATIAL FEATURES")
print("=" * 60)

print("Rows:", len(ml))
print(
    "Rows with coordinates:",
    ml["latitude"].notna().sum()
)

print(
    "Missing coordinates:",
    ml["latitude"].isna().sum()
)

print(
    "\nLatitude range:",
    ml["latitude"].min(),
    "to",
    ml["latitude"].max()
)

print(
    "Longitude range:",
    ml["longitude"].min(),
    "to",
    ml["longitude"].max()
)

ml.to_csv(
    OUTPUT,
    index=False
)

print("\nSaved:")
print(OUTPUT)