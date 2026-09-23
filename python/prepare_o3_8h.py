import os
import glob
import pandas as pd
import numpy as np

BASE = r"E:\AeroVision-Real"

INPUT_DIR = os.path.join(
    BASE,
    "data",
    "raw",
    "cpcb"
)

OUTPUT = os.path.join(
    BASE,
    "data",
    "processed",
    "cpcb_o3_8h_daily.csv"
)

START = pd.Timestamp("2026-06-01 00:00:00")
END   = pd.Timestamp("2026-07-01 00:00:00")

files = glob.glob(
    os.path.join(
        INPUT_DIR,
        "*.csv"
    )
)

print("=" * 65)
print("AEROVISION - CPCB O3 8-HOUR PREPARATION")
print("=" * 65)

print("Files found:", len(files))


def station_from_filename(path):

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

    return name.strip().lower()


all_daily = []


for i, file in enumerate(files, start=1):

    station = station_from_filename(file)

    print(
        f"\n[{i}/{len(files)}] {station}"
    )

    try:

        df = pd.read_csv(file)

    except Exception as e:

        print("  read error:", e)
        continue


    if "Timestamp" not in df.columns:

        print("  missing Timestamp")
        continue


    if "Ozone (µg/m³)" not in df.columns:

        print("  missing Ozone")
        continue


    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"],
        errors="coerce"
    )


    df["O3"] = pd.to_numeric(
        df["Ozone (µg/m³)"],
        errors="coerce"
    )


    df = df[
        (df["Timestamp"] >= START)
        &
        (df["Timestamp"] < END)
    ].copy()


    if len(df) == 0:

        print("  no June rows")
        continue


    # --------------------------------------------------------
    # Basic cleaning
    # --------------------------------------------------------

    df.loc[
        (df["O3"] < 0)
        |
        (df["O3"] > 1000),
        "O3"
    ] = np.nan


    df = df.sort_values(
        "Timestamp"
    )


    # --------------------------------------------------------
    # Rolling 8-hour mean
    #
    # Require at least 6 valid hourly values out of 8.
    # --------------------------------------------------------

    df["O3_8H"] = (
        df["O3"]
        .rolling(
            window=8,
            min_periods=6
        )
        .mean()
    )


    # --------------------------------------------------------
    # Assign rolling result to day based on window end time
    # --------------------------------------------------------

    df["date"] = (
        df["Timestamp"]
        .dt.date
    )


    # --------------------------------------------------------
    # Daily maximum 8-hour average
    # --------------------------------------------------------

    daily = (
        df.groupby(
            "date",
            as_index=False
        )
        .agg(
            O3_8H_MAX=(
                "O3_8H",
                "max"
            ),
            O3_VALID_HOURS=(
                "O3",
                "count"
            )
        )
    )


    daily["station"] = station


    # --------------------------------------------------------
    # Keep daily O3 only if enough hourly observations exist
    #
    # 18/24 = 75% daily coverage
    # --------------------------------------------------------

    daily.loc[
        daily["O3_VALID_HOURS"] < 18,
        "O3_8H_MAX"
    ] = np.nan


    all_daily.append(
        daily
    )


if not all_daily:

    raise RuntimeError(
        "No usable O3 data generated."
    )


result = pd.concat(
    all_daily,
    ignore_index=True
)


result = result[
    [
        "station",
        "date",
        "O3_8H_MAX",
        "O3_VALID_HOURS"
    ]
]


result = result.sort_values(
    [
        "station",
        "date"
    ]
)


result.to_csv(
    OUTPUT,
    index=False
)


print("\n" + "=" * 65)
print("O3 8-HOUR DATA READY")
print("=" * 65)

print(
    "Rows:",
    len(result)
)

print(
    "Stations:",
    result["station"].nunique()
)

print(
    "Valid O3 8H targets:",
    result["O3_8H_MAX"]
    .notna()
    .sum()
)

print(
    "Date range:",
    result["date"].min(),
    "to",
    result["date"].max()
)

print("\nSaved:")
print(OUTPUT)

print("=" * 65)