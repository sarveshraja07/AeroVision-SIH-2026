# ============================================================
# AEROVISION INDIA
# REGIONAL REAL-DATA AQI SURFACE GENERATOR
#
# EVENT DATE:
#   08 June 2026
#
# REGION:
#   27N - 33N
#   73E - 79E
#
# GRID:
#   0.25 degree
#
# REAL INPUTS:
#   MODIS MAIAC AOD
#   Sentinel-5P HCHO
#   Sentinel-5P NO2
#   ERA5-Land weather
#   NASA FIRMS fire activity
#
# MODELS:
#   Current AeroVision production V3 XGBoost models
#
# OUTPUT:
#   data/exports/aqi_surface_2026_06_08.geojson
#
# IMPORTANT:
# - No interpolation from CPCB stations.
# - No simulated pollutant concentrations.
# - Missing satellite pixels remain missing / NaN.
# - FIRMS count = 0 is legitimate when no fire is detected.
# - This is a regional prototype surface, not India-wide
#   scientific validation.
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

from pathlib import Path

import json
import math
import time
import warnings

import ee
import joblib
import numpy as np
import pandas as pd


warnings.filterwarnings(
    "ignore"
)


# ============================================================
# PROJECT PATHS
# ============================================================

ROOT = Path(
    __file__
).resolve().parents[1]


EXPORT_DIR = (
    ROOT
    / "data"
    / "exports"
)


PRODUCTION_DIR = (
    ROOT
    / "models"
    / "production"
)


EXPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# OUTPUT FILES
# ============================================================

EVENT_DATE_TEXT = (
    "2026-06-08"
)


OUTPUT_GEOJSON = (
    EXPORT_DIR
    / "aqi_surface_2026_06_08.geojson"
)


OUTPUT_CSV = (
    EXPORT_DIR
    / "aqi_surface_features_2026_06_08.csv"
)


OUTPUT_SUMMARY = (
    EXPORT_DIR
    / "aqi_surface_summary_2026_06_08.json"
)


# ============================================================
# EARTH ENGINE PROJECT
# ============================================================

EE_PROJECT = (
    "aqi-sih-506616"
)


# ============================================================
# REGION
# ============================================================

MIN_LAT = 27.0
MAX_LAT = 33.0

MIN_LON = 73.0
MAX_LON = 79.0


# ============================================================
# GRID SIZE
# ============================================================
#
# 0.25 degrees creates:
#
# 24 x 24 = 576 cells
#
# This is detailed enough for the demo without creating
# thousands of expensive Earth Engine requests.
# ============================================================

GRID_STEP = 0.25


# ============================================================
# GEE BATCH SIZE
# ============================================================

BATCH_SIZE = 25


# ============================================================
# V3 FEATURES
# ============================================================

DEFAULT_FEATURES = [

    "AOD",

    "ERA5_DEWPOINT",

    "ERA5_RH",

    "ERA5_TEMP",

    "HCHO",

    "SAT_NO2",

    "WIND_SPEED",

    "WIND_U",

    "WIND_V",

    "FIRE_COUNT_25KM",

    "FIRE_CONF_MAX_25KM",

    "FIRE_T21_MAX_25KM",

    "latitude",

    "longitude",
]


# ============================================================
# MODEL PATHS
# ============================================================

MODEL_PATHS = {

    "PM25":
        PRODUCTION_DIR
        / "aerovision_PM25.joblib",

    "PM10":
        PRODUCTION_DIR
        / "aerovision_PM10.joblib",

    "NO2":
        PRODUCTION_DIR
        / "aerovision_NO2.joblib",

    "O3_8H":
        PRODUCTION_DIR
        / "aerovision_O3_8H.joblib",
}


# ============================================================
# START
# ============================================================

print()
print("=" * 72)
print("AEROVISION REGIONAL AQI SURFACE")
print("=" * 72)

print()
print(
    "Event date :",
    EVENT_DATE_TEXT
)

print(
    "Region     :",
    f"{MIN_LAT} -> {MAX_LAT} N,",
    f"{MIN_LON} -> {MAX_LON} E"
)

print(
    "Grid step  :",
    GRID_STEP,
    "degrees"
)


# ============================================================
# INITIALIZE EARTH ENGINE
# ============================================================

print()
print(
    "Initializing Google Earth Engine..."
)


try:

    ee.Initialize(
        project=EE_PROJECT
    )


except Exception as exc:

    print()
    print(
        "Earth Engine initialization failed."
    )

    print()
    print(
        "Run this first:"
    )

    print()
    print(
        "earthengine authenticate"
    )

    print()

    raise exc


print(
    "Earth Engine initialized:",
    EE_PROJECT
)


# ============================================================
# LOAD FEATURE LIST
# ============================================================

