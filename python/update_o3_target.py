import os
import pandas as pd

BASE = r"E:\AeroVision-Real"

ML_FILE = os.path.join(
    BASE,
    "data",
    "processed",
    "final_ml_dataset_v2.csv"
)

O3_FILE = os.path.join(
    BASE,
    "data",
    "processed",
    "cpcb_o3_8h_daily.csv"
)

OUTPUT = os.path.join(
    BASE,
    "data",
    "processed",
    "final_ml_dataset_v3.csv"
)

ml = pd.read_csv(ML_FILE)
o3 = pd.read_csv(O3_FILE)

ml["station"] = ml["station"].astype(str).str.strip().str.lower()
o3["station"] = o3["station"].astype(str).str.strip().str.lower()

ml["date_text"] = pd.to_datetime(ml["date_text"]).dt.strftime("%Y-%m-%d")
o3["date"] = pd.to_datetime(o3["date"]).dt.strftime("%Y-%m-%d")

o3 = o3.rename(columns={
    "date": "date_text",
    "O3_8H_MAX": "O3_8H"
})

# Remove old daily-mean O3
if "O3" in ml.columns:
    ml = ml.drop(columns=["O3"])

ml = ml.merge(
    o3[
        [
            "station",
            "date_text",
            "O3_8H",
            "O3_VALID_HOURS"
        ]
    ],
    on=["station", "date_text"],
    how="left",
    validate="one_to_one"
)

ml.to_csv(
    OUTPUT,
    index=False
)

print("=" * 60)
print("O3 TARGET UPDATED")
print("=" * 60)

print("Rows:", len(ml))
print("Valid O3 8H:", ml["O3_8H"].notna().sum())
print("Missing O3 8H:", ml["O3_8H"].isna().sum())

print("\nSaved:")
print(OUTPUT)

print("=" * 60)