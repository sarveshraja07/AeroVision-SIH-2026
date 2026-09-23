import os
import re
import time
import math
import requests
import pandas as pd
from difflib import SequenceMatcher

BASE = r"E:\AeroVision-Real"

INPUT = os.path.join(
    BASE,
    "data",
    "processed",
    "station_coordinates_verified.csv"
)

OUTPUT = INPUT

API_URL = (
    "https://api.data.gov.in/resource/"
    "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
)

# Public/demo key previously used for this OGD resource.
API_KEY = "579b464db66ec23bdd0000017d0WN0HXzcUDg5Jq"


# ============================================================
# NORMALIZE STATION NAME
# ============================================================

def normalize(text):

    if pd.isna(text):
        return ""

    text = str(text).lower()

    # Remove agency suffix
    text = re.sub(
        r"\s*-\s*(dpcc|cpcb|ppcb|hspcb|iitm|imd)\s*$",
        "",
        text
    )

    text = text.replace("&", "and")

    text = re.sub(
        r"[^a-z0-9 ]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# HAVERSINE DISTANCE
# ============================================================

def haversine(lat1, lon1, lat2, lon2):

    R = 6371.0

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(p1)
        *
        math.cos(p2)
        *
        math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return R * c


# ============================================================
# API QUERY WITH RETRIES
# ============================================================

def fetch_city(state, city):

    print(
        f"\nDownloading official metadata: "
        f"{city}, {state}"
    )

    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 500,
        "offset": 0,
        "filters[state]": state,
        "filters[city]": city
    }

    for attempt in range(1, 5):

        try:

            response = requests.get(
                API_URL,
                params=params,
                timeout=60
            )

            response.raise_for_status()

            data = response.json()

            records = data.get(
                "records",
                []
            )

            print(
                f"  ✓ Records received: {len(records)}"
            )

            return records

        except Exception as e:

            print(
                f"  Attempt {attempt}/4 failed:",
                e
            )

            if attempt < 4:
                time.sleep(
                    attempt * 4
                )

    return []


# ============================================================
# LOAD OUR COORDINATES
# ============================================================

df = pd.read_csv(INPUT)

print("=" * 72)
print("AEROVISION CPCB COORDINATE VERIFICATION")
print("=" * 72)

print(
    "Stations to verify:",
    len(df)
)


# Make sure verification columns have correct types

for c in [
    "coordinate_status",
    "coordinate_source"
]:
    df[c] = df[c].astype("string")


for c in [
    "verified_latitude",
    "verified_longitude",
    "coordinate_difference_km"
]:
    df[c] = pd.to_numeric(
        df[c],
        errors="coerce"
    )


# ============================================================
# QUERY ONLY UNIQUE CITY/STATE PAIRS
# ============================================================

pairs = (
    df[
        [
            "state",
            "city"
        ]
    ]
    .drop_duplicates()
    .dropna()
)


official_records = []


for _, row in pairs.iterrows():

    state = str(
        row["state"]
    ).strip()

    city = str(
        row["city"]
    ).strip()

    records = fetch_city(
        state,
        city
    )

    official_records.extend(
        records
    )

    # Be polite to API
    time.sleep(1)


# ============================================================
# BUILD OFFICIAL METADATA TABLE
# ============================================================

if len(official_records) == 0:

    raise RuntimeError(
        "No official station metadata could be downloaded."
    )


official = pd.DataFrame(
    official_records
)


print("\nOfficial API columns:")
print(
    official.columns.tolist()
)


required = [
    "station",
    "latitude",
    "longitude",
    "city",
    "state"
]


for col in required:

    if col not in official.columns:

        raise ValueError(
            f"Official API missing column: {col}"
        )


official["latitude"] = pd.to_numeric(
    official["latitude"],
    errors="coerce"
)

official["longitude"] = pd.to_numeric(
    official["longitude"],
    errors="coerce"
)


official = official.dropna(
    subset=[
        "station",
        "latitude",
        "longitude"
    ]
)


official["station_norm"] = (
    official["station"]
    .apply(normalize)
)


# Multiple pollutant rows refer to same station.
official = official.drop_duplicates(
    subset=[
        "station_norm",
        "latitude",
        "longitude"
    ]
)


print(
    "\nUnique official station locations downloaded:",
    len(official)
)


