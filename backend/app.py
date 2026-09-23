from flask import (
    Flask,
    send_from_directory,
    request,
    jsonify
)

import os
import math
from datetime import datetime

import ee
import joblib
import numpy as np
import pandas as pd


# ============================================================
# AEROVISION INDIA
#
# BACKEND RESPONSIBILITIES
#
# 1. Serve new public AeroVision dashboard:
#       /
#
# 2. Serve the FROZEN AeroVision core map:
#       /map.html
#
# 3. Serve existing exported/processed real datasets
#
# 4. Extract real satellite / meteorological / FIRMS
#    features from Google Earth Engine
#
# 5. Run AeroVision V3 XGBoost models
#
# 6. Calculate CPCB-style AQI
#
# IMPORTANT:
# The core map frontend is NOT modified by this backend.
# ============================================================


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

ROOT = os.path.dirname(
    BASE_DIR
)

FRONTEND = os.path.join(
    ROOT,
    "frontend"
)

EXPORTS = os.path.join(
    ROOT,
    "data",
    "exports"
)

PROCESSED = os.path.join(
    ROOT,
    "data",
    "processed"
)

MODEL_DIR = os.path.join(
    ROOT,
    "models",
    "production"
)


app = Flask(__name__)


# ============================================================
# SETTINGS
# ============================================================

EE_PROJECT = "aqi-sih-506616"

DEFAULT_PREDICTION_DATE = "2026-06-08"


# Current scientifically supported ML prototype region.
#
# IMPORTANT:
# The basemap itself can remain worldwide.
# Prediction is intentionally restricted to this region.

MIN_LAT = 27.0
MAX_LAT = 33.0

MIN_LON = 73.0
MAX_LON = 79.0


# High-confidence FIRMS threshold

FIRE_CONFIDENCE_THRESHOLD = 80


# ============================================================
# MODEL PATHS
# ============================================================

MODEL_PATHS = {

    "PM25": os.path.join(
        MODEL_DIR,
        "aerovision_PM25.joblib"
    ),

    "PM10": os.path.join(
        MODEL_DIR,
        "aerovision_PM10.joblib"
    ),

    "NO2": os.path.join(
        MODEL_DIR,
        "aerovision_NO2.joblib"
    ),

    "O3_8H": os.path.join(
        MODEL_DIR,
        "aerovision_O3_8H.joblib"
    )

}


# ============================================================
# GOOGLE EARTH ENGINE
# ============================================================

earth_engine_ready = False
earth_engine_error = None


def initialize_earth_engine():

    global earth_engine_ready
    global earth_engine_error

    print()
    print(
        "Initializing Google Earth Engine..."
    )

    try:

        ee.Initialize(
            project=EE_PROJECT
        )

        earth_engine_ready = True
        earth_engine_error = None

        print(
            "OK: Earth Engine connected"
        )

        print(
            "Project:",
            EE_PROJECT
        )

    except Exception as error:

        earth_engine_ready = False
        earth_engine_error = str(
            error
        )

        print(
            "ERROR: Earth Engine initialization failed"
        )

        print(
            error
        )


initialize_earth_engine()


# ============================================================
# LOAD AEROVISION MODELS
# ============================================================

models = {}


def load_models():

    print()

    print(
        "Loading AeroVision XGBoost models..."
    )

    for name, path in MODEL_PATHS.items():

        if not os.path.exists(
            path
        ):

            print(
                f"WARNING: Missing model: {path}"
            )

            continue

        try:

            model = joblib.load(
                path
            )

            models[
                name
            ] = model

            print(
                f"OK: {name}"
            )

        except Exception as error:

            print(
                f"ERROR loading {name}: {error}"
            )


load_models()


# ============================================================
# MODEL FEATURE NAMES
# ============================================================

def get_model_feature_names(
    model
):

    # --------------------------------------------------------
    # sklearn estimators / pipelines
    # --------------------------------------------------------

    if hasattr(
        model,
        "feature_names_in_"
    ):

        return list(
            model.feature_names_in_
        )


    # --------------------------------------------------------
    # XGBoost
    # --------------------------------------------------------

    if hasattr(
        model,
        "get_booster"
    ):

        try:

            booster = (
                model.get_booster()
            )

            if booster.feature_names:

                return list(
                    booster.feature_names
                )

        except Exception:

            pass


    return None


