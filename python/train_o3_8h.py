import os
import joblib
import numpy as np
import pandas as pd

from xgboost import XGBRegressor

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

BASE = r"E:\AeroVision-Real"

INPUT = os.path.join(
    BASE,
    "data",
    "processed",
    "final_ml_dataset_v3.csv"
)

MODEL_DIR = os.path.join(
    BASE,
    "models"
)

OUTPUT_DIR = os.path.join(
    BASE,
    "data",
    "processed"
)

df = pd.read_csv(INPUT)

df["date_text"] = pd.to_datetime(
    df["date_text"]
)

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

TRAIN_END = pd.Timestamp(
    "2026-06-24"
)

data = df[
    df[TARGET].notna()
].copy()

train = data[
    data["date_text"] < TRAIN_END
]

test = data[
    data["date_text"] >= TRAIN_END
]

X_train = train[FEATURES]
y_train = train[TARGET]

X_test = test[FEATURES]
y_test = test[TARGET]

print("=" * 65)
print("AEROVISION O3 8-HOUR MODEL")
print("=" * 65)

print(
    "Training rows:",
    len(train)
)

print(
    "Testing rows:",
    len(test)
)

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

model.fit(
    X_train,
    y_train
)

pred = model.predict(
    X_test
)

mae = mean_absolute_error(
    y_test,
    pred
)

rmse = np.sqrt(
    mean_squared_error(
        y_test,
        pred
    )
)

r2 = r2_score(
    y_test,
    pred
)

corr = np.corrcoef(
    y_test,
    pred
)[0, 1]

print(
    f"MAE         : {mae:.3f}"
)

print(
    f"RMSE        : {rmse:.3f}"
)

print(
    f"R²          : {r2:.3f}"
)

print(
    f"Correlation : {corr:.3f}"
)

model_path = os.path.join(
    MODEL_DIR,
    "xgboost_v3_O3_8H.joblib"
)

joblib.dump(
    model,
    model_path
)

print(
    "\nModel saved:",
    model_path
)

importance = pd.DataFrame({
    "feature": FEATURES,
    "importance": model.feature_importances_
}).sort_values(
    "importance",
    ascending=False
)

print("\nTOP FEATURES:")
print(
    importance
    .head(8)
    .to_string(index=False)
)

importance.to_csv(
    os.path.join(
        OUTPUT_DIR,
        "feature_importance_O3_8H.csv"
    ),
    index=False
)

print("=" * 65)