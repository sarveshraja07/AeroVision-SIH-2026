import os
import math
import warnings
from datetime import datetime, timedelta

import ee
import pandas as pd
import numpy as np


# ============================================================
# AEROVISION SIH 2026
# REAL CPCB + GEE NATIONWIDE FUSION V1
#
# Pilot:
#   Stations : 5684, 1418, 5707
#   Date     : 2026-01-01
#   Expected : 72 rows
#
# Main V3 correction:
#   CPCB timestamps are explicitly converted from IST to UTC
#   and matched to the nearest ERA5-Land hourly timestamp.
#
# IMPORTANT:
#   No fake values.
#   Missing satellite observations remain NaN.
# ============================================================


# ============================================================
# CONFIGURATION
# ============================================================

GEE_PROJECT = "aqi-sih-506616"

CPCB_FILE = (
    r"E:\AeroVision-CPCB-2026"
    r"\04_cleaned\CPCB_2026_CLEAN_MASTER.csv"
)

COORD_FILE = (
    r"E:\AeroVision-CPCB-2026"
    r"\05_station_metadata"
    r"\CPCB_COORDINATE_LOOKUP_FINAL.csv"
)

OUTPUT_DIR = (
    r"E:\AeroVision-CPCB-2026"
    r"\05_features"
    r"\fusion_nationwide"
)

# PILOT_DATE = "2026-01-01"

# PILOT_STATIONS = [
#     "5684",
#     "1418",
#     "5707",
# ]
START_DATE = "2026-01-01"
END_DATE = "2026-09-01"
# CPCB timestamp interpretation used for this nationwide extraction.
# The data timestamps are treated as India local time.
CPCB_TIMEZONE = "Asia/Kolkata"

# ERA5 source is hourly.
# We allow a maximum nearest-hour difference of 31 minutes.
# For an IST hour against UTC hourly data, the expected offset
# is 30 minutes.
ERA5_MATCH_TOLERANCE_MINUTES = 31

# Spatial radius for FIRMS context.
FIRE_RADIUS_METERS = 25000

# Spatial scale used for point extraction.
POINT_SCALE_METERS = 1000


# ============================================================
# DATASET NAMES
# ============================================================

AOD_COLLECTION = "MODIS/061/MCD19A2_GRANULES"

HCHO_COLLECTION = "COPERNICUS/S5P/OFFL/L3_HCHO"

SAT_NO2_COLLECTION = "COPERNICUS/S5P/OFFL/L3_NO2"

ERA5_COLLECTION = "ECMWF/ERA5_LAND/HOURLY"

FIRMS_COLLECTION = "FIRMS"


# ============================================================
# OUTPUT FILES
# ============================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_MAIN = os.path.join(
    OUTPUT_DIR,
    "FUSION_NATIONWIDE_2026_V1.csv"
)

OUTPUT_QC = os.path.join(
    OUTPUT_DIR,
   "FUSION_NATIONWIDE_2026_QC.csv"
)

OUTPUT_AOD_QC = os.path.join(
    OUTPUT_DIR,
    "FUSION_NATIONWIDE_2026_AOD_QC.csv"
)

OUTPUT_ERA5_QC = os.path.join(
    OUTPUT_DIR,
   "FUSION_NATIONWIDE_2026_ERA5_QC.csv"
)

OUTPUT_FIRMS_QC = os.path.join(
    OUTPUT_DIR,
  "FUSION_NATIONWIDE_2026_FIRMS_QC.csv"
)


# ============================================================
#  POLLUTANTS
# ============================================================

POLLUTANTS = [
    "PM25",
    "PM10",
    "NO2",
    "O3",
    "SO2",
    "CO",
    "NH3",
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_float(value):
    """
    Convert a value to float.

    Returns NaN when conversion is not possible.
    """
    try:
        if value is None:
            return np.nan

        if isinstance(value, float) and math.isnan(value):
            return np.nan

        return float(value)

    except Exception:
        return np.nan


def millis_to_datetime_utc(millis):
    """
    Convert Earth Engine millisecond timestamp to
    timezone-aware UTC pandas Timestamp.
    """
    if millis is None:
        return pd.NaT

    return pd.to_datetime(
        int(millis),
        unit="ms",
        utc=True
    )


def get_geometry(lat, lon):
    """
    Create an Earth Engine point geometry.
    """
    return ee.Geometry.Point([
        float(lon),
        float(lat)
    ])


def ee_reduce_point(image, geometry, scale):
    """
    Reduce a single-band Earth Engine image at a point.
    """
    result = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=scale,
        bestEffort=True,
        maxPixels=1e8
    ).getInfo()

    return result


def get_feature_value(image, band, geometry, scale):
    """
    Extract one band from one image at a point.
    """
    try:
        result = image.select(band).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=scale,
            bestEffort=True,
            maxPixels=1e8
        ).getInfo()

        if not result:
            return np.nan

        return safe_float(result.get(band))

    except Exception:
        return np.nan


def get_collection_image_count(
    collection_id,
    start_date,
    end_date,
    geometry
):
    """
    Return number of images in a GEE collection
    for a spatial/temporal query.
    """
    collection = (
        ee.ImageCollection(collection_id)
        .filterDate(start_date, end_date)
        .filterBounds(geometry)
    )

    try:
        return int(collection.size().getInfo())
    except Exception:
        return 0


# ============================================================
# INITIALIZE EARTH ENGINE
# ============================================================

print("=" * 70)
print("AEROVISION - CPCB + GEE NATIONWIDE FUSION V1")
print("=" * 70)

print("\nInitializing Earth Engine...")

try:
    ee.Initialize(project=GEE_PROJECT)
except Exception:
    print("Earth Engine initialization failed.")
    print("Trying authentication...")
    ee.Authenticate()
    ee.Initialize(project=GEE_PROJECT)

print("Earth Engine initialized.")


# ============================================================
# LOAD CPCB MASTER
# ============================================================

print("\n" + "=" * 70)
print("1. LOADING CPCB MASTER")
print("=" * 70)

print(f"\nCPCB file:")
print(CPCB_FILE)

cpcb = pd.read_csv(
    CPCB_FILE,
    low_memory=False
)

print(f"\nCPCB rows loaded: {len(cpcb):,}")


# ============================================================
# NORMALIZE SITE ID
# ============================================================

if "site_id" not in cpcb.columns:
    raise ValueError(
        "CPCB master does not contain 'site_id'."
    )

cpcb["site_id"] = (
    cpcb["site_id"]
    .astype(str)
    .str.strip()
    .str.replace(r"\.0$", "", regex=True)
)


# ============================================================
# CHECK REQUIRED COLUMNS
# ============================================================

required_columns = [
    "timestamp",
    "site_id",
    "PM25",
    "PM10",
    "NO2",
    "O3",
    "SO2",
    "CO",
    "NH3",
]

missing_columns = [
    c for c in required_columns
    if c not in cpcb.columns
]

if missing_columns:
    raise ValueError(
        f"Missing CPCB columns: {missing_columns}"
    )


# ============================================================
# PARSE CPCB TIMESTAMP
# ============================================================

cpcb["timestamp"] = pd.to_datetime(
    cpcb["timestamp"],
    errors="coerce"
)

if cpcb["timestamp"].isna().any():
    bad_count = int(cpcb["timestamp"].isna().sum())

    raise ValueError(
        f"CPCB timestamp parsing failed for {bad_count} rows."
    )
# ============================================================
# FILTER NATIONWIDE DATA
# ============================================================

start_date = pd.Timestamp(START_DATE)
end_date = pd.Timestamp(END_DATE)

fusion = cpcb[
    (cpcb["timestamp"] >= start_date)
    &
    (cpcb["timestamp"] < end_date)
].copy()

print("\nFusion rows:", len(fusion))
print("Fusion stations:", fusion["site_id"].nunique())

if fusion.empty:
    raise ValueError(
        "Fusion dataset is empty."
    )

fusion_stations = sorted(
    fusion["site_id"]
    .dropna()
    .astype(str)
    .unique()
)

print(
    f"Nationwide stations loaded: "
    f"{len(fusion_stations)}"
)

# ============================================================
# VERIFY STATION DATA
# ============================================================

