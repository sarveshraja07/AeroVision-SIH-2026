import os
import json
import joblib
import pandas as pd

from xgboost import XGBRegressor

BASE = r"E:\AeroVision-Real"

INPUT = os.path.join(
    BASE,
    "data",
    "processed",
    "final_ml_dataset_v2.csv"
)

MODEL_DIR = os.path.join(
    BASE,
    "models",
    "production"
)

os.makedirs(MODEL_DIR, exist_ok=True)

df = pd.read_csv(INPUT)

FEATURES = [
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
    "FIRE_T21_MAX_25KM"
]

TARGETS = [
    "PM25",
    "PM10",
    "NO2",
    "O3"
]

print("=" * 65)
print("AEROVISION PRODUCTION MODEL TRAINING")
print("=" * 65)

print("Dataset rows:", len(df))
print("Stations:", df["station"].nunique())


for target in TARGETS:

    print("\n" + "=" * 60)
    print("TRAINING FINAL:", target)
    print("=" * 60)

    data = df[
        df[target].notna()
    ].copy()

    X = data[FEATURES]
    y = data[target]

    print("Training observations:", len(data))

    model = XGBRegressor(
        n_estimators=500,
        learning_rate=0.025,
        max_depth=3,
        min_child_weight=6,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.3,
        reg_lambda=2.0,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1
    )

    model.fit(X, y)

    path = os.path.join(
        MODEL_DIR,
        f"aerovision_{target}.joblib"
    )

    joblib.dump(model, path)

    print("Saved:", path)


config = {
    "version": "AeroVision-XGBoost-V2",
    "period": "2026-06-01 to 2026-06-30",

    "features": FEATURES,

    "targets": TARGETS,

    "validation": {
        "method": "temporal_holdout",
        "train": "2026-06-01 to 2026-06-23",
        "test": "2026-06-24 to 2026-06-30",

        "R2": {
            "PM25": 0.334,
            "PM10": 0.304,
            "NO2": 0.755,
            "O3": 0.686
        }
    },

    "sources": {
        "ground": "CPCB",
        "AOD": "MODIS MAIAC",
        "HCHO": "Sentinel-5P TROPOMI",
        "NO2": "Sentinel-5P TROPOMI",
        "weather": "ERA5-Land",
        "fire": "NASA FIRMS"
    }
}

with open(
    os.path.join(MODEL_DIR, "model_config.json"),
    "w"
) as f:

    json.dump(config, f, indent=2)


print("\n" + "=" * 65)
print("PRODUCTION MODELS READY")
print("=" * 65)

print("PM2.5")
print("PM10")
print("NO2")
print("O3")

print("\nSaved in:")
print(MODEL_DIR)

print("=" * 65)