import os
import pandas as pd

BASE = r"E:\AeroVision-Real"

DAILY = os.path.join(
    BASE,
    "data",
    "processed",
    "cpcb_daily_master.csv"
)

COORDS = os.path.join(
    BASE,
    "data",
    "processed",
    "station_coordinates.csv"
)

OUTPUT = os.path.join(
    BASE,
    "data",
    "processed",
    "gee_station_days.csv"
)

# ============================================================
# LOAD
# ============================================================

daily = pd.read_csv(DAILY)
coords = pd.read_csv(COORDS)

print("=" * 60)
print("BUILDING GEE STATION-DAY TABLE")
print("=" * 60)

print("Daily rows:", len(daily))
print("Coordinate rows:", len(coords))


# ============================================================
# NORMALIZE STATION NAMES
# ============================================================

daily["station"] = (
    daily["station"]
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


# ============================================================
# MERGE
# ============================================================

df = daily.merge(
    coords[
        [
            "station",
            "latitude",
            "longitude",
            "city",
            "state"
        ]
    ],
    on="station",
    how="left"
)


# ============================================================
# CHECK MISSING COORDINATES
# ============================================================

missing = df[
    df["latitude"].isna()
    |
    df["longitude"].isna()
]

if len(missing) > 0:

    print("\n❌ Missing coordinates for:")

    print(
        missing["station"]
        .drop_duplicates()
        .to_string(index=False)
    )

    raise RuntimeError(
        "Some station coordinates are missing."
    )


# ============================================================
# FORMAT DATE
# ============================================================

df["date"] = pd.to_datetime(
    df["date"],
    errors="coerce"
)

df["date"] = df["date"].dt.strftime(
    "%Y-%m-%d"
)


# ============================================================
# CREATE UNIQUE ID
# ============================================================

df["station_day_id"] = (
    df["station"]
    .str.replace(
        r"[^a-z0-9]+",
        "_",
        regex=True
    )
    .str.strip("_")
    +
    "_"
    +
    df["date"]
)


# ============================================================
# KEEP REQUIRED COLUMNS
# ============================================================

columns = [
    "station_day_id",
    "date",
    "station",
    "city",
    "state",
    "latitude",
    "longitude",

    "PM25",
    "PM10",
    "NO2",
    "O3",

    "CPCB_TEMP",
    "CPCB_RH",
    "CPCB_WS",
    "CPCB_WD",

    "PM25_valid_hours",
    "PM10_valid_hours",
    "NO2_valid_hours",
    "O3_valid_hours"
]

columns = [
    c for c in columns
    if c in df.columns
]

df = df[columns].copy()


# ============================================================
# SORT
# ============================================================

df = df.sort_values(
    [
        "date",
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

print("\n" + "=" * 60)
print("GEE STATION-DAY TABLE READY")
print("=" * 60)

print("Rows:", len(df))
print("Stations:", df["station"].nunique())
print("Dates:", df["date"].nunique())

print(
    "From:",
    df["date"].min()
)

print(
    "To:",
    df["date"].max()
)

print("\nSaved:")
print(OUTPUT)

print("\nPreview:")
print(
    df.head(10).to_string(index=False)
)

print("=" * 60)