for station in fusion_stations:

    count = int(
        (fusion["site_id"] == station).sum()
    )

    if count == 0:
        raise ValueError(
            f"Station {station} has no rows."
        )


# ============================================================
# VERIFY 7 POLLUTANTS
# ============================================================

print("\n" + "=" * 70)
print("2. CPCB POLLUTANT COVERAGE")
print("=" * 70)

for station in fusion_stations:

    station_df = fusion[
        fusion["site_id"] == station
    ]

    print(f"\nStation {station}")

    for pollutant in POLLUTANTS:

        count = int(
            station_df[pollutant]
            .notna()
            .sum()
        )

        total = len(station_df)

        print(
            f"  {pollutant:5s}: "
            f"{count}/{total}"
        )
# ============================================================
# LOAD COORDINATES
# ============================================================

print("\n" + "=" * 70)
print("3. LOADING OFFICIAL STATION COORDINATES")
print("=" * 70)

coords = pd.read_csv(
    COORD_FILE,
    low_memory=False
)

coords["site_id"] = (
    coords["site_id"]
    .astype(str)
    .str.strip()
    .str.replace(r"\.0$", "", regex=True)
)

print(
    f"\nCoordinate rows loaded: {len(coords)}"
)


# ============================================================
# DETERMINE COORDINATE COLUMN NAMES
# ============================================================

lat_candidates = [
    "latitude",
    "Latitude",
    "LATITUDE",
    "lat",
    "LAT",
]

lon_candidates = [
    "longitude",
    "Longitude",
    "LONGITUDE",
    "lon",
    "LON",
]


def find_column(df, candidates):

    for column in candidates:

        if column in df.columns:
            return column

    return None


LAT_COL = find_column(
    coords,
    lat_candidates
)

LON_COL = find_column(
    coords,
    lon_candidates
)

if LAT_COL is None or LON_COL is None:

    raise ValueError(
        "Could not identify latitude/longitude columns "
        "in coordinate lookup."
    )


coords[LAT_COL] = pd.to_numeric(
    coords[LAT_COL],
    errors="coerce"
)

coords[LON_COL] = pd.to_numeric(
    coords[LON_COL],
    errors="coerce"
)


# ============================================================
# BUILD STATION METADATA
# ============================================================

station_metadata = {}

for station in fusion_stations:

    matches = coords[
        coords["site_id"] == station
    ]

    if len(matches) != 1:

        raise ValueError(
            f"Expected exactly one coordinate row "
            f"for station {station}, found {len(matches)}."
        )

    row = matches.iloc[0]

    lat = safe_float(row[LAT_COL])
    lon = safe_float(row[LON_COL])

    if np.isnan(lat) or np.isnan(lon):

        raise ValueError(
            f"Missing coordinates for station {station}."
        )

    metadata = {
        "site_id": station,
        "latitude": lat,
        "longitude": lon,
    }

    # Add station name if present.
    for name_col in [
        "station_name",
        "Station_Name",
        "station",
        "name",
        "Name",
    ]:

        if name_col in coords.columns:

            metadata["station_name"] = str(
                row[name_col]
            )

            break

    # Add state if present.
    for state_col in [
        "state",
        "State",
        "STATE",
    ]:

        if state_col in coords.columns:

            metadata["state"] = str(
                row[state_col]
            )

            break

    if "station_name" not in metadata:
        metadata["station_name"] = ""

    if "state" not in metadata:
        metadata["state"] = ""

    station_metadata[station] = metadata

    print(
        f"\n{station}"
        f" | {metadata['station_name']}"
        f" | {metadata['state']}"
        f" | {lat}"
        f" | {lon}"
    )


# ============================================================
# CPCB TIMEZONE PREPARATION
# ============================================================

print("\n" + "=" * 70)
print("4. CPCB TEMPORAL ALIGNMENT PREPARATION")
print("=" * 70)

# IMPORTANT:
# The CPCB source timestamps are interpreted as India local time
# for this pilot. This interpretation must remain explicit.
#
# We retain:
#
#   CPCB_TIMESTAMP_ORIGINAL
#   CPCB_TIMESTAMP_IST
#   CPCB_TIMESTAMP_UTC
#
# so that temporal alignment is auditable.

fusion["CPCB_TIMESTAMP_ORIGINAL"] = (
    fusion["timestamp"]
    .dt.strftime("%Y-%m-%d %H:%M:%S")
)

fusion["CPCB_TIMESTAMP_IST"] = (
    fusion["timestamp"]
    .dt.tz_localize(
        CPCB_TIMEZONE
    )
)

fusion["CPCB_TIMESTAMP_UTC"] = (
    fusion["CPCB_TIMESTAMP_IST"]
    .dt.tz_convert("UTC")
)


print(
    "\nExample CPCB timestamp conversion:"
)

example = fusion.iloc[0]

print(
    "  Original :",
    example["CPCB_TIMESTAMP_ORIGINAL"]
)

print(
    "  IST      :",
    example["CPCB_TIMESTAMP_IST"]
)

print(
    "  UTC      :",
    example["CPCB_TIMESTAMP_UTC"]
)


# ============================================================
# ERA5 UTC QUERY WINDOW
# ============================================================

# The pilot day is 2026-01-01 in India.
#
# Because India is UTC+05:30, the beginning of the local day
# corresponds to the previous UTC date.
#
# We therefore query a wider UTC window.
#
# This prevents loss of early local-day observations.

era5_query_start = (
    fusion["CPCB_TIMESTAMP_UTC"].min()
    - pd.Timedelta(hours=2)
)

era5_query_end = (
    fusion["CPCB_TIMESTAMP_UTC"].max()
    + pd.Timedelta(hours=2)
)

# Convert to Python datetimes for Earth Engine.
era5_start_datetime = (
    era5_query_start.to_pydatetime()
)

era5_end_datetime = (
    era5_query_end.to_pydatetime()
)

era5_start_ee = (
    era5_start_datetime.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
)

era5_end_ee = (
    era5_end_datetime.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
)

print(
    "\nERA5 query window:"
)

print(
    "  Start:",
    era5_start_ee
)

print(
    "  End  :",
    era5_end_ee
)


# ============================================================
# GEE EXTRACTION FUNCTIONS
# ============================================================

def extract_era5_hourly(
    station_id,
    latitude,
    longitude
):

    """
    Extract ERA5-Land hourly meteorology.

    Returns a DataFrame with:

        ERA5_TIMESTAMP_UTC
        TEMP_C
        DEWPOINT_C
        RH_PERCENT
        WIND_U_M_S
        WIND_V_M_S
        WIND_SPEED_M_S
    """

    geometry = get_geometry(
        latitude,
        longitude
    )

    collection = (
        ee.ImageCollection(
            ERA5_COLLECTION
        )
        .filterDate(
            era5_start_ee,
            era5_end_ee
        )
        .filterBounds(
            geometry
        )
        .select([
            "temperature_2m",
            "dewpoint_temperature_2m",
            "u_component_of_wind_10m",
            "v_component_of_wind_10m",
        ])
        .sort("system:time_start")
    )

    image_list = collection.toList(
        collection.size()
    )

    count = collection.size().getInfo()

    records = []

    for i in range(count):

        image = ee.Image(
            image_list.get(i)
        )

        timestamp_millis = (
            image.get(
                "system:time_start"
            ).getInfo()
        )

        timestamp_utc = (
            millis_to_datetime_utc(
                timestamp_millis
            )
        )

        try:

            values = image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=11000,
                bestEffort=True,
                maxPixels=1e8
            ).getInfo()

        except Exception as exc:

            print(
                f"    ERA5 extraction error "
                f"{station_id}: {exc}"
            )

            values = {}

        temp_k = safe_float(
            values.get(
                "temperature_2m"
            )
        )

        dewpoint_k = safe_float(
            values.get(
                "dewpoint_temperature_2m"
            )
        )

        wind_u = safe_float(
            values.get(
                "u_component_of_wind_10m"
            )
        )

        wind_v = safe_float(
            values.get(
                "v_component_of_wind_10m"
            )
        )

        temp_c = (
            temp_k - 273.15
            if not np.isnan(temp_k)
            else np.nan
        )

        dewpoint_c = (
            dewpoint_k - 273.15
            if not np.isnan(dewpoint_k)
            else np.nan
        )

        if (
            not np.isnan(temp_c)
            and not np.isnan(dewpoint_c)
        ):

            # Magnus approximation for RH.
            a = 17.625
            b = 243.04

            gamma_t = (
                (a * temp_c)
                /
                (b + temp_c)
            )

            gamma_td = (
                (a * dewpoint_c)
                /
                (b + dewpoint_c)
            )

            rh = (
                100.0
                *
                np.exp(
                    gamma_td - gamma_t
                )
            )

        else:

            rh = np.nan

        if (
            not np.isnan(wind_u)
            and not np.isnan(wind_v)
        ):

            wind_speed = math.sqrt(
                wind_u ** 2
                +
                wind_v ** 2
            )

        else:

            wind_speed = np.nan

        records.append({

            "site_id": station_id,

            "ERA5_TIMESTAMP_UTC":
                timestamp_utc,

            "TEMP_C":
                temp_c,

            "DEWPOINT_C":
                dewpoint_c,

            "RH_PERCENT":
                rh,

            "WIND_U_M_S":
                wind_u,

            "WIND_V_M_S":
                wind_v,

            "WIND_SPEED_M_S":
                wind_speed,

        })

    return pd.DataFrame(records)


