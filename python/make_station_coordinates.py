import pandas as pd
import os

BASE = r"E:\AeroVision-Real"

INPUT = os.path.join(
    BASE,
    "data",
    "processed",
    "cpcb_daily_master.csv"
)

OUTPUT = os.path.join(
    BASE,
    "data",
    "processed",
    "station_coordinates.csv"
)

df = pd.read_csv(INPUT)

stations = sorted(
    df["station"]
    .dropna()
    .unique()
)

out = pd.DataFrame({
    "station": stations,
    "latitude": "",
    "longitude": "",
    "city": "",
    "state": ""
})

out.to_csv(
    OUTPUT,
    index=False
)

print("=" * 60)
print("STATION COORDINATE TEMPLATE CREATED")
print("=" * 60)

print("Stations:", len(out))

print("\nSaved to:")
print(OUTPUT)

print("\nColumns:")
print(out.columns.tolist())

print("=" * 60)