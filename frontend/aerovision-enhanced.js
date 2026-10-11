
/* ============================================================
   AEROVISION FRONTEND ENHANCEMENT
   Add-on JS. Designed to coexist with the existing frontend.
   Does NOT modify backend routes.
   ============================================================ */

(() => {
  "use strict";

  const AV = {
    state: {
      theme: localStorage.getItem("aerovision-theme") || "light",
      location: null,
      prediction: null,
      date: new Date().toISOString().slice(0, 10),
      map: null,
      chartValues: []
    },

    async json(url, options = {}) {
      try {
        const r = await fetch(url, options);
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        return await r.json();
      } catch (e) {
        console.warn("[AeroVision] request failed:", url, e);
        return null;
      }
    },

    esc(v) {
      return String(v ?? "").replace(/[&<>"']/g, c => ({
        "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
      }[c]));
    },

    num(v, digits = 1) {
      const n = Number(v);
      if (!Number.isFinite(n)) return "—";
      return n.toFixed(digits).replace(/\.0+$/, "");
    },

    aqiClass(aqi) {
      const n = Number(aqi);
      if (!Number.isFinite(n)) return "av-moderate";
      if (n <= 50) return "av-good";
      if (n <= 100) return "av-moderate";
      if (n <= 150) return "av-poor";
      if (n <= 200) return "av-unhealthy";
      return "av-hazardous";
    },

    aqiText(aqi) {
      const n = Number(aqi);
      if (!Number.isFinite(n)) return "Unknown";
      if (n <= 50) return "Good";
      if (n <= 100) return "Moderate";
      if (n <= 150) return "Poor";
      if (n <= 200) return "Unhealthy";
      return "Hazardous";
    },

    extractPredictionValue(obj, keys) {
      if (!obj || typeof obj !== "object") return null;
      for (const key of keys) {
        if (obj[key] !== undefined && obj[key] !== null) return obj[key];
        if (obj.prediction && obj.prediction[key] !== undefined) return obj.prediction[key];
        if (obj.features && obj.features[key] !== undefined) return obj.features[key];
        if (obj.environmental_features && obj.environmental_features[key] !== undefined) {
          return obj.environmental_features[key];
        }
      }
      return null;
    },

   applyTheme() {
    const isDark = AV.state.theme === "dark";

    document.body.classList.toggle("av-enhanced", true);
    document.body.classList.toggle("av-dark", isDark);
    document.documentElement.classList.toggle("av-dark", isDark);

    const themeBtn = document.querySelector("#avx-theme-toggle");

    if (themeBtn) {
        themeBtn.textContent = isDark ? "☀ Light" : "🌙 Dark";
        themeBtn.setAttribute(
            "aria-label",
            isDark ? "Switch to light mode" : "Switch to dark mode"
        );
    }

    /*
     * The existing AeroVision UI contains many components whose
     * original CSS uses hard-coded white backgrounds and dark text.
     *
     * Mark those components so the add-on theme can override them
     * without changing the original HTML or backend.
     */

    document.querySelectorAll(
        `
        .card,
        .card-body,
        .panel,
        .panel-card,
        .widget,
        .widget-card,
        .info-card,
        .stat-card,
        .metric-card,
        .data-card,
        .content-card,
        .weather-card,
        .weather-panel,
        .aqi-card,
        .aqi-panel,
        .pollutant-card,
        .pollutant-item,
        .pollutant-box,
        .rank-card,
        .ranking-card,
        .station-card,
        .station-panel,
        .environment-card,
        .environment-item,
        .validation-card,
        .chart-card,
        .chart-container,
        .timeline-chart,
        .source-card,
        .info-panel,
        .location-panel,
        .selected-location,
        .map-info-panel
        `
    ).forEach(element => {
        element.classList.toggle("av-theme-surface", isDark);
    });

    /*
     * Theme common white/light surfaces.
     */
    document.querySelectorAll(
        `
        .aqi-hero,
        .hero-card,
        .hero-panel,
        .hero-weather,
        .hero-metrics,
        .weather,
        .weather-box,
        .city-rank,
        .city-ranking,
        .rank-box,
        .pollutants,
        .pollutant-grid,
        .environment-grid,
        .environment-intelligence
        `
    ).forEach(element => {
        element.classList.toggle("av-theme-surface", isDark);
    });

    /*
     * Do not theme Leaflet tiles/images/canvas.
     */
    document.querySelectorAll(
        "img, canvas, svg, .leaflet-container, .leaflet-container *"
    ).forEach(element => {
        element.classList.remove("av-theme-surface");
    });
},

    toggleTheme() {
      AV.state.theme = AV.state.theme === "dark" ? "light" : "dark";
      localStorage.setItem("aerovision-theme", AV.state.theme);
      AV.applyTheme();
    },

    locateMe() {
      if (!navigator.geolocation) {
        alert("Location is not supported by this browser.");
        return;
      }

      const btn = document.querySelector("#avx-locate");
      if (btn) {
        btn.disabled = true;
        btn.textContent = "Locating…";
      }

      navigator.geolocation.getCurrentPosition(
        async pos => {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          AV.state.location = { lat, lon };

          if (AV.state.map && typeof AV.state.map.setView === "function") {
            AV.state.map.setView([lat, lon], Math.max(AV.state.map.getZoom?.() || 8, 11));
            if (window.L) {
              if (AV.state.userMarker) AV.state.userMarker.remove();
              AV.state.userMarker = L.circleMarker([lat, lon], {
                radius: 8,
                weight: 3,
                color: "#176fd2",
                fillColor: "#4bb1ff",
                fillOpacity: .9
              }).addTo(AV.state.map).bindTooltip("Your location");
            }
          }

          await AV.loadPrediction(lat, lon);
          if (btn) {
            btn.disabled = false;
            btn.textContent = "⌖ Locate me";
          }
        },
        err => {
          console.warn("[AeroVision] geolocation:", err);
          alert("Unable to get your location. Please allow location access in the browser.");
          if (btn) {
            btn.disabled = false;
            btn.textContent = "⌖ Locate me";
          }
        },
        { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 }
      );
    },

    async loadPrediction(lat, lon, date = AV.state.date) {
      const panel = document.querySelector("#avx-location-info");
      if (panel) {
        panel.querySelector(".avx-map-loading")?.remove();
        const load = document.createElement("div");
        load.className = "avx-map-loading";
        load.textContent = "Loading AeroVision prediction…";
        panel.appendChild(load);
      }

      const data = await AV.json("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ latitude: lat, longitude: lon, date })
      });

      if (!data) {
        if (panel) {
          const load = panel.querySelector(".avx-map-loading");
          if (load) load.textContent = "Prediction unavailable for this location/date.";
        }
        return null;
      }

      AV.state.prediction = data;
      AV.renderPrediction(data, lat, lon);
      return data;
    },

    renderPrediction(data, lat, lon) {
      const panel = document.querySelector("#avx-location-info");
      if (!panel) return;

      const aqi = AV.extractPredictionValue(data, ["AQI", "aqi", "predicted_aqi", "aqi_us"]);
      const pm25 = AV.extractPredictionValue(data, ["PM2.5", "pm25", "PM25", "pm2_5"]);
      const pm10 = AV.extractPredictionValue(data, ["PM10", "pm10"]);
      const no2 = AV.extractPredictionValue(data, ["NO2", "NO₂", "no2"]);
      const hcho = AV.extractPredictionValue(data, ["HCHO", "hcho", "HCHO_mol_m2"]);
      const temp = AV.extractPredictionValue(data, ["temperature", "Temperature", "temp"]);
      const humidity = AV.extractPredictionValue(data, ["humidity", "Humidity"]);

      panel.innerHTML = `
        <div class="avx-kicker">● Selected location</div>
        <h3>AeroVision environmental view</h3>
        <div class="avx-coords">${AV.num(lat,5)}°, ${AV.num(lon,5)}° · ${AV.esc(AV.state.date)}</div>
        <div style="margin-top:14px">
          <span class="avx-aqi-badge ${AV.aqiClass(aqi)}">${AV.aqiText(aqi)}</span>
          <strong style="font-size:38px;margin-left:10px">${AV.num(aqi,0)}</strong>
        </div>
        <div class="avx-detail-grid">
          <div class="avx-detail"><div class="avx-detail-label">PM2.5</div><div class="avx-detail-value">${AV.num(pm25,2)}</div></div>
          <div class="avx-detail"><div class="avx-detail-label">PM10</div><div class="avx-detail-value">${AV.num(pm10,2)}</div></div>
          <div class="avx-detail"><div class="avx-detail-label">NO₂</div><div class="avx-detail-value">${AV.num(no2,5)}</div></div>
          <div class="avx-detail"><div class="avx-detail-label">HCHO</div><div class="avx-detail-value">${AV.num(hcho,7)}</div></div>
          <div class="avx-detail"><div class="avx-detail-label">Temperature</div><div class="avx-detail-value">${AV.num(temp,1)}</div></div>
          <div class="avx-detail"><div class="avx-detail-label">Humidity</div><div class="avx-detail-value">${AV.num(humidity,1)}</div></div>
        </div>
      `;
    },

    buildShell() {
      if (document.querySelector("#avx-shell")) return;

      const shell = document.createElement("div");
      shell.id = "avx-shell";

      shell.innerHTML = `
        <header class="avx-topbar">
          <div class="avx-brand">
            <div class="avx-brand-mark">AQ</div>
            <span>AeroVision India</span>
          </div>
          <nav class="avx-nav">
            <button class="avx-btn" id="avx-theme-toggle">◐ Dark</button>
            <button class="avx-btn avx-btn-primary" id="avx-locate">⌖ Locate me</button>
            <button class="avx-btn" onclick="document.querySelector('#avx-map-section')?.scrollIntoView({behavior:'smooth'})">Map</button>
          </nav>
        </header>

        <section class="avx-hero" aria-label="AeroVision overview">
          <div class="avx-hero-copy">
            <div class="avx-kicker">◉ REAL ENVIRONMENTAL INTELLIGENCE</div>
            <h1 class="avx-title">See the air.<br>Understand the event.</h1>
            <p class="avx-subtitle">
              Satellite observations, CPCB measurements and environmental signals
              brought together in one interactive AeroVision view.
            </p>
            <div class="avx-aqi-row">
              <div class="avx-aqi-number" id="avx-hero-aqi">—</div>
              <div class="avx-aqi-status" id="avx-hero-status">Loading</div>
            </div>
            <div class="avx-pollutant-strip">
              <div class="avx-mini"><div class="avx-mini-label">PM2.5</div><div class="avx-mini-value" id="avx-pm25">—</div></div>
              <div class="avx-mini"><div class="avx-mini-label">PM10</div><div class="avx-mini-value" id="avx-pm10">—</div></div>
              <div class="avx-mini"><div class="avx-mini-label">NO₂</div><div class="avx-mini-value" id="avx-no2">—</div></div>
              <div class="avx-mini"><div class="avx-mini-label">HCHO</div><div class="avx-mini-value" id="avx-hcho">—</div></div>
            </div>
          </div>

          <div class="avx-character-zone">
            <div class="avx-character-card">
              <div class="avx-boy" aria-label="Animated AeroVision character">
                <div class="avx-hair"></div>
                <div class="avx-head">
                  <span class="avx-eye left"></span>
                  <span class="avx-eye right"></span>
                  <span class="avx-mouth"></span>
                </div>
                <div class="avx-body"></div>
                <div class="avx-arm left"></div>
                <div class="avx-arm right"></div>
                <div class="avx-leg left"></div>
                <div class="avx-leg right"></div>
              </div>
            </div>
          </div>
        </section>

        <section class="avx-section" id="avx-graph-section">
          <div class="avx-section-head">
            <div>
              <h2>Air Quality Trend</h2>
              <p>Use your existing exported data when available.</p>
            </div>
          </div>
          <div class="avx-chart-wrap" id="avx-chart-wrap">
            <div class="avx-chart-empty">Loading existing AeroVision data…</div>
          </div>
        </section>

        <section class="avx-section">
          <div class="avx-section-head">
            <div>
              <h2>Indian Cities</h2>
              <p>Real records are used when an existing export is available.</p>
            </div>
          </div>
          <div class="avx-grid" id="avx-cities"></div>
        </section>

        <section class="avx-section">
          <div class="avx-section-head">
            <div>
              <h2>Stations</h2>
              <p>Station-level observations from your existing data.</p>
            </div>
          </div>
          <div class="avx-stations" id="avx-stations"></div>
        </section>

        <section class="avx-map-shell" id="avx-map-section">
          <div class="avx-map-host" id="avx-map-host">
            <div class="avx-map-placeholder">
              <div>
                <strong>Existing AeroVision map</strong><br>
                The enhancement will attach to your existing Leaflet map when it is available.
              </div>
            </div>
          </div>
          <aside class="avx-map-info" id="avx-location-info">
            <div class="avx-kicker">⌖ Map interaction</div>
            <h3>Click a location</h3>
            <div class="avx-coords">Select a point on the existing map to see the location here.</div>
          </aside>
        </section>
      `;

      document.body.insertBefore(shell, document.body.firstChild);
      document.body.classList.add("av-enhanced");

      document.querySelector("#avx-theme-toggle").addEventListener("click", AV.toggleTheme);
      document.querySelector("#avx-locate").addEventListener("click", AV.locateMe);

      AV.applyTheme();
    },

    async loadExistingExports() {
      const candidates = [
        "/data/exports/dashboard_june_2026.json",
        "/data/exports/validation_summary.json",
        "/data/exports/cpcb_comparison.geojson",
        "/data/exports/aqi_surface_2026_06_08.geojson"
      ];

      let first = null;
      for (const url of candidates) {
        const data = await AV.json(url);
        if (data) {
          first = first || data;
          AV.consumeData(data);
        }
      }

      if (!first) {
        AV.renderFallbackStructure();
      }
    },

    consumeData(data) {
      const rows = [];

      const walk = (obj, keyHint = "") => {
        if (!obj) return;
        if (Array.isArray(obj)) {
          for (const x of obj) walk(x, keyHint);
          return;
        }
        if (typeof obj !== "object") return;

        const hasAQI = ["aqi","AQI","aqi_us","AQI_US"].some(k => obj[k] !== undefined);
        const hasStation = ["station","station_name","site_id","location","name"].some(k => obj[k] !== undefined);

        if (hasAQI || hasStation) rows.push(obj);

        for (const [k,v] of Object.entries(obj)) {
          if (v && typeof v === "object") walk(v, k);
        }
      };

      walk(data);

      if (rows.length) {
        AV.renderStations(rows);
        AV.renderCities(rows);
        AV.renderChart(rows);
      }
    },

    renderFallbackStructure() {
      const cities = document.querySelector("#avx-cities");
      const stations = document.querySelector("#avx-stations");
      const chart = document.querySelector("#avx-chart-wrap");

      if (cities) {
        cities.innerHTML = `
          <div class="avx-card"><div class="avx-card-title">CPCB network</div><div class="avx-card-meta">Station data remains available through your existing system.</div></div>
          <div class="avx-card"><div class="avx-card-title">Satellite</div><div class="avx-card-meta">HCHO, NO₂ and AOD layers remain connected to the existing project.</div></div>
          <div class="avx-card"><div class="avx-card-title">Meteorology</div><div class="avx-card-meta">ERA5 and fire context remain handled by the existing backend.</div></div>
        `;
      }

      if (stations) stations.innerHTML = `
        <table class="avx-table">
          <thead><tr><th>Station</th><th>Status</th><th>AQI</th><th>PM2.5</th><th>PM10</th></tr></thead>
          <tbody><tr><td colspan="5">Connect this section to an existing station export to populate real records.</td></tr></tbody>
        </table>`;

      if (chart) chart.innerHTML = `<div class="avx-chart-empty">No compatible existing export was found for the trend chart.</div>`;
    },

    renderStations(rows) {
      const host = document.querySelector("#avx-stations");
      if (!host) return;

      const usable = rows.filter(r =>
        ["station","station_name","site_id","location","name"].some(k => r[k] != null)
      ).slice(0, 100);

      if (!usable.length) return;

      const val = (r, keys) => {
        for (const k of keys) if (r[k] != null) return r[k];
        return "—";
      };

      host.innerHTML = `
        <table class="avx-table">
          <thead>
            <tr><th>Station / Location</th><th>Status</th><th>AQI</th><th>PM2.5</th><th>PM10</th><th>Temperature</th></tr>
          </thead>
          <tbody>
            ${usable.map(r => {
              const aqi = val(r, ["aqi","AQI","aqi_us","AQI_US"]);
              return `<tr>
                <td>${AV.esc(val(r,["station_name","station","location","name","site_id"]))}</td>
                <td><span class="avx-aqi-badge ${AV.aqiClass(aqi)}">${AV.aqiText(aqi)}</span></td>
                <td><strong>${AV.esc(aqi)}</strong></td>
                <td>${AV.esc(val(r,["pm25","PM25","PM2.5","PM2_5"]))}</td>
                <td>${AV.esc(val(r,["pm10","PM10"]))}</td>
                <td>${AV.esc(val(r,["temperature","Temperature","temp"]))}</td>
              </tr>`;
            }).join("")}
          </tbody>
        </table>`;
    },

    renderCities(rows) {
      const host = document.querySelector("#avx-cities");
      if (!host) return;

      const cityMap = new Map();

      for (const r of rows) {
        const name = r.city || r.city_name || r.state || r.station_name || r.location;
        if (!name) continue;
        const aqi = AV.extractPredictionValue(r, ["aqi","AQI","aqi_us","AQI_US"]);
        if (!cityMap.has(name)) cityMap.set(name, {name, aqi});
      }

      const cities = [...cityMap.values()].slice(0, 9);
      if (!cities.length) return;

      host.innerHTML = cities.map(c => `
        <div class="avx-card">
          <div class="avx-card-title">${AV.esc(c.name)}</div>
          <div class="avx-card-value">${AV.esc(c.aqi ?? "—")}</div>
          <div class="avx-card-meta">${AV.aqiText(c.aqi)} · AQI</div>
        </div>
      `).join("");
    },

    renderChart(rows) {
      const host = document.querySelector("#avx-chart-wrap");
      if (!host) return;

      const vals = rows.map(r => Number(AV.extractPredictionValue(r, ["aqi","AQI","aqi_us","AQI_US"])))
        .filter(Number.isFinite)
        .slice(0, 48);

      if (vals.length < 2) return;

      const w = 1100, h = 230, pad = 20;
      const max = Math.max(...vals, 100);
      const min = Math.min(...vals, 0);
      const span = Math.max(max - min, 1);

      const pts = vals.map((v,i) => {
        const x = pad + i * ((w - pad*2) / (vals.length-1));
        const y = h-pad - ((v-min)/span)*(h-pad*2);
        return `${x},${y}`;
      }).join(" ");

      host.innerHTML = `
        <svg class="avx-chart" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-label="AQI trend">
          <line x1="${pad}" y1="${h-pad}" x2="${w-pad}" y2="${h-pad}" stroke="currentColor" opacity=".12"/>
          <line x1="${pad}" y1="${pad}" x2="${pad}" y2="${h-pad}" stroke="currentColor" opacity=".12"/>
          <polyline points="${pts}" fill="none" stroke="#ef9c2f" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
          <polyline points="${pts}" fill="none" stroke="#f4c52b" stroke-width="10" opacity=".08"/>
        </svg>
      `;
    },

    attachToExistingLeafletMap() {
      if (!window.L) return false;

      // Try common names first.
      const possible = [
        window.map,
        window.aqiMap,
        window.dashboardMap,
        window.leafletMap
      ];

      let map = possible.find(x => x && typeof x.on === "function");

      // If the existing app exposes a Leaflet map but not globally, find
      // the map container and use the Leaflet DOM relationship when possible.
      if (!map) {
        const container = document.querySelector(".leaflet-container");
        if (container && container._leaflet_map) map = container._leaflet_map;
      }

      if (!map) return false;

      AV.state.map = map;

      map.on("click", async e => {
        const lat = e.latlng.lat;
        const lon = e.latlng.lng;
        AV.state.location = { lat, lon };

        if (window.L) {
          if (AV.state.clickMarker) AV.state.clickMarker.remove();
          AV.state.clickMarker = L.circleMarker([lat, lon], {
            radius: 7,
            weight: 2,
            color: "#176fd2",
            fillColor: "#4bb1ff",
            fillOpacity: .95
          }).addTo(map);
        }

        await AV.loadPrediction(lat, lon);
      });

      return true;
    },

    async boot() {
      //AV.buildShell();
      await AV.loadExistingExports();
      const themeBtn = document.querySelector("#avx-theme-toggle");
if (themeBtn) {
  themeBtn.addEventListener("click", AV.toggleTheme);
}

const locateBtn = document.querySelector("#avx-locate");
if (locateBtn) {
  locateBtn.addEventListener("click", AV.locateMe);
}

AV.applyTheme();

      // Give the existing page's scripts time to create its Leaflet map.
      let tries = 0;
      const timer = setInterval(() => {
        tries++;
        if (AV.attachToExistingLeafletMap() || tries > 30) clearInterval(timer);
      }, 500);

      // Load a useful real default prediction only if the existing page
      // already provides a known location. Otherwise the user can Locate Me
      // or click the map.
      const status = await AV.json("/api/status");
      if (status?.default_prediction_date) AV.state.date = status.default_prediction_date;
    }
  };

  window.AeroVisionEnhancement = AV;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", AV.boot);
  } else {
    AV.boot();
  }
})();
/* =========================================================
   POLLUTANT SELECTION VISUAL SYSTEM
   ========================================================= */

