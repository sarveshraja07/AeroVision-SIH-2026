import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

BASE = r"E:\AeroVision-Real"

WEATHER_DIR = os.path.join(BASE, "data", "raw", "weather")
FIRE_DIR = os.path.join(BASE, "data", "raw", "fire")
HCHO_DIR = os.path.join(BASE, "data", "raw", "hcho")
EXPORT_DIR = os.path.join(BASE, "data", "exports")

os.makedirs(EXPORT_DIR, exist_ok=True)

# -------------------------------------------------
# 1. WIND
# -------------------------------------------------

wind_files = [
    f for f in os.listdir(WEATHER_DIR)
    if f.lower().endswith(".csv")
]

if not wind_files:
    raise FileNotFoundError("No wind CSV found.")

wind_path = os.path.join(WEATHER_DIR, wind_files[0])

wind = pd.read_csv(wind_path)

print("Wind columns:")
print(wind.columns.tolist())

# Earth Engine sample output usually includes:
# longitude, latitude, WIND_U, WIND_V, WIND_SPEED

possible_lon = ["longitude", "lon"]
possible_lat = ["latitude", "lat"]

lon_col = next((c for c in possible_lon if c in wind.columns), None)
lat_col = next((c for c in possible_lat if c in wind.columns), None)

if lon_col is None or lat_col is None:
    raise ValueError("Longitude/latitude columns not found in wind CSV.")

required = ["WIND_U", "WIND_V", "WIND_SPEED"]

for c in required:
    if c not in wind.columns:
        raise ValueError(f"Missing wind column: {c}")

wind_clean = wind[
    [lon_col, lat_col, "WIND_U", "WIND_V", "WIND_SPEED"]
].copy()

wind_clean.columns = [
    "longitude",
    "latitude",
    "u",
    "v",
    "speed"
]

wind_clean = wind_clean.dropna()

wind_clean.to_csv(
    os.path.join(EXPORT_DIR, "wind_event.csv"),
    index=False
)

print("✅ wind_event.csv created")


# -------------------------------------------------
# 2. FIRE
# -------------------------------------------------

fire_files = [
    f for f in os.listdir(FIRE_DIR)
    if f.lower().endswith(".csv")
]

if not fire_files:
    raise FileNotFoundError("No FIRMS fire CSV found.")

fire_path = os.path.join(FIRE_DIR, fire_files[0])

fire = pd.read_csv(fire_path)

print("Fire columns:")
print(fire.columns.tolist())

fire_lon = next(
    (c for c in ["longitude", "lon"] if c in fire.columns),
    None
)

fire_lat = next(
    (c for c in ["latitude", "lat"] if c in fire.columns),
    None
)

if fire_lon is None or fire_lat is None:
    raise ValueError("Fire longitude/latitude columns missing.")

confidence_col = next(
    (c for c in ["FIRE_CONFIDENCE", "confidence"] if c in fire.columns),
    None
)

temp_col = next(
    (c for c in ["FIRE_T21", "T21"] if c in fire.columns),
    None
)

cols = [fire_lon, fire_lat]

if confidence_col:
    cols.append(confidence_col)

if temp_col:
    cols.append(temp_col)

fire_clean = fire[cols].copy()

rename_map = {
    fire_lon: "longitude",
    fire_lat: "latitude"
}

if confidence_col:
    rename_map[confidence_col] = "confidence"

if temp_col:
    rename_map[temp_col] = "temperature"

fire_clean = fire_clean.rename(columns=rename_map)

fire_clean = fire_clean.dropna(
    subset=["longitude", "latitude"]
)

fire_clean.to_csv(
    os.path.join(EXPORT_DIR, "fire_event.csv"),
    index=False
)

print("✅ fire_event.csv created")


# -------------------------------------------------
# 3. HCHO HOTSPOTS GEOJSON
# -------------------------------------------------

hcho_files = [
    f for f in os.listdir(HCHO_DIR)
    if f.lower().endswith(".geojson")
]

if not hcho_files:
    raise FileNotFoundError("No HCHO hotspot GeoJSON found.")

hcho_path = os.path.join(HCHO_DIR, hcho_files[0])

hcho = gpd.read_file(hcho_path)

print("HCHO columns:")
print(hcho.columns.tolist())

# Standardize CRS
if hcho.crs is None:
    hcho = hcho.set_crs("EPSG:4326")
else:
    hcho = hcho.to_crs("EPSG:4326")

hcho.to_file(
    os.path.join(EXPORT_DIR, "hcho_hotspots_event.geojson"),
    driver="GeoJSON"
)

print("✅ hcho_hotspots_event.geojson created")


# -------------------------------------------------
# 4. SUMMARY
# -------------------------------------------------

print("\n==============================")
print("EVENT LAYERS READY")
print("==============================")

print("Wind points :", len(wind_clean))
print("Fire points :", len(fire_clean))
print("HCHO points :", len(hcho))

print("\nOutput:")
print(os.path.join(EXPORT_DIR, "wind_event.csv"))
print(os.path.join(EXPORT_DIR, "fire_event.csv"))
print(os.path.join(EXPORT_DIR, "hcho_hotspots_event.geojson"))