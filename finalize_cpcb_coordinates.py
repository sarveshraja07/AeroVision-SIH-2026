import pandas as pd
from pathlib import Path

src = Path(r"E:\AeroVision-CPCB-2026\05_station_metadata\CPCB_COORDINATE_LOOKUP_CCR_MATCHED.csv")
out = Path(r"E:\AeroVision-CPCB-2026\05_station_metadata\CPCB_COORDINATE_LOOKUP_FINAL.csv")

df = pd.read_csv(src, dtype={"site_id": str})

df["coordinate_source"] = df["coordinate_source"].astype("string")
df["coordinate_status"] = df["coordinate_status"].astype("string")

kerala = {
    "KERALA_ELOOR":              (10.073232, 76.302765, "site_5105"),
    "KERALA_ERNAKULAM":          (9.985653, 76.281342, "site_5272"),
    "KERALA_KANNUR":             (11.875, 75.3732, "site_5276"),
    "KERALA_KOCHI":              (9.969447, 76.321186, "site_5270"),
    "KERALA_KOLLAM":             (8.8787, 76.6073, "site_5334"),
    "KERALA_KOZHIKODE":          (11.249077, 75.784371, "site_5271"),
    "KERALA_THRISSUR":           (10.5324, 76.2159, "site_5390"),
    "KERALA_TRIVANDRUM_1":       (8.5149093, 76.9435879, "site_252"),
    "KERALA_TRIVANDRUM_2":       (8.5637, 76.8865, "site_5331"),
}

matched = 0

for sid, (lat, lon, ccr_id) in kerala.items():
    mask = df["site_id"].eq(sid)

    if mask.sum() != 1:
        raise ValueError(f"{sid}: expected exactly 1 row, found {mask.sum()}")

    df.loc[mask, "latitude"] = lat
    df.loc[mask, "longitude"] = lon
    df.loc[mask, "coordinate_source"] = "CPCB CCR Continuous Stations"
    df.loc[mask, "coordinate_status"] = f"KERALA_SOURCE_MATCH_{ccr_id}"

    matched += 1

df.to_csv(out, index=False)

coords = df["latitude"].notna() & df["longitude"].notna()

print("TOTAL STATIONS:", len(df))
print("EXACT NUMERIC ID MATCHES:", (df["coordinate_status"] == "EXACT_SITE_ID_MATCH").sum())
print("KERALA SOURCE MATCHES:", matched)
print("WITH COORDINATES:", int(coords.sum()))
print("MISSING COORDINATES:", int((~coords).sum()))
print("UNIQUE SITE IDs:", df["site_id"].nunique())
print("OUTPUT:", out)

print("\nKERALA FINAL:")
print(
    df[df["site_id"].str.startswith("KERALA_")][
        ["site_id", "station_location_text", "latitude", "longitude", "coordinate_status"]
    ].to_string(index=False)
)