(function () {

    function pollutantClass(text) {
        text = String(text || "").toUpperCase();

        if (text.includes("PM2.5") || text.includes("PM25")) {
            return "av-pollutant-pm25";
        }

        if (text.includes("PM10")) {
            return "av-pollutant-pm10";
        }

        if (text.includes("NO2") || text.includes("NO₂")) {
            return "av-pollutant-no2";
        }

        if (
            text.includes("O3") ||
            text.includes("O₃") ||
            text.includes("O3 8H") ||
            text.includes("O₃ 8H")
        ) {
            return "av-pollutant-o3";
        }

        if (text.includes("SO2") || text.includes("SO₂")) {
            return "av-pollutant-so2";
        }

        if (text.includes("CO")) {
            return "av-pollutant-co";
        }

        if (text.includes("HCHO")) {
            return "av-pollutant-hcho";
        }

        return "av-pollutant-default";
    }


    function updateSelectedPollutant() {

        /*
         * Find the currently selected parameter.
         * The page already changes this text when the user
         * clicks PM2.5 / PM10 / NO2 / O3.
         */

        const candidates = document.querySelectorAll(
            "h1, h2, h3, h4, h5, h6, .selected-parameter, .parameter-name, .pollutant-name"
        );

        let selected = "";

        candidates.forEach(el => {
            const text = el.textContent.trim();

            if (
                /PM2\.5|PM25|PM10|NO2|NO₂|O3|O₃|SO2|SO₂|CO|HCHO/i.test(text)
            ) {
                selected = text;
            }
        });

        if (!selected) return;

        const newClass = pollutantClass(selected);

        /*
         * Find likely selected-parameter surfaces.
         */

        const boxes = document.querySelectorAll(
            ".selected-parameter, " +
            ".parameter-card, " +
            ".parameter-panel, " +
            ".selected-card, " +
            ".pollutant-card, " +
            ".pollutant-panel, " +
            ".data-card"
        );

        boxes.forEach(box => {

            box.classList.remove(
                "av-pollutant-pm25",
                "av-pollutant-pm10",
                "av-pollutant-no2",
                "av-pollutant-o3",
                "av-pollutant-so2",
                "av-pollutant-co",
                "av-pollutant-hcho",
                "av-pollutant-default"
            );

            box.classList.add(newClass);
        });
    }


    /*
     * Run initially.
     */
    updateSelectedPollutant();


    /*
     * The existing page changes the selected pollutant
     * dynamically, so watch for those DOM changes.
     */

    const observer = new MutationObserver(() => {
        updateSelectedPollutant();
    });

    observer.observe(document.body, {
        subtree: true,
        childList: true,
        characterData: true
    });

})();
/* =========================================================
   AQI CATEGORY COLOUR ENGINE
   ========================================================= */