# ============================================================
# PRINT MODEL FEATURES
# ============================================================

print()

for model_name, model in models.items():

    features = (
        get_model_feature_names(
            model
        )
    )

    print(
        f"{model_name} features:",
        features
    )


# ============================================================
# GENERAL UTILITIES
# ============================================================

def number_or_none(
    value
):

    if value is None:

        return None

    try:

        result = float(
            value
        )

        if not math.isfinite(
            result
        ):

            return None

        return result

    except Exception:

        return None


def rounded_or_none(
    value,
    digits=4
):

    value = number_or_none(
        value
    )

    if value is None:

        return None

    return round(
        value,
        digits
    )


# ============================================================
# DATE VALIDATION
# ============================================================

def validate_prediction_date(
    date_text
):

    try:

        date_value = datetime.strptime(
            date_text,
            "%Y-%m-%d"
        )

    except Exception:

        raise ValueError(
            "Date must use YYYY-MM-DD format."
        )


    # --------------------------------------------------------
    # AeroVision V3 was developed using June 2026 data.
    #
    # Do not silently extrapolate the internal demonstration
    # to unsupported dates.
    # --------------------------------------------------------

    minimum = datetime(
        2026,
        6,
        1
    )

    maximum = datetime(
        2026,
        6,
        30
    )


    if not (
        minimum
        <=
        date_value
        <=
        maximum
    ):

        raise ValueError(
            "Internal prototype currently supports "
            "1-30 June 2026."
        )


    return date_text


# ============================================================
# COVERAGE CHECK
# ============================================================

def inside_prototype_region(
    latitude,
    longitude
):

    return (

        MIN_LAT
        <=
        latitude
        <=
        MAX_LAT

        and

        MIN_LON
        <=
        longitude
        <=
        MAX_LON

    )


# ============================================================
# GOOGLE EARTH ENGINE FEATURE EXTRACTION
# ============================================================

