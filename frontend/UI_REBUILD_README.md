# AeroVision UI rebuild — reference-first + backend-first

This rebuild replaces the generic single-page dashboard with separate, real routes while keeping the original Flask backend and exported data.

## Pages
- `/index.html` — Dashboard
- `/aqi-map.html` — full-screen AQI Map
- `/hcho.html` — HCHO Hotspots
- `/analytics.html` — Analytics
- `/stations.html` — Continuous Stations
- `/history.html` — Historical AQI
- `/pollutant.html?pollutant=PM25` — pollutant detail (PM25 / PM10 / NO2 / O3_8H / CO / SO2)

## Design system
The UI follows the provided references: dark monitoring-dashboard header, AQI pill navigation, large rounded hero card, map-first pages, compact CPCB-style analytics/table blocks, semantic AQI colors, floating lower navigation, and a working dark/light switch.

## Backend sync
The UI reads the real exports from `/data/exports/` and the existing `/api/status` + `/api/predict` endpoints. The dashboard explicitly avoids inventing CO/SO2 values because they are not present in `dashboard_june_2026.json`.

## Run
From the repository root:

```bash
pip install -r requirements.txt
python backend/app.py
```
Then open `http://127.0.0.1:5000/`.

The `frontend/index_legacy_backup.html` file is the previous entrance page saved as a rollback copy.
