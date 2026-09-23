import os
import glob
import pandas as pd
import numpy as np

# ============================================================
# AEROVISION INDIA
# CPCB PREPARATION PIPELINE
# Period: 01 June 2026 - 30 June 2026
# ============================================================

BASE_DIR = r"E:\AeroVision-Real"

INPUT_DIR = os.path.join(
    BASE_DIR,
    "data",
    "raw",
    "cpcb"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "data",
    "processed"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

START_DATE = pd.Timestamp("2026-06-01 00:00:00")
END_DATE = pd.Timestamp("2026-07-01 00:00:00")


# ============================================================
# REQUIRED COLUMNS
# ============================================================

COLUMN_MAP = {
    "PM2.5 (µg/m³)": "PM25",
    "PM10 (µg/m³)": "PM10",
    "NO2 (µg/m³)": "NO2",
    "Ozone (µg/m³)": "O3",
    "AT (°C)": "CPCB_TEMP",
    "RH (%)": "CPCB_RH",
    "WS (m/s)": "CPCB_WS",
    "WD (deg)": "CPCB_WD"
}


# ============================================================
# STATION NAME FROM FILE
# ============================================================

def station_name_from_filename(path):

    name = os.path.basename(path)

    name = name.replace(
        "raw_data_hourly_",
        ""
    )

    name = name.replace(
        "_1H.csv",
        ""
    )

    name = name.replace(
        "_",
        " "
    )

    return name.strip()


# ============================================================
# LOAD ALL FILES
# ============================================================

files = glob.glob(
    os.path.join(
        INPUT_DIR,
        "*.csv"
    )
)

print("=" * 60)
print("AEROVISION CPCB PREPARATION")
print("=" * 60)

print("CPCB files found:", len(files))

if len(files) == 0:
    raise FileNotFoundError(
        "No CPCB CSV files found."
    )


all_hourly = []
quality_rows = []


# ============================================================
# PROCESS EACH STATION
# ============================================================

for index, file in enumerate(files, start=1):

    station = station_name_from_filename(file)

    print(
        f"\n[{index}/{len(files)}] {station}"
    )

    try:

        df = pd.read_csv(file)

    except Exception as e:

        print(
            "  ❌ Could not read:",
            e
        )

        continue


    # --------------------------------------------------------
    # Timestamp
    # --------------------------------------------------------

    if "Timestamp" not in df.columns:

        print(
            "  ❌ Timestamp column missing"
        )

        continue


    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"],
        errors="coerce"
    )


    # --------------------------------------------------------
    # Filter exact June period
    # --------------------------------------------------------

    df = df[
        (df["Timestamp"] >= START_DATE)
        &
        (df["Timestamp"] < END_DATE)
    ].copy()


    print(
        "  June hourly rows:",
        len(df)
    )


    if len(df) == 0:

        print(
            "  ⚠ No June 2026 observations"
        )

        continue


    # --------------------------------------------------------
    # Keep only available columns
    # --------------------------------------------------------

    available_original = [
        col
        for col in COLUMN_MAP
        if col in df.columns
    ]


    df = df[
        ["Timestamp"]
        +
        available_original
    ].copy()


    df = df.rename(
        columns=COLUMN_MAP
    )


    # --------------------------------------------------------
    # Add station identity
    # --------------------------------------------------------

    df["station"] = station


    # --------------------------------------------------------
    # Make pollutants numeric
    # --------------------------------------------------------

    numeric_columns = [
        "PM25",
        "PM10",
        "NO2",
        "O3",
        "CPCB_TEMP",
        "CPCB_RH",
        "CPCB_WS",
        "CPCB_WD"
    ]


    for col in numeric_columns:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )


    # --------------------------------------------------------
    # Basic impossible-value cleaning
    # --------------------------------------------------------

    if "PM25" in df.columns:
        df.loc[
            (df["PM25"] < 0)
            |
            (df["PM25"] > 1000),
            "PM25"
        ] = np.nan


    if "PM10" in df.columns:
        df.loc[
            (df["PM10"] < 0)
            |
            (df["PM10"] > 1500),
            "PM10"
        ] = np.nan


    if "NO2" in df.columns:
        df.loc[
            (df["NO2"] < 0)
            |
            (df["NO2"] > 1000),
            "NO2"
        ] = np.nan


    if "O3" in df.columns:
        df.loc[
            (df["O3"] < 0)
            |
            (df["O3"] > 1000),
            "O3"
        ] = np.nan


    if "CPCB_RH" in df.columns:
        df.loc[
            (df["CPCB_RH"] < 0)
            |
            (df["CPCB_RH"] > 100),
            "CPCB_RH"
        ] = np.nan


    if "CPCB_WS" in df.columns:
        df.loc[
            df["CPCB_WS"] < 0,
            "CPCB_WS"
        ] = np.nan


    # --------------------------------------------------------
    # Quality report
    # --------------------------------------------------------

    quality = {
        "station": station,
        "hourly_rows": len(df)
    }


    for pollutant in [
        "PM25",
        "PM10",
        "NO2",
        "O3"
    ]:

        if pollutant in df.columns:

            valid = df[pollutant].notna().sum()

            quality[
                pollutant + "_valid_hours"
            ] = valid

            quality[
                pollutant + "_coverage_pct"
            ] = round(
                valid
                /
                len(df)
                *
                100,
                1
            )

        else:

            quality[
                pollutant + "_valid_hours"
            ] = 0

            quality[
                pollutant + "_coverage_pct"
            ] = 0


    quality_rows.append(
        quality
    )

    all_hourly.append(
        df
    )


