import pandas as pd
import os

BASE = r"E:\AeroVision-Real"

INPUT = os.path.join(
    BASE,
    "data",
    "processed",
    "station_coordinates.csv"
)

OUTPUT = INPUT


# ============================================================
# STATION COORDINATE LOOKUP
# Keep your existing coordinates here
# ============================================================

coords = {
    "alipur, delhi - dpcc":
        (28.815329, 77.153010, "Delhi", "Delhi"),

    "anand vihar, delhi - dpcc":
        (28.646835, 77.316032, "Delhi", "Delhi"),

    "ashok vihar, delhi - dpcc":
        (28.695381, 77.181665, "Delhi", "Delhi"),

    "bawana, delhi - dpcc":
        (28.776200, 77.051074, "Delhi", "Delhi"),

    "civil line, jalandhar - ppcb":
        (31.326000, 75.576000, "Jalandhar", "Punjab"),

    "golden temple, amritsar - ppcb":
        (31.620000, 74.876000, "Amritsar", "Punjab"),

    "hardev nagar, bathinda - ppcb":
        (30.211000, 74.945000, "Bathinda", "Punjab"),

    "ito, delhi - cpcb":
        (28.628624, 77.241060, "Delhi", "Delhi"),

    "mandir marg, delhi - dpcc":
        (28.636429, 77.201067, "Delhi", "Delhi"),

    "model town, patiala - ppcb":
        (30.339800, 76.386900, "Patiala", "Punjab"),

    "mundka, delhi - dpcc":
        (28.684678, 77.076574, "Delhi", "Delhi"),

    "murthal, sonipat - hspcb":
        (29.027200, 77.062100, "Sonipat", "Haryana"),

    "najafgarh, delhi - dpcc":
        (28.570173, 76.933762, "Delhi", "Delhi"),

    "narela, delhi - dpcc":
        (28.822836, 77.101981, "Delhi", "Delhi"),

    "new industrial town, faridabad - hspcb":
        (28.390720, 77.300590, "Faridabad", "Haryana"),

    "nise gwal pahari, gurugram - iitm":
        (28.425010, 77.148190, "Gurugram", "Haryana"),

    "patti mehar, ambala - hspcb":
        (30.377600, 76.776900, "Ambala", "Haryana"),

    "punjab agricultural university, ludhiana - ppcb":
        (30.902800, 75.808600, "Ludhiana", "Punjab"),

    "punjabi bagh, delhi - dpcc":
        (28.674045, 77.131023, "Delhi", "Delhi"),

    "r k puram, delhi - dpcc":
        (28.563262, 77.186937, "Delhi", "Delhi"),

    "rimt university, mandi gobindgarh - ppcb":
        (30.651000, 76.293000, "Mandi Gobindgarh", "Punjab"),

    "rohini, delhi - dpcc":
        (28.732820, 77.119920, "Delhi", "Delhi"),

    "sector 11, faridabad - hspcb":
        (28.376060, 77.315740, "Faridabad", "Haryana"),

    "sector 30, faridabad - hspcb":
        (28.450124, 77.308500, "Faridabad", "Haryana"),

    "teri gram, gurugram - hspcb":
        (28.423000, 77.146500, "Gurugram", "Haryana"),

    "vikas sadan, gurugram - hspcb":
        (28.450000, 77.026000, "Gurugram", "Haryana"),
}


# ============================================================
# LOAD FILE
# ============================================================

df = pd.read_csv(INPUT)


# ============================================================
# FIX COLUMN DATA TYPES
# ============================================================

# Numeric columns
df["latitude"] = pd.to_numeric(
    df["latitude"],
    errors="coerce"
)

df["longitude"] = pd.to_numeric(
    df["longitude"],
    errors="coerce"
)

# Text columns
df["station"] = df["station"].astype("string")
df["city"] = df["city"].astype("string")
df["state"] = df["state"].astype("string")


# ============================================================
# FILL VALUES
# ============================================================

filled = 0
missing = []

for i, row in df.iterrows():

    station = str(row["station"]).strip().lower()

    if station in coords:

        lat, lon, city, state = coords[station]

        df.at[i, "latitude"] = float(lat)
        df.at[i, "longitude"] = float(lon)
        df.at[i, "city"] = city
        df.at[i, "state"] = state

        filled += 1

    else:

        missing.append(station)


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

print("=" * 60)
print("STATION COORDINATES FILLED")
print("=" * 60)

print(
    "Filled:",
    filled,
    "/",
    len(df)
)

print(
    "Missing:",
    len(missing)
)

if missing:

    print("\nMissing stations:")

    for station in missing:
        print(" -", station)

print("\nSaved:")
print(OUTPUT)

print("\nPreview:")
print(
    df[
        [
            "station",
            "latitude",
            "longitude",
            "city",
            "state"
        ]
    ].to_string(index=False)
)

print("=" * 60)