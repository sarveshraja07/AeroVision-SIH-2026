
AEROVISION FRONTEND ADD-ONS
===========================

Files
-----
1. aerovision-enhanced.css
2. aerovision-enhanced.js
3. aerovision-location.css
4. aerovision-location.js

Purpose
-------
These files are an add-on layer. They do not replace backend/app.py and
do not require changing /api/predict.

Integration
-----------
Add these four lines near the END of your existing index.html, immediately
before </body>:

<link rel="stylesheet" href="/static/aerovision-enhanced.css">
<link rel="stylesheet" href="/static/aerovision-location.css">
<script src="/static/aerovision-enhanced.js"></script>
<script src="/static/aerovision-location.js"></script>

IMPORTANT:
If your Flask static URL is different, use the same URL pattern your existing
index.html uses for landing.css / landing.js.

Map integration
---------------
The enhancement tries, in order:
window.map
window.aqiMap
window.dashboardMap
window.leafletMap

If your existing Leaflet map is stored under another variable, add this line
BEFORE aerovision-enhanced.js:

<script>
window.AeroVisionMap = YOUR_EXISTING_MAP_VARIABLE;
</script>

The enhancement then attaches a click handler to the existing Leaflet map.

Backend
-------
No backend changes are required.

Location click:
POST /api/predict
{
  "latitude": <clicked latitude>,
  "longitude": <clicked longitude>,
  "date": <date>
}

Locate Me:
Uses browser geolocation, then calls the same existing /api/predict route.

Data exports
------------
The script attempts to read these existing project exports if available:
- /data/exports/dashboard_june_2026.json
- /data/exports/validation_summary.json
- /data/exports/cpcb_comparison.geojson
- /data/exports/aqi_surface_2026_06_08.geojson

If your actual exports use different names, change only the candidates array
inside aerovision-enhanced.js.

Safety
------
This layer is additive. It does not delete or rewrite existing DOM sections.
The old landing/map/backend files remain in place.
