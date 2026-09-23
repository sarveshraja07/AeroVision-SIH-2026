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
    "final_ml_dataset_v3.csv"
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

TARGET = "O3_8H"

print("=" * 65)
print("AEROVISION FINAL O3 8-HOUR PRODUCTION MODEL")
print("=" * 65)

data = df[
    df[TARGET].notna()
].copy()

print("Dataset rows:", len(df))
print("Valid O3 8H observations:", len(data))
print("Stations:", data["station"].nunique())

X = data[FEATURES]
y = data[TARGET]

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

# ------------------------------------------------------------
# Replace OLD daily-mean O3 production model
# ------------------------------------------------------------

OLD_MODEL = os.path.join(
    MODEL_DIR,
    "aerovision_O3.joblib"
)

BACKUP_MODEL = os.path.join(
    MODEL_DIR,
    "aerovision_O3_dailymean_OLD.joblib"
)

if os.path.exists(OLD_MODEL):

    if not os.path.exists(BACKUP_MODEL):
        os.replace(
            OLD_MODEL,
            BACKUP_MODEL
        )

        print("\nOld O3 model backed up:")
        print(BACKUP_MODEL)

    else:
        print("\nOld O3 backup already exists.")

# ------------------------------------------------------------
# Save corrected production model
# ------------------------------------------------------------

NEW_MODEL = os.path.join(
    MODEL_DIR,
    "aerovision_O3_8H.joblib"
)

joblib.dump(
    model,
    NEW_MODEL
)

print("\nCorrected O3 production model saved:")
print(NEW_MODEL)


# ------------------------------------------------------------
# Feature importance
# ------------------------------------------------------------

importance = pd.DataFrame({
    "feature": FEATURES,
    "importance": model.feature_importances_
}).sort_values(
    "importance",
    ascending=False
)

print("\nTop features:")
print(
    importance.head(10).to_string(
        index=False
    )
)

importance.to_csv(
    os.path.join(
        BASE,
        "data",
        "processed",
        "feature_importance_production_O3_8H.csv"
    ),
    index=False
)


# ------------------------------------------------------------
# Update model configuration
# ------------------------------------------------------------

CONFIG = os.path.join(
    MODEL_DIR,
    "model_config.json"
)

if os.path.exists(CONFIG):

    with open(CONFIG, "r") as f:
        config = json.load(f)

else:
    config = {}

config["version"] = "AeroVision-XGBoost-V3"

config["o3_target"] = {
    "name": "O3_8H",
    "description": "Daily maximum rolling 8-hour O3 concentration",
    "unit": "ug/m3",
    "valid_training_observations": len(data),
    "validation": {
        "train_period": "2026-06-01 to 2026-06-23",
        "test_period": "2026-06-24 to 2026-06-30",
        "MAE": 11.570,
        "RMSE": 15.199,
        "R2": 0.565,
        "correlation": 0.772
    }
}

config["production_models"] = {
    "PM25": "aerovision_PM25.joblib",
    "PM10": "aerovision_PM10.joblib",
    "NO2": "aerovision_NO2.joblib",
    "O3": "aerovision_O3_8H.joblib"
}

with open(
    CONFIG,
    "w"
) as f:

    json.dump(
        config,
        f,
        indent=2
    )


print("\nModel configuration updated:")
print(CONFIG)


print("\n" + "=" * 65)
print("FINAL PRODUCTION MODEL SET")
print("=" * 65)

for filename in [
    "aerovision_PM25.joblib",
    "aerovision_PM10.joblib",
    "aerovision_NO2.joblib",
    "aerovision_O3_8H.joblib"
]:

    path = os.path.join(
        MODEL_DIR,
        filename
    )

    if os.path.exists(path):

        size_kb = (
            os.path.getsize(path)
            / 1024
        )

        print(
            f"OK  {filename:<30} "
            f"{size_kb:.1f} KB"
        )

    else:

        print(
            f"MISSING  {filename}"
        )


print("\nProduction targets:")
print("PM2.5 -> CPCB daily PM2.5")
print("PM10  -> CPCB daily PM10")
print("NO2   -> CPCB daily NO2")
print("O3    -> CPCB-derived O3 8-hour target")

print("=" * 65)