import json
import pandas as pd
import re

official = json.load(open("cpcb_official_stations.json", encoding="utf-8"))

local = pd.read_csv(
    r"E:\AeroVision-CPCB-2026\05_station_metadata\CPCB_COORDINATE_LOOKUP.csv",
    dtype={"site_id": str}
)

def official_id(x):
    x = str(x).strip()
    m = re.fullmatch(r"site_(\d+)", x, re.I)
    return m.group(1) if m else x

official_ids = {official_id(x["station_id"]) for x in official}
local_ids = set(local["site_id"].astype(str).str.strip())

matched = local_ids & official_ids
missing = local_ids - official_ids

numeric_local = {x for x in local_ids if x.isdigit()}
numeric_matched = numeric_local & official_ids

print("OFFICIAL CPCB STATIONS:", len(official_ids))
print("OUR 2026 STATIONS:", len(local_ids))
print("DIRECT ID MATCHES:", len(matched))
print("NUMERIC STATIONS IN OUR DATA:", len(numeric_local))
print("NUMERIC ID MATCHES:", len(numeric_matched))
print("UNMATCHED TOTAL:", len(missing))

print("\nFIRST 20 UNMATCHED:")
for x in sorted(missing)[:20]:
    print(x)
