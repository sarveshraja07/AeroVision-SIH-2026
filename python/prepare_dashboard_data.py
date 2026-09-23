import os
import json
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

BASE = r"E:\AeroVision-Real"

PROCESSED = os.path.join(BASE, "data", "processed")
EXPORTS = os.path.join(BASE, "data", "exports")

os.makedirs(EXPORTS, exist_ok=True)

AQI_FILE = os.path.join(
    PROCESSED,
    "cpcb_vs_aerovision_aqi.csv"
)

OUT_GEOJSON = os.path.join(
    EXPORTS,
    "cpcb_comparison.geojson"
)

OUT_SUMMARY = os.path.join(
    EXPORTS,
    "validation_summary.json"
)

print("=" * 65)
print("AEROVISION DASHBOARD DATA PREPARATION")
print("=" * 65)

df = pd.read_csv(AQI_FILE)

df["date_text"] = pd.to_datetime(
    df["date_text"],
    errors="coerce"
)

# ------------------------------------------------------------
# USE LATEST VALIDATION DATE FOR MAP
# ------------------------------------------------------------

latest_date = df["date_text"].max()

latest = df[
    df["date_text"] == latest_date
].copy()

print("Latest validation date:", latest_date.date())
print("Station rows:", len(latest))

# ------------------------------------------------------------
# CREATE GEOMETRY
# ------------------------------------------------------------

latest = latest.dropna(
    subset=[
        "latitude",
        "longitude"
    ]
)

geometry = [
    Point(lon, lat)
    for lon, lat
    in zip(
        latest["longitude"],
        latest["latitude"]
    )
]

gdf = gpd.GeoDataFrame(
    latest,
    geometry=geometry,
    crs="EPSG:4326"
)

# Convert date to string for JSON
gdf["date_text"] = (
    gdf["date_text"]
    .dt.strftime("%Y-%m-%d")
)

gdf.to_file(
    OUT_GEOJSON,
    driver="GeoJSON"
)

print("✅ CPCB comparison GeoJSON created")

# ------------------------------------------------------------
# VALIDATION SUMMARY
# ------------------------------------------------------------

summary = {
    "validation_period": "24–30 June 2026",

    "aqi": {
        "r2": 0.207,
        "correlation": 0.470,
        "mae": 38.57,
        "rmse": 61.20,
        "bias": -4.94,
        "category_agreement": 73.86,
        "dominant_pollutant_agreement": 87.50
    },

    "models": {
        "PM2.5": {
            "r2": 0.334,
            "mae": 17.611,
            "rmse": 30.398,
            "correlation": 0.640
        },

        "PM10": {
            "r2": 0.304,
            "mae": 37.383,
            "rmse": 50.314,
            "correlation": 0.587
        },

        "NO2": {
            "r2": 0.755,
            "mae": 5.956,
            "rmse": 9.568,
            "correlation": 0.885
        },

        "O3_8H": {
            "r2": 0.565,
            "mae": 11.570,
            "rmse": 15.199,
            "correlation": 0.772
        }
    },

    "event": {
        "date": "2026-06-08",
        "fire_detections": 359,
        "hcho_hotspots": 1711,
        "hotspots_near_fire": 462,
        "association_percentage": 27.00
    }
}

with open(
    OUT_SUMMARY,
    "w"
) as f:

    json.dump(
        summary,
        f,
        indent=2
    )

print("✅ Validation summary created")

print("\nOUTPUT:")
print(OUT_GEOJSON)
print(OUT_SUMMARY)

print("=" * 65)