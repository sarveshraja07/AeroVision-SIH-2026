import os
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
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
    "final_ml_dataset.csv"
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

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 70)
print("AEROVISION INDIA - REAL XGBOOST TRAINING")
print("=" * 70)

df = pd.read_csv(INPUT)

df["date_text"] = pd.to_datetime(
    df["date_text"],
    errors="coerce"
)

print("Rows:", len(df))
print("Stations:", df["station"].nunique())
print("Dates:", df["date_text"].nunique())


# ============================================================
# REAL INPUT FEATURES
# ============================================================

FEATURES = [
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


# ============================================================
# ADD REAL SPATIO-TEMPORAL FEATURES
#
# Latitude/longitude were not preserved in the first GEE export,
# so we do not use them in this first model.
#
# Month/day information is real and available from date.
# ============================================================

df["day_of_month"] = df["date_text"].dt.day
df["day_of_year"] = df["date_text"].dt.dayofyear

FEATURES += [
    "day_of_month",
    "day_of_year"
]


# ============================================================
# TARGETS
# ============================================================

TARGETS = {
    "PM25": "PM2.5",
    "PM10": "PM10",
    "NO2": "NO2",
    "O3": "Ozone"
}


# ============================================================
# TIME-AWARE SPLIT
#
# Train: 01-Jun through 23-Jun
# Test : 24-Jun through 30-Jun
#
# This avoids randomly mixing the same dates across train/test.
# ============================================================

TRAIN_END = pd.Timestamp("2026-06-24")

train_mask = df["date_text"] < TRAIN_END
test_mask = df["date_text"] >= TRAIN_END

print("\nTRAIN PERIOD:")
print(
    df.loc[train_mask, "date_text"].min(),
    "to",
    df.loc[train_mask, "date_text"].max()
)

print("\nTEST PERIOD:")
print(
    df.loc[test_mask, "date_text"].min(),
    "to",
    df.loc[test_mask, "date_text"].max()
)


# ============================================================
# RESULTS STORAGE
# ============================================================

metrics = []
all_predictions = []


# ============================================================
# TRAIN EACH POLLUTANT
# ============================================================

for target_col, display_name in TARGETS.items():

    print("\n" + "=" * 70)
    print("TRAINING:", display_name)
    print("=" * 70)

    if target_col not in df.columns:
        print("Skipping - target missing.")
        continue

    target_df = df[
        df[target_col].notna()
    ].copy()

    train_df = target_df[
        target_df["date_text"] < TRAIN_END
    ].copy()

    test_df = target_df[
        target_df["date_text"] >= TRAIN_END
    ].copy()

    print(
        "Training rows:",
        len(train_df)
    )

    print(
        "Testing rows:",
        len(test_df)
    )

    if len(train_df) < 50 or len(test_df) < 20:
        print(
            "Not enough observations - skipping."
        )
        continue

    X_train = train_df[FEATURES]
    y_train = train_df[target_col]

    X_test = test_df[FEATURES]
    y_test = test_df[target_col]


    # ========================================================
    # MODEL
    #
    # Conservative configuration to reduce overfitting
    # on this prototype-sized dataset.
    # ========================================================

    model = XGBRegressor(
        n_estimators=350,
        learning_rate=0.03,
        max_depth=4,
        min_child_weight=5,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.5,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1
    )

    model.fit(
        X_train,
        y_train
    )

    predictions = model.predict(
        X_test
    )


    # ========================================================
    # METRICS
    # ========================================================

    mae = mean_absolute_error(
        y_test,
        predictions
    )

    rmse = np.sqrt(
        mean_squared_error(
            y_test,
            predictions
        )
    )

    r2 = r2_score(
        y_test,
        predictions
    )

    correlation = np.corrcoef(
        y_test,
        predictions
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
        f"Correlation : {correlation:.3f}"
    )


    # ========================================================
    # SAVE MODEL
    # ========================================================

    model_path = os.path.join(
        MODEL_DIR,
        f"xgboost_{target_col}.joblib"
    )

    joblib.dump(
        model,
        model_path
    )

    print(
        "Model saved:",
        model_path
    )


    # ========================================================
    # FEATURE IMPORTANCE
    # ========================================================

    importance = pd.DataFrame({
        "feature": FEATURES,
        "importance": model.feature_importances_
    }).sort_values(
        "importance",
        ascending=False
    )

    importance_path = os.path.join(
        OUTPUT_DIR,
        f"feature_importance_{target_col}.csv"
    )

    importance.to_csv(
        importance_path,
        index=False
    )

    print("\nTop features:")
    print(
        importance.head(8).to_string(
            index=False
        )
    )


    # ========================================================
    # PREDICTION TABLE
    # ========================================================

    prediction_df = test_df[
        [
            "station_day_id",
            "date_text",
            "station",
            "city",
            "state"
        ]
    ].copy()

    prediction_df["pollutant"] = target_col
    prediction_df["actual"] = y_test.values
    prediction_df["predicted"] = predictions
    prediction_df["absolute_error"] = np.abs(
        y_test.values - predictions
    )

    all_predictions.append(
        prediction_df
    )


    # ========================================================
    # ACTUAL VS PREDICTED GRAPH
    # ========================================================

    plt.figure(
        figsize=(7, 6)
    )

    plt.scatter(
        y_test,
        predictions,
        alpha=0.65
    )

    min_val = min(
        y_test.min(),
        predictions.min()
    )

    max_val = max(
        y_test.max(),
        predictions.max()
    )

    plt.plot(
        [min_val, max_val],
        [min_val, max_val],
        "--"
    )

    plt.xlabel(
        f"Actual {display_name}"
    )

    plt.ylabel(
        f"Predicted {display_name}"
    )

    plt.title(
        f"AeroVision {display_name}\n"
        f"R²={r2:.2f}, RMSE={rmse:.2f}, MAE={mae:.2f}"
    )

    plt.tight_layout()

    graph_path = os.path.join(
        OUTPUT_DIR,
        f"actual_vs_predicted_{target_col}.png"
    )

    plt.savefig(
        graph_path,
        dpi=200
    )

    plt.close()


    # ========================================================
    # STORE METRICS
    # ========================================================

    metrics.append({
        "pollutant": target_col,
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
        "correlation": correlation
    })


# ============================================================
# SAVE METRICS
# ============================================================

metrics_df = pd.DataFrame(
    metrics
)

metrics_path = os.path.join(
    OUTPUT_DIR,
    "model_metrics.csv"
)

metrics_df.to_csv(
    metrics_path,
    index=False
)


# ============================================================
# SAVE ALL TEST PREDICTIONS
# ============================================================

if all_predictions:

    predictions_df = pd.concat(
        all_predictions,
        ignore_index=True
    )

    predictions_path = os.path.join(
        OUTPUT_DIR,
        "actual_vs_predicted_all.csv"
    )

    predictions_df.to_csv(
        predictions_path,
        index=False
    )


# ============================================================
# SAVE MODEL CONFIG
# ============================================================

config = {
    "features": FEATURES,
    "train_period": "2026-06-01 to 2026-06-23",
    "test_period": "2026-06-24 to 2026-06-30",
    "data_type": "real CPCB + satellite + ERA5 + FIRMS",
    "missing_satellite_handling": "XGBoost native NaN handling"
}

with open(
    os.path.join(
        MODEL_DIR,
        "model_config.json"
    ),
    "w"
) as f:

    json.dump(
        config,
        f,
        indent=2
    )


# ============================================================
# FINAL REPORT
# ============================================================

print("\n")
print("=" * 70)
print("AEROVISION MODEL TRAINING COMPLETE")
print("=" * 70)

if len(metrics_df) > 0:

    print(
        metrics_df.round(3).to_string(
            index=False
        )
    )

print("\nSaved metrics:")
print(metrics_path)

print("\nModels:")
print(MODEL_DIR)

print("=" * 70)