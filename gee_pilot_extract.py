import ee
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT = "aqi-sih-506616"

COORD_FILE = Path(
    r"E:\AeroVision-CPCB-2026\05_station_metadata\CPCB_COORDINATE_LOOKUP_FINAL.csv"
)

OUT_DIR = Path(
    r"E:\AeroVision-CPCB-2026\05_features\gee_pilot"
)

OUT_DIR.mkdir(parents=True, exist_ok=True)

START = "2026-06-01"
END   = "2026-06-03"   # end-exclusive: June 1 and June 2

ee.Initialize(project=PROJECT)

# ---------------------------------------------------------
# Load the SAME 3 pilot stations selected previously
# ---------------------------------------------------------

stations = pd.read_csv(COORD_FILE, dtype={"site_id": str})

pilot = stations.iloc[
    [0, len(stations)//2, len(stations)-1]
][
    ["site_id", "station_location_text",
     "state_folder", "latitude", "longitude"]
].copy()

print("\nPILOT STATIONS:")
print(pilot.to_string(index=False))


# ---------------------------------------------------------
# GEE collections
# ---------------------------------------------------------

aod = (
    ee.ImageCollection("MODIS/061/MCD19A2_GRANULES")
    .filterDate(START, END)
    .select("Optical_Depth_055")
)

hcho = (
    ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_HCHO")
    .filterDate(START, END)
    .select("tropospheric_HCHO_column_number_density")
)

no2 = (
    ee.ImageCollection("COPERNICUS/S5P/OFFL/L3_NO2")
    .filterDate(START, END)
    .select("tropospheric_NO2_column_number_density")
)

era5 = (
    ee.ImageCollection("ECMWF/ERA5_LAND/HOURLY")
    .filterDate(START, END)
    .select([
        "temperature_2m",
        "dewpoint_temperature_2m",
        "u_component_of_wind_10m",
        "v_component_of_wind_10m"
    ])
)

firms = (
    ee.ImageCollection("FIRMS")
    .filterDate(START, END)
)


# ---------------------------------------------------------
# Safe reducer
# ---------------------------------------------------------

def mean_at_point(collection, band, point, scale):

    image = collection.mean()

    value = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=point,
        scale=scale,
        bestEffort=True,
        maxPixels=1_000_000
    ).get(band)

    try:
        return value.getInfo()
    except Exception:
        return None


# ---------------------------------------------------------
# Fire features within 25 km
# ---------------------------------------------------------

def fire_features(point):

    region = point.buffer(25000)

    fire_count = firms.select("T21").count().reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=region,
        scale=1000,
        bestEffort=True,
        maxPixels=10_000_000
    ).get("T21")

    fire_t21 = firms.select("T21").max().reduceRegion(
        reducer=ee.Reducer.max(),
        geometry=region,
        scale=1000,
        bestEffort=True,
        maxPixels=10_000_000
    ).get("T21")

    fire_conf = firms.select("confidence").max().reduceRegion(
        reducer=ee.Reducer.max(),
        geometry=region,
        scale=1000,
        bestEffort=True,
        maxPixels=10_000_000
    ).get("confidence")

    try:
        count = fire_count.getInfo()
    except Exception:
        count = None

    try:
        t21 = fire_t21.getInfo()
    except Exception:
        t21 = None

    try:
        conf = fire_conf.getInfo()
    except Exception:
        conf = None

    return count, t21, conf


# ---------------------------------------------------------
# ERA5 derived features
# ---------------------------------------------------------

def relative_humidity(temp_k, dew_k):

    if temp_k is None or dew_k is None:
        return None

    t = temp_k - 273.15
    td = dew_k - 273.15

    rh = 100.0 * (
        np.exp((17.625 * td) / (243.04 + td)) /
        np.exp((17.625 * t) / (243.04 + t))
    )

    return float(np.clip(rh, 0, 100))


# ---------------------------------------------------------
# Extract
# ---------------------------------------------------------

rows = []

for _, station in pilot.iterrows():

    sid = station["site_id"]
    lat = float(station["latitude"])
    lon = float(station["longitude"])

    print(
        f"\nExtracting {sid} - "
        f"{station['station_location_text']}..."
    )

    point = ee.Geometry.Point([lon, lat])

    aod_raw = mean_at_point(
        aod,
        "Optical_Depth_055",
        point,
        1000
    )

    # MAIAC Optical_Depth_055 scale factor = 0.001
    aod_value = (
        aod_raw * 0.001
        if aod_raw is not None
        else None
    )

    hcho_value = mean_at_point(
        hcho,
        "tropospheric_HCHO_column_number_density",
        point,
        7000
    )

    no2_value = mean_at_point(
        no2,
        "tropospheric_NO2_column_number_density",
        point,
        7000
    )

    temp = mean_at_point(
        era5,
        "temperature_2m",
        point,
        11000
    )

    dew = mean_at_point(
        era5,
        "dewpoint_temperature_2m",
        point,
        11000
    )

    u = mean_at_point(
        era5,
        "u_component_of_wind_10m",
        point,
        11000
    )

    v = mean_at_point(
        era5,
        "v_component_of_wind_10m",
        point,
        11000
    )

    temp_c = temp - 273.15 if temp is not None else None
    dew_c = dew - 273.15 if dew is not None else None

    rh = relative_humidity(temp, dew)

    wind_speed = (
        float(np.sqrt(u*u + v*v))
        if u is not None and v is not None
        else None
    )

    fire_count, fire_t21, fire_conf = fire_features(point)

    rows.append({
        "site_id": sid,
        "station_name": station["station_location_text"],
        "state_folder": station["state_folder"],
        "latitude": lat,
        "longitude": lon,

        "period_start": START,
        "period_end_exclusive": END,

        "AOD_055": aod_value,

        "HCHO_mol_m2": hcho_value,
        "NO2_mol_m2": no2_value,

        "ERA5_TEMP_C": temp_c,
        "ERA5_DEWPOINT_C": dew_c,
        "ERA5_RH": rh,

        "WIND_U": u,
        "WIND_V": v,
        "WIND_SPEED": wind_speed,

        "FIRE_COUNT_25KM": fire_count,
        "FIRE_T21_MAX_25KM": fire_t21,
        "FIRE_CONF_MAX_25KM": fire_conf
    })


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

result = pd.DataFrame(rows)

outfile = OUT_DIR / "GEE_PILOT_3STATIONS_2026-06-01_02.csv"

result.to_csv(outfile, index=False)

print("\n==============================")
print("PILOT EXTRACTION COMPLETE")
print("==============================")

print(result.to_string(index=False))

print("\nOUTPUT:")
print(outfile)

print("\nMISSING VALUES:")
print(result.isna().sum().to_string())