FEATURE_LIST_FILE = (
    PRODUCTION_DIR
    / "feature_list.json"
)


if FEATURE_LIST_FILE.exists():

    with open(
        FEATURE_LIST_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        FEATURES = json.load(
            file
        )


else:

    FEATURES = DEFAULT_FEATURES.copy()


print()
print(
    "Model features:"
)

for feature in FEATURES:

    print(
        " -",
        feature
    )


# ============================================================
# VERIFY FEATURES
# ============================================================

missing_required_features = (

    set(
        DEFAULT_FEATURES
    )

    -

    set(
        FEATURES
    )

)


if missing_required_features:

    print()
    print(
        "WARNING:"
    )

    print(
        "Production feature_list.json differs "
        "from the expected V3 feature set."
    )

    print(
        "Missing expected fields:",
        sorted(
            missing_required_features
        )
    )


# ============================================================
# LOAD MODELS
# ============================================================

print()
print(
    "Loading production models..."
)


models = {}


for target, path in MODEL_PATHS.items():

    if not path.exists():

        raise FileNotFoundError(
            f"Missing model: {path}"
        )


    models[target] = joblib.load(
        path
    )


    print(
        "Loaded:",
        target,
        "->",
        path.name
    )


# ============================================================
# EVENT DATES
# ============================================================

START_DATE = ee.Date(
    EVENT_DATE_TEXT
)


END_DATE = START_DATE.advance(
    1,
    "day"
)


# ============================================================
# PROTOTYPE REGION
# ============================================================

REGION = ee.Geometry.Rectangle(

    [
        MIN_LON,
        MIN_LAT,
        MAX_LON,
        MAX_LAT
    ],

    geodesic=False

)


# ============================================================
# MODIS MAIAC AOD
# ============================================================
#
# Dataset:
# MODIS/061/MCD19A2_GRANULES
#
# Band:
# Optical_Depth_055
#
# Scale factor:
# 0.001
# ============================================================

print()
print(
    "Preparing MODIS AOD..."
)


aod_collection = (

    ee.ImageCollection(
        "MODIS/061/MCD19A2_GRANULES"
    )

    .filterDate(
        START_DATE,
        END_DATE
    )

    .filterBounds(
        REGION
    )

    .select(
        "Optical_Depth_055"
    )

)


aod_count = int(
    aod_collection
    .size()
    .getInfo()
)


print(
    "MODIS images:",
    aod_count
)


AOD_IMAGE = (

    aod_collection
    .mean()

    .multiply(
        0.001
    )

    .rename(
        "AOD"
    )

)


# ============================================================
# SENTINEL-5P HCHO
# ============================================================

print()
print(
    "Preparing Sentinel-5P HCHO..."
)


hcho_collection = (

    ee.ImageCollection(
        "COPERNICUS/S5P/OFFL/L3_HCHO"
    )

    .filterDate(
        START_DATE,
        END_DATE
    )

    .filterBounds(
        REGION
    )

    .select(
        "tropospheric_HCHO_column_number_density"
    )

)


hcho_count = int(
    hcho_collection
    .size()
    .getInfo()
)


print(
    "HCHO images:",
    hcho_count
)


HCHO_IMAGE = (

    hcho_collection
    .mean()

    .rename(
        "HCHO"
    )

)


# ============================================================
# SENTINEL-5P NO2
# ============================================================

print()
print(
    "Preparing Sentinel-5P NO2..."
)


no2_collection = (

    ee.ImageCollection(
        "COPERNICUS/S5P/OFFL/L3_NO2"
    )

    .filterDate(
        START_DATE,
        END_DATE
    )

    .filterBounds(
        REGION
    )

    .select(
        "tropospheric_NO2_column_number_density"
    )

)


no2_count = int(
    no2_collection
    .size()
    .getInfo()
)


print(
    "NO2 images:",
    no2_count
)


NO2_IMAGE = (

    no2_collection
    .mean()

    .rename(
        "SAT_NO2"
    )

)


# ============================================================
# ERA5 LAND
# ============================================================

print()
print(
    "Preparing ERA5-Land..."
)


era5_collection = (

    ee.ImageCollection(
        "ECMWF/ERA5_LAND/HOURLY"
    )

    .filterDate(
        START_DATE,
        END_DATE
    )

    .filterBounds(
        REGION
    )

)


era5_count = int(
    era5_collection
    .size()
    .getInfo()
)


print(
    "ERA5 hourly images:",
    era5_count
)


# ============================================================
# DAILY ERA5 MEANS
# ============================================================

ERA5_TEMP_K = (

    era5_collection

    .select(
        "temperature_2m"
    )

    .mean()

)


ERA5_DEWPOINT_K = (

    era5_collection

    .select(
        "dewpoint_temperature_2m"
    )

    .mean()

)


ERA5_U = (

    era5_collection

    .select(
        "u_component_of_wind_10m"
    )

    .mean()

    .rename(
        "WIND_U"
    )

)


ERA5_V = (

    era5_collection

    .select(
        "v_component_of_wind_10m"
    )

    .mean()

    .rename(
        "WIND_V"
    )

)


# ============================================================
# KELVIN -> CELSIUS
# ============================================================

ERA5_TEMP = (

    ERA5_TEMP_K

    .subtract(
        273.15
    )

    .rename(
        "ERA5_TEMP"
    )

)


ERA5_DEWPOINT = (

    ERA5_DEWPOINT_K

    .subtract(
        273.15
    )

    .rename(
        "ERA5_DEWPOINT"
    )

)


# ============================================================
# RELATIVE HUMIDITY
#
# Magnus formula
# ============================================================

# ============================================================
# RELATIVE HUMIDITY
#
# Magnus formula calculated directly with Earth Engine
# image arithmetic.
#
# RH = 100 * exp(17.625*Td/(243.04+Td))
#          / exp(17.625*T /(243.04+T))
#
# T  = air temperature in Celsius
# Td = dew point in Celsius
# ============================================================

print(
    "Calculating ERA5 relative humidity..."
)


# ------------------------------------------------------------
# Saturation component using dew point
# ------------------------------------------------------------

dewpoint_exponent = (

    ERA5_DEWPOINT

    .multiply(
        17.625
    )

    .divide(

        ERA5_DEWPOINT
        .add(
            243.04
        )

    )

)


dewpoint_vapor = (
    dewpoint_exponent
    .exp()
)


# ------------------------------------------------------------
# Saturation component using temperature
# ------------------------------------------------------------

temperature_exponent = (

    ERA5_TEMP

    .multiply(
        17.625
    )

    .divide(

        ERA5_TEMP
        .add(
            243.04
        )

    )

)


temperature_vapor = (
    temperature_exponent
    .exp()
)


# ------------------------------------------------------------
# Relative humidity %
# ------------------------------------------------------------

ERA5_RH = (

    dewpoint_vapor

    .divide(
        temperature_vapor
    )

    .multiply(
        100
    )

    .clamp(
        0,
        100
    )

    .rename(
        "ERA5_RH"
    )

)


print(
    "ERA5 relative humidity prepared."
)

# ============================================================
# WIND SPEED
# ============================================================

WIND_SPEED = (

    ERA5_U
    .pow(
        2
    )

    .add(

        ERA5_V
        .pow(
            2
        )

    )

    .sqrt()

    .rename(
        "WIND_SPEED"
    )

)


# ============================================================
# NASA FIRMS
# ============================================================

print()
print(
    "Preparing NASA FIRMS..."
)


fire_collection = (

    ee.ImageCollection(
        "FIRMS"
    )

    .filterDate(
        START_DATE,
        END_DATE
    )

    .filterBounds(
        REGION.buffer(
            25000
        )
    )

)


fire_image_count = int(

    fire_collection
    .size()
    .getInfo()

)


print(
    "FIRMS images:",
    fire_image_count
)


# ============================================================
# FIRE DETECTION COUNT IMAGE
#
# Each high-confidence observation contributes 1.
# ============================================================

def make_high_confidence_fire(image):

    confidence = (
        image
        .select(
            "confidence"
        )
    )


    return (

        confidence
        .gte(
            80
        )

        .selfMask()

        .rename(
            "FIRE_DETECTION"
        )

    )


HIGH_CONF_FIRE_COUNT_IMAGE = (

    fire_collection

    .map(
        make_high_confidence_fire
    )

    .sum()

    .rename(
        "FIRE_COUNT"
    )

)


# ============================================================
# MAXIMUM FIRE CONFIDENCE
# ============================================================

FIRE_CONFIDENCE_IMAGE = (

    fire_collection

    .select(
        "confidence"
    )

    .max()

    .updateMask(

        fire_collection

        .select(
            "confidence"
        )

        .max()

        .gte(
            80
        )

    )

    .rename(
        "FIRE_CONFIDENCE"
    )

)


# ============================================================
# MAXIMUM T21
# ============================================================

FIRE_T21_IMAGE = (

    fire_collection

    .select(
        "T21"
    )

    .max()

    .updateMask(

        fire_collection

        .select(
            "confidence"
        )

        .max()

        .gte(
            80
        )

    )

    .rename(
        "FIRE_T21"
    )

)


# ============================================================
# GRID GENERATION
# ============================================================

print()
print(
    "Creating regional grid..."
)


half_step = (
    GRID_STEP
    /
    2.0
)


latitudes = np.arange(

    MIN_LAT + half_step,

    MAX_LAT,

    GRID_STEP

)


longitudes = np.arange(

    MIN_LON + half_step,

    MAX_LON,

    GRID_STEP

)


grid_rows = []


grid_id = 0


for latitude in latitudes:

    for longitude in longitudes:

        grid_rows.append(

            {

                "grid_id":
                    grid_id,

                "latitude":
                    float(
                        latitude
                    ),

                "longitude":
                    float(
                        longitude
                    )

            }

        )


        grid_id += 1


print(
    "Grid points:",
    len(
        grid_rows
    )
)


print(
    "Grid dimensions:",
    len(
        latitudes
    ),
    "x",
    len(
        longitudes
    )
)


# ============================================================
# EARTH ENGINE SAMPLE FUNCTION
# ============================================================

def enrich_feature(feature):

    feature = ee.Feature(
        feature
    )


    point = feature.geometry()


    # --------------------------------------------------------
    # MODIS AOD
    # --------------------------------------------------------

    aod_value = (

        AOD_IMAGE
        .reduceRegion(

            reducer=
                ee.Reducer.first(),

            geometry=
                point,

            scale=
                1000,

            bestEffort=
                True,

            maxPixels=
                 10000000

        )

        .get(
            "AOD"
        )

    )


    # --------------------------------------------------------
    # HCHO
    # --------------------------------------------------------

    hcho_value = (

        HCHO_IMAGE
        .reduceRegion(

            reducer=
                ee.Reducer.first(),

            geometry=
                point,

            scale=
                5000,

            bestEffort=
                True,

            maxPixels=
                 10000000

        )

        .get(
            "HCHO"
        )

    )


    # --------------------------------------------------------
    # SATELLITE NO2
    # --------------------------------------------------------

    sat_no2_value = (

        NO2_IMAGE
        .reduceRegion(

            reducer=
                ee.Reducer.first(),

            geometry=
                point,

            scale=
                5000,

            bestEffort=
                True,

            maxPixels=
                 10000000

        )

        .get(
            "SAT_NO2"
        )

    )


    # --------------------------------------------------------
    # ERA5 TEMP
    # --------------------------------------------------------

    temperature = (

        ERA5_TEMP
        .reduceRegion(

            reducer=
                ee.Reducer.first(),

            geometry=
                point,

            scale=
                10000,

            bestEffort=
                True,

            maxPixels=
                 10000000

        )

        .get(
            "ERA5_TEMP"
        )

    )


    # --------------------------------------------------------
    # ERA5 DEWPOINT
    # --------------------------------------------------------

    dewpoint = (

        ERA5_DEWPOINT
        .reduceRegion(

            reducer=
                ee.Reducer.first(),

            geometry=
                point,

            scale=
                10000,

            bestEffort=
                True,

            maxPixels=
                 10000000

        )

        .get(
            "ERA5_DEWPOINT"
        )

    )


    # --------------------------------------------------------
    # ERA5 RH
    # --------------------------------------------------------

    humidity = (

        ERA5_RH
        .reduceRegion(

            reducer=
                ee.Reducer.first(),

            geometry=
                point,

            scale=
                10000,

            bestEffort=
                True,

            maxPixels=
                 10000000

        )

        .get(
            "ERA5_RH"
        )

    )


    # --------------------------------------------------------
    # WIND U
    # --------------------------------------------------------

    wind_u = (

        ERA5_U
        .reduceRegion(

            reducer=
                ee.Reducer.first(),

            geometry=
                point,

            scale=
                10000,

            bestEffort=
                True,

            maxPixels=
                 10000000

        )

        .get(
            "WIND_U"
        )

    )


    # --------------------------------------------------------
    # WIND V
    # --------------------------------------------------------

    wind_v = (

        ERA5_V
        .reduceRegion(

            reducer=
                ee.Reducer.first(),

            geometry=
                point,

            scale=
                10000,

            bestEffort=
                True,

            maxPixels=
                 10000000

        )

        .get(
            "WIND_V"
        )

    )


    # --------------------------------------------------------
    # WIND SPEED
    # --------------------------------------------------------

    wind_speed = (

        WIND_SPEED
        .reduceRegion(

            reducer=
                ee.Reducer.first(),

            geometry=
                point,

            scale=
                10000,

            bestEffort=
                True,

            maxPixels=
                 10000000

        )

        .get(
            "WIND_SPEED"
        )

    )


    # ========================================================
    # 25 KM FIRE BUFFER
    # ========================================================

    fire_region = point.buffer(
        25000
    )


    # --------------------------------------------------------
    # FIRE COUNT
    # --------------------------------------------------------

    fire_count_raw = (

        HIGH_CONF_FIRE_COUNT_IMAGE

        .unmask(
            0
        )

        .reduceRegion(

            reducer=
                ee.Reducer.sum(),

            geometry=
                fire_region,

            scale=
                1000,

            bestEffort=
                True,

            maxPixels=
                 10000000

        )

        .get(
            "FIRE_COUNT"
        )

    )


    # --------------------------------------------------------
    # MAX FIRE CONFIDENCE
    # --------------------------------------------------------

    fire_confidence = (

        FIRE_CONFIDENCE_IMAGE

        .reduceRegion(

            reducer=
                ee.Reducer.max(),

            geometry=
                fire_region,

            scale=
                1000,

            bestEffort=
                True,

            maxPixels=
                 10000000

        )

        .get(
            "FIRE_CONFIDENCE"
        )

    )


    # --------------------------------------------------------
    # MAX FIRE T21
    # --------------------------------------------------------

    fire_t21 = (

        FIRE_T21_IMAGE

        .reduceRegion(

            reducer=
                ee.Reducer.max(),

            geometry=
                fire_region,

            scale=
                1000,

            bestEffort=
                True,

            maxPixels=
                 10000000

        )

        .get(
            "FIRE_T21"
        )

    )


    return feature.set(

        {

            "AOD":
                aod_value,

            "HCHO":
                hcho_value,

            "SAT_NO2":
                sat_no2_value,

            "ERA5_TEMP":
                temperature,

            "ERA5_DEWPOINT":
                dewpoint,

            "ERA5_RH":
                humidity,

            "WIND_U":
                wind_u,

            "WIND_V":
                wind_v,

            "WIND_SPEED":
                wind_speed,

            "FIRE_COUNT_25KM":
                fire_count_raw,

            "FIRE_CONF_MAX_25KM":
                fire_confidence,

            "FIRE_T21_MAX_25KM":
                fire_t21,

            "date_text":
                EVENT_DATE_TEXT

        }

    )


# ============================================================
# CREATE BATCH FEATURES
# ============================================================

def create_ee_features(rows):

    features = []


    for row in rows:

        latitude = float(
            row[
                "latitude"
            ]
        )


        longitude = float(
            row[
                "longitude"
            ]
        )


        feature = ee.Feature(

            ee.Geometry.Point(
                [
                    longitude,
                    latitude
                ]
            ),

            {

                "grid_id":
                    int(
                        row[
                            "grid_id"
                        ]
                    ),

                "latitude":
                    latitude,

                "longitude":
                    longitude,

                "date_text":
                    EVENT_DATE_TEXT

            }

        )


        features.append(
            feature
        )


    return features


# ============================================================
# DOWNLOAD ONE GEE BATCH
# ============================================================

def download_batch(
    rows,
    attempt_limit=3
):

    for attempt in range(
        1,
        attempt_limit + 1
    ):

        try:

            ee_features = (
                create_ee_features(
                    rows
                )
            )


            collection = (

                ee.FeatureCollection(
                    ee_features
                )

                .map(
                    enrich_feature
                )

            )


            info = (
                collection
                .getInfo()
            )


            output_rows = []


            for feature in info.get(
                "features",
                []
            ):

                properties = (
                    feature.get(
                        "properties",
                        {}
                    )
                )


                output_rows.append(
                    properties
                )


            return output_rows


        except Exception as exc:

            print()

            print(
                f"Batch attempt {attempt} failed:"
            )

            print(
                str(exc)
            )


            if attempt >= attempt_limit:

                raise


            print(
                "Retrying in 5 seconds..."
            )


            time.sleep(
                5
            )


# ============================================================
# EXTRACT REAL GEE FEATURES
# ============================================================

print()
print("=" * 72)
print("EXTRACTING REAL GEE GRID FEATURES")
print("=" * 72)


all_sampled_rows = []


total_batches = math.ceil(

    len(
        grid_rows
    )

    /

    BATCH_SIZE

)


for batch_number, start_index in enumerate(

    range(
        0,
        len(
            grid_rows
        ),
        BATCH_SIZE
    ),

    start=1

):

    end_index = min(

        start_index + BATCH_SIZE,

        len(
            grid_rows
        )

    )


    batch_rows = grid_rows[
        start_index:
        end_index
    ]


    print()
    print(

        f"Batch {batch_number}/{total_batches}"

        +

        f" | grid points "

        +

        f"{start_index + 1}-{end_index}"

    )


    sampled_rows = download_batch(
        batch_rows
    )


    all_sampled_rows.extend(
        sampled_rows
    )


    print(
        "Received:",
        len(
            sampled_rows
        ),
        "rows"
    )


# ============================================================
# DATAFRAME
# ============================================================

df = pd.DataFrame(
    all_sampled_rows
)


print()
print(
    "Total GEE rows:",
    len(
        df
    )
)


# ============================================================
# ENSURE ALL COLUMNS EXIST
# ============================================================

for column in DEFAULT_FEATURES:

    if column not in df.columns:

        df[
            column
        ] = np.nan


# ============================================================
# CONVERT NUMERIC FIELDS
# ============================================================

numeric_columns = [

    "grid_id",

    "latitude",

    "longitude",

    "AOD",

    "HCHO",

    "SAT_NO2",

    "ERA5_TEMP",

    "ERA5_DEWPOINT",

    "ERA5_RH",

    "WIND_U",

    "WIND_V",

    "WIND_SPEED",

    "FIRE_COUNT_25KM",

    "FIRE_CONF_MAX_25KM",

    "FIRE_T21_MAX_25KM",
]


for column in numeric_columns:

    if column in df.columns:

        df[
            column
        ] = pd.to_numeric(

            df[
                column
            ],

            errors="coerce"

        )


# ============================================================
# FIRE COUNT
# ============================================================
#
# If no high-confidence FIRMS observation exists in the
# 25-km region, count is genuinely zero.
# ============================================================

df[
    "FIRE_COUNT_25KM"
] = (

    df[
        "FIRE_COUNT_25KM"
    ]

    .fillna(
        0
    )

)


# ============================================================
# PRINT COVERAGE
# ============================================================

print()
print("=" * 72)
print("REAL FEATURE COVERAGE")
print("=" * 72)


coverage_columns = [

    "AOD",

    "HCHO",

    "SAT_NO2",

    "ERA5_TEMP",

    "ERA5_DEWPOINT",

    "ERA5_RH",

    "WIND_SPEED",

    "FIRE_COUNT_25KM",
]


for column in coverage_columns:

    valid_count = int(

        df[
            column
        ]
        .notna()
        .sum()

    )


    print(

        f"{column:24s}: "

        f"{valid_count}/{len(df)}"

    )


# ============================================================
# MODEL INPUT
# ============================================================

for feature in FEATURES:

    if feature not in df.columns:

        raise KeyError(

            f"Required model feature missing: {feature}"

        )


X = df[
    FEATURES
].copy()


for column in FEATURES:

    X[
        column
    ] = pd.to_numeric(

        X[
            column
        ],

        errors="coerce"

    )


# ============================================================
# PREDICT POLLUTANTS
# ============================================================

print()
print("=" * 72)
print("RUNNING V3 XGBOOST MODELS")
print("=" * 72)


for target, model in models.items():

    print(
        "Predicting:",
        target
    )


    prediction = model.predict(
        X
    )


    prediction = np.asarray(
        prediction,
        dtype=float
    )


    # Pollutant concentration cannot be negative.

    prediction = np.maximum(
        prediction,
        0
    )


    output_column = (
        "PRED_"
        +
        target
    )


    df[
        output_column
    ] = prediction


# ============================================================
# CPCB AQI SUB-INDEX
# ============================================================

def interpolate_subindex(
    concentration,
    breakpoints
):

    if pd.isna(
        concentration
    ):

        return np.nan


    concentration = max(

        float(
            concentration
        ),

        0.0

    )


    # CPCB concentration bands are defined as integer ranges.
    #
    # For a model-predicted decimal concentration, use the
    # nearest integer concentration before sub-index lookup.

    c = int(

        round(
            concentration
        )

    )


    for (
        concentration_low,
        concentration_high,
        index_low,
        index_high
    ) in breakpoints:


        if (
            c >= concentration_low
            and
            c <= concentration_high
        ):


            if (
                concentration_high
                ==
                concentration_low
            ):

                return float(
                    index_high
                )


            return float(

                (

                    (
                        index_high
                        -
                        index_low
                    )

                    /

                    (
                        concentration_high
                        -
                        concentration_low
                    )

                )

                *

                (
                    c
                    -
                    concentration_low
                )

                +

                index_low

            )


    # --------------------------------------------------------
    # ABOVE HIGHEST BAND
    # --------------------------------------------------------

    (
        concentration_low,
        concentration_high,
        index_low,
        index_high
    ) = breakpoints[-1]


    value = (

        (

            (
                index_high
                -
                index_low
            )

            /

            (
                concentration_high
                -
                concentration_low
            )

        )

        *

        (
            c
            -
            concentration_low
        )

        +

        index_low

    )


    return float(

        min(
            500.0,
            value
        )

    )


# ============================================================
# CPCB BREAKPOINTS
# ============================================================

PM25_BREAKPOINTS = [

    (0, 30, 0, 50),

    (31, 60, 51, 100),

    (61, 90, 101, 200),

    (91, 120, 201, 300),

    (121, 250, 301, 400),

    (251, 500, 401, 500),
]


PM10_BREAKPOINTS = [

    (0, 50, 0, 50),

    (51, 100, 51, 100),

    (101, 250, 101, 200),

    (251, 350, 201, 300),

    (351, 430, 301, 400),

    (431, 600, 401, 500),
]


NO2_BREAKPOINTS = [

    (0, 40, 0, 50),

    (41, 80, 51, 100),

    (81, 180, 101, 200),

    (181, 280, 201, 300),

    (281, 400, 301, 400),

    (401, 800, 401, 500),
]


O3_BREAKPOINTS = [

    (0, 50, 0, 50),

    (51, 100, 51, 100),

    (101, 168, 101, 200),

    (169, 208, 201, 300),

    (209, 748, 301, 400),

    (749, 1000, 401, 500),
]


# ============================================================
# AQI CATEGORY
# ============================================================

def aqi_category(
    aqi
):

    if pd.isna(
        aqi
    ):

        return "N/A"


    if aqi <= 50:

        return "Good"


    if aqi <= 100:

        return "Satisfactory"


    if aqi <= 200:

        return "Moderate"


    if aqi <= 300:

        return "Poor"


    if aqi <= 400:

        return "Very Poor"


    return "Severe"


# ============================================================
# COMPUTE AQI
# ============================================================

print()
print(
    "Calculating CPCB-style AQI..."
)


def calculate_aqi(
    row
):

    subindices = {

        "PM25":
            interpolate_subindex(

                row[
                    "PRED_PM25"
                ],

                PM25_BREAKPOINTS

            ),

        "PM10":
            interpolate_subindex(

                row[
                    "PRED_PM10"
                ],

                PM10_BREAKPOINTS

            ),

        "NO2":
            interpolate_subindex(

                row[
                    "PRED_NO2"
                ],

                NO2_BREAKPOINTS

            ),

        "O3_8H":
            interpolate_subindex(

                row[
                    "PRED_O3_8H"
                ],

                O3_BREAKPOINTS

            ),

    }


    valid_subindices = {

        pollutant:
            value

        for pollutant, value
        in subindices.items()

        if not pd.isna(
            value
        )

    }


    if not valid_subindices:

        return pd.Series(

            {

                "PM25_SUBINDEX":
                    np.nan,

                "PM10_SUBINDEX":
                    np.nan,

                "NO2_SUBINDEX":
                    np.nan,

                "O3_SUBINDEX":
                    np.nan,

                "AQI":
                    np.nan,

                "AQI_CATEGORY":
                    "N/A",

                "DOMINANT_POLLUTANT":
                    "N/A"

            }

        )


    dominant_pollutant = max(

        valid_subindices,

        key=
            valid_subindices.get

    )


    overall_aqi = max(

        valid_subindices.values()

    )


    return pd.Series(

        {

            "PM25_SUBINDEX":
                subindices[
                    "PM25"
                ],

            "PM10_SUBINDEX":
                subindices[
                    "PM10"
                ],

            "NO2_SUBINDEX":
                subindices[
                    "NO2"
                ],

            "O3_SUBINDEX":
                subindices[
                    "O3_8H"
                ],

            "AQI":
                overall_aqi,

            "AQI_CATEGORY":
                aqi_category(
                    overall_aqi
                ),

            "DOMINANT_POLLUTANT":
                dominant_pollutant

        }

    )


aqi_results = df.apply(

    calculate_aqi,

    axis=1

)


df = pd.concat(

    [
        df,
        aqi_results
    ],

    axis=1

)


# ============================================================
# METADATA
# ============================================================

df[
    "prediction_mode"
] = (
    "regional_real_gee_v3"
)


df[
    "event_date"
] = (
    EVENT_DATE_TEXT
)


df[
    "model_validation_region"
] = (
    "Delhi + Haryana + Punjab regional prototype"
)


# ============================================================
# SAVE CSV
# ============================================================

df = df.sort_values(
    "grid_id"
).reset_index(
    drop=True
)


df.to_csv(

    OUTPUT_CSV,

    index=False

)


print()
print(
    "Feature/prediction CSV saved:"
)

print(
    OUTPUT_CSV
)


# ============================================================
# JSON SAFE
# ============================================================

def json_safe(
    value
):

    if value is None:

        return None


    if isinstance(
        value,
        (
            np.integer,
            np.int64,
            np.int32
        )
    ):

        return int(
            value
        )


    if isinstance(
        value,
        (
            np.floating,
            np.float64,
            np.float32
        )
    ):

        if np.isnan(
            value
        ):

            return None


        return float(
            value
        )


    if pd.isna(
        value
    ):

        return None


    return value


# ============================================================
# CREATE GEOJSON GRID CELLS
# ============================================================

print()
print(
    "Creating AQI grid GeoJSON..."
)


features = []


for _, row in df.iterrows():

    latitude = float(
        row[
            "latitude"
        ]
    )


    longitude = float(
        row[
            "longitude"
        ]
    )


    # ========================================================
    # SQUARE CELL
    # ========================================================

    west = (
        longitude
        -
        half_step
    )


    east = (
        longitude
        +
        half_step
    )


    south = (
        latitude
        -
        half_step
    )


    north = (
        latitude
        +
        half_step
    )


    coordinates = [

        [
            [west, south],

            [east, south],

            [east, north],

            [west, north],

            [west, south]
        ]

    ]


    # ========================================================
    # PROPERTIES
    # ========================================================

    properties = {}


    for column in df.columns:

        properties[
            column
        ] = json_safe(
            row[
                column
            ]
        )


    feature = {

        "type":
            "Feature",

        "geometry":
        {

            "type":
                "Polygon",

            "coordinates":
                coordinates

        },

        "properties":
            properties

    }


    features.append(
        feature
    )


# ============================================================
# FEATURE COLLECTION
# ============================================================

geojson = {

    "type":
        "FeatureCollection",

    "name":
        "AeroVision Regional AQI Surface 2026-06-08",

    "metadata":
    {

        "date":
            EVENT_DATE_TEXT,

        "grid_step_degrees":
            GRID_STEP,

        "region":
        {

            "min_lat":
                MIN_LAT,

            "max_lat":
                MAX_LAT,

            "min_lon":
                MIN_LON,

            "max_lon":
                MAX_LON

        },

        "data_source":
            "Google Earth Engine real satellite/weather/fire data",

        "model":
            "AeroVision V3 XGBoost",

        "scientific_note":
            (
                "Regional prototype model validated using "
                "CPCB stations in Delhi, Haryana and Punjab. "
                "The surface should not be interpreted as "
                "India-wide scientific validation."
            )

    },

    "features":
        features

}


# ============================================================
# SAVE GEOJSON
# ============================================================

with open(

    OUTPUT_GEOJSON,

    "w",

    encoding="utf-8"

) as file:

    json.dump(

        geojson,

        file,

        ensure_ascii=False,

        indent=2

    )


# ============================================================
# SUMMARY
# ============================================================

valid_aqi = df[
    "AQI"
].dropna()


summary = {

    "event_date":
        EVENT_DATE_TEXT,

    "grid_points":
        int(
            len(
                df
            )
        ),

    "valid_aqi_cells":
        int(
            valid_aqi.shape[
                0
            ]
        ),

    "missing_aqi_cells":
        int(

            len(
                df
            )

            -

            valid_aqi.shape[
                0
            ]

        ),

    "minimum_aqi":

        float(
            valid_aqi.min()
        )

        if len(
            valid_aqi
        )

        else None,

    "maximum_aqi":

        float(
            valid_aqi.max()
        )

        if len(
            valid_aqi
        )

        else None,

    "mean_aqi":

        float(
            valid_aqi.mean()
        )

        if len(
            valid_aqi
        )

        else None,

    "median_aqi":

        float(
            valid_aqi.median()
        )

        if len(
            valid_aqi
        )

        else None,

    "feature_coverage":
    {

        column:

            int(
                df[
                    column
                ]
                .notna()
                .sum()
            )

        for column in coverage_columns

    }

}


with open(

    OUTPUT_SUMMARY,

    "w",

    encoding="utf-8"

) as file:

    json.dump(

        summary,

        file,

        indent=2

    )


# ============================================================
# FINAL RESULTS
# ============================================================

print()
print("=" * 72)
print("AEROVISION AQI SURFACE COMPLETE")
print("=" * 72)


print()
print(
    "Grid cells       :",
    len(
        df
    )
)


print(
    "Valid AQI cells  :",
    len(
        valid_aqi
    )
)


print(
    "Missing AQI cells:",
    (
        len(
            df
        )

        -

        len(
            valid_aqi
        )
    )
)


if len(
    valid_aqi
):

    print()
    print(
        "Minimum AQI:",
        round(
            valid_aqi.min(),
            1
        )
    )


    print(
        "Mean AQI   :",
        round(
            valid_aqi.mean(),
            1
        )
    )


    print(
        "Median AQI :",
        round(
            valid_aqi.median(),
            1
        )
    )


    print(
        "Maximum AQI:",
        round(
            valid_aqi.max(),
            1
        )
    )


print()
print(
    "GeoJSON:"
)

print(
    OUTPUT_GEOJSON
)


print()
print(
    "CSV:"
)

print(
    OUTPUT_CSV
)


print()
print(
    "Summary:"
)

print(
    OUTPUT_SUMMARY
)


print()
print(
    "Next step: load the GeoJSON as a Leaflet AQI surface layer."
)

print()