# ============================================================
# AOD EXTRACTION
# ============================================================

def extract_aod(
    station_id,
    latitude,
    longitude
):

    geometry = get_geometry(
        latitude,
        longitude
    )

    start = (
        f"{START_DATE}T00:00:00"
    )

    end_date = (
        pd.Timestamp(END_DATE)
    )

    end = (
        end_date.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
    )

    collection = (
        ee.ImageCollection(
            AOD_COLLECTION
        )
        .filterDate(
            start,
            end
        )
        .filterBounds(
            geometry
        )
    )

    raw_count = int(
        collection.size().getInfo()
    )

    # --------------------------------------------------------
    # MAIAC AOD QA
    #
    # Existing pilot rule:
    #
    # cloud_mask = AOD_QA & 7
    # cloud_mask == 1
    #
    # retrieval QA:
    # bits 8-11 == 0
    #
    # Keep the rule explicit.
    # --------------------------------------------------------

    def qa_mask(image):

        qa = image.select(
            "AOD_QA"
        )

        cloud_bits = (
            qa.bitwiseAnd(7)
            .eq(1)
        )

        retrieval_bits = (
            qa.rightShift(8)
            .bitwiseAnd(15)
            .eq(0)
        )

        return image.updateMask(
            cloud_bits
            .And(retrieval_bits)
        )

    qa_collection = (
        collection
        .map(qa_mask)
    )

    qa_count = int(
        qa_collection.size().getInfo()
    )

    # --------------------------------------------------------
    # Extract individual images.
    # --------------------------------------------------------

    image_list = qa_collection.toList(
        qa_count
    )

    values = []

    for i in range(qa_count):

        image = ee.Image(
            image_list.get(i)
        )

        result = image.select(
            "Optical_Depth_055"
        ).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=1000,
            bestEffort=True,
            maxPixels=1e8
        ).getInfo()

        value = safe_float(
            result.get(
                "Optical_Depth_055"
            )
            if result
            else None
        )

        if not np.isnan(value):

            # MAIAC scale factor.
            value = value * 0.001

            values.append(value)

    if values:

        aod_value = float(
            np.mean(values)
        )

    else:

        aod_value = np.nan

    # --------------------------------------------------------
    # Unfiltered diagnostic.
    # --------------------------------------------------------

    raw_values = []

    raw_list = collection.toList(
        raw_count
    )

    for i in range(raw_count):

        image = ee.Image(
            raw_list.get(i)
        )

        result = image.select(
            "Optical_Depth_055"
        ).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=1000,
            bestEffort=True,
            maxPixels=1e8
        ).getInfo()

        value = safe_float(
            result.get(
                "Optical_Depth_055"
            )
            if result
            else None
        )

        if not np.isnan(value):

            raw_values.append(
                value * 0.001
            )

    if raw_values:

        aod_unfiltered = float(
            np.mean(raw_values)
        )

    else:

        aod_unfiltered = np.nan

    return {

        "site_id":
            station_id,

        "AOD_055":
            aod_value,

        "AOD_055_UNFILTERED":
            aod_unfiltered,

        "AOD_SOURCE_IMAGES":
            raw_count,

        "AOD_QA_PASSED_IMAGES":
            qa_count,

        "AOD_VALID_POINT_VALUES":
            len(values),

        "AOD_TEMPORAL_RESOLUTION":
            "daily_observation_context",

    }


# ============================================================
# HCHO EXTRACTION
# ============================================================

def extract_hcho(
    station_id,
    latitude,
    longitude
):

    geometry = get_geometry(
        latitude,
        longitude
    )

    start = (
        f"{START_DATE}T00:00:00"
    )

    end = (
            pd.Timestamp(END_DATE)
        .strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
    )

    collection = (
        ee.ImageCollection(
            HCHO_COLLECTION
        )
        .filterDate(
            start,
            end
        )
        .filterBounds(
            geometry
        )
    )

    count = int(
        collection.size().getInfo()
    )

    image_list = collection.toList(
        count
    )

    values = []

    for i in range(count):

        image = ee.Image(
            image_list.get(i)
        )

        result = image.select(
            "tropospheric_HCHO_column_number_density"
        ).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=10000,
            bestEffort=True,
            maxPixels=1e8
        ).getInfo()

        value = safe_float(
            result.get(
                "tropospheric_HCHO_column_number_density"
            )
            if result
            else None
        )

        if not np.isnan(value):

            values.append(value)

    if values:

        hcho = float(
            np.mean(values)
        )

    else:

        hcho = np.nan

    return {

        "site_id":
            station_id,

        "HCHO_mol_m2":
            hcho,

        "HCHO_SOURCE_IMAGES":
            count,

        "HCHO_TEMPORAL_RESOLUTION":
            "daily_observation_context",

    }


# ============================================================
# SATELLITE NO2 EXTRACTION
# ============================================================

def extract_sat_no2(
    station_id,
    latitude,
    longitude
):

    geometry = get_geometry(
        latitude,
        longitude
    )

    start = (
        f"{START_DATE}T00:00:00"
    )
    
    end = (
            pd.Timestamp(END_DATE)
        .strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
    )

    collection = (
        ee.ImageCollection(
            SAT_NO2_COLLECTION
        )
        .filterDate(
            start,
            end
        )
        .filterBounds(
            geometry
        )
    )

    count = int(
        collection.size().getInfo()
    )

    image_list = collection.toList(
        count
    )

    values = []

    for i in range(count):

        image = ee.Image(
            image_list.get(i)
        )

        result = image.select(
            "tropospheric_NO2_column_number_density"
        ).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=10000,
            bestEffort=True,
            maxPixels=1e8
        ).getInfo()

        value = safe_float(
            result.get(
                "tropospheric_NO2_column_number_density"
            )
            if result
            else None
        )

        if not np.isnan(value):

            values.append(value)

    if values:

        sat_no2 = float(
            np.mean(values)
        )

    else:

        sat_no2 = np.nan

    return {

        "site_id":
            station_id,

        "SAT_NO2_mol_m2":
            sat_no2,

        "SAT_NO2_SOURCE_IMAGES":
            count,

        "SAT_NO2_TEMPORAL_RESOLUTION":
            "daily_observation_context",

    }


# ============================================================
# FIRMS EXTRACTION
# ============================================================