(function () {

    function getAQICategory(value) {

        value = Number(value);

        if (!Number.isFinite(value)) {
            return "aqi-moderate";
        }

        if (value <= 50) {
            return "aqi-good";
        }

        if (value <= 100) {
            return "aqi-satisfactory";
        }

        if (value <= 200) {
            return "aqi-moderate";
        }

        if (value <= 300) {
            return "aqi-poor";
        }

        if (value <= 400) {
            return "aqi-very-poor";
        }

        return "aqi-severe";
    }


    function updateAQIColours() {

        /*
         * Existing AeroVision AQI value.
         */
        const aqiElement =
            document.querySelector("#heroAeroAQI") ||
            document.querySelector(".hero-aqi") ||
            document.querySelector(".aqi-value") ||
            document.querySelector("[class*='aqi-value']");

        if (!aqiElement) return;

        const value = parseFloat(
            aqiElement.textContent.replace(/[^\d.-]/g, "")
        );

        if (!Number.isFinite(value)) return;

        const category = getAQICategory(value);

        /*
         * Apply to the actual AQI card.
         */
        const boxes = document.querySelectorAll(
            ".aqi-hero, " +
            ".aqi-card, " +
            ".aqi-panel, " +
            ".hero-aqi-card, " +
            ".hero-card"
        );

        boxes.forEach(box => {

            box.classList.remove(
                "aqi-severity-box",
                "aqi-good",
                "aqi-satisfactory",
                "aqi-moderate",
                "aqi-poor",
                "aqi-very-poor",
                "aqi-severe"
            );

            box.classList.add(
                "aqi-severity-box",
                category
            );
        });
    }


    updateAQIColours();

    /*
     * Existing page changes AQI dynamically,
     * so automatically detect those changes.
     */
    const observer = new MutationObserver(() => {
        updateAQIColours();
    });

    observer.observe(document.body, {
        subtree: true,
        childList: true,
        characterData: true
    });

})();// =====================================================
// SELECTED POLLUTANT DETAIL
// =====================================================