# ============================================================
# MERGE HOURLY DATA
# ============================================================

if len(all_hourly) == 0:

    raise RuntimeError(
        "No usable CPCB data was found."
    )


hourly_master = pd.concat(
    all_hourly,
    ignore_index=True
)


hourly_master = hourly_master.sort_values(
    [
        "station",
        "Timestamp"
    ]
)


hourly_output = os.path.join(
    OUTPUT_DIR,
    "cpcb_hourly_master.csv"
)


hourly_master.to_csv(
    hourly_output,
    index=False
)


# ============================================================
# DAILY AGGREGATION
# ============================================================

hourly_master["date"] = (
    hourly_master["Timestamp"]
    .dt.date
)


aggregation_columns = [
    col
    for col in [
        "PM25",
        "PM10",
        "NO2",
        "O3",
        "CPCB_TEMP",
        "CPCB_RH",
        "CPCB_WS",
        "CPCB_WD"
    ]
    if col in hourly_master.columns
]


daily = (
    hourly_master
    .groupby(
        [
            "station",
            "date"
        ],
        as_index=False
    )[aggregation_columns]
    .mean()
)


# ============================================================
# ADD DAILY VALID-HOUR COUNTS
# ============================================================

for pollutant in [
    "PM25",
    "PM10",
    "NO2",
    "O3"
]:

    if pollutant in hourly_master.columns:

        counts = (
            hourly_master
            .groupby(
                [
                    "station",
                    "date"
                ]
            )[pollutant]
            .count()
            .reset_index(
                name=pollutant
                +
                "_valid_hours"
            )
        )


        daily = daily.merge(
            counts,
            on=[
                "station",
                "date"
            ],
            how="left"
        )


# ============================================================
# MINIMUM DAILY COVERAGE
#
# Keep pollutant daily mean only if at least 18 of 24
# hourly values are available (~75%).
# ============================================================

MIN_HOURS = 18


for pollutant in [
    "PM25",
    "PM10",
    "NO2",
    "O3"
]:

    hours_col = (
        pollutant
        +
        "_valid_hours"
    )

    if (
        pollutant in daily.columns
        and
        hours_col in daily.columns
    ):

        daily.loc[
            daily[hours_col] < MIN_HOURS,
            pollutant
        ] = np.nan


# ============================================================
# SAVE DAILY MASTER
# ============================================================

daily_output = os.path.join(
    OUTPUT_DIR,
    "cpcb_daily_master.csv"
)


daily.to_csv(
    daily_output,
    index=False
)


# ============================================================
# SAVE QUALITY REPORT
# ============================================================

quality_df = pd.DataFrame(
    quality_rows
)


quality_df = quality_df.sort_values(
    "station"
)


quality_output = os.path.join(
    OUTPUT_DIR,
    "cpcb_station_quality.csv"
)


quality_df.to_csv(
    quality_output,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n")
print("=" * 60)
print("CPCB PROCESSING COMPLETE")
print("=" * 60)

print(
    "Stations processed:",
    hourly_master["station"].nunique()
)

print(
    "Hourly observations:",
    len(hourly_master)
)

print(
    "Daily station records:",
    len(daily)
)

print("\nVALID DAILY TARGETS:")

for pollutant in [
    "PM25",
    "PM10",
    "NO2",
    "O3"
]:

    if pollutant in daily.columns:

        print(
            pollutant,
            ":",
            daily[pollutant]
            .notna()
            .sum()
        )


print("\nOUTPUT FILES:")

print(hourly_output)
print(daily_output)
print(quality_output)

print("=" * 60)