def extract_firms(
    station_id,
    latitude,
    longitude
):

    point = get_geometry(
        latitude,
        longitude
    )

    region = point.buffer(
        FIRE_RADIUS_METERS
    )

    start = (
        f"{START_DATE}T00:00:00"
    )
    
    end = (
            pd.Timestamp(END_DATE)
        .strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
    )

    collection = (
        ee.ImageCollection(
            FIRMS_COLLECTION
        )
        .filterDate(
            start,
            end
        )
        .filterBounds(
            region
        )
    )

    count = int(
        collection.size().getInfo()
    )

    # --------------------------------------------------------
    # Important:
    #
    # FIRMS is being treated here as raster active-fire
    # context, not automatically as individual fire-detection
    # count.
    #
    # FIRE_PIXEL_COUNT therefore means:
    #
    #   number of raster pixels with valid T21 information
    #
    # inside the 25 km region.
    #
    # It must NOT be described as an exact number of fires.
    # --------------------------------------------------------

    fire_pixel_count = 0.0

    t21_max = np.nan

    confidence_max = np.nan

    if count > 0:

        image_list = collection.toList(
            count
        )

        for i in range(count):

            image = ee.Image(
                image_list.get(i)
            )

            t21 = image.select(
                "T21"
            )

            confidence = image.select(
                "confidence"
            )

            # Count valid T21 raster pixels.
            try:

                pixel_count_result = (
                    t21.mask()
                    .reduceRegion(
                        reducer=ee.Reducer.count(),
                        geometry=region,
                        scale=1000,
                        bestEffort=True,
                        maxPixels=1e8
                    )
                    .getInfo()
                )

                count_value = safe_float(
                    pixel_count_result.get(
                        "T21"
                    )
                    if pixel_count_result
                    else None
                )

                if not np.isnan(count_value):

                    fire_pixel_count += count_value

            except Exception:

                pass

            # Maximum T21.
            try:

                t21_result = t21.reduceRegion(
                    reducer=ee.Reducer.max(),
                    geometry=region,
                    scale=1000,
                    bestEffort=True,
                    maxPixels=1e8
                ).getInfo()

                value = safe_float(
                    t21_result.get(
                        "T21"
                    )
                    if t21_result
                    else None
                )

                if not np.isnan(value):

                    if (
                        np.isnan(t21_max)
                        or value > t21_max
                    ):

                        t21_max = value

            except Exception:

                pass

            # Maximum confidence.
            try:

                confidence_result = (
                    confidence.reduceRegion(
                        reducer=ee.Reducer.max(),
                        geometry=region,
                        scale=1000,
                        bestEffort=True,
                        maxPixels=1e8
                    ).getInfo()
                )

                value = safe_float(
                    confidence_result.get(
                        "confidence"
                    )
                    if confidence_result
                    else None
                )

                if not np.isnan(value):

                    if (
                        np.isnan(confidence_max)
                        or value > confidence_max
                    ):

                        confidence_max = value

            except Exception:

                pass

    fire_present = (
        fire_pixel_count > 0
    )

    return {

        "site_id":
            station_id,

        "FIRE_PIXEL_COUNT_25KM":
            fire_pixel_count,

        "FIRE_PRESENT_25KM":
            fire_present,

        "FIRE_T21_MAX_K_25KM":
            t21_max,

        "FIRE_CONF_MAX_PCT_25KM":
            confidence_max,

        "FIRMS_SOURCE_IMAGES":
            count,

        "FIRMS_TEMPORAL_RESOLUTION":
            "daily",

        "FIRE_COUNT_SEMANTICS":
            "raster_active_fire_pixels_not_individual_detections",

    }


# ============================================================
# DAILY BATCHED SATELLITE + FIRMS EXTRACTION
# ============================================================

all_station_features = []
era5_all = []
aod_qc_records = []
firms_qc_records = []

print("\n" + "=" * 70)
print("5. GEE EXTRACTION")
print("=" * 70)

# Keep the existing hourly ERA5 extraction and matching workflow unchanged.
for station in fusion_stations:
    meta = station_metadata[station]
    lat = meta["latitude"]
    lon = meta["longitude"]

    print(f"\nERA5 station {station}: {meta['station_name']}")
    era5 = extract_era5_hourly(station, lat, lon)
    print(f"    ERA5 rows: {len(era5)}")

    if len(era5) == 0:
        warnings.warn(
            f"No ERA5 rows returned for station {station}."
        )

    era5_all.append(era5)


# Build one Earth Engine FeatureCollection containing all station points.
station_features_ee = []
for station in fusion_stations:
    meta = station_metadata[station]
    point = get_geometry(meta["latitude"], meta["longitude"])
    station_features_ee.append(
        ee.Feature(
            point,
            {
                "site_id": str(station),
                "station_name": str(meta["station_name"]),
                "state": str(meta["state"]),
                "latitude": float(meta["latitude"]),
                "longitude": float(meta["longitude"]),
            },
        )
    )

station_fc = ee.FeatureCollection(station_features_ee)


def _feature_collection_records(feature_collection):
    """Fetch a reduced station FeatureCollection as ordinary Python records."""
    payload = feature_collection.getInfo()
    records = []
    for feature in payload.get("features", []):
        props = feature.get("properties", {})
        if props.get("site_id") is not None:
            records.append(dict(props))
    return records


def _daily_qa_mask(image):
    """Keep the existing MAIAC QA bit rules unchanged."""
    qa = image.select("AOD_QA")
    cloud_bits = qa.bitwiseAnd(7).eq(1)
    retrieval_bits = qa.rightShift(8).bitwiseAnd(15).eq(0)
    return image.updateMask(cloud_bits.And(retrieval_bits))


