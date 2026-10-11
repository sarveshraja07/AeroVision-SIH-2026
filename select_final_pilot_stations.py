import pandas as pd
from pathlib import Path

CLEAN = Path(
    r"E:\AeroVision-CPCB-2026\04_cleaned\CPCB_2026_CLEAN_MASTER.csv"
)

COORD = Path(
    r"E:\AeroVision-CPCB-2026\05_station_metadata\CPCB_COORDINATE_LOOKUP_FINAL.csv"
)

POLLUTANTS = ["PM25", "PM10", "NO2", "O3", "SO2", "CO", "NH3"]

cols = ["timestamp", "site_id"] + POLLUTANTS

parts = []

print("Reading CPCB data...")

for chunk in pd.read_csv(
    CLEAN,
    usecols=cols,
    dtype={"site_id": str},
    parse_dates=["timestamp"],
    chunksize=200000
):
    chunk["date"] = chunk["timestamp"].dt.date

    # Require the four core pollutants for pilot selection
    chunk["core_valid"] = chunk[
        ["PM25", "PM10", "NO2", "O3"]
    ].notna().all(axis=1)

    x = (
        chunk.groupby(["site_id", "date"])
        .agg(
            valid_core_hours=("core_valid", "sum")
        )
        .reset_index()
    )

    parts.append(x)

daily = pd.concat(parts, ignore_index=True)

# Because chunks can split station-days, combine again
daily = (
    daily.groupby(["site_id", "date"], as_index=False)
    ["valid_core_hours"]
    .sum()
)

# Strong day = at least 18/24 hours where
# PM2.5 + PM10 + NO2 + O3 are all available
daily["strong_day"] = daily["valid_core_hours"] >= 18

station_score = (
    daily.groupby("site_id")
    .agg(
        strong_days=("strong_day", "sum"),
        total_core_hours=("valid_core_hours", "sum")
    )
    .reset_index()
)

coords = pd.read_csv(
    COORD,
    dtype={"site_id": str}
)

meta_cols = [
    "site_id",
    "station_location_text",
    "state_folder",
    "latitude",
    "longitude"
]

ranking = station_score.merge(
    coords[meta_cols],
    on="site_id",
    how="inner"
)

ranking = ranking.sort_values(
    ["strong_days", "total_core_hours"],
    ascending=False
)

print("\nTOP 20 HIGH-COVERAGE STATIONS:")
print(
    ranking[
        [
            "site_id",
            "station_location_text",
            "state_folder",
            "strong_days",
            "total_core_hours",
            "latitude",
            "longitude"
        ]
    ].head(20).to_string(index=False)
)

# Select best station from each different state
selected = (
    ranking
    .drop_duplicates("state_folder")
    .head(3)
)

print("\n================================")
print("SELECTED 3 PILOT STATIONS")
print("================================")

print(
    selected[
        [
            "site_id",
            "station_location_text",
            "state_folder",
            "strong_days",
            "total_core_hours",
            "latitude",
            "longitude"
        ]
    ].to_string(index=False)
)

# Find dates where all selected stations have >=18 valid core hours
ids = set(selected["site_id"])

overlap = daily[daily["site_id"].isin(ids)].copy()

good = overlap[
    overlap["valid_core_hours"] >= 18
]

date_score = (
    good.groupby("date")
    .agg(
        stations=("site_id", "nunique"),
        minimum_hours=("valid_core_hours", "min"),
        total_hours=("valid_core_hours", "sum")
    )
)

date_score = date_score[
    date_score["stations"] == 3
].sort_values(
    ["minimum_hours", "total_hours"],
    ascending=False
)

print("\n================================")
print("COMMON HIGH-QUALITY DATES")
print("================================")

print(date_score.head(10).to_string())

if len(date_score):

    best = date_score.index[0]

    print("\nBEST PILOT DATE:", best)

    print("\nCOVERAGE ON BEST DATE:")

    print(
        overlap[overlap["date"] == best]
        [["site_id", "date", "valid_core_hours"]]
        .to_string(index=False)
    )

else:
    print("\nNo common >=18-hour date found.")