def extract_real_features(
    latitude,
    longitude,
    date_text
):

    if not earth_engine_ready:

        raise RuntimeError(

            "Google Earth Engine is not connected. "

            +

            (
                earth_engine_error
                or
                ""
            )

        )


    # ========================================================
    # GEOMETRY
    # ========================================================

    point = ee.Geometry.Point(
        [
            longitude,
            latitude
        ]
    )


    # FIRMS context around clicked coordinate

    fire_region = point.buffer(
        25000
    )


    start = ee.Date(
        date_text
    )

    end = start.advance(
        1,
        "day"
    )


    # ========================================================
    # 1. MODIS MAIAC AOD
    # ========================================================

    aod_collection = (

        ee.ImageCollection(
            "MODIS/061/MCD19A2_GRANULES"
        )

        .filterDate(
            start,
            end
        )

        .filterBounds(
            point
        )

        .select(
            "Optical_Depth_055"
        )

    )


    # MODIS AOD scale factor = 0.001

    aod_image = (

        aod_collection
        .mean()

        .multiply(
            0.001
        )

        .rename(
            "AOD"
        )

    )


    # ========================================================
    # 2. SENTINEL-5P HCHO
    # ========================================================

    hcho_collection = (

        ee.ImageCollection(
            "COPERNICUS/S5P/OFFL/L3_HCHO"
        )

        .filterDate(
            start,
            end
        )

        .filterBounds(
            point
        )

        .select(
            "tropospheric_HCHO_column_number_density"
        )

    )


    hcho_image = (

        hcho_collection
        .mean()

        .rename(
            "HCHO"
        )

    )


    # ========================================================
    # 3. SENTINEL-5P NO2
    # ========================================================

    no2_collection = (

        ee.ImageCollection(
            "COPERNICUS/S5P/OFFL/L3_NO2"
        )

        .filterDate(
            start,
            end
        )

        .filterBounds(
            point
        )

        .select(
            "tropospheric_NO2_column_number_density"
        )

    )


    sat_no2_image = (

        no2_collection
        .mean()

        .rename(
            "SAT_NO2"
        )

    )


    # ========================================================
    # 4. ERA5-LAND
    # ========================================================

    era5_collection = (

        ee.ImageCollection(
            "ECMWF/ERA5_LAND/HOURLY"
        )

        .filterDate(
            start,
            end
        )

        .filterBounds(
            point
        )

    )


    era5_mean = (
        era5_collection.mean()
    )


    temperature_kelvin = (

        era5_mean
        .select(
            "temperature_2m"
        )

    )


    dewpoint_kelvin = (

        era5_mean
        .select(
            "dewpoint_temperature_2m"
        )

    )


    # Kelvin -> Celsius

    temperature_c = (

        temperature_kelvin
        .subtract(
            273.15
        )

        .rename(
            "ERA5_TEMP"
        )

    )


    dewpoint_c = (

        dewpoint_kelvin
        .subtract(
            273.15
        )

        .rename(
            "ERA5_DEWPOINT"
        )

    )


    # ========================================================
    # RELATIVE HUMIDITY
    #
    # Magnus approximation
    #
    # This is derived from REAL ERA5 temperature/dewpoint.
    # ========================================================

    dewpoint_exponent = (

        dewpoint_c
        .multiply(
            17.625
        )

        .divide(

            dewpoint_c
            .add(
                243.04
            )

        )

    )


    dewpoint_vapor = (
        dewpoint_exponent.exp()
    )


    temperature_exponent = (

        temperature_c
        .multiply(
            17.625
        )

        .divide(

            temperature_c
            .add(
                243.04
            )

        )

    )


    temperature_vapor = (
        temperature_exponent.exp()
    )


    rh_image = (

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


    # ========================================================
    # WIND
    # ========================================================

    wind_u = (

        era5_mean
        .select(
            "u_component_of_wind_10m"
        )

        .rename(
            "WIND_U"
        )

    )


    wind_v = (

        era5_mean
        .select(
            "v_component_of_wind_10m"
        )

        .rename(
            "WIND_V"
        )

    )


    wind_speed = (

        wind_u
        .pow(
            2
        )

        .add(

            wind_v
            .pow(
                2
            )

        )

        .sqrt()

        .rename(
            "WIND_SPEED"
        )

    )


    # ========================================================
    # POINT SAMPLING HELPER
    # ========================================================

    def point_value(
        image,
        band,
        scale
    ):

        return (

            image
            .reduceRegion(

                reducer=ee.Reducer.mean(),

                geometry=point,

                scale=scale,

                bestEffort=True,

                maxPixels=1_000_000

            )

            .get(
                band
            )

        )


    # ========================================================
    # AOD VALUE
    # ========================================================

    aod_value = ee.Algorithms.If(

        aod_collection
        .size()
        .gt(
            0
        ),

        point_value(
            aod_image,
            "AOD",
            1000
        ),

        None

    )


    # ========================================================
    # HCHO VALUE
    # ========================================================

    hcho_value = ee.Algorithms.If(

        hcho_collection
        .size()
        .gt(
            0
        ),

        point_value(
            hcho_image,
            "HCHO",
            7000
        ),

        None

    )


    # ========================================================
    # SATELLITE NO2 VALUE
    # ========================================================

    sat_no2_value = ee.Algorithms.If(

        no2_collection
        .size()
        .gt(
            0
        ),

        point_value(
            sat_no2_image,
            "SAT_NO2",
            7000
        ),

        None

    )


    # ========================================================
    # ERA5 TEMPERATURE
    # ========================================================

    temp_value = ee.Algorithms.If(

        era5_collection
        .size()
        .gt(
            0
        ),

        point_value(
            temperature_c,
            "ERA5_TEMP",
            11000
        ),

        None

    )


    # ========================================================
    # ERA5 DEWPOINT
    # ========================================================

    dewpoint_value = ee.Algorithms.If(

        era5_collection
        .size()
        .gt(
            0
        ),

        point_value(
            dewpoint_c,
            "ERA5_DEWPOINT",
            11000
        ),

        None

    )


    # ========================================================
    # ERA5 RH
    # ========================================================

    rh_value = ee.Algorithms.If(

        era5_collection
        .size()
        .gt(
            0
        ),

        point_value(
            rh_image,
            "ERA5_RH",
            11000
        ),

        None

    )


    # ========================================================
    # WIND U
    # ========================================================

    wind_u_value = ee.Algorithms.If(

        era5_collection
        .size()
        .gt(
            0
        ),

        point_value(
            wind_u,
            "WIND_U",
            11000
        ),

        None

    )


    # ========================================================
    # WIND V
    # ========================================================

    wind_v_value = ee.Algorithms.If(

        era5_collection
        .size()
        .gt(
            0
        ),

        point_value(
            wind_v,
            "WIND_V",
            11000
        ),

        None

    )


    # ========================================================
    # WIND SPEED
    # ========================================================

    wind_speed_value = ee.Algorithms.If(

        era5_collection
        .size()
        .gt(
            0
        ),

        point_value(
            wind_speed,
            "WIND_SPEED",
            11000
        ),

        None

    )


    # ========================================================
    # 5. NASA FIRMS
    # ========================================================

    firms = (

        ee.ImageCollection(
            "FIRMS"
        )

        .filterDate(
            start,
            end
        )

        .filterBounds(
            fire_region
        )

    )


    # ========================================================
    # HIGH-CONFIDENCE FIRMS MASK
    # ========================================================

    def mask_high_confidence(
        image
    ):

        confidence = (
            image.select(
                "confidence"
            )
        )

        mask = confidence.gte(
            FIRE_CONFIDENCE_THRESHOLD
        )

        return image.updateMask(
            mask
        )


    high_conf_firms = firms.map(
        mask_high_confidence
    )


    # ========================================================
    # FIRE COUNT
    # ========================================================

    fire_count_image = (

        high_conf_firms
        .select(
            "confidence"
        )

        .count()

        .rename(
            "fire_count"
        )

    )


    fire_count_value = ee.Algorithms.If(

        high_conf_firms
        .size()
        .gt(
            0
        ),

        fire_count_image
        .reduceRegion(

            reducer=ee.Reducer.sum(),

            geometry=fire_region,

            scale=1000,

            bestEffort=True,

            maxPixels=10_000_000

        )

        .get(
            "fire_count"
        ),

        0

    )


    # ========================================================
    # MAX FIRE CONFIDENCE
    # ========================================================

    fire_confidence_max_image = (

        high_conf_firms
        .select(
            "confidence"
        )

        .max()

        .rename(
            "fire_conf_max"
        )

    )


    fire_confidence_max_value = ee.Algorithms.If(

        high_conf_firms
        .size()
        .gt(
            0
        ),

        fire_confidence_max_image
        .reduceRegion(

            reducer=ee.Reducer.max(),

            geometry=fire_region,

            scale=1000,

            bestEffort=True,

            maxPixels=10_000_000

        )

        .get(
            "fire_conf_max"
        ),

        0

    )


    # ========================================================
    # MAX FIRMS T21
    # ========================================================

    fire_t21_max_image = (

        high_conf_firms
        .select(
            "T21"
        )

        .max()

        .rename(
            "fire_t21_max"
        )

    )


    fire_t21_max_value = ee.Algorithms.If(

        high_conf_firms
        .size()
        .gt(
            0
        ),

        fire_t21_max_image
        .reduceRegion(

            reducer=ee.Reducer.max(),

            geometry=fire_region,

            scale=1000,

            bestEffort=True,

            maxPixels=10_000_000

        )

        .get(
            "fire_t21_max"
        ),

        0

    )


    # ========================================================
    # ONE EARTH ENGINE REQUEST
    # ========================================================

    ee_result = ee.Dictionary({

        "AOD":
            aod_value,

        "HCHO":
            hcho_value,

        "SAT_NO2":
            sat_no2_value,

        "ERA5_TEMP":
            temp_value,

        "ERA5_DEWPOINT":
            dewpoint_value,

        "ERA5_RH":
            rh_value,

        "WIND_U":
            wind_u_value,

        "WIND_V":
            wind_v_value,

        "WIND_SPEED":
            wind_speed_value,

        "FIRE_COUNT_25KM":
            fire_count_value,

        "FIRE_CONF_MAX_25KM":
            fire_confidence_max_value,

        "FIRE_T21_MAX_25KM":
            fire_t21_max_value,

        "AOD_IMAGE_COUNT":
            aod_collection.size(),

        "HCHO_IMAGE_COUNT":
            hcho_collection.size(),

        "NO2_IMAGE_COUNT":
            no2_collection.size(),

        "ERA5_IMAGE_COUNT":
            era5_collection.size()

    }).getInfo()


    # ========================================================
    # NORMALIZE FEATURE RESPONSE
    # ========================================================

    features = {

        "AOD":
            number_or_none(
                ee_result.get(
                    "AOD"
                )
            ),

        "HCHO":
            number_or_none(
                ee_result.get(
                    "HCHO"
                )
            ),

        "SAT_NO2":
            number_or_none(
                ee_result.get(
                    "SAT_NO2"
                )
            ),

        "ERA5_TEMP":
            number_or_none(
                ee_result.get(
                    "ERA5_TEMP"
                )
            ),

        "ERA5_DEWPOINT":
            number_or_none(
                ee_result.get(
                    "ERA5_DEWPOINT"
                )
            ),

        "ERA5_RH":
            number_or_none(
                ee_result.get(
                    "ERA5_RH"
                )
            ),

        "WIND_SPEED":
            number_or_none(
                ee_result.get(
                    "WIND_SPEED"
                )
            ),

        "WIND_U":
            number_or_none(
                ee_result.get(
                    "WIND_U"
                )
            ),

        "WIND_V":
            number_or_none(
                ee_result.get(
                    "WIND_V"
                )
            ),

        "FIRE_COUNT_25KM":
            number_or_none(
                ee_result.get(
                    "FIRE_COUNT_25KM"
                )
            )
            or
            0.0,

        "FIRE_CONF_MAX_25KM":
            number_or_none(
                ee_result.get(
                    "FIRE_CONF_MAX_25KM"
                )
            )
            or
            0.0,

        "FIRE_T21_MAX_25KM":
            number_or_none(
                ee_result.get(
                    "FIRE_T21_MAX_25KM"
                )
            )
            or
            0.0,

        "latitude":
            float(
                latitude
            ),

        "longitude":
            float(
                longitude
            )

    }


    # ========================================================
    # LEGACY ALIASES
    #
    # These still represent the SAME real FIRMS measurements.
    # No simulated values are introduced.
    # ========================================================

    features[
        "FIRE_CONFIDENCE"
    ] = features[
        "FIRE_CONF_MAX_25KM"
    ]


    features[
        "FIRE_T21"
    ] = features[
        "FIRE_T21_MAX_25KM"
    ]


    metadata = {

        "date":
            date_text,

        "aod_images":
            ee_result.get(
                "AOD_IMAGE_COUNT",
                0
            ),

        "hcho_images":
            ee_result.get(
                "HCHO_IMAGE_COUNT",
                0
            ),

        "no2_images":
            ee_result.get(
                "NO2_IMAGE_COUNT",
                0
            ),

        "era5_images":
            ee_result.get(
                "ERA5_IMAGE_COUNT",
                0
            )

    }


    return (
        features,
        metadata
    )


# ============================================================
# BUILD MODEL INPUT
# ============================================================

def build_model_input(
    model,
    real_features
):

    feature_names = (
        get_model_feature_names(
            model
        )
    )


    if not feature_names:

        raise RuntimeError(
            "Unable to determine model feature names."
        )


    unsupported = []

    row = {}


    for feature in feature_names:

        if feature not in real_features:

            unsupported.append(
                feature
            )

            continue


        value = real_features[
            feature
        ]


        if value is None:

            row[
                feature
            ] = np.nan

        else:

            row[
                feature
            ] = value


    if unsupported:

        raise RuntimeError(

            "The model requires features that cannot "
            "currently be obtained for an arbitrary "
            "map coordinate: "

            +

            ", ".join(
                unsupported
            )

        )


    return pd.DataFrame(

        [
            row
        ],

        columns=feature_names

    )


# ============================================================
# CPCB AQI BREAKPOINTS
# ============================================================

PM25_BREAKPOINTS = [

    (0, 30, 0, 50),

    (30, 60, 50, 100),

    (60, 90, 100, 200),

    (90, 120, 200, 300),

    (120, 250, 300, 400),

    (250, 500, 400, 500)

]


PM10_BREAKPOINTS = [

    (0, 50, 0, 50),

    (50, 100, 50, 100),

    (100, 250, 100, 200),

    (250, 350, 200, 300),

    (350, 430, 300, 400),

    (430, 600, 400, 500)

]


NO2_BREAKPOINTS = [

    (0, 40, 0, 50),

    (40, 80, 50, 100),

    (80, 180, 100, 200),

    (180, 280, 200, 300),

    (280, 400, 300, 400),

    (400, 800, 400, 500)

]


O3_BREAKPOINTS = [

    (0, 50, 0, 50),

    (50, 100, 50, 100),

    (100, 168, 100, 200),

    (168, 208, 200, 300),

    (208, 748, 300, 400),

    (748, 1000, 400, 500)

]


# ============================================================
# AQI SUBINDEX
# ============================================================

def pollutant_subindex(
    concentration,
    breakpoints
):

    concentration = number_or_none(
        concentration
    )


    if concentration is None:

        return None


    concentration = max(
        0,
        concentration
    )


    for (
        concentration_low,
        concentration_high,
        index_low,
        index_high
    ) in breakpoints:

        if (

            concentration_low
            <=
            concentration
            <=
            concentration_high

        ):

            result = (

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

                *

                (
                    concentration
                    -
                    concentration_low
                )

                +

                index_low

            )


            return result


    return 500.0


# ============================================================
# AQI CATEGORY
# ============================================================

def aqi_category(
    value
):

    if value <= 50:

        return "Good"

    elif value <= 100:

        return "Satisfactory"

    elif value <= 200:

        return "Moderate"

    elif value <= 300:

        return "Poor"

    elif value <= 400:

        return "Very Poor"

    return "Severe"


# ============================================================
# CALCULATE AQI
# ============================================================

def calculate_aqi(
    pm25,
    pm10,
    no2,
    o3
):

    subindices = {

        "PM2.5":
            pollutant_subindex(
                pm25,
                PM25_BREAKPOINTS
            ),

        "PM10":
            pollutant_subindex(
                pm10,
                PM10_BREAKPOINTS
            ),

        "NO2":
            pollutant_subindex(
                no2,
                NO2_BREAKPOINTS
            ),

        "O3":
            pollutant_subindex(
                o3,
                O3_BREAKPOINTS
            )

    }


    valid = {

        key:
            value

        for key, value
        in subindices.items()

        if value is not None

    }


    if not valid:

        return (
            None,
            "Unknown",
            "Unknown",
            {}
        )


    dominant = max(
        valid,
        key=valid.get
    )


    aqi_value = valid[
        dominant
    ]


    return (

        int(
            round(
                aqi_value
            )
        ),

        aqi_category(
            aqi_value
        ),

        dominant,

        {

            key:
                round(
                    value,
                    1
                )

            for key, value
            in valid.items()

        }

    )


# ============================================================
# FRONTEND ROUTES
#
# IMPORTANT ARCHITECTURE:
#
# /
#     New AQI.in-inspired AeroVision entrance.
#
# /map.html
#     Existing frozen AeroVision core map.
#
# dashboard.js / style.css used by map.html remain untouched.
# ============================================================


@app.route("/")
def index():

    return send_from_directory(
        FRONTEND,
        "index.html"
    )


@app.route("/map.html")
def aerovision_core_map():

    map_file = os.path.join(
        FRONTEND,
        "map.html"
    )


    if not os.path.exists(
        map_file
    ):

        return (

            "AeroVision core map file is missing. "
            "Expected frontend/map.html",

            404

        )


    return send_from_directory(
        FRONTEND,
        "map.html"
    )


# ============================================================
# REAL EXPORTED DATA
# ============================================================

@app.route(
    "/data/exports/<path:filename>"
)
def exports(
    filename
):

    return send_from_directory(
        EXPORTS,
        filename
    )


# ============================================================
# REAL PROCESSED DATA
# ============================================================

@app.route(
    "/data/processed/<path:filename>"
)
def processed(
    filename
):

    return send_from_directory(
        PROCESSED,
        filename
    )


# ============================================================
# API STATUS
# ============================================================

@app.route(
    "/api/status"
)
def api_status():

    model_features = {}


    for name, model in models.items():

        model_features[
            name
        ] = (

            get_model_feature_names(
                model
            )

        )


    return jsonify({

        "status":
            "ok",

        "application":
            "AeroVision India",

        "landing_dashboard":
            "/",

        "core_map":
            "/map.html",

        "earth_engine_ready":
            earth_engine_ready,

        "earth_engine_project":
            EE_PROJECT,

        "default_prediction_date":
            DEFAULT_PREDICTION_DATE,

        "models_loaded":
            list(
                models.keys()
            ),

        "model_features":
            model_features,

        "coverage":
            "Delhi + Haryana + Punjab prototype",

        "data_policy":
            "Real observations and real environmental inputs only"

    })


# ============================================================
# REAL FEATURE TEST API
# ============================================================

@app.route(
    "/api/features",
    methods=[
        "POST"
    ]
)
def feature_test():

    try:

        payload = (

            request.get_json(
                silent=True
            )

            or

            {}

        )


        latitude = float(
            payload.get(
                "latitude"
            )
        )


        longitude = float(
            payload.get(
                "longitude"
            )
        )


        date_text = payload.get(
            "date",
            DEFAULT_PREDICTION_DATE
        )


        date_text = (
            validate_prediction_date(
                date_text
            )
        )


        # ----------------------------------------------------
        # Keep feature extraction scientifically consistent
        # with prediction coverage.
        # ----------------------------------------------------

        if not inside_prototype_region(
            latitude,
            longitude
        ):

            return jsonify({

                "success":
                    False,

                "error":
                    (
                        "Location is outside the current "
                        "scientifically supported internal "
                        "prototype region."
                    ),

                "coverage":
                    "Delhi + Haryana + Punjab"

            }), 400


        features, metadata = (

            extract_real_features(

                latitude,

                longitude,

                date_text

            )

        )


        return jsonify({

            "success":
                True,

            "latitude":
                latitude,

            "longitude":
                longitude,

            "date":
                date_text,

            "features":
                features,

            "metadata":
                metadata

        })


    except (
        TypeError,
        ValueError
    ) as error:

        return jsonify({

            "success":
                False,

            "error":
                str(
                    error
                )

        }), 400


    except Exception as error:

        print(
            "Feature extraction error:",
            error
        )


        return jsonify({

            "success":
                False,

            "error":
                str(
                    error
                )

        }), 500


# ============================================================
# PREDICTION API
# ============================================================

@app.route(
    "/api/predict",
    methods=[
        "POST"
    ]
)
def predict():

    # ========================================================
    # VALIDATE REQUEST
    # ========================================================

    try:

        payload = (

            request.get_json(
                silent=True
            )

            or

            {}

        )


        if payload.get(
            "latitude"
        ) is None:

            raise ValueError(
                "latitude is required."
            )


        if payload.get(
            "longitude"
        ) is None:

            raise ValueError(
                "longitude is required."
            )


        latitude = float(
            payload.get(
                "latitude"
            )
        )


        longitude = float(
            payload.get(
                "longitude"
            )
        )


        if not math.isfinite(
            latitude
        ):

            raise ValueError(
                "latitude must be a valid number."
            )


        if not math.isfinite(
            longitude
        ):

            raise ValueError(
                "longitude must be a valid number."
            )


        if not (
            -90
            <=
            latitude
            <=
            90
        ):

            raise ValueError(
                "latitude must be between -90 and 90."
            )


        if not (
            -180
            <=
            longitude
            <=
            180
        ):

            raise ValueError(
                "longitude must be between -180 and 180."
            )


        date_text = payload.get(
            "date",
            DEFAULT_PREDICTION_DATE
        )


        date_text = (
            validate_prediction_date(
                date_text
            )
        )


    except (
        TypeError,
        ValueError
    ) as error:

        return jsonify({

            "success":
                False,

            "error":
                str(
                    error
                )

        }), 400


    except Exception as error:

        return jsonify({

            "success":
                False,

            "error":
                str(
                    error
                )

        }), 400


    # ========================================================
    # COVERAGE GUARD
    # ========================================================

    if not inside_prototype_region(
        latitude,
        longitude
    ):

        return jsonify({

            "success":
                False,

            "error":
                (
                    "Location is outside the current "
                    "scientifically supported internal "
                    "prototype region."
                ),

            "coverage":
                "Delhi + Haryana + Punjab"

        }), 400


    # ========================================================
    # CHECK REQUIRED MODELS
    # ========================================================

    required_models = [

        "PM25",

        "PM10",

        "NO2",

        "O3_8H"

    ]


    missing_models = [

        name

        for name in required_models

        if name not in models

    ]


    if missing_models:

        return jsonify({

            "success":
                False,

            "error":
                "Required model files are missing.",

            "missing_models":
                missing_models

        }), 500


    try:

        # ====================================================
        # EXACT-COORDINATE REAL GEE FEATURES
        # ====================================================

        real_features, metadata = (

            extract_real_features(

                latitude,

                longitude,

                date_text

            )

        )


        # ====================================================
        # RUN V3 MODELS
        # ====================================================

        predictions = {}


        for target in required_models:

            model = models[
                target
            ]


            X = build_model_input(

                model,

                real_features

            )


            result = model.predict(
                X
            )[0]


            result = max(

                0,

                float(
                    result
                )

            )


            predictions[
                target
            ] = result


        # ====================================================
        # CALCULATE CPCB-STYLE AQI
        # ====================================================

        (
            aqi,
            category,
            dominant,
            subindices
        ) = calculate_aqi(

            predictions[
                "PM25"
            ],

            predictions[
                "PM10"
            ],

            predictions[
                "NO2"
            ],

            predictions[
                "O3_8H"
            ]

        )


        # ====================================================
        # CLEAN ENVIRONMENTAL RESPONSE
        # ====================================================

        feature_response = {

            key:
                rounded_or_none(
                    value,
                    6
                )

            for key, value
            in real_features.items()

        }


        # ====================================================
        # RESPONSE
        # ====================================================

        return jsonify({

            "success":
                True,

            "mode":
                "exact_coordinate_real_gee_features",

            "latitude":
                round(
                    latitude,
                    6
                ),

            "longitude":
                round(
                    longitude,
                    6
                ),

            "date":
                date_text,

            "prediction": {

                "PM25":
                    round(
                        predictions[
                            "PM25"
                        ],
                        1
                    ),

                "PM10":
                    round(
                        predictions[
                            "PM10"
                        ],
                        1
                    ),

                "NO2":
                    round(
                        predictions[
                            "NO2"
                        ],
                        1
                    ),

                "O3_8H":
                    round(
                        predictions[
                            "O3_8H"
                        ],
                        1
                    ),

                "AQI":
                    aqi,

                "category":
                    category,

                "dominant_pollutant":
                    dominant,

                "subindices":
                    subindices

            },

            "environmental_features":
                feature_response,

            "earth_engine_metadata":
                metadata,

            # ------------------------------------------------
            # Keep this structure because the existing
            # dashboard.js expects these fields.
            # ------------------------------------------------

            "real_feature_source": {

                "station":
                    "Exact clicked coordinate",

                "date":
                    date_text,

                "distance_km":
                    0

            },

            "scientific_note":
                (
                    "Satellite, meteorological and FIRMS "
                    "features were queried from Google Earth "
                    "Engine for the clicked coordinate and "
                    "selected date. The ML model remains "
                    "validated only for the current regional "
                    "prototype coverage."
                )

        })


    except Exception as error:

        print()
        print(
            "Prediction error:"
        )

        print(
            error
        )


        return jsonify({

            "success":
                False,

            "error":
                str(
                    error
                )

        }), 500


# ============================================================
# FRONTEND STATIC FILES
#
# KEEP THIS ROUTE LAST.
#
# Examples:
#
# /landing.css
# /landing.js
# /style.css
# /dashboard.js
#
# map.html can therefore continue using its existing
# relative/static frontend references.
# ============================================================

@app.route(
    "/<path:filename>"
)
def frontend(
    filename
):

    return send_from_directory(
        FRONTEND,
        filename
    )


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)

    print(
        "AEROVISION INDIA"
    )

    print(
        "REAL DATA AIR QUALITY INTELLIGENCE"
    )

    print("=" * 70)

    print()

    print(
        "Entrance Dashboard:"
    )

    print(
        "http://127.0.0.1:5000/"
    )

    print()

    print(
        "Frozen Core AQI Map:"
    )

    print(
        "http://127.0.0.1:5000/map.html"
    )

    print()

    print(
        "Backend Status:"
    )

    print(
        "http://127.0.0.1:5000/api/status"
    )

    print()

    print(
        "Default prediction date:",
        DEFAULT_PREDICTION_DATE
    )

    print()

    print(
        "ML coverage:",
        "Delhi + Haryana + Punjab"
    )

    print()

    print(
        "Models loaded:",
        ", ".join(
            models.keys()
        )
        if models
        else
        "NONE"
    )

    print()

    print(
        "Earth Engine:",
        (
            "READY"
            if earth_engine_ready
            else
            "NOT READY"
        )
    )

    print("=" * 70)
    print()


    app.run(

        host="127.0.0.1",

        port=5000,

        debug=True

    )