# ============================================================
# MATCH EACH OF OUR 26 STATIONS
# ============================================================

verified_count = 0
review_count = 0
unmatched_count = 0


for i, row in df.iterrows():

    station = str(
        row["station"]
    ).strip()

    state = str(
        row["state"]
    ).strip()

    city = str(
        row["city"]
    ).strip()


    target = normalize(
        station
    )


    # Restrict candidates to same city/state first

    candidates = official[
        (
            official["state"]
            .astype(str)
            .str.lower()
            ==
            state.lower()
        )
        &
        (
            official["city"]
            .astype(str)
            .str.lower()
            ==
            city.lower()
        )
    ].copy()


    # If city spelling differs in API,
    # fall back to same state.

    if len(candidates) == 0:

        candidates = official[
            official["state"]
            .astype(str)
            .str.lower()
            ==
            state.lower()
        ].copy()


    best = None
    best_score = 0.0


    for _, candidate in candidates.iterrows():

        score = SequenceMatcher(
            None,
            target,
            candidate["station_norm"]
        ).ratio()


        if score > best_score:

            best_score = score
            best = candidate


    print(
        "\n----------------------------------------"
    )

    print(
        station
    )


    if best is None or best_score < 0.65:

        print(
            "  ❌ No confident official match"
        )

        df.at[
            i,
            "coordinate_status"
        ] = "UNMATCHED"

        df.at[
            i,
            "coordinate_source"
        ] = "CPCB/Data.gov.in"

        unmatched_count += 1

        continue


    verified_lat = float(
        best["latitude"]
    )

    verified_lon = float(
        best["longitude"]
    )


    original_lat = float(
        row["latitude"]
    )

    original_lon = float(
        row["longitude"]
    )


    difference = haversine(
        original_lat,
        original_lon,
        verified_lat,
        verified_lon
    )


    df.at[
        i,
        "verified_latitude"
    ] = verified_lat


    df.at[
        i,
        "verified_longitude"
    ] = verified_lon


    df.at[
        i,
        "coordinate_difference_km"
    ] = round(
        difference,
        3
    )


    df.at[
        i,
        "coordinate_source"
    ] = "CPCB/Data.gov.in"


    # ========================================================
    # STATUS
    #
    # <= 1 km → acceptable verification
    # 1–3 km  → needs review
    # > 3 km  → coordinate should be replaced
    # ========================================================

    if difference <= 1.0:

        status = "VERIFIED"

        verified_count += 1

    elif difference <= 3.0:

        status = "REVIEW"

        review_count += 1

    else:

        status = "MISMATCH"

        review_count += 1


    df.at[
        i,
        "coordinate_status"
    ] = status


    print(
        "  Official match:",
        best["station"]
    )

    print(
        "  Match score:",
        round(best_score, 3)
    )

    print(
        "  Current:",
        original_lat,
        original_lon
    )

    print(
        "  Official:",
        verified_lat,
        verified_lon
    )

    print(
        "  Difference:",
        round(difference, 3),
        "km"
    )

    print(
        "  Status:",
        status
    )


# ============================================================
# SAVE
# ============================================================

df.to_csv(
    OUTPUT,
    index=False
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n")
print("=" * 72)
print("COORDINATE VERIFICATION COMPLETE")
print("=" * 72)


print(
    "VERIFIED:",
    (
        df["coordinate_status"]
        ==
        "VERIFIED"
    ).sum()
)


print(
    "REVIEW:",
    (
        df["coordinate_status"]
        ==
        "REVIEW"
    ).sum()
)


print(
    "MISMATCH:",
    (
        df["coordinate_status"]
        ==
        "MISMATCH"
    ).sum()
)


print(
    "UNMATCHED:",
    (
        df["coordinate_status"]
        ==
        "UNMATCHED"
    ).sum()
)


print("\nSaved:")
print(
    OUTPUT
)


print(
    "\nStations requiring attention:"
)


attention = df[
    df["coordinate_status"]
    !=
    "VERIFIED"
][
    [
        "station",
        "coordinate_status",
        "coordinate_difference_km"
    ]
]


if len(attention) == 0:

    print(
        "None — all coordinates verified."
    )

else:

    print(
        attention.to_string(
            index=False
        )
    )


print("=" * 72)