def extract_daily_station_batch(day):
    """Extract one daily satellite/fire record for each station in a batch.

    Values are daily composites. Source-image counts are station-specific.
    FIRMS pixel count is the number of distinct spatial pixels with valid T21
    information in that day's max composite, not a count of individual fires.
    """
    day_start = pd.Timestamp(day).strftime("%Y-%m-%d")
    day_end = (pd.Timestamp(day) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    aod_raw = (
        ee.ImageCollection(AOD_COLLECTION)
        .filterDate(day_start, day_end)
        .filterBounds(station_fc.geometry())
    )
    hcho_collection = (
        ee.ImageCollection(HCHO_COLLECTION)
        .filterDate(day_start, day_end)
        .filterBounds(station_fc.geometry())
    )
    no2_collection = (
        ee.ImageCollection(SAT_NO2_COLLECTION)
        .filterDate(day_start, day_end)
        .filterBounds(station_fc.geometry())
    )
    firms_collection = (
        ee.ImageCollection(FIRMS_COLLECTION)
        .filterDate(day_start, day_end)
        # Filter globally to the station geometry. The per-station source
        # count below uses the full 25 km buffer around each station.
        .filterBounds(station_fc.geometry())
    )

    # Counts are calculated server-side per station and day, avoiding one
    # client-side getInfo call per station or source image.
    def add_source_counts(feature):
        feature = ee.Feature(feature)
        point = feature.geometry()
        fire_region = point.buffer(FIRE_RADIUS_METERS)
        return feature.set({
            "CPCB_DATE": day_start,
            "AOD_SOURCE_IMAGES": aod_raw.filterBounds(point).size(),
            # The existing script counted the QA-mapped collection, not the
            # number of images with a valid pixel; preserve that count meaning.
            "AOD_QA_PASSED_IMAGES": aod_raw.map(_daily_qa_mask).filterBounds(point).size(),
            "HCHO_SOURCE_IMAGES": hcho_collection.filterBounds(point).size(),
            "SAT_NO2_SOURCE_IMAGES": no2_collection.filterBounds(point).size(),
            "FIRMS_SOURCE_IMAGES": firms_collection.filterBounds(fire_region).size(),
        })

    base_fc = station_fc.map(add_source_counts)
    base_records = _feature_collection_records(base_fc)
    by_station = {str(row["site_id"]): row for row in base_records}

    # AOD: daily mean of QA-filtered images and separate unfiltered diagnostic.
    aod_global_count = int(aod_raw.size().getInfo())
    if aod_global_count > 0:
        aod_qa = aod_raw.map(_daily_qa_mask)
        aod_qa_mean = aod_qa.select("Optical_Depth_055").mean().multiply(0.001).rename("AOD_055")
        aod_raw_mean = aod_raw.select("Optical_Depth_055").mean().multiply(0.001).rename("AOD_055_UNFILTERED")
        aod_image = aod_qa_mean.addBands(aod_raw_mean)
        aod_reduced = aod_image.reduceRegions(
            collection=base_fc,
            reducer=ee.Reducer.mean(),
            scale=1000,
            tileScale=4,
        )
        for row in _feature_collection_records(aod_reduced):
            sid = str(row["site_id"])
            by_station[sid]["AOD_055"] = safe_float(row.get("AOD_055"))
            by_station[sid]["AOD_055_UNFILTERED"] = safe_float(row.get("AOD_055_UNFILTERED"))
    else:
        for row in by_station.values():
            row["AOD_055"] = np.nan
            row["AOD_055_UNFILTERED"] = np.nan

    # HCHO daily mean composite.
    hcho_global_count = int(hcho_collection.size().getInfo())
    if hcho_global_count > 0:
        hcho_image = hcho_collection.select(
            "tropospheric_HCHO_column_number_density"
        ).mean().rename("HCHO_mol_m2")
        hcho_reduced = hcho_image.reduceRegions(
            collection=base_fc,
            reducer=ee.Reducer.mean(),
            scale=10000,
            tileScale=4,
        )
        for row in _feature_collection_records(hcho_reduced):
            by_station[str(row["site_id"])]["HCHO_mol_m2"] = safe_float(row.get("HCHO_mol_m2"))
    else:
        for row in by_station.values():
            row["HCHO_mol_m2"] = np.nan

    # Satellite NO2 daily mean composite; kept separate from CPCB ground NO2.
    no2_global_count = int(no2_collection.size().getInfo())
    if no2_global_count > 0:
        no2_image = no2_collection.select(
            "tropospheric_NO2_column_number_density"
        ).mean().rename("SAT_NO2_mol_m2")
        no2_reduced = no2_image.reduceRegions(
            collection=base_fc,
            reducer=ee.Reducer.mean(),
            scale=10000,
            tileScale=4,
        )
        for row in _feature_collection_records(no2_reduced):
            by_station[str(row["site_id"])]["SAT_NO2_mol_m2"] = safe_float(row.get("SAT_NO2_mol_m2"))
    else:
        for row in by_station.values():
            row["SAT_NO2_mol_m2"] = np.nan

    # FIRMS: daily max T21/confidence and count of spatial pixels with valid T21.
    firms_global_count = int(firms_collection.size().getInfo())
    if firms_global_count > 0:
        # FIRMS values and pixel counts are measured within each station's
        # configured 25 km buffer, matching the original spatial intent.
        firms_reduce_fc = base_fc.map(
            lambda feature: ee.Feature(feature).setGeometry(
                ee.Feature(feature).geometry().buffer(FIRE_RADIUS_METERS)
            )
        )
        firms_max = firms_collection.select(["T21", "confidence"]).max()
        t21_pixels = firms_max.select("T21").mask().rename("FIRE_PIXEL_COUNT_25KM")
        firms_image = firms_max.select("T21").rename("FIRE_T21_MAX_K_25KM")
        firms_image = firms_image.addBands(
            firms_max.select("confidence").rename("FIRE_CONF_MAX_PCT_25KM")
        ).addBands(t21_pixels)
        firms_reduced = firms_image.reduceRegions(
            collection=firms_reduce_fc,
            reducer=ee.Reducer.mean(),
            scale=1000,
            tileScale=4,
        )
        for row in _feature_collection_records(firms_reduced):
            sid = str(row["site_id"])
            by_station[sid]["FIRE_T21_MAX_K_25KM"] = safe_float(row.get("FIRE_T21_MAX_K_25KM"))
            by_station[sid]["FIRE_CONF_MAX_PCT_25KM"] = safe_float(row.get("FIRE_CONF_MAX_PCT_25KM"))
            # Reducer mean over the binary mask equals 1, not pixel count.
            # Compute the actual count using a count reducer over that mask.
        fire_count_reduced = t21_pixels.reduceRegions(
            collection=firms_reduce_fc,
            reducer=ee.Reducer.count(),
            scale=1000,
            tileScale=4,
        )
        for row in _feature_collection_records(fire_count_reduced):
            sid = str(row["site_id"])
            by_station[sid]["_FIRE_PIXEL_COUNT_AVAILABLE"] = safe_float(
                row.get("FIRE_PIXEL_COUNT_25KM")
            )
    else:
        for row in by_station.values():
            row["FIRE_T21_MAX_K_25KM"] = np.nan
            row["FIRE_CONF_MAX_PCT_25KM"] = np.nan
            row["_FIRE_PIXEL_COUNT_AVAILABLE"] = np.nan

    daily_records = []
    for station in fusion_stations:
        row = by_station[str(station)]
        firms_count = int(row.get("FIRMS_SOURCE_IMAGES", 0) or 0)
        fire_pixels = row.get("_FIRE_PIXEL_COUNT_AVAILABLE", np.nan)
        if firms_count == 0:
            fire_pixels = np.nan
            fire_present = None
            fire_t21 = np.nan
            fire_conf = np.nan
        else:
            # Source images exist but can contain no valid T21 pixels in region.
            if pd.isna(fire_pixels):
                fire_pixels = 0.0
            fire_present = bool(fire_pixels > 0)
            fire_t21 = row.get("FIRE_T21_MAX_K_25KM", np.nan)
            fire_conf = row.get("FIRE_CONF_MAX_PCT_25KM", np.nan)

        record = {
            "site_id": str(station),
            "CPCB_DATE": day_start,
            "station_name": station_metadata[station]["station_name"],
            "state": station_metadata[station]["state"],
            "latitude": station_metadata[station]["latitude"],
            "longitude": station_metadata[station]["longitude"],
            "AOD_055": row.get("AOD_055", np.nan),
            "AOD_055_UNFILTERED": row.get("AOD_055_UNFILTERED", np.nan),
            "AOD_SOURCE_IMAGES": int(row.get("AOD_SOURCE_IMAGES", 0) or 0),
            "AOD_QA_PASSED_IMAGES": int(row.get("AOD_QA_PASSED_IMAGES", 0) or 0),
            "AOD_VALID_POINT_VALUES": int(pd.notna(row.get("AOD_055", np.nan))),
            "AOD_TEMPORAL_RESOLUTION": "daily_composite",
            "HCHO_mol_m2": row.get("HCHO_mol_m2", np.nan),
            "HCHO_SOURCE_IMAGES": int(row.get("HCHO_SOURCE_IMAGES", 0) or 0),
            "HCHO_TEMPORAL_RESOLUTION": "daily_composite",
            "SAT_NO2_mol_m2": row.get("SAT_NO2_mol_m2", np.nan),
            "SAT_NO2_SOURCE_IMAGES": int(row.get("SAT_NO2_SOURCE_IMAGES", 0) or 0),
            "SAT_NO2_TEMPORAL_RESOLUTION": "daily_composite",
            "FIRE_PIXEL_COUNT_25KM": fire_pixels,
            "FIRE_PRESENT_25KM": fire_present,
            "FIRE_T21_MAX_K_25KM": fire_t21,
            "FIRE_CONF_MAX_PCT_25KM": fire_conf,
            "FIRMS_SOURCE_IMAGES": firms_count,
            "FIRMS_TEMPORAL_RESOLUTION": "daily_composite",
            "FIRE_COUNT_SEMANTICS": "distinct_valid_T21_raster_pixels_in_daily_max_composite_not_individual_detections",
        }
        daily_records.append(record)
        aod_qc_records.append({
            key: record[key]
            for key in [
                "site_id", "CPCB_DATE", "AOD_055", "AOD_055_UNFILTERED",
                "AOD_SOURCE_IMAGES", "AOD_QA_PASSED_IMAGES", "AOD_VALID_POINT_VALUES",
            ]
        })
        firms_qc_records.append({
            key: record[key]
            for key in [
                "site_id", "CPCB_DATE", "FIRE_PIXEL_COUNT_25KM", "FIRE_PRESENT_25KM",
                "FIRE_T21_MAX_K_25KM", "FIRE_CONF_MAX_PCT_25KM", "FIRMS_SOURCE_IMAGES",
                "FIRE_COUNT_SEMANTICS",
            ]
        })

    all_station_features.extend(daily_records)
    print(
        f"Daily satellite/FIRMS batch complete: {day_start} "
        f"({len(daily_records)} station records; "
        f"source images AOD/HCHO/NO2/FIRMS = "
        f"{aod_global_count}/{hcho_global_count}/{no2_global_count}/{firms_global_count})"
    )


for daily_day in pd.date_range(
    start=START_DATE,
    end=(pd.Timestamp(END_DATE) - pd.Timedelta(days=1)),
    freq="D",
):
    extract_daily_station_batch(daily_day)


# ============================================================
# COMBINE ERA5
# ============================================================

era5_all_df = pd.concat(
    era5_all,
    ignore_index=True
)

era5_all_df[
    "ERA5_TIMESTAMP_UTC"
] = pd.to_datetime(
    era5_all_df[
        "ERA5_TIMESTAMP_UTC"
    ],
    utc=True
)

era5_all_df = (
    era5_all_df
    .sort_values(
        [
            "site_id",
            "ERA5_TIMESTAMP_UTC"
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# ERA5 NEAREST-HOUR MATCH
# ============================================================

print("\n" + "=" * 70)
print("6. ERA5 TEMPORAL ALIGNMENT")
print("=" * 70)

# IMPORTANT:
#
# CPCB timestamps:
#     local India time
#
# ERA5:
#     UTC hourly timestamps
#
# Therefore:
#
#     CPCB IST -> CPCB UTC
#     then nearest ERA5 hourly timestamp
#
# We use merge_asof with:
#
#     direction = nearest
#     tolerance = 31 minutes
#
# The resulting difference is explicitly recorded.

cpcb_for_merge = fusion.copy()

# ------------------------------------------------------------
# Normalize merge-key dtype.
#
# pandas merge_asof requires both datetime keys to have the
# exact same dtype. Earth Engine timestamps and CPCB-derived
# timestamps can otherwise arrive at different datetime
# resolutions (for example ms vs us), even though both are UTC.
# ------------------------------------------------------------

cpcb_for_merge["CPCB_TIMESTAMP_UTC"] = (
    pd.to_datetime(
        cpcb_for_merge["CPCB_TIMESTAMP_UTC"],
        utc=True
    ).astype("datetime64[ms, UTC]")
)

cpcb_for_merge = (
    cpcb_for_merge
    .sort_values(
        [
            "CPCB_TIMESTAMP_UTC"
        ]
    )
    .reset_index(drop=True)
)

era5_for_merge = era5_all_df.copy()

era5_for_merge["ERA5_TIMESTAMP_UTC"] = (
    pd.to_datetime(
        era5_for_merge["ERA5_TIMESTAMP_UTC"],
        utc=True
    ).astype("datetime64[ms, UTC]")
)

era5_for_merge = (
    era5_for_merge
    .sort_values(
        [
            "ERA5_TIMESTAMP_UTC"
        ]
    )
    .reset_index(drop=True)
)

# Sanity check: merge_asof keys must match exactly.
if (
    cpcb_for_merge["CPCB_TIMESTAMP_UTC"].dtype
    != era5_for_merge["ERA5_TIMESTAMP_UTC"].dtype
):
    raise TypeError(
        "ERA5 merge-key dtype mismatch: "
        f"CPCB={cpcb_for_merge['CPCB_TIMESTAMP_UTC'].dtype}, "
        f"ERA5={era5_for_merge['ERA5_TIMESTAMP_UTC'].dtype}"
    )

print(
    "\nERA5 merge-key dtype:",
    cpcb_for_merge["CPCB_TIMESTAMP_UTC"].dtype
)


# ------------------------------------------------------------
# merge_asof requires globally sorted keys.
# We perform one station at a time to avoid cross-station
# matching.
# ------------------------------------------------------------

matched_station_frames = []

era5_qc_records = []


for station in fusion_stations:

    cpcb_station = (
        cpcb_for_merge[
            cpcb_for_merge["site_id"]
            == station
        ]
        .copy()
        .sort_values(
            "CPCB_TIMESTAMP_UTC"
        )
    )

    era5_station = (
        era5_for_merge[
            era5_for_merge["site_id"]
            == station
        ]
        .copy()
        .sort_values(
            "ERA5_TIMESTAMP_UTC"
        )
    )

    if era5_station.empty:

        print(
            f"\nStation {station}: "
            f"NO ERA5 DATA"
        )

        cpcb_station[
            "ERA5_TIMESTAMP_UTC"
        ] = pd.NaT

        cpcb_station[
            "TEMP_C"
        ] = np.nan

        cpcb_station[
            "DEWPOINT_C"
        ] = np.nan

        cpcb_station[
            "RH_PERCENT"
        ] = np.nan

        cpcb_station[
            "WIND_U_M_S"
        ] = np.nan

        cpcb_station[
            "WIND_V_M_S"
        ] = np.nan

        cpcb_station[
            "WIND_SPEED_M_S"
        ] = np.nan

    else:

        merged = pd.merge_asof(

            cpcb_station,

            era5_station[
                [
                    "ERA5_TIMESTAMP_UTC",
                    "TEMP_C",
                    "DEWPOINT_C",
                    "RH_PERCENT",
                    "WIND_U_M_S",
                    "WIND_V_M_S",
                    "WIND_SPEED_M_S",
                ]
            ],

            left_on="CPCB_TIMESTAMP_UTC",

            right_on="ERA5_TIMESTAMP_UTC",

            direction="nearest",

            tolerance=pd.Timedelta(
                minutes=
                ERA5_MATCH_TOLERANCE_MINUTES
            ),

        )

        cpcb_station = merged


    # --------------------------------------------------------
    # Calculate exact temporal difference.
    # --------------------------------------------------------

    cpcb_station[
        "ERA5_TIME_DIFF_MINUTES"
    ] = (

        (
            cpcb_station[
                "CPCB_TIMESTAMP_UTC"
            ]
            -
            cpcb_station[
                "ERA5_TIMESTAMP_UTC"
            ]
        )
        .abs()
        .dt.total_seconds()
        / 60.0

    )

    cpcb_station[
        "ERA5_HOURLY_MATCH"
    ] = (
        cpcb_station[
            "ERA5_TIMESTAMP_UTC"
        ]
        .notna()
    )

    cpcb_station[
        "ERA5_TEMPORAL_RESOLUTION"
    ] = (
        "hourly_source_nearest_match"
    )

    matched_station_frames.append(
        cpcb_station
    )


    # --------------------------------------------------------
    # QC
    # --------------------------------------------------------

    matches = int(
        cpcb_station[
            "ERA5_HOURLY_MATCH"
        ].sum()
    )

    total = len(
        cpcb_station
    )

    diffs = (
        cpcb_station[
            "ERA5_TIME_DIFF_MINUTES"
        ]
        .dropna()
    )

    if len(diffs) > 0:

        min_diff = float(
            diffs.min()
        )

        max_diff = float(
            diffs.max()
        )

        mean_diff = float(
            diffs.mean()
        )

        median_diff = float(
            diffs.median()
        )

    else:

        min_diff = np.nan
        max_diff = np.nan
        mean_diff = np.nan
        median_diff = np.nan


    print(
        f"\nStation {station}"
    )

    print(
        f"  CPCB rows       : {total}"
    )

    print(
        f"  ERA5 matches    : "
        f"{matches}/{total}"
    )

    print(
        f"  Min diff        : "
        f"{min_diff} min"
    )

    print(
        f"  Max diff        : "
        f"{max_diff} min"
    )

    print(
        f"  Mean diff       : "
        f"{mean_diff} min"
    )

    print(
        f"  Median diff     : "
        f"{median_diff} min"
    )


    era5_qc_records.append({

        "site_id":
            station,

        "CPCB_ROWS":
            total,

        "ERA5_SOURCE_ROWS":
            len(era5_station),

        "ERA5_MATCHED_ROWS":
            matches,

        "ERA5_MATCH_RATE":
            (
                matches / total
                if total > 0
                else np.nan
            ),

        "ERA5_TIME_DIFF_MINUTES_MIN":
            min_diff,

        "ERA5_TIME_DIFF_MINUTES_MAX":
            max_diff,

        "ERA5_TIME_DIFF_MINUTES_MEAN":
            mean_diff,

        "ERA5_TIME_DIFF_MINUTES_MEDIAN":
            median_diff,

        "ERA5_MATCH_TOLERANCE_MINUTES":
            ERA5_MATCH_TOLERANCE_MINUTES,

    })


# ============================================================
# COMBINE MATCHED CPCB DATA
# ============================================================

fusion = pd.concat(
    matched_station_frames,
    ignore_index=True
)


# ============================================================
# MERGE DAILY STATION FEATURES
# ============================================================

station_features_df = pd.DataFrame(
    all_station_features
)

# Daily satellite/fire features join to CPCB rows on station AND local date.
fusion["CPCB_DATE"] = pd.to_datetime(
    fusion["CPCB_TIMESTAMP_IST"]
).dt.strftime("%Y-%m-%d")
station_features_df["CPCB_DATE"] = pd.to_datetime(
    station_features_df["CPCB_DATE"]
).dt.strftime("%Y-%m-%d")

if station_features_df.duplicated(["site_id", "CPCB_DATE"]).any():
    raise ValueError(
        "Daily station features contain duplicate site_id/CPCB_DATE keys."
    )

fusion = fusion.merge(
    station_features_df,
    on=["site_id", "CPCB_DATE"],
    how="left",
    validate="many_to_one"
)


# ============================================================
# SORT FINAL DATA
# ============================================================

fusion = (
    fusion
    .sort_values(
        [
            "site_id",
            "CPCB_TIMESTAMP_IST"
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# REMOVE INTERNAL DUPLICATE COLUMNS IF ANY
# ============================================================

duplicate_columns = (
    fusion.columns[
        fusion.columns.duplicated()
    ]
    .tolist()
)

if duplicate_columns:

    print(
        "\nRemoving duplicate columns:",
        duplicate_columns
    )

    fusion = fusion.loc[
        :,
        ~fusion.columns.duplicated()
    ]


# ============================================================
# ADD EXPLICIT TEMPORAL SEMANTICS
# ============================================================

fusion[
    "CPCB_TIMESTAMP_SEMANTICS"
] = (
    "CPCB source timestamp interpreted as India local time "
    "for this nationwide extraction; confirm source timestamp convention "
    "before production extraction"
)

fusion[
    "ERA5_MATCH_METHOD"
] = (
    "nearest ERA5 hourly observation to CPCB timestamp "
    "after IST-to-UTC conversion"
)

fusion[
    "ERA5_MATCH_TOLERANCE_MINUTES"
] = (
    ERA5_MATCH_TOLERANCE_MINUTES
)


# ============================================================
# FINAL COLUMN ORDER
# ============================================================

preferred_columns = [

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    "site_id",
    "station_name",
    "state",
    "latitude",
    "longitude",

    # --------------------------------------------------------
    # CPCB time
    # --------------------------------------------------------

    "CPCB_TIMESTAMP_ORIGINAL",
    "CPCB_TIMESTAMP_IST",
    "CPCB_TIMESTAMP_UTC",

    # --------------------------------------------------------
    # CPCB pollutants
    # --------------------------------------------------------

    "PM25",
    "PM10",
    "NO2",
    "O3",
    "SO2",
    "CO",
    "NH3",

    # --------------------------------------------------------
    # ERA5
    # --------------------------------------------------------

    "ERA5_TIMESTAMP_UTC",
    "ERA5_TIME_DIFF_MINUTES",
    "ERA5_HOURLY_MATCH",

    "TEMP_C",
    "DEWPOINT_C",
    "RH_PERCENT",

    "WIND_U_M_S",
    "WIND_V_M_S",
    "WIND_SPEED_M_S",

    "ERA5_TEMPORAL_RESOLUTION",

    # --------------------------------------------------------
    # Satellite AOD
    # --------------------------------------------------------

    "AOD_055",
    "AOD_055_UNFILTERED",
    "AOD_SOURCE_IMAGES",
    "AOD_QA_PASSED_IMAGES",
    "AOD_VALID_POINT_VALUES",
    "AOD_TEMPORAL_RESOLUTION",

    # --------------------------------------------------------
    # HCHO
    # --------------------------------------------------------

    "HCHO_mol_m2",
    "HCHO_SOURCE_IMAGES",
    "HCHO_TEMPORAL_RESOLUTION",

    # --------------------------------------------------------
    # Satellite NO2
    # --------------------------------------------------------

    "SAT_NO2_mol_m2",
    "SAT_NO2_SOURCE_IMAGES",
    "SAT_NO2_TEMPORAL_RESOLUTION",

    # --------------------------------------------------------
    # FIRMS
    # --------------------------------------------------------

    "FIRE_PIXEL_COUNT_25KM",
    "FIRE_PRESENT_25KM",
    "FIRE_T21_MAX_K_25KM",
    "FIRE_CONF_MAX_PCT_25KM",

    "FIRMS_SOURCE_IMAGES",
    "FIRMS_TEMPORAL_RESOLUTION",
    "FIRE_COUNT_SEMANTICS",

    # --------------------------------------------------------
    # Temporal documentation
    # --------------------------------------------------------

    "CPCB_TIMESTAMP_SEMANTICS",
    "ERA5_MATCH_METHOD",
    "ERA5_MATCH_TOLERANCE_MINUTES",
]


existing_preferred = [
    c for c in preferred_columns
    if c in fusion.columns
]

remaining_columns = [
    c for c in fusion.columns
    if c not in existing_preferred
]

fusion = fusion[
    existing_preferred
    +
    remaining_columns
]


# ============================================================
# VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("7. FINAL FUSION VALIDATION")
print("=" * 70)


# ------------------------------------------------------------
# Row count
# ------------------------------------------------------------

print(
    f"\nRows: {len(fusion)}"
)

if fusion.empty:
    raise ValueError(
        "Fusion dataset is empty."
    )

# ------------------------------------------------------------
# Station count
# ------------------------------------------------------------

station_count = (
    fusion["site_id"]
    .nunique()
)

print(
    f"Stations: {station_count}"
)

if station_count != len(fusion_stations):

    raise ValueError(
        f"Unexpected station count: "
        f"{station_count}, expected {len(fusion_stations)}."
    )

# ------------------------------------------------------------
# Rows per station
# ------------------------------------------------------------

print(
    "\nRows per station:"
)

rows_per_station = (
    fusion
    .groupby("site_id")
    .size()
)

print(
    rows_per_station.to_string()
)

if rows_per_station.empty:

    raise ValueError(
        "No station rows found in final fusion."
    )


# ------------------------------------------------------------
# Duplicate station-hour
# ------------------------------------------------------------

duplicates = fusion.duplicated(
    subset=[
        "site_id",
        "CPCB_TIMESTAMP_IST"
    ]
).sum()

print(
    f"\nDuplicate station-hour rows: "
    f"{duplicates}"
)

if duplicates != 0:

    raise ValueError(
        "Duplicate station-hour rows detected."
    )


# ============================================================
# CPCB MISSINGNESS
# ============================================================
print(
    "\nCPCB pollutant completeness:"
)

total_rows = len(fusion)

for pollutant in POLLUTANTS:

    valid = int(
        fusion[pollutant]
        .notna()
        .sum()
    )

    missing = total_rows - valid

    missing_pct = (
        (missing / total_rows) * 100
        if total_rows > 0
        else np.nan
    )

    print(
        f"  {pollutant:5s}: "
        f"{valid}/{total_rows} valid "
        f"({missing_pct:.2f}% missing)"
    )

# ============================================================
# HCHO
# ============================================================

hcho_missing = int(
    fusion["HCHO_mol_m2"]
    .isna()
    .sum()
)

f"\nHCHO missing: "
f"{hcho_missing}/{len(fusion)}"


# ============================================================
# SATELLITE NO2
# ============================================================

sat_no2_missing = int(
    fusion["SAT_NO2_mol_m2"]
    .isna()
    .sum()
)

print(
    f"Satellite NO2 missing: "
    f"{sat_no2_missing}/{len(fusion)}"
)

# ============================================================
# ERA5 MATCH VALIDATION
# ============================================================

era5_matches = int(
    fusion[
        "ERA5_HOURLY_MATCH"
    ]
    .sum()
)

era5_total = len(
    fusion
)

print(
    f"\nERA5 hourly matches: "
    f"{era5_matches}/{era5_total}"
)


era5_match_rate = (
    era5_matches
    /
    era5_total
    *
    100
)


print(
    f"ERA5 match rate: "
    f"{era5_match_rate:.2f}%"
)


if era5_matches != era5_total:

    warnings.warn(
        "Not all CPCB rows received an ERA5 match. "
        "Inspect V3_ERA5_QC.csv."
    )


# ============================================================
# ERA5 TIME DIFFERENCE
# ============================================================

era5_diffs = (
    fusion[
        "ERA5_TIME_DIFF_MINUTES"
    ]
    .dropna()
)

if len(era5_diffs) > 0:

    print(
        "\nERA5 time difference summary:"
    )

    print(
        f"  min    : "
        f"{era5_diffs.min():.2f} min"
    )

    print(
        f"  max    : "
        f"{era5_diffs.max():.2f} min"
    )

    print(
        f"  mean   : "
        f"{era5_diffs.mean():.2f} min"
    )

    print(
        f"  median : "
        f"{era5_diffs.median():.2f} min"
    )


# ============================================================
# FIRMS VALIDATION
# ============================================================

print(
    "\nFIRMS summary:"
)

firms_summary = (
    fusion[
        [
            "site_id",
            "CPCB_DATE",
            "FIRE_PRESENT_25KM",
            "FIRE_PIXEL_COUNT_25KM",
            "FIRE_T21_MAX_K_25KM",
            "FIRE_CONF_MAX_PCT_25KM",
        ]
    ]
    .drop_duplicates(
        subset=["site_id", "CPCB_DATE"]
    )
)

print(
    firms_summary.to_string(
        index=False
    )
)


# ============================================================
# AOD VALIDATION
# ============================================================

print(
    "\nAOD summary:"
)

aod_summary = (
    fusion[
        [
            "site_id",
            "CPCB_DATE",
            "AOD_SOURCE_IMAGES",
            "AOD_QA_PASSED_IMAGES",
            "AOD_VALID_POINT_VALUES",
            "AOD_055",
            "AOD_055_UNFILTERED",
        ]
    ]
    .drop_duplicates(
        subset=["site_id", "CPCB_DATE"]
    )
)

print(
    aod_summary.to_string(
        index=False
    )
)


# ============================================================
# CHECK SOURCE COUNTS
# ============================================================

print(
    "\nSource image counts:"
)

source_summary = (
    fusion[
        [
            "site_id",
            "AOD_SOURCE_IMAGES",
            "HCHO_SOURCE_IMAGES",
            "SAT_NO2_SOURCE_IMAGES",
            "FIRMS_SOURCE_IMAGES",
        ]
    ]
    .drop_duplicates(
        subset=["site_id"]
    )
)

print(
    source_summary.to_string(
        index=False
    )
)


# ============================================================
# SAVE MAIN DATASET
# ============================================================

print("\n" + "=" * 70)
print("8. SAVING OUTPUT")
print("=" * 70)

fusion.to_csv(
    OUTPUT_MAIN,
    index=False
)

print(
    f"\nMain fusion dataset:"
)

print(
    OUTPUT_MAIN
)


# ============================================================
# BUILD GENERAL QC
# ============================================================

qc_rows = []

for station in fusion_stations:

    station_df = fusion[
        fusion["site_id"] == station
    ]

    row = {

        "site_id":
            station,

        "rows":
            len(station_df),

        "duplicate_station_hour":
            int(
                station_df.duplicated(
                    subset=[
                        "site_id",
                        "CPCB_TIMESTAMP_IST"
                    ]
                ).sum()
            ),

        "PM25_missing":
            int(
                station_df["PM25"]
                .isna()
                .sum()
            ),

        "PM10_missing":
            int(
                station_df["PM10"]
                .isna()
                .sum()
            ),

        "NO2_missing":
            int(
                station_df["NO2"]
                .isna()
                .sum()
            ),

        "O3_missing":
            int(
                station_df["O3"]
                .isna()
                .sum()
            ),

        "SO2_missing":
            int(
                station_df["SO2"]
                .isna()
                .sum()
            ),

        "CO_missing":
            int(
                station_df["CO"]
                .isna()
                .sum()
            ),

        "NH3_missing":
            int(
                station_df["NH3"]
                .isna()
                .sum()
            ),

        "HCHO_missing":
            int(
                station_df["HCHO_mol_m2"]
                .isna()
                .sum()
            ),

        "SAT_NO2_missing":
            int(
                station_df[
                    "SAT_NO2_mol_m2"
                ]
                .isna()
                .sum()
            ),

        "ERA5_missing":
            int(
                station_df[
                    "ERA5_HOURLY_MATCH"
                ]
                .eq(False)
                .sum()
            ),

        "FIRE_PRESENT_ROWS":
            int(
                station_df[
                    "FIRE_PRESENT_25KM"
                ]
                .fillna(False)
                .sum()
            ),

        "AOD_missing":
            int(
                station_df[
                    "AOD_055"
                ]
                .isna()
                .sum()
            ),

    }

    qc_rows.append(row)


qc_df = pd.DataFrame(
    qc_rows
)

qc_df.to_csv(
    OUTPUT_QC,
    index=False
)

print(
    "\nGeneral QC:"
)

print(
    OUTPUT_QC
)


# ============================================================
# SAVE AOD QC
# ============================================================

aod_qc_df = pd.DataFrame(
    aod_qc_records
)

aod_qc_df.to_csv(
    OUTPUT_AOD_QC,
    index=False
)

print(
    "\nAOD QC:"
)

print(
    OUTPUT_AOD_QC
)


# ============================================================
# SAVE ERA5 QC
# ============================================================

era5_qc_df = pd.DataFrame(
    era5_qc_records
)

era5_qc_df.to_csv(
    OUTPUT_ERA5_QC,
    index=False
)

print(
    "\nERA5 QC:"
)

print(
    OUTPUT_ERA5_QC
)


# ============================================================
# SAVE FIRMS QC
# ============================================================

firms_qc_df = pd.DataFrame(
    firms_qc_records
)

firms_qc_df.to_csv(
    OUTPUT_FIRMS_QC,
    index=False
)

print(
    "\nFIRMS QC:"
)

print(
    OUTPUT_FIRMS_QC
)


# ============================================================
# FINAL SAMPLE
# ============================================================

print("\n" + "=" * 70)
print("9. FINAL SAMPLE")
print("=" * 70)

display_columns = [

    "site_id",

    "CPCB_TIMESTAMP_IST",

    "CPCB_TIMESTAMP_UTC",

    "ERA5_TIMESTAMP_UTC",

    "ERA5_TIME_DIFF_MINUTES",

    "ERA5_HOURLY_MATCH",

    "PM25",

    "PM10",

    "NO2",

    "O3",

    "SO2",

    "CO",

    "NH3",

    "AOD_055",

    "HCHO_mol_m2",

    "SAT_NO2_mol_m2",

    "TEMP_C",

    "DEWPOINT_C",

    "RH_PERCENT",

    "WIND_U_M_S",

    "WIND_V_M_S",

    "WIND_SPEED_M_S",

    "FIRE_PRESENT_25KM",

    "FIRE_PIXEL_COUNT_25KM",

]


available_display_columns = [
    c
    for c in display_columns
    if c in fusion.columns
]

print(
    fusion[
        available_display_columns
    ]
    .head(12)
    .to_string(index=False)
)


# ============================================================
# FINAL STATUS
# ============================================================

print("\n" + "=" * 70)
print("AEROVISION FUSION NATIONWIDE COMPLETE")
print("=" * 70)

print(
    f"\nRows              : {len(fusion)}"
)

print(
    f"Stations          : "
    f"{fusion['site_id'].nunique()}"
)

print(
    f"Total rows        : {len(fusion)}"
)
print(
    f"ERA5 matches      : "
    f"{era5_matches}/{era5_total}"
)
print(
    f"ERA5 match rate   : "
    f"{era5_match_rate:.2f}%"
)

print(
    "\nOutput files:"
)

print(
    f"  MAIN    : {OUTPUT_MAIN}"
)

print(
    f"  QC      : {OUTPUT_QC}"
)

print(
    f"  AOD QC  : {OUTPUT_AOD_QC}"
)

print(
    f"  ERA5 QC : {OUTPUT_ERA5_QC}"
)

print(
    f"  FIRMS QC: {OUTPUT_FIRMS_QC}"
)

print(
    "\nNext step:"
)

print(
    "Inspect nationwide ERA5 temporal alignment, "
    "AOD missingness, FIRMS semantics, and overall "
    "feature completeness before CNN-LSTM preparation."
)
print("=" * 70)	