import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "data" / "processed" / "cpcb_vs_aerovision_aqi.csv"
OUTPUT_FILE = ROOT / "data" / "exports" / "cpcb_vs_aerovision_aqi_corrected.csv"
SUMMARY_FILE = ROOT / "data" / "exports" / "validation_reference_summary.csv"

df = pd.read_csv(INPUT_FILE)

# CPCB pollutants required for a complete AQI comparison
required_pollutants = [
    "PM25",
    "PM10",
    "NO2",
    "O3_8H"
]

# ---------------------------------------------------
# 1. Count how many real CPCB pollutants are available
# ---------------------------------------------------

df["CPCB_REFERENCE_COUNT"] = (
    df[required_pollutants]
    .notna()
    .sum(axis=1)
)

# ---------------------------------------------------
# 2. Mark FULL vs PARTIAL CPCB reference
# ---------------------------------------------------

df["CPCB_REFERENCE_STATUS"] = df["CPCB_REFERENCE_COUNT"].apply(
    lambda x: "FULL" if x == 4 else "PARTIAL"
)

# ---------------------------------------------------
# 3. Create fair-validation flag
# ---------------------------------------------------

df["USE_FOR_FULL_AQI_VALIDATION"] = (
    df["CPCB_REFERENCE_STATUS"] == "FULL"
)

# ---------------------------------------------------
# 4. Save corrected comparison
# ---------------------------------------------------

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_FILE, index=False)

# ---------------------------------------------------
# 5. Calculate metrics using ONLY full CPCB reference
# ---------------------------------------------------

full = df[df["USE_FOR_FULL_AQI_VALIDATION"]].copy()

mae = full["AQI_ABS_ERROR"].mean()
median_error = full["AQI_ABS_ERROR"].median()

rmse = (
    ((full["AEROVISION_AQI"] - full["CPCB_AQI"]) ** 2).mean()
    ** 0.5
)

correlation = full["CPCB_AQI"].corr(
    full["AEROVISION_AQI"]
)

category_agreement = (
    full["CPCB_CATEGORY"] == full["AEROVISION_CATEGORY"]
).mean() * 100

error_over_25 = (full["AQI_ABS_ERROR"] > 25).sum()
error_over_50 = (full["AQI_ABS_ERROR"] > 50).sum()
error_over_75 = (full["AQI_ABS_ERROR"] > 75).sum()
error_over_100 = (full["AQI_ABS_ERROR"] > 100).sum()

summary = pd.DataFrame({
    "metric": [
        "Total validation rows",
        "Full CPCB reference rows",
        "Partial CPCB reference rows",
        "AQI MAE",
        "AQI Median Absolute Error",
        "AQI RMSE",
        "AQI Correlation",
        "Category Agreement (%)",
        "Error > 25",
        "Error > 50",
        "Error > 75",
        "Error > 100"
    ],
    "value": [
        len(df),
        len(full),
        len(df) - len(full),
        mae,
        median_error,
        rmse,
        correlation,
        category_agreement,
        error_over_25,
        error_over_50,
        error_over_75,
        error_over_100
    ]
})

summary.to_csv(SUMMARY_FILE, index=False)

print()
print("=" * 60)
print("AEROVISION FAIR CPCB VALIDATION")
print("=" * 60)

print(f"Total rows                 : {len(df)}")
print(f"Full CPCB reference        : {len(full)}")
print(f"Partial CPCB reference     : {len(df) - len(full)}")

print()
print("FULL-REFERENCE VALIDATION")
print("-" * 60)

print(f"AQI MAE                    : {mae:.2f}")
print(f"Median absolute error      : {median_error:.2f}")
print(f"AQI RMSE                   : {rmse:.2f}")
print(f"Correlation                : {correlation:.3f}")
print(f"Category agreement         : {category_agreement:.2f}%")

print()
print("LARGE ERRORS")
print("-" * 60)

print(f"> 25 AQI                    : {error_over_25}")
print(f"> 50 AQI                    : {error_over_50}")
print(f"> 75 AQI                    : {error_over_75}")
print(f"> 100 AQI                   : {error_over_100}")

print()
print(f"Corrected file saved:")
print(OUTPUT_FILE)

print()
print(f"Summary saved:")
print(SUMMARY_FILE)

print("=" * 60)