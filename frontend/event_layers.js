// ============================================================
// AEROVISION INDIA
// REAL EVENT LAYERS
//
// HCHO HOTSPOTS + FIRMS FIRE + ERA5 WIND
// Event: 08 June 2026
// ============================================================

console.log("AeroVision event layers loading...");


// ============================================================
// 1. EVENT LAYER GROUPS
// ============================================================

var hchoLayer = L.layerGroup();
var fireLayer = L.layerGroup();
var windLayer = L.layerGroup();


// ============================================================
// 2. HCHO HOTSPOTS
// ============================================================

fetch('/data/exports/hcho_hotspots_event.geojson')
  .then(response => response.json())
  .then(data => {

    L.geoJSON(data, {

      pointToLayer: function(feature, latlng) {

        var hcho = feature.properties.HCHO;
        var assoc = feature.properties.HCHO_FIRE_ASSOC;

        var color = assoc === 1
          ? "#ffffff"
          : "#ff00ff";

        return L.circleMarker(latlng, {

          radius: 4,
          color: color,
          fillColor: color,
          fillOpacity: 0.75,
          weight: 1

        });

      },

      onEachFeature: function(feature, layer) {

        var hcho = feature.properties.HCHO;
        var assoc = feature.properties.HCHO_FIRE_ASSOC;

        var relation = assoc === 1
          ? "Within 25 km of detected fire"
          : "No nearby fire within 25 km";

        layer.bindPopup(

          "<b>🛰️ TROPOMI HCHO Hotspot</b><br>" +

          "Date: 08 June 2026<br>" +

          "HCHO: " +
          Number(hcho).toExponential(3) +
          " mol/m²<br>" +

          "<b>Fire relationship:</b><br>" +
          relation

        );

      }

    }).addTo(hchoLayer);


    console.log(
      "✅ Real HCHO hotspots loaded"
    );

  })
  .catch(error => {

    console.error(
      "HCHO load error:",
      error
    );

  });


// ============================================================
// 3. FIRMS FIRES
// ============================================================

Papa.parse(
  '/data/exports/fire_event.csv',
  {

    download: true,
    header: true,

    complete: function(results) {

      results.data.forEach(function(row) {

        var lat = parseFloat(
          row.latitude
        );

        var lon = parseFloat(
          row.longitude
        );

        var confidence = parseFloat(
          row.confidence
        );

        var temperature = parseFloat(
          row.temperature
        );


        if (
          !isNaN(lat) &&
          !isNaN(lon)
        ) {

          var radius = 5;

          if (!isNaN(confidence)) {

            radius =
              4 +
              (confidence / 100) * 5;

          }


          var marker = L.circleMarker(

            [lat, lon],

            {

              radius: radius,

              color: "#ff4500",

              fillColor: "#ff0000",

              fillOpacity: 0.85,

              weight: 1

            }

          );


          var popup =

            "<b>🔥 FIRMS Fire Detection</b><br>" +

            "Date: 08 June 2026<br>";


          if (!isNaN(confidence)) {

            popup +=
              "Confidence: " +
              confidence.toFixed(0) +
              "%<br>";

          }


          if (!isNaN(temperature)) {

            popup +=
              "Brightness Temp: " +
              temperature.toFixed(1) +
              " K";

          }


          marker.bindPopup(
            popup
          );


          marker.addTo(
            fireLayer
          );

        }

      });


      console.log(
        "✅ Real FIRMS fires loaded:",
        fireLayer.getLayers().length
      );

    }

  }
);


// ============================================================
// 4. REAL ERA5 WIND
// ============================================================

Papa.parse(
  '/data/exports/wind_event.csv',
  {

    download: true,
    header: true,

    complete: function(results) {

      results.data.forEach(function(row) {

        var lat = parseFloat(
          row.latitude
        );

        var lon = parseFloat(
          row.longitude
        );

        var u = parseFloat(
          row.u
        );

        var v = parseFloat(
          row.v
        );

        var speed = parseFloat(
          row.speed
        );


        if (
          !isNaN(lat) &&
          !isNaN(lon) &&
          !isNaN(u) &&
          !isNaN(v)
        ) {

          // Mathematical vector angle
          var angle =
            Math.atan2(v, u) *
            180 /
            Math.PI;


          var arrowIcon = L.divIcon({

            className:
              'aerovision-wind-arrow',

            html:

              '<div style="' +

              'transform:rotate(' +
              angle +
              'deg);' +

              'font-size:18px;' +

              'color:#00e5ff;' +

              'font-weight:bold;' +

              'text-shadow:' +
              '0 0 4px #000;' +

              '">' +

              '➤' +

              '</div>',

            iconSize: [24, 24],

            iconAnchor: [12, 12]

          });


          var marker = L.marker(

            [lat, lon],

            {
              icon: arrowIcon
            }

          );


          marker.bindPopup(

            "<b>💨 ERA5 Wind</b><br>" +

            "Date: 08 June 2026<br>" +

            "U: " +
            u.toFixed(2) +
            " m/s<br>" +

            "V: " +
            v.toFixed(2) +
            " m/s<br>" +

            "Speed: " +
            speed.toFixed(2) +
            " m/s"

          );


          marker.addTo(
            windLayer
          );

        }

      });


      console.log(
        "✅ Real ERA5 wind loaded:",
        windLayer.getLayers().length
      );

    }

  }
);


// ============================================================
// 5. ADD LAYERS TO GLOBAL DICTIONARY
// ============================================================

layerDict['hchoHotspots'] =
  hchoLayer;

layerDict['fire'] =
  fireLayer;

layerDict['wind'] =
  windLayer;


// ============================================================
// 6. DEFAULT DISPLAY
// ============================================================

// HCHO visible initially

hchoLayer.addTo(map);


// Fire visible initially

fireLayer.addTo(map);


// Wind visible initially

windLayer.addTo(map);


console.log(
  "✅ AeroVision real event layers initialized"
);