(function () {

    const pollutantDetail =
        document.getElementById("avxPollutantDetail");

    const pollutantName =
        document.getElementById("avxPollutantName");

    const pollutantValue =
        document.getElementById("avxPollutantValue");

    const pollutantUnit =
        document.getElementById("avxPollutantUnit");

    const pollutantCpcb =
        document.getElementById("avxPollutantCpcb");

    const pollutantAero =
        document.getElementById("avxPollutantAero");

    const pollutantCards =
        document.querySelectorAll(".pollutant-card");


    if (!pollutantDetail || !pollutantCards.length) {
        return;
    }


    const pollutantConfig = {

        PM25: {
            name: "PM2.5",
            unit: "µg/m³",
            color: "#ef4444"
        },

        PM10: {
            name: "PM10",
            unit: "µg/m³",
            color: "#f97316"
        },

        NO2: {
            name: "NO₂",
            unit: "µg/m³",
            color: "#8b5cf6"
        },

        O3: {
            name: "O₃",
            unit: "µg/m³",
            color: "#10b981"
        }

    };


    pollutantCards.forEach(function (card) {

        card.addEventListener("click", function () {

            const pollutant =
                card.dataset.pollutant;

            const config =
                pollutantConfig[pollutant];

            if (!config) {
                return;
            }


            // -----------------------------------------
            // Selected pollutant information
            // -----------------------------------------

            pollutantName.textContent =
                config.name;

            pollutantUnit.textContent =
                config.unit;


            // -----------------------------------------
            // Get values from the clicked card
            // -----------------------------------------

          const valueIds = {

    PM25: {
        cpcb: "cardPM25",
        aero: "cardPredPM25"
    },

    PM10: {
        cpcb: "cardPM10",
        aero: "cardPredPM10"
    },

    NO2: {
        cpcb: "cardNO2",
        aero: "cardPredNO2"
    },

    O3: {
        cpcb: "cardO3",
        aero: "cardPredO3"
    }

};


const ids = valueIds[pollutant];

const cpcbElement =
    ids
        ? document.getElementById(ids.cpcb)
        : null;

const aeroElement =
    ids
        ? document.getElementById(ids.aero)
        : null;


const cpcbValue =
    cpcbElement
        ? cpcbElement.textContent.trim()
        : "--";

const aeroValue =
    aeroElement
        ? aeroElement.textContent.trim()
        : "--";


pollutantValue.textContent =
    aeroValue;

pollutantCpcb.textContent =
    cpcbValue;

pollutantAero.textContent =
    aeroValue;


            // -----------------------------------------
            // Change ONLY the detail box color
            // -----------------------------------------

            pollutantDetail.style.setProperty(
                "--pollutant-color",
                config.color
            );


            // -----------------------------------------
            // Show detail box
            // -----------------------------------------

            pollutantDetail.hidden = false;


            // -----------------------------------------
            // Scroll to detail box
            // -----------------------------------------

            pollutantDetail.scrollIntoView({
                behavior: "smooth",
                block: "center"
            });
            

        });

    });
    

})();
// ============================================================
// DATA VIEW NAVIGATION
// ============================================================

