import json
import pandas as pd
import re
from pathlib import Path

src = Path(r"E:\AeroVision-CPCB-2026\05_station_metadata\CPCB_COORDINATE_LOOKUP.csv")
out = Path(r"E:\AeroVision-CPCB-2026\05_station_metadata\CPCB_COORDINATE_LOOKUP_CCR_MATCHED.csv")

local = pd.read_csv(src, dtype={"site_id": str})
local["coordinate_source"] = local["coordinate_source"].astype("string")
local["coordinate_status"] = local["coordinate_status"].astype("string")

with open("cpcb_official_stations.json", encoding="utf-8") as f:
    official = json.load(f)

records = {}

for x in official:
    sid = str(x.get("station_id", "")).strip()

    m = re.fullmatch(r"site_(\d+)", sid, re.I)
    if not m:
        continue

    records[m.group(1)] = x

matched = 0

for i, row in local.iterrows():
    sid = str(row["site_id"]).strip()

    if sid not in records:
        continue

    x = records[sid]

    local.at[i, "latitude"] = x["latitude"]
    local.at[i, "longitude"] = x["longitude"]
    local.at[i, "coordinate_source"] = "CPCB CCR Continuous Stations"
    local.at[i, "coordinate_status"] = "EXACT_SITE_ID_MATCH"

    matched += 1

local.to_csv(out, index=False)

both = local["latitude"].notna() & local["longitude"].notna()

print("INPUT ROWS:", len(local))
print("EXACT CPCB ID MATCHES:", matched)
print("COORDINATES FILLED:", int(both.sum()))
print("STILL MISSING:", int((~both).sum()))
print("OUTPUT:", out)

print("\nMISSING STATIONS:")
print(
    local.loc[
        ~both,
        ["site_id", "station_location_text", "state_folder"]
    ].to_string(index=False)
)