document.querySelectorAll(".data-view-btn").forEach(function (button) {

    button.addEventListener("click", function () {

        const view =
            button.getAttribute("data-view");

        // -----------------------------------------
        // AQI
        // -----------------------------------------

        if (view === "AQI") {

            const target =
                document.querySelector("#aqiHero");

            if (target) {
                target.scrollIntoView({
                    behavior: "smooth",
                    block: "center"
                });
            }

            return;
        }

        // -----------------------------------------
        // HISTORY
        // -----------------------------------------

        if (view === "HISTORY") {

            const target =
                document.querySelector("#history");

            if (target) {
                target.scrollIntoView({
                    behavior: "smooth",
                    block: "center"
                });
            }

            return;
        }

        // -----------------------------------------
        // POLLUTANTS
        // -----------------------------------------

        const pollutantCard =
            document.querySelector(
                `.pollutant-card[data-pollutant="${view}"]`
            );

        if (!pollutantCard) {
            return;
        }

        // Trigger the existing pollutant logic
        pollutantCard.click();

        // Scroll to the existing selected-pollutant detail
        setTimeout(function () {

            const detail =
                document.querySelector(
                    "#avxPollutantDetail"
                );

            if (detail) {
                detail.scrollIntoView({
                    behavior: "smooth",
                    block: "center"
                });
            }

        }, 150